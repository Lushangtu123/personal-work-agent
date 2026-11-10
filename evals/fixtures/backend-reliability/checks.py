"""Observable synthetic contracts; policy fakes do not qualify a real HTTP client."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

import service


class ErrorChecks(unittest.TestCase):
    def test_unexpected_failure_is_not_success(self):
        failure = OSError("synthetic required storage failure")

        def broken_write():
            raise failure

        with self.assertRaises(OSError) as caught:
            service.run_job(broken_write)
        self.assertIs(caught.exception, failure)

    def test_legitimate_success_and_expected_rejection(self):
        self.assertEqual(service.run_job(lambda: "stored"), {"ok": True, "value": "stored"})

        def reject():
            raise service.ExpectedRejection("quota")

        self.assertEqual(service.run_job(reject), {"ok": False, "reason": "quota"})


class QueryChecks(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.executescript("CREATE TABLE accounts(id INTEGER PRIMARY KEY,name TEXT);"
                              "CREATE TABLE events(id INTEGER PRIMARY KEY,account_id INTEGER);")
        self.db.executemany("INSERT INTO accounts VALUES(?,?)", [(n, f"user{n}") for n in range(1, 151)])
        self.db.executemany("INSERT INTO events(account_id) VALUES(?)", [(1,), (1,), (3,)])

    def test_query_growth_and_output_are_bounded(self):
        counts = []
        for size in (1, 40):
            statements = []
            self.db.set_trace_callback(statements.append)
            rows = service.list_accounts(self.db, limit=size)
            self.db.set_trace_callback(None)
            counts.append(sum(s.lstrip().upper().startswith("SELECT") for s in statements))
            self.assertEqual([r["id"] for r in rows], list(range(1, size + 1)))
            self.assertEqual(rows[0], {"id": 1, "name": "user1", "events": 2})
            if size > 1:
                self.assertEqual(rows[1]["events"], 0)
        self.assertLessEqual(max(counts), 2, f"actual SQLite SELECT counts: {counts}")

    def test_cursor_limit_and_invalid_sizes(self):
        self.assertEqual([r["id"] for r in service.list_accounts(self.db, limit=2, after=2)], [3, 4])
        self.assertEqual(len(service.list_accounts(self.db, limit=100)), 100)
        self.assertEqual(service.list_accounts(self.db, limit=2, after=150), [])
        for size in (0, -1, 101, True):
            with self.subTest(size=size), self.assertRaises(ValueError):
                service.list_accounts(self.db, limit=size)


class ConcurrentChecks(unittest.TestCase):
    def test_two_contenders_only_one_committed_claim(self):
        with tempfile.TemporaryDirectory(prefix="pwa-race-") as folder:
            database = Path(folder) / "owned.sqlite"
            with sqlite3.connect(database) as setup:
                setup.executescript("CREATE TABLE stock(key TEXT PRIMARY KEY,stock INTEGER);"
                                    "INSERT INTO stock VALUES('one',1);")
            barrier = threading.Barrier(2, timeout=3)

            def contender():
                with sqlite3.connect(database, isolation_level=None, timeout=3) as db:
                    return service.claim(db, "one", lambda: barrier.wait())

            with ThreadPoolExecutor(max_workers=2) as pool:
                pending = [pool.submit(contender) for _ in range(2)]
                outcomes = [f.result(timeout=5) for f in pending]
            with sqlite3.connect(database) as db:
                remaining = db.execute("SELECT stock FROM stock WHERE key='one'").fetchone()[0]
                self.assertFalse(service.claim(db, "missing"))
                self.assertFalse(service.claim(db, "one"))
            self.assertEqual((outcomes.count(True), outcomes.count(False), remaining), (1, 1, 0))

    def test_uncontended_legitimate_claim(self):
        with sqlite3.connect(":memory:", isolation_level=None) as db:
            db.executescript("CREATE TABLE stock(key TEXT PRIMARY KEY,stock INTEGER);"
                             "INSERT INTO stock VALUES('one',1);")
            self.assertTrue(service.claim(db, "one"))
            self.assertFalse(service.claim(db, "one"))


class Clock:
    def __init__(self):
        self.time = 0.0
        self.waits = []

    def now(self):
        return self.time

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.time += seconds


class NetworkPolicyChecks(unittest.TestCase):
    def call(self, send, clock, **kwargs):
        return service.fetch(send, retry_safe=kwargs.pop("retry_safe", True),
                             deadline=kwargs.pop("deadline", 5), now=clock.now,
                             sleep=clock.sleep, jitter=lambda: 0.5, **kwargs)

    def test_transient_then_success_has_remaining_timeout_and_jitter(self):
        clock = Clock()
        timeouts = []

        def send(*, timeout):
            timeouts.append(timeout)
            if len(timeouts) < 3:
                raise service.TransientFailure("synthetic temporary fault")
            return "ok"

        self.assertEqual(self.call(send, clock), "ok")
        self.assertEqual(len(timeouts), 3)
        self.assertEqual(clock.waits, [0.1, 0.2])
        for actual, expected in zip(timeouts, [5, 4.9, 4.7]):
            self.assertAlmostEqual(actual, expected)

    def test_permanent_and_unsafe_mutation_do_not_retry(self):
        for error, replay_safe in ((ValueError("invalid"), True),
                                   (service.TransientFailure("outcome unknown"), False)):
            clock, calls = Clock(), []

            def send(*, timeout):
                calls.append(timeout)
                raise error

            with self.subTest(error=error), self.assertRaises(type(error)):
                self.call(send, clock, retry_safe=replay_safe)
            self.assertEqual(len(calls), 1)
            self.assertEqual(clock.waits, [])

    def test_attempt_limit_and_initial_call_count(self):
        clock, calls = Clock(), []

        def send(*, timeout):
            calls.append(timeout)
            raise service.TransientFailure("still failing")

        with self.assertRaises(service.TransientFailure):
            self.call(send, clock, max_attempts=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(clock.waits, [0.1])

    def test_elapsed_budget_and_expired_deadline(self):
        clock, calls = Clock(), []

        def send(*, timeout):
            calls.append(timeout)
            clock.time += min(3, timeout) if timeout is not None else 3
            raise service.TransientFailure("scripted slow dependency")

        with self.assertRaises((service.TransientFailure, TimeoutError)):
            self.call(send, clock)
        self.assertLessEqual(clock.time, 5)
        self.assertEqual(len(calls), 2)
        calls.clear()
        with self.assertRaises(TimeoutError):
            self.call(send, clock, deadline=clock.time)
        self.assertEqual(calls, [])

    def test_invalid_attempt_limit_is_rejected_without_call(self):
        for attempts in (0, 6, True):
            calls = []
            with self.subTest(attempts=attempts), self.assertRaises(ValueError):
                self.call(lambda **kwargs: calls.append(kwargs), Clock(), max_attempts=attempts)
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
