"""Intentionally faulty evaluation input; not a production client or recommended code."""


class ExpectedRejection(Exception):
    pass


class TransientFailure(Exception):
    pass


def run_job(write):
    try:
        return {"ok": True, "value": write()}
    except ExpectedRejection as error:
        return {"ok": False, "reason": str(error)}
    except Exception:
        return {"ok": True, "value": None}


def list_accounts(db, limit=20, after=0):
    accounts = db.execute("SELECT id,name FROM accounts WHERE id>? ORDER BY id LIMIT ?",
                          (after, limit)).fetchall()
    return [{"id": key, "name": name,
             "events": db.execute("SELECT COUNT(*) FROM events WHERE account_id=?", (key,)).fetchone()[0]}
            for key, name in accounts]


def claim(db, key, before_write=lambda: None):
    row = db.execute("SELECT stock FROM stock WHERE key=?", (key,)).fetchone()
    before_write()
    if row is None or row[0] <= 0:
        return False
    db.execute("UPDATE stock SET stock=? WHERE key=?", (row[0] - 1, key))
    return True


def fetch(send, *, retry_safe, deadline, now, sleep, jitter, max_attempts=3):
    for attempt in range(3):
        try:
            return send(timeout=None)
        except Exception:
            if attempt == 2:
                raise
            sleep(1)
