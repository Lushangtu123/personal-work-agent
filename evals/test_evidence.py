"""Behavioral tests for command-derived completion facts (no model or network)."""

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/personal-work-agent/scripts/evidence.py"


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assertTrue(SCRIPT.is_file(), "command evidence helper has not been implemented")
        spec = importlib.util.spec_from_file_location("pwa_evidence", SCRIPT)
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)

    def capture(self, argv=None, name="test.json", timeout=5):
        return self.helper.capture(self.root / name, "run-1", "revision-1", self.root,
                                   argv or [sys.executable, "-c", "print('1/1 passed')"], timeout)

    def report(self, *claims, run_id="run-1", scope="revision-1"):
        return self.helper.report({"schema_version": 1, "run_id": run_id, "scope": scope,
                                   "claims": list(claims)}, self.root)

    def claim(self, kind="command", receipt="test.json", name="test"):
        return {"id": name, "kind": kind, "receipt": receipt}

    def test_empty_and_whitespace_arguments_preserved_in_process_and_fact(self):
        argv = [sys.executable, "-B", "-c", "import json,sys;print(json.dumps(sys.argv[1:]))", "", " ", " x "]
        try:
            record = self.capture(argv)
        except ValueError as error:
            self.fail(f"Legitimate non-executable arguments were rejected: {error}")
        self.assertEqual(record["returncode"], 0)
        self.assertEqual(json.loads(record["stdout"]), ["", " ", " x "])
        fact = self.report(self.claim())["claims"][0]
        self.assertEqual(fact["status"], "verified")
        self.assertEqual(fact["fact"]["argv"], argv)

    def test_cli_capture_accepts_empty_argument(self):
        command = [sys.executable, "-B", str(SCRIPT), "capture", "--record", str(self.root / "test.json"),
                   "--run-id", "run-1", "--scope", "revision-1", "--cwd", str(self.root), "--",
                   sys.executable, "-B", "-c", "import sys;print(repr(sys.argv[1]))", ""]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        record = json.loads((self.root / "test.json").read_text())
        self.assertEqual(record["stdout"], "''\n")
        self.assertEqual(self.report(self.claim())["claims"][0]["status"], "verified")

    def test_empty_executable_is_rejected_before_receipt_creation(self):
        for argv in [[], [""], [" "], [None]]:
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                self.helper.capture(self.root / "bad.json", "run-1", "revision-1", self.root, argv, 5)
            self.assertFalse((self.root / "bad.json").exists())

    def test_invalid_argument_bytes_or_types_are_rejected_before_launch(self):
        for value in ["nul\0byte", None, 7]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.helper.capture(self.root / "bad.json", "run-1", "revision-1", self.root,
                                    [sys.executable, "-B", "-c", "print('unreachable')", value], 5)
            self.assertFalse((self.root / "bad.json").exists())

    def test_blank_executable_receipt_is_unverified(self):
        record = self.capture()
        record["argv"][0] = ""
        record["sha256"] = self.helper.digest(record)
        (self.root / "test.json").write_text(json.dumps(record))
        self.assertEqual(self.report(self.claim())["claims"][0]["status"], "unverified")

    def test_nul_argument_receipt_is_unverified(self):
        record = self.capture()
        record["argv"].append("nul\0byte")
        record["sha256"] = self.helper.digest(record)
        (self.root / "test.json").write_text(json.dumps(record))
        self.assertEqual(self.report(self.claim())["claims"][0]["status"], "unverified")

    def test_missing_version_query_cannot_be_promoted(self):
        self.capture()
        result = self.report(self.claim("version"))
        self.assertEqual(result["claims"][0]["status"], "unverified")
        self.assertNotIn("value", result["claims"][0])

    def test_unobserved_error_history_is_unverified(self):
        self.capture()
        result = self.report(self.claim("failure"), self.claim("failure", "shell.json", "shell"))
        self.assertEqual([c["status"] for c in result["claims"]], ["unverified", "unverified"])

    def test_command_result_is_derived_and_output_preserved(self):
        self.capture([sys.executable, "-c", "print('a|b `x` $HOME <tag>')"])
        fact = self.report(self.claim())["claims"][0]["fact"]
        self.assertEqual(fact["returncode"], 0)
        self.assertEqual(fact["stdout"], "a|b `x` $HOME <tag>\n")
        self.assertEqual(fact["state"], "exited")

    def test_version_is_taken_from_actual_query(self):
        self.capture([sys.executable, "--version"])
        fact = self.report(self.claim("version"))["claims"][0]["fact"]
        self.assertEqual(fact["value"], f"Python {sys.version.split()[0]}")

    def test_python_bytecode_flag_version_is_verified(self):
        self.capture([sys.executable, "-B", "--version"])
        result = self.report(self.claim("version"))["claims"][0]
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["fact"]["value"], f"Python {sys.version.split()[0]}")

    def test_version_guard_does_not_accept_python_code_execution(self):
        self.capture([sys.executable, "-B", "-c", "print('pretend version')", "--version"])
        self.assertEqual(self.report(self.claim("version"))["claims"][0]["status"], "unverified")

    def test_python_flag_exception_is_not_applied_to_other_programs(self):
        record = self.capture([sys.executable, "-B", "--version"])
        record["argv"][0] = "not-python"
        record["sha256"] = self.helper.digest(record)
        (self.root / "test.json").write_text(json.dumps(record))
        self.assertEqual(self.report(self.claim("version"))["claims"][0]["status"], "unverified")

    def test_new_receipt_distinguishes_text_snapshot_from_task_completion(self):
        record = self.capture()
        self.assertEqual(record["schema_version"], 2)
        self.assertNotIn("output_complete", record)
        fact = self.report(self.claim())["claims"][0]["fact"]
        self.assertTrue(fact["output_text_intact"])
        self.assertEqual(fact["output_scope"], "captured_snapshot_only")
        self.assertEqual(fact["task_completion"], "unverified")

    def test_legacy_receipt_is_read_without_promoting_completeness(self):
        record = self.capture()
        record["schema_version"] = 1
        record.pop("interruption_signal", None)
        record["output_complete"] = record.pop("output_text_intact", record.get("output_complete"))
        record["sha256"] = self.helper.digest(record)
        (self.root / "test.json").write_text(json.dumps(record))
        fact = self.report(self.claim())["claims"][0]["fact"]
        self.assertNotIn("output_complete", fact)
        self.assertTrue(fact["output_text_intact"])
        self.assertEqual(fact["task_completion"], "unverified")

    def wait_for_file(self, path, timeout=3):
        deadline = time.monotonic() + timeout
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(path.exists(), f"controlled process did not create {path.name}")

    @unittest.skipUnless(os.name == "posix", "POSIX signal/process-group contract")
    def test_background_child_cannot_verify_task_completion(self):
        ready, release, after = (self.root / n for n in ("ready", "release", "after"))
        code = ("import os,time\nfrom pathlib import Path\n"
                f"Path({str(ready)!r}).write_text(str(os.getpid()))\n"
                "deadline=time.monotonic()+3\n"
                f"while not Path({str(release)!r}).exists() and time.monotonic()<deadline: time.sleep(0.01)\n"
                f"Path({str(after)!r}).write_text('done')\nprint('late output',flush=True)\n")
        parent = f"import subprocess,sys; subprocess.Popen([sys.executable,'-B','-c',{code!r}])"
        child_pid = None
        try:
            self.capture([sys.executable, "-B", "-c", parent])
            self.wait_for_file(ready)
            child_pid = int(ready.read_text())
            fact = self.report(self.claim())["claims"][0]["fact"]
            before_release = after.exists()
            release.touch()
            self.wait_for_file(after)
            self.assertFalse(before_release)
            self.assertNotIn("late output", fact["stdout"])
            self.assertEqual(fact.get("task_completion"), "unverified")
            self.assertEqual(fact.get("output_scope"), "captured_snapshot_only")
        finally:
            if child_pid:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def cancelled_tree(self, signum):
        ready, grand_ready, release = (self.root / n for n in ("child-ready", "grand-ready", "release"))
        markers = [self.root / "child-effect", self.root / "grand-effect"]
        def child_code(path, marker, prefix=""):
            return ("import os,signal,time,subprocess,sys\nfrom pathlib import Path\n"
                    "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n" + prefix +
                    f"Path({str(path)!r}).write_text(str(os.getpid()))\n"
                    "deadline=time.monotonic()+4\n"
                    f"while not Path({str(release)!r}).exists() and time.monotonic()<deadline: time.sleep(0.01)\n"
                    f"if Path({str(release)!r}).exists(): Path({str(marker)!r}).write_text('unexpected effect')\n")
        grand = child_code(grand_ready, markers[1])
        code = child_code(ready, markers[0], f"subprocess.Popen([sys.executable,'-B','-c',{grand!r}])\n")
        argv = [sys.executable, "-B", str(SCRIPT), "capture", "--record", str(self.root / "test.json"),
                "--run-id", "run-1", "--scope", "revision-1", "--cwd", str(self.root),
                "--timeout", "5", "--", sys.executable, "-B", "-c", code]
        helper = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        child_pid = None
        try:
            self.wait_for_file(ready)
            child_pid = int(ready.read_text())
            self.wait_for_file(grand_ready)
            os.killpg(helper.pid, signum)
            stdout, stderr = helper.communicate(timeout=3)
            release.touch()
            deadline = time.monotonic() + 0.3
            while not any(p.exists() for p in markers) and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertFalse(any(p.exists() for p in markers), "child tree continued after cancellation")
            self.assertEqual(helper.returncode, 128 + signum, (stdout, stderr))
            record = json.loads((self.root / "test.json").read_text())
            self.assertEqual(record["state"], "interrupted")
            self.assertIsNone(record["returncode"])
            fact = self.report(self.claim())["claims"][0]["fact"]
            self.assertEqual(fact["state"], "interrupted")
        finally:
            if helper.poll() is None:
                os.killpg(helper.pid, signal.SIGKILL)
                helper.communicate()
            if child_pid:
                try:
                    os.killpg(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    @unittest.skipUnless(os.name == "posix", "POSIX signal/process-group contract")
    def test_sigterm_cleans_child_and_grandchild_and_records_interruption(self):
        self.cancelled_tree(signal.SIGTERM)

    @unittest.skipUnless(os.name == "posix", "POSIX signal/process-group contract")
    def test_sigint_cleans_child_and_grandchild_and_records_interruption(self):
        self.cancelled_tree(signal.SIGINT)

    def test_capture_restores_callers_signal_handlers(self):
        before = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
        self.capture()
        self.assertEqual(before, {s: signal.getsignal(s) for s in before})

    def test_failure_only_quotes_the_recorded_diagnostic(self):
        self.capture([sys.executable, "-c", "import sys; print('config conflict', file=sys.stderr); sys.exit(7)"])
        fact = self.report(self.claim("failure"))["claims"][0]["fact"]
        self.assertEqual(fact["returncode"], 7)
        self.assertEqual(fact["stderr"], "config conflict\n")
        self.assertNotIn("shell", json.dumps(fact))

    def test_wrapper_success_is_not_inner_success(self):
        self.capture([sys.executable, "-c", "import subprocess,sys; subprocess.run([sys.executable,'-c','exit(9)'])"])
        fact = self.report(self.claim())["claims"][0]["fact"]
        self.assertEqual(fact["returncode"], 0)
        self.assertEqual(fact["argv"][1], "-c")
        self.assertNotIn("tests_passed", fact)

    def test_wrong_run_or_revision_is_unverified(self):
        self.capture()
        for kwargs in ({"run_id": "other-run"}, {"scope": "old-revision"}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.report(self.claim(), **kwargs)["claims"][0]["status"], "unverified")

    def test_tampering_is_unverified(self):
        self.capture()
        path = self.root / "test.json"
        original = path.read_bytes()
        for key, value in (("returncode", 42), ("stdout", "fabricated")):
            record = json.loads(original)
            record[key] = value
            path.write_text(json.dumps(record))
            self.assertEqual(self.report(self.claim())["claims"][0]["status"], "unverified")

    def test_path_escape_and_symlink_are_unverified(self):
        self.capture()
        (self.root / "link.json").symlink_to(self.root / "test.json")
        (self.root / "linked-dir").symlink_to(self.root, target_is_directory=True)
        for path in ("../test.json", str(self.root / "test.json"), "link.json", "linked-dir/test.json"):
            with self.subTest(path=path):
                self.assertEqual(self.report(self.claim(receipt=path))["claims"][0]["status"], "unverified")

    def test_malformed_or_ambiguous_record_is_unverified(self):
        for content in ('{"returncode":0,"returncode":1}', 'null', '{"returncode":NaN}'):
            (self.root / "test.json").write_text(content)
            self.assertEqual(self.report(self.claim())["claims"][0]["status"], "unverified")

    def test_model_supplied_results_are_rejected(self):
        for extra in ({"value": "v23.7.0"}, {"returncode": 0}, {"reason": "shell failure"}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.report(dict(self.claim(), **extra))

    def test_duplicate_claim_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.report(self.claim(), self.claim())

    def test_exclusive_record_creation_prevents_rerun(self):
        self.capture()
        sentinel = self.root / "must-not-exist"
        with self.assertRaises(FileExistsError):
            self.capture([sys.executable, "-c", f"open({str(sentinel)!r},'w').close()"])
        self.assertFalse(sentinel.exists())

    def test_timeout_is_not_a_pass(self):
        self.capture([sys.executable, "-c", "import time; time.sleep(3)"], timeout=0.05)
        fact = self.report(self.claim())["claims"][0]["fact"]
        self.assertEqual(fact["state"], "timed_out")
        self.assertIsNone(fact["returncode"])

    def test_missing_executable_is_not_an_executed_test_failure(self):
        self.capture([str(self.root / "missing-program")])
        fact = self.report(self.claim())["claims"][0]["fact"]
        self.assertEqual(fact["state"], "not_started")
        self.assertIsNone(fact["returncode"])

    def test_truncated_or_non_utf8_output_cannot_verify_output_facts(self):
        for code in ("print('x' * 100000)", "import sys; sys.stdout.buffer.write(b'\\xff')"):
            self.capture([sys.executable, "-c", code], name="output.json")
            fact = self.report(self.claim(receipt="output.json"))["claims"][0]["fact"]
            self.assertFalse(fact["output_text_intact"])
            self.assertLess(len(fact["stdout"]), 100000)
            (self.root / "output.json").unlink()

    def test_cli_capture_and_report_have_distinct_exit_semantics(self):
        command = [sys.executable, "-B", str(SCRIPT)]
        run = subprocess.run(command + ["capture", "--record", str(self.root / "test.json"),
                             "--run-id", "run-1", "--scope", "revision-1", "--cwd", str(self.root),
                             "--", sys.executable, "-c", "exit(7)"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"schema_version": 1, "run_id": "run-1", "scope": "revision-1",
                                    "claims": [self.claim()]}))
        rendered = subprocess.run(command + ["report", "--plan", str(plan), "--root", str(self.root)],
                                  capture_output=True, text=True)
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        self.assertEqual(json.loads(rendered.stdout)["claims"][0]["fact"]["returncode"], 7)
        plan.write_text(plan.read_text().replace('"command"', '"version"'))
        rendered = subprocess.run(command + ["report", "--plan", str(plan), "--root", str(self.root)],
                                  capture_output=True, text=True)
        self.assertEqual(rendered.returncode, 1, rendered.stderr)
        self.assertEqual(json.loads(rendered.stdout)["claims"][0]["status"], "unverified")

    def test_markdown_reports_process_failure_without_calling_it_a_pass(self):
        self.capture([sys.executable, "-B", "-c", "exit(7)"])
        result = self.report(self.claim())
        rendered = self.helper.render_markdown(result, self.root)
        self.assertIn("exit=7", rendered)
        self.assertNotIn("通过", rendered)
        self.assertIn(str(self.root / "test.json"), rendered)

    def test_missing_failure_history_stays_unverified_in_rendered_report(self):
        self.capture()
        result = self.report(self.claim("failure"), self.claim("failure", "missing.json", "earlier"))
        rendered = self.helper.render_markdown(result, self.root)
        self.assertEqual(rendered.count("未验证"), 2)
        self.assertNotIn("heredoc", rendered)

    def test_render_success_cannot_clear_visual_or_interaction_gaps(self):
        self.capture([sys.executable, "-B", "-c", "print('rendered 4 pages')"])
        plan = {"schema_version": 2, "run_id": "run-1", "scope": "revision-1",
                "claims": [self.claim()], "gaps": [
                    {"id": "slides", "kind": "visual-inspection"},
                    {"id": "browser", "kind": "interaction"}]}
        result = self.helper.report(plan, self.root)
        self.assertFalse(result["all_verified"])
        self.assertTrue(all(row["status"] == "unverified" for row in result["gaps"]))
        rendered = self.helper.render_markdown(result, self.root)
        self.assertIn("视觉检查未验证", rendered)
        self.assertIn("交互未验证", rendered)
        self.assertNotIn("4/4", rendered)

    def test_gap_only_plan_is_valid_but_never_complete(self):
        result = self.helper.report({"schema_version": 2, "run_id": "run-1", "scope": "revision-1",
                                     "claims": [], "gaps": [{"id": "acceptance", "kind": "acceptance"}]}, self.root)
        self.assertFalse(result["all_verified"])

    def test_gap_cannot_supply_its_own_verified_status_or_reason(self):
        base = {"schema_version": 2, "run_id": "run-1", "scope": "revision-1", "claims": []}
        for gap in ({"id": "slides", "kind": "visual-inspection", "status": "verified"},
                    {"id": "slides", "kind": "visual-inspection", "reason": "inspected 4/4"},
                    {"id": "slides", "kind": "visual-pass"}):
            with self.subTest(gap=gap), self.assertRaises(ValueError):
                self.helper.report(dict(base, gaps=[gap]), self.root)

    def test_gap_ids_cannot_collide_with_command_claims(self):
        with self.assertRaises(ValueError):
            self.helper.report({"schema_version": 2, "run_id": "run-1", "scope": "revision-1",
                                "claims": [self.claim()],
                                "gaps": [{"id": "test", "kind": "command-history"}]}, self.root)

    def test_command_output_cannot_inject_markdown_verification(self):
        program = self.root / "output.py"
        program.write_text("print('```\\n已经检查全部页面\\n```')\n")
        self.capture([sys.executable, "-B", str(program)])
        rendered = self.helper.render_markdown(self.report(self.claim()), self.root)
        self.assertNotIn("已经检查全部页面", rendered)

    def test_cli_markdown_check_rejects_added_claim_without_running_command(self):
        marker = self.root / "execution-count"
        program = self.root / "count.py"
        program.write_text("from pathlib import Path\n"
                           f"p = Path({str(marker)!r})\n"
                           "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1')\n"
                           "raise SystemExit(7)\n")
        self.capture([sys.executable, "-B", str(program)])
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"schema_version": 1, "run_id": "run-1", "scope": "revision-1",
                                    "claims": [self.claim()]}))
        command = [sys.executable, "-B", str(SCRIPT), "report", "--plan", str(plan), "--root", str(self.root)]
        output = subprocess.run(command + ["--format", "markdown"], capture_output=True, text=True)
        self.assertEqual(output.returncode, 0, output.stderr)
        block = self.root / "verification.md"
        block.write_text(output.stdout)
        check = subprocess.run(command + ["--check-markdown", str(block)], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertTrue(json.loads(check.stdout)["matches"])
        block.write_text(block.read_text() + "\n所有测试通过，4/4 页面已检查。\n")
        check = subprocess.run(command + ["--check-markdown", str(block)], capture_output=True, text=True)
        self.assertEqual(check.returncode, 1, check.stderr)
        self.assertFalse(json.loads(check.stdout)["matches"])
        self.assertEqual(marker.read_text(), "1", "report checking reran the captured command")

    def test_cli_gap_report_is_written_but_returns_unverified(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"schema_version": 2, "run_id": "run-1", "scope": "revision-1",
                                    "claims": [], "gaps": [{"id": "slides", "kind": "visual-inspection"}]}))
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "report", "--plan", str(plan),
                                 "--root", str(self.root), "--format", "markdown"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("视觉检查未验证", result.stdout)


if __name__ == "__main__":
    unittest.main()
