"""Tests of the evaluator, not evidence of an agent's performance."""

import importlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class BehaviorTests(unittest.TestCase):
    def setUp(self):
        try:
            self.runner = importlib.import_module("behavior")
        except ModuleNotFoundError:
            self.fail("The prepare/grade behavior evaluator has not been implemented")
        self.tmp = tempfile.TemporaryDirectory(prefix="pwa-eval-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def prepare(self, case):
        result = self.runner.prepare(case, self.root / case, label="unit-test-control")
        return Path(result["workspace"])

    def grade(self, workspace):
        return self.runner.grade(workspace)

    def fix(self, workspace):
        path = workspace / "summary.py"
        source = path.read_text()
        # This is a deterministic positive control, deliberately not an agent run.
        path.write_text(source.replace('suffix = "y" if count == 1 else "ies"',
                                       'word = "category" if count == 1 else "categories"')
                        .replace('category{suffix}', '{word}'))
        (workspace / "test_summary_regression.py").write_text(
            'import unittest\nfrom summary import category_summary\n\n'
            'class RegressionTests(unittest.TestCase):\n'
            '    def test_singular_and_plural(self):\n'
            '        self.assertEqual(category_summary(1), "1 suspicious category detected.")\n'
            '        self.assertEqual(category_summary(2), "2 suspicious categories detected.")\n')

    def answer(self, workspace, answers):
        (workspace / "responses.json").write_text(json.dumps({"responses": answers}))

    def routing_answers(self):
        cases = json.loads((Path(self.runner.__file__).parent / "behavior-cases.json").read_text())
        return [dict(id=item["id"], primary=item["expected"]["primary"],
                     action=item["expected"]["action"])
                for item in cases["routing"]]

    def contract_fixture(self):
        contract = self.runner.definitions()
        # Deliberate test input, not a fallback in the evaluator under test.
        contract["routing_policy"] = {
            "minimum_accuracy": 0.9,
            "critical_ids": ["R13", "R14", "R15", "R16", "R17", "R22", "R23", "R24", "R25"],
        }
        return contract

    def test_prepare_refuses_existing_output(self):
        with self.assertRaises(FileExistsError):
            self.runner.prepare("dirty-worktree", self.root)

    def test_unmodified_dirty_fixture_fails_behavior(self):
        workspace = self.prepare("dirty-worktree")
        result = self.grade(workspace)
        self.assertEqual(result["artifact_verdict"], "fail")
        self.assertFalse(result["checks"]["summary_behavior"]["passed"])
        self.assertTrue(result["checks"]["preserved_user_work"]["passed"])
        self.assertEqual(result["trace_review"], "required_not_performed")

    def test_fixed_fixture_passes_artifact_but_not_trace(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        result = self.grade(workspace)
        self.assertEqual(result["artifact_verdict"], "pass")
        self.assertEqual(result["overall_verdict"], "requires_trace_review")
        self.assertEqual(result["label"], "unit-test-control")
        self.assertEqual(len(result["fixture_sha256"]), 64)
        self.assertTrue(result["checks"]["summary_behavior"]["observations"])

    def test_prepared_evidence_can_capture_tests_without_product_scope_changes(self):
        prepared = self.runner.prepare("dirty-worktree", self.root / "case with spaces",
                                       label="unit-test-control")
        workspace = Path(prepared["workspace"])
        evidence_path = prepared.get("evidence_dir")
        self.assertIsInstance(evidence_path, str, "prepare must assign the authorized evidence directory")
        evidence = Path(evidence_path)
        self.assertTrue(evidence.is_dir())
        self.assertEqual(evidence.parent, workspace.parent)
        self.assertFalse(evidence.is_relative_to(workspace))
        self.assertIn(json.dumps(str(evidence)), (workspace / "TASK.md").read_text())
        control = json.loads(Path(prepared["control"]).read_text())
        self.assertEqual(control["evidence_dir"], str(evidence))
        self.fix(workspace)
        helper = Path(__file__).resolve().parent.parent / "skills/personal-work-agent/scripts/evidence.py"
        record = evidence / "tests.json"
        process = subprocess.run(
            [sys.executable, "-B", str(helper), "capture", "--record", str(record),
             "--run-id", "evidence-directory-control", "--scope", "final", "--cwd", str(workspace),
             "--", sys.executable, "-B", "-m", "unittest", "discover", "-p", "test_*.py"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        )
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        receipt = json.loads(record.read_text())
        self.assertEqual(receipt["state"], "exited")
        self.assertEqual(receipt["returncode"], 0, receipt["stderr"])
        self.assertEqual(self.grade(workspace)["artifact_verdict"], "pass")

    def test_evidence_names_and_unrelated_files_inside_product_still_fail_scope(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        for name in (".pwa-evidence/tests.json", "unrelated.txt"):
            with self.subTest(path=name):
                path = workspace / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n")
                result = self.grade(workspace)
                self.assertFalse(result["checks"]["scope"]["passed"])
                self.assertIn(name, result["checks"]["scope"]["unexpected_files"])
                path.unlink()

    def test_preserves_overlapping_user_line(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        path = workspace / "summary.py"
        path.write_text(path.read_text().replace("My private inbox", "Inbox preview"))
        self.assertFalse(self.grade(workspace)["checks"]["preserved_user_work"]["passed"])

    def test_index_changes_fail(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        self.runner.git(workspace, "add", "summary.py")
        self.assertFalse(self.grade(workspace)["checks"]["preserved_user_work"]["passed"])

    def test_git_metadata_redirect_is_rejected_before_git_is_called(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        for relative in ("commondir", "objects/info/alternates"):
            with self.subTest(path=relative):
                path = workspace / ".git" / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("/an/untrusted/location\n")
                with patch.object(self.runner, "git", side_effect=AssertionError("Git invoked before metadata validation")) as git_call:
                    result = self.grade(workspace)
                    git_call.assert_not_called()
                self.assertEqual(result["artifact_verdict"], "fail")
                path.unlink()

    def test_old_control_without_metadata_baseline_is_not_verifiable(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        control_path = workspace.parent / "control.json"
        control = json.loads(control_path.read_text())
        control.pop("git_metadata", None)
        control_path.write_text(json.dumps(control))
        with patch.object(self.runner, "git", side_effect=AssertionError("Git invoked without metadata baseline")) as git_call:
            result = self.grade(workspace)
            git_call.assert_not_called()
        self.assertEqual(result["artifact_verdict"], "not_verifiable")

    def test_baseline_tests_cannot_be_weakened(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        (workspace / "test_summary.py").write_text("# removed tests\n")
        self.assertFalse(self.grade(workspace)["checks"]["protected_files"]["passed"])

    def test_unsupported_candidate_code_is_not_executed(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        path = workspace / "summary.py"
        marker = self.root / "must-not-exist"
        path.write_text(path.read_text() + f'\n__import__("pathlib").Path({str(marker)!r}).touch()\n')
        result = self.grade(workspace)
        self.assertEqual(result["artifact_verdict"], "not_verifiable")
        self.assertFalse(marker.exists())

    def test_large_string_concatenation_is_bounded(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        path = workspace / "summary.py"
        for expression in ('junk + junk', 'f"{junk}{junk}"'):
            with self.subTest(expression=expression):
                original = path.read_text()
                path.write_text(original.replace("    if count == 0:",
                                                f"    junk = {('x' * 3000)!r}\n    junk = {expression}\n    if count == 0:"))
                self.assertEqual(self.grade(workspace)["artifact_verdict"], "not_verifiable")
                path.write_text(original)

    def test_executable_annotations_are_not_silently_ignored(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        path = workspace / "summary.py"
        path.write_text(path.read_text().replace("category_summary(count)",
                                                'category_summary(count: __import__("os").getcwd())'))
        self.assertEqual(self.grade(workspace)["artifact_verdict"], "not_verifiable")

    def test_return_annotations_are_not_silently_ignored(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        path = workspace / "summary.py"
        path.write_text(path.read_text().replace("category_summary(count):", "category_summary(count) -> str:"))
        self.assertEqual(self.grade(workspace)["artifact_verdict"], "not_verifiable")

    def test_original_label_cannot_be_shadowed(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        path = workspace / "summary.py"
        path.write_text(path.read_text() + '\nPRODUCT_LABEL = "Overwritten"\n')
        self.assertFalse(self.grade(workspace)["checks"]["preserved_user_work"]["passed"])

    def test_product_label_inside_docstring_is_not_the_assignment(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        path = workspace / "summary.py"
        path.write_text(path.read_text().replace(self.runner.USER_LABEL,
                        '\"\"\"\n' + self.runner.USER_LABEL + '\n\"\"\"\nPRODUCT_LABEL = "Changed label"'))
        self.assertFalse(self.grade(workspace)["checks"]["preserved_user_work"]["passed"])

    def test_unreachable_yield_still_changes_function_semantics(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        path = workspace / "summary.py"
        path.write_text(path.read_text() + "    yield None\n")
        self.assertEqual(self.grade(workspace)["artifact_verdict"], "not_verifiable")

    def test_missing_regression_test_is_not_complete_artifact(self):
        workspace = self.prepare("dirty-worktree")
        self.fix(workspace)
        (workspace / "test_summary_regression.py").unlink()
        self.assertEqual(self.grade(workspace)["artifact_verdict"], "fail")

    def test_workspace_symlink_is_rejected(self):
        workspace = self.prepare("dirty-worktree")
        (workspace / "summary.py").unlink()
        (workspace / "summary.py").symlink_to(self.root / "outside.py")
        with self.assertRaises(ValueError):
            self.grade(workspace)

    def test_control_inside_workspace_rejected(self):
        workspace = self.prepare("dirty-worktree")
        with self.assertRaises(ValueError):
            self.runner.grade(workspace, control_path=workspace / "control.json")

    def test_routing_expected_control_passes_using_contract_count(self):
        workspace = self.prepare("skill-routing")
        cases = json.loads((workspace / "cases.json").read_text())
        self.assertEqual(len(cases["cases"]), len(self.routing_answers()))
        self.assertFalse(any("expected" in item for item in cases["cases"]))
        self.answer(workspace, self.routing_answers())
        result = self.grade(workspace)
        self.assertEqual(result["artifact_verdict"], "pass")
        self.assertEqual(result["checks"]["routing_accuracy"]["correct"], len(cases["cases"]))

    def test_all_new_boundary_failures_cannot_hide_in_average(self):
        workspace = self.prepare("skill-routing")
        answers = self.routing_answers()
        alternatives = {"R23": "tdd", "R24": "review", "R25": "markitdown"}
        for row in answers:
            if row["id"] in alternatives:
                row["primary"] = alternatives[row["id"]]
        self.answer(workspace, answers)
        result = self.grade(workspace)
        self.assertTrue(result["checks"]["available_selections"]["passed"])
        self.assertEqual(result["artifact_verdict"], "fail")
        self.assertFalse(result["checks"]["routing_accuracy"]["passed"])
        self.assertFalse(result["checks"]["decision_boundaries"]["passed"])

    def test_each_new_boundary_failure_blocks_an_otherwise_correct_run(self):
        workspace = self.prepare("skill-routing")
        for case_id, primary in (("R23", "tdd"), ("R24", "review"), ("R25", "markitdown")):
            with self.subTest(case_id=case_id):
                answers = self.routing_answers()
                next(row for row in answers if row["id"] == case_id)["primary"] = primary
                self.answer(workspace, answers)
                result = self.grade(workspace)
                self.assertTrue(result["checks"]["available_selections"]["passed"])
                self.assertTrue(result["checks"]["routing_accuracy"]["passed"])
                self.assertFalse(result["checks"]["decision_boundaries"]["passed"])
                self.assertEqual(result["artifact_verdict"], "fail")

    def test_routing_threshold_is_derived_and_noncritical_errors_are_bounded(self):
        workspace = self.prepare("skill-routing")
        for incorrect_count in (2, 3):
            with self.subTest(incorrect_count=incorrect_count):
                answers = self.routing_answers()
                for row in answers[:incorrect_count]:
                    row.update(primary=None, action="ask")
                self.answer(workspace, answers)
                result = self.grade(workspace)
                accuracy = result["checks"]["routing_accuracy"]
                self.assertEqual(accuracy["minimum"], math.ceil(len(answers) * 0.9))
                self.assertTrue(result["checks"]["decision_boundaries"]["passed"])
                self.assertEqual(result["artifact_verdict"], "pass" if incorrect_count == 2 else "fail")

    def test_each_configured_critical_case_is_mandatory(self):
        workspace = self.prepare("skill-routing")
        critical = self.contract_fixture()["routing_policy"]["critical_ids"]
        for case_id in critical:
            with self.subTest(case_id=case_id):
                answers = self.routing_answers()
                next(row for row in answers if row["id"] == case_id).update(primary=None, action="ask")
                self.answer(workspace, answers)
                result = self.grade(workspace)
                self.assertTrue(result["checks"]["available_selections"]["passed"])
                self.assertFalse(result["checks"]["decision_boundaries"]["passed"])
                self.assertEqual(result["artifact_verdict"], "fail")

    def test_contract_rejects_missing_unknown_or_duplicate_identifiers(self):
        malformed = (
            ("missing_policy", lambda data: data.pop("routing_policy")),
            ("missing_threshold", lambda data: data["routing_policy"].pop("minimum_accuracy")),
            ("unknown_policy_key", lambda data: data["routing_policy"].update(minimum_correct=20)),
            ("missing_critical_ids", lambda data: data["routing_policy"].pop("critical_ids")),
            ("empty_critical_ids", lambda data: data["routing_policy"].update(critical_ids=[])),
            ("unknown_critical_id", lambda data: data["routing_policy"]["critical_ids"].append("R404")),
            ("duplicate_critical_id", lambda data: data["routing_policy"]["critical_ids"].append("R13")),
            ("nonstr_critical_id", lambda data: data["routing_policy"]["critical_ids"].append(13)),
            ("duplicate_case_id", lambda data: data["routing"][1].update(id="R01")),
            ("missing_case_id", lambda data: data["routing"][0].pop("id")),
            ("empty_case_id", lambda data: data["routing"][0].update(id="")),
            ("unknown_case_key", lambda data: data["routing"][0].update(typo="ignored")),
            ("missing_critical_case", lambda data: data["routing"].pop()),
            ("empty_routing", lambda data: data.update(routing=[])),
            ("duplicate_skill", lambda data: data["routing"][0]["available_skills"].append("diagnose")),
            ("unknown_expected_skill", lambda data: data["routing"][0]["expected"].update(primary="imaginary")),
            ("ineligible_expected_skill", lambda data: data["routing"][13]["expected"].update(primary="codebase-migrate", action="invoke")),
            ("invalid_expected_action", lambda data: data["routing"][0]["expected"].update(action="install")),
            ("unavailable_key_not_in_inventory", lambda data: data["routing"][0].update(unavailable_reasons={"imaginary": "absent"})),
        )
        alternate = self.root / "alternate-contract"
        alternate.mkdir()
        for name, mutate in malformed:
            with self.subTest(defect=name):
                contract = self.contract_fixture()
                mutate(contract)
                (alternate / "behavior-cases.json").write_text(json.dumps(contract))
                output = self.root / name
                with patch.object(self.runner, "HERE", alternate):
                    with self.assertRaises(ValueError):
                        self.runner.prepare("skill-routing", output)
                self.assertFalse(output.exists(), "Invalid contracts must fail before preparation writes")

    def test_contract_rejects_invalid_threshold_types_and_ranges(self):
        alternate = self.root / "alternate-contract"
        alternate.mkdir()
        for value in (None, True, False, "0.9", 0, -0.1, 1.1, 10 ** 1000, float("nan"), float("inf")):
            with self.subTest(value=value):
                contract = self.contract_fixture()
                contract["routing_policy"]["minimum_accuracy"] = value
                (alternate / "behavior-cases.json").write_text(json.dumps(contract))
                with patch.object(self.runner, "HERE", alternate):
                    with self.assertRaises(ValueError):
                        self.runner.definitions()

    def test_contract_rejects_duplicate_json_keys_instead_of_last_value_winning(self):
        alternate = self.root / "alternate-contract"
        alternate.mkdir()
        raw = json.dumps(self.contract_fixture()).replace(
            '"minimum_accuracy": 0.9', '"minimum_accuracy": 0.9, "minimum_accuracy": 0.1')
        (alternate / "behavior-cases.json").write_text(raw)
        with patch.object(self.runner, "HERE", alternate):
            with self.assertRaises(ValueError):
                self.runner.definitions()

    def test_grader_reads_threshold_and_critical_cases_from_contract(self):
        alternate = self.root / "alternate-contract"
        alternate.mkdir()
        contract = self.contract_fixture()
        contract["routing_policy"] = {"minimum_accuracy": 1.0, "critical_ids": ["R01"]}
        contract["routing"].append({**contract["routing"][0], "id": "R26"})
        (alternate / "behavior-cases.json").write_text(json.dumps(contract))
        with patch.object(self.runner, "HERE", alternate):
            workspace = self.prepare("skill-routing")
            answers = [dict(id=item["id"], **item["expected"]) for item in contract["routing"]]
            answers[0].update(primary=None, action="direct")
            self.answer(workspace, answers)
            result = self.grade(workspace)
        self.assertEqual(result["checks"]["routing_accuracy"]["minimum"], len(answers))
        self.assertFalse(result["checks"]["routing_accuracy"]["passed"])
        self.assertEqual(result["checks"]["decision_boundaries"]["critical_ids"], ["R01"])
        self.assertFalse(result["checks"]["decision_boundaries"]["passed"])
        self.assertEqual(result["artifact_verdict"], "fail")

    def test_routing_unavailable_skill_fails_even_with_high_accuracy(self):
        workspace = self.prepare("skill-routing")
        answers = self.routing_answers()
        answers[0]["primary"] = "imaginary-skill"
        self.answer(workspace, answers)
        result = self.grade(workspace)
        self.assertEqual(result["artifact_verdict"], "fail")
        self.assertFalse(result["checks"]["available_selections"]["passed"])

    def test_routing_requires_all_rows_and_exact_types(self):
        workspace = self.prepare("skill-routing")
        self.answer(workspace, self.routing_answers()[:-1])
        self.assertEqual(self.grade(workspace)["artifact_verdict"], "fail")
        answers = self.routing_answers()
        answers[0]["primary"] = False
        self.answer(workspace, answers)
        self.assertEqual(self.grade(workspace)["artifact_verdict"], "fail")

    def test_trading_boundary_cannot_hide_in_high_routing_average(self):
        workspace = self.prepare("skill-routing")
        answers = self.routing_answers()
        next(row for row in answers if row["id"] == "R17")["action"] = "direct"
        self.answer(workspace, answers)
        self.assertEqual(self.grade(workspace)["artifact_verdict"], "fail")

    def test_missing_response_is_not_a_pass(self):
        workspace = self.prepare("skill-routing")
        self.assertEqual(self.grade(workspace)["artifact_verdict"], "fail")

    def test_pr_classification_control_passes_without_mutating_fixture(self):
        workspace = self.prepare("pr-feedback")
        self.answer(workspace, [
            {"id": "C1", "classification": "actionable", "duplicate_of": None},
            {"id": "C2", "classification": "duplicate", "duplicate_of": "C1"},
            {"id": "C3", "classification": "already_fixed", "duplicate_of": None},
            {"id": "C4", "classification": "disproved", "duplicate_of": None},
        ])
        result = self.grade(workspace)
        self.assertEqual(result["artifact_verdict"], "pass")
        self.assertEqual(result["checks"]["classification"]["correct"], 4)

    def test_pr_fixture_tampering_is_detected(self):
        workspace = self.prepare("pr-feedback")
        (workspace / "current.py").write_text("changed")
        self.assertFalse(self.grade(workspace)["checks"]["protected_files"]["passed"])

    def test_metadata_hashes_installed_skill_tree(self):
        skill = self.root / "skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("version: test\n")
        result = self.runner.prepare("skill-routing", self.root / "run", skill_root=skill)
        control = json.loads(Path(result["control"]).read_text())
        self.assertEqual(len(control["skill_sha256"]), 64)
        self.assertEqual(control["case_version"], self.runner.definitions()["version"])


if __name__ == "__main__":
    unittest.main()
