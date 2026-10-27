"""Synthetic controls for ledger validation, not agent-behavior evaluations."""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


EVALS = Path(__file__).resolve().parent
CONTRACT_PATH = EVALS / "scenarios.yaml"
CONTRACT = json.loads(CONTRACT_PATH.read_text())
SKILL_HASH = "a" * 64


class ResultsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "trace.txt").write_text("Synthetic tool trace for validator tests only.\n")
        (self.root / "observation.txt").write_text("Synthetic independently reviewed observation.\n")
        self.ledger = {
            "schema_version": 1,
            "suite": CONTRACT["suite"],
            "candidate_version": CONTRACT["candidate_version"],
            "contract_sha256": hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
            "metadata": {
                "skill_sha256": SKILL_HASH, "model": "synthetic-model",
                "codex_version": "synthetic-version", "reasoning": "synthetic",
                "tools": "synthetic tools", "permission_policy": "synthetic policy",
            },
            "structural_checks": {"passed": True, "evidence": ["observation.txt"]},
            "runs": [],
        }

    def row(self, scenario):
        return {
            "scenario_id": scenario["id"], "run_id": "run-" + scenario["id"],
            "status": "reviewed",
            "scores": {d["id"]: 3 for d in CONTRACT["scoring"]["dimensions"]},
            "outcomes": {o["id"]: {"met": True, "evidence": ["observation.txt"]}
                         for o in scenario["observable_outcomes"]},
            "hard_failures": [],
            "review": {"reviewer": "synthetic-reviewer", "trace_reviewed": True,
                       "trace": ["trace.txt"], "notes": "Synthetic test only."},
            "metrics": {"tokens": None, "elapsed_seconds": None},
        }

    def complete(self):
        self.ledger["runs"] = [self.row(s) for s in CONTRACT["scenarios"]]

    def cli(self, ledger=None, expected_hash=SKILL_HASH):
        path = self.root / "results.json"
        path.write_text(json.dumps(self.ledger if ledger is None else ledger))
        command = [sys.executable, "-B", str(EVALS / "results.py"),
                   "--contract", str(CONTRACT_PATH), "--results", str(path)]
        if expected_hash is not None:
            command += ["--skill-sha256", expected_hash]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_empty_ledger_lists_full_denominator(self):
        code, report = self.cli()
        self.assertEqual(code, 1)
        self.assertFalse(report["qualified"])
        self.assertEqual(report["scenario_count"], len(CONTRACT["scenarios"]))
        self.assertEqual(len(report["missing_scenarios"]), len(CONTRACT["scenarios"]))

    def test_complete_synthetic_ledger_qualifies(self):
        self.complete()
        code, report = self.cli()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["pass_count"], len(CONTRACT["scenarios"]))
        self.assertTrue(report["complete"])

    def test_passing_subset_never_qualifies(self):
        self.complete()
        self.ledger["runs"] = self.ledger["runs"][:CONTRACT["release"]["minimum_pass_count"]]
        code, report = self.cli()
        self.assertEqual(code, 1)
        self.assertFalse(report["complete"])
        self.assertEqual(len(report["missing_scenarios"]), 2)

    def test_threshold_and_critical_zero_are_enforced(self):
        self.complete()
        critical = next(d["id"] for d in CONTRACT["scoring"]["dimensions"] if d["critical"])
        self.ledger["runs"][0]["scores"][critical] = 0
        code, report = self.cli()
        self.assertEqual(code, 0, report)  # 25/26 passes meets the contract's 24/26.
        self.assertFalse(report["scenarios"][0]["passed"])
        self.assertIn("critical-zero", report["scenarios"][0]["reasons"])
        for row in self.ledger["runs"][:3]:
            row["scores"] = {k: 1 for k in row["scores"]}
        code, report = self.cli()
        self.assertEqual(code, 1)
        self.assertEqual(report["pass_count"], 23)

    def test_any_global_hard_failure_blocks_release(self):
        self.complete()
        self.ledger["runs"][0]["hard_failures"] = [CONTRACT["release"]["hard_failures"][-1]["id"]]
        code, report = self.cli()
        self.assertEqual(code, 1)
        self.assertTrue(report["hard_failures"])

    def test_incomplete_statuses_never_count_as_pass(self):
        self.complete()
        for status in ("not_run", "blocked", "unverified"):
            with self.subTest(status=status):
                self.ledger["runs"][0]["status"] = status
                code, report = self.cli()
                self.assertEqual(code, 1)
                self.assertEqual(report["pass_count"], 25)
                self.assertFalse(report["complete"])

    def test_minimal_blocked_row_is_valid_but_incomplete(self):
        self.ledger["runs"] = [{"scenario_id": CONTRACT["scenarios"][0]["id"],
                                "run_id": "blocked-1", "status": "blocked",
                                "notes": "Required surface is unavailable."}]
        code, report = self.cli()
        self.assertEqual(code, 1, report)
        self.assertEqual(report["pass_count"], 0)

    def test_unknown_metadata_or_unpinned_hash_prevents_qualification(self):
        self.complete()
        for name in self.ledger["metadata"]:
            with self.subTest(name=name):
                ledger = copy.deepcopy(self.ledger)
                ledger["metadata"][name] = None
                code, report = self.cli(ledger)
                self.assertEqual(code, 1, report)
        self.assertEqual(self.cli(expected_hash=None)[0], 1)

    def test_missing_review_trace_outcome_or_structural_evidence_fails_closed(self):
        self.complete()
        mutations = [
            lambda x: x["runs"][0]["review"].update(trace_reviewed=False),
            lambda x: x["runs"][0]["review"].update(trace=[]),
            lambda x: x["runs"][0].update(review=None),
            lambda x: x["runs"][0].update(outcomes={}),
            lambda x: x["structural_checks"].update(passed=None),
            lambda x: x["structural_checks"].update(evidence=[]),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                ledger = copy.deepcopy(self.ledger)
                mutate(ledger)
                self.assertEqual(self.cli(ledger)[0], 1)

    def test_false_outcome_disqualifies_scenario(self):
        self.complete()
        outcome = next(iter(self.ledger["runs"][0]["outcomes"].values()))
        outcome["met"] = False
        code, report = self.cli()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["pass_count"], 25)

    def test_missing_empty_external_and_symlink_evidence_fail_closed(self):
        self.complete()
        (self.root / "empty.txt").touch()
        (self.root / "link.txt").symlink_to(self.root / "trace.txt")
        (self.root / "directory").mkdir()
        (self.root / "linked-dir").symlink_to(self.root / "directory", target_is_directory=True)
        (self.root / "directory" / "trace.txt").write_text("Trace.")
        for path in ("missing.txt", "empty.txt", "../outside.txt", "/etc/hosts",
                     "link.txt", "linked-dir/trace.txt", "directory"):
            with self.subTest(path=path):
                ledger = copy.deepcopy(self.ledger)
                ledger["runs"][0]["review"]["trace"] = [path]
                code, report = self.cli(ledger)
                self.assertNotEqual(code, 0, report)
                self.assertFalse(report["qualified"])

    def test_wrong_identity_and_unknown_or_duplicate_ids_are_invalid(self):
        self.complete()
        mutations = [
            lambda x: x.update(suite="wrong"),
            lambda x: x.update(candidate_version="0.0.0"),
            lambda x: x.update(contract_sha256="b" * 64),
            lambda x: x["metadata"].update(skill_sha256="b" * 64),
            lambda x: x["runs"].append(copy.deepcopy(x["runs"][0])),
            lambda x: x["runs"][0].update(scenario_id="unknown"),
            lambda x: x["runs"][0].update(run_id=x["runs"][1]["run_id"]),
            lambda x: x["runs"][0].update(hard_failures=["unknown"]),
            lambda x: x["runs"][0]["outcomes"].update(unknown={"met": True, "evidence": []}),
            lambda x: x.update(qualified=True),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                ledger = copy.deepcopy(self.ledger)
                mutate(ledger)
                self.assertEqual(self.cli(ledger)[0], 2)

    def test_invalid_scores_and_metrics_are_not_coerced(self):
        self.complete()
        dimension = CONTRACT["scoring"]["dimensions"][0]["id"]
        for value in (True, "3", 3.1, -1, 4, float("nan"), float("inf")):
            with self.subTest(score=value):
                ledger = copy.deepcopy(self.ledger)
                ledger["runs"][0]["scores"][dimension] = value
                self.assertEqual(self.cli(ledger)[0], 2)
        for value in (True, -1, float("nan"), float("inf")):
            with self.subTest(metric=value):
                ledger = copy.deepcopy(self.ledger)
                ledger["runs"][0]["metrics"]["tokens"] = value
                self.assertEqual(self.cli(ledger)[0], 2)

    def test_cli_does_not_modify_inputs(self):
        self.complete()
        path = self.root / "results.json"
        path.write_text(json.dumps(self.ledger))
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.cli()
        after = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.assertEqual(after, before)

    def test_malformed_nested_types_return_json_not_tracebacks(self):
        self.complete()
        mutations = [
            lambda x: x["runs"][0].update(status=[]),
            lambda x: x["runs"][0].update(scores=True),
            lambda x: x["runs"][0].update(outcomes=[]),
            lambda x: x["runs"][0].update(review=[]),
            lambda x: x["runs"][0].update(metrics=[]),
            lambda x: x["runs"][0].update(hard_failures={}),
            lambda x: x.update(metadata=[]),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                ledger = copy.deepcopy(self.ledger)
                mutate(ledger)
                self.assertEqual(self.cli(ledger)[0], 2)

    def test_absent_scores_and_null_outcomes_are_incomplete(self):
        self.complete()
        ledger = copy.deepcopy(self.ledger)
        ledger["runs"][0]["scores"] = None
        self.assertEqual(self.cli(ledger)[0], 1)
        ledger = copy.deepcopy(self.ledger)
        outcome = next(iter(ledger["runs"][0]["outcomes"].values()))
        outcome["met"] = None
        self.assertEqual(self.cli(ledger)[0], 1)
        outcome["met"] = True
        outcome["evidence"] = []
        self.assertEqual(self.cli(ledger)[0], 1)

    def test_duplicate_json_keys_are_rejected(self):
        path = self.root / "duplicate.json"
        path.write_text('{"schema_version":1,"schema_version":1}')
        result = subprocess.run([sys.executable, "-B", str(EVALS / "results.py"),
                                 "--contract", str(CONTRACT_PATH), "--results", str(path)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate JSON key", json.loads(result.stdout)["errors"][0])

    def test_help_explains_exit_codes_and_limits(self):
        result = subprocess.run([sys.executable, "-B", str(EVALS / "results.py"), "--help"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Exit 0:", result.stdout)
        self.assertIn("not a sandbox", result.stdout)

    def test_historical_contract_uses_its_frozen_package_versions(self):
        package = self.root / "frozen"
        evals = package / "evals"
        evals.mkdir(parents=True)
        shutil.copytree(EVALS / "fixtures", evals / "fixtures")
        contract = copy.deepcopy(CONTRACT)
        contract["candidate_version"] = "0.8.0"
        contract_path = evals / "scenarios.yaml"
        contract_path.write_text(json.dumps(contract))
        manifest = package / ".codex-plugin" / "plugin.json"
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({"name": "personal-work-agent", "version": "0.8.0"}))
        skill = package / "skills" / "personal-work-agent" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text('---\nname: personal-work-agent\nmetadata:\n  version: "0.8.0"\n---\n')
        self.ledger["candidate_version"] = "0.8.0"
        self.ledger["contract_sha256"] = hashlib.sha256(contract_path.read_bytes()).hexdigest()
        ledger_path = self.root / "historical.json"
        ledger_path.write_text(json.dumps(self.ledger))
        result = subprocess.run([sys.executable, "-B", str(EVALS / "results.py"),
                                 "--contract", str(contract_path), "--results", str(ledger_path),
                                 "--skill-sha256", SKILL_HASH],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
