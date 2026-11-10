"""Fixture integrity controls, not evidence of agent behavior or token savings."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "token_tasks", Path(__file__).parent / "fixtures/token-efficiency/prepare.py")
TASKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TASKS)


class TokenFixtureTests(unittest.TestCase):
    def test_log_preserves_target_failure_amid_unrelated_events(self):
        rows = TASKS.files_for("large-log")["logs/service.log"].splitlines()
        self.assertEqual(len(rows), 8000)
        target = [row for row in rows if "request=req-7421 " in row]
        self.assertEqual(len(target), 4)
        self.assertIn("Disk_quota_exceeded", target[1])
        self.assertIn("outcome=failed artifact_created=false", target[-1])
        self.assertIn("request=other-99", rows[7998])

    def test_summary_omits_later_compensation(self):
        files = TASKS.files_for("excerpt-recovery")
        summary = json.loads(files["summary.json"])
        rows = files["logs/service.log"].splitlines()
        self.assertEqual(len(rows), 8000)
        self.assertTrue(all(item in rows[:40] for item in summary["excerpt"]))
        self.assertFalse(any("rolled_back" in item for item in summary["excerpt"]))
        self.assertIn("job=job-508 event=job_terminal final_state=rolled_back", rows[7762])

    def test_fresh_workspace_hashes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            result = TASKS.prepare("search-reassessment", root)
            before = {p: (root / p).read_bytes() for p in result["input_sha256"]}
            self.assertNotIn("findings.json", result["input_sha256"])
            with self.assertRaises(FileExistsError):
                TASKS.prepare("large-log", root)
            self.assertEqual(before, {p: (root / p).read_bytes() for p in before})

    def test_small_case_and_invalid_requests(self):
        self.assertEqual(set(TASKS.files_for("small-task")), {"TASK.md", "summary.py"})
        with self.assertRaises(ValueError):
            TASKS.files_for("unknown")
        with self.assertRaises(ValueError):
            TASKS.prepare("small-task", Path("relative"))


if __name__ == "__main__":
    unittest.main()
