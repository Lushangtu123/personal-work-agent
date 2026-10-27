from __future__ import annotations

import copy
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


EVALS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS_ROOT))

import check  # noqa: E402


class EvaluationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = check.load_document(EVALS_ROOT / "scenarios.yaml")

    def assert_has_error(self, errors: list[str], fragment: str) -> None:
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected an error containing {fragment!r}, got: {errors}",
        )

    def test_current_suite_is_valid(self) -> None:
        self.assertEqual(check.validate_suite(self.suite, EVALS_ROOT), [])

    def test_runner_provided_evidence_policy_is_explicit_and_bounded(self) -> None:
        suite = copy.deepcopy(self.suite)
        dirty = next(s for s in suite["scenarios"] if s["id"] == "dirty-worktree")
        dirty["allowed_mutations"]["verification_evidence"] = "runner-provided-directory"
        self.assertEqual(check.validate_suite(suite, EVALS_ROOT), [])

    def test_unbounded_or_malformed_evidence_policy_is_rejected(self) -> None:
        for policy in ("anywhere", "/tmp", "", None, True, {}):
            with self.subTest(policy=policy):
                suite = copy.deepcopy(self.suite)
                suite["scenarios"][0]["allowed_mutations"]["verification_evidence"] = policy
                self.assert_has_error(check.validate_suite(suite, EVALS_ROOT),
                                      "must be none or runner-provided-directory")

    def test_dirty_worktree_contract_authorizes_only_assigned_evidence_directory(self) -> None:
        dirty = next(s for s in self.suite["scenarios"] if s["id"] == "dirty-worktree")
        self.assertEqual(dirty["allowed_mutations"].get("verification_evidence"),
                         "runner-provided-directory")
        self.assertEqual(dirty["allowed_mutations"]["path_classes"], ["implementation", "tests"])

    def test_action_boundary_scenarios_are_present(self) -> None:
        scenario_ids = {scenario["id"] for scenario in self.suite["scenarios"]}
        self.assertTrue(
            {
                "script-side-effect-gate",
                "exact-push-authorization",
                "uncertain-external-mutation",
                "investment-transaction-refusal",
            }.issubset(scenario_ids)
        )

    def test_duplicate_scenario_id_is_rejected(self) -> None:
        suite = copy.deepcopy(self.suite)
        suite["scenarios"][1]["id"] = suite["scenarios"][0]["id"]

        errors = check.validate_suite(suite, EVALS_ROOT)

        self.assert_has_error(errors, "duplicate scenario id")

    def test_impossible_release_threshold_is_rejected(self) -> None:
        suite = copy.deepcopy(self.suite)
        suite["release"]["minimum_pass_count"] = len(suite["scenarios"]) + 1

        errors = check.validate_suite(suite, EVALS_ROOT)

        self.assert_has_error(errors, "minimum_pass_count")

    def test_boolean_values_are_rejected_by_all_integer_fields(self) -> None:
        paths = (
            ("scoring", "minimum_dimension_score"),
            ("scoring", "maximum_dimension_score"),
            ("scoring", "minimum_scenario_score"),
            ("release", "scenario_count"),
            ("release", "minimum_pass_count"),
        )
        for section, field in paths:
            for boolean in (False, True):
                with self.subTest(field=f"{section}.{field}", value=boolean):
                    suite = copy.deepcopy(self.suite)
                    suite[section][field] = boolean

                    errors = check.validate_suite(suite, EVALS_ROOT)

                    self.assert_has_error(errors, f"{section}.{field} must be an integer")

    def test_schema_version_requires_an_integer(self) -> None:
        for value in (True, False, 2.0, "2"):
            with self.subTest(value=value):
                suite = copy.deepcopy(self.suite)
                suite["schema_version"] = value

                errors = check.validate_suite(suite, EVALS_ROOT)

                self.assert_has_error(errors, "schema_version must be the integer 2")

    def test_candidate_version_rejects_non_semver_numbers(self) -> None:
        for version in ("0.3.0-01", "0.3.0-beta.01", "1١.3.0", "0.3.0-١"):
            with self.subTest(version=version):
                suite = copy.deepcopy(self.suite)
                suite["candidate_version"] = version

                errors = check.validate_suite(suite, EVALS_ROOT)

                self.assert_has_error(errors, "candidate_version must be strict semantic")

    def test_candidate_version_accepts_valid_prerelease_and_build_identifiers(self) -> None:
        for version in (
            "0.3.0-alpha.01a", "0.3.0-0", "0.3.0-beta.0", "0.3.0+001.02"
        ):
            with self.subTest(version=version):
                suite = copy.deepcopy(self.suite)
                suite["candidate_version"] = version

                self.assertEqual(check.validate_suite(suite, EVALS_ROOT), [])

    def test_unknown_hard_failure_reference_is_rejected(self) -> None:
        suite = copy.deepcopy(self.suite)
        suite["scenarios"][0]["hard_failure_ids"].append("not-defined")

        errors = check.validate_suite(suite, EVALS_ROOT)

        self.assert_has_error(errors, "unknown hard failure")

    def test_duplicate_hard_failure_reference_is_rejected(self) -> None:
        suite = copy.deepcopy(self.suite)
        failure_ids = suite["scenarios"][0]["hard_failure_ids"]
        failure_ids.append(failure_ids[0])

        errors = check.validate_suite(suite, EVALS_ROOT)

        self.assert_has_error(errors, "duplicate hard failure reference")

    def test_duplicate_observable_outcome_id_is_rejected(self) -> None:
        suite = copy.deepcopy(self.suite)
        outcomes = suite["scenarios"][0]["observable_outcomes"]
        outcomes.append(copy.deepcopy(outcomes[0]))

        errors = check.validate_suite(suite, EVALS_ROOT)

        self.assert_has_error(errors, "duplicate observable outcome id")

    def test_fixture_path_must_stay_inside_evals_directory(self) -> None:
        suite = copy.deepcopy(self.suite)
        scenario = suite["scenarios"][0]
        scenario["execution"] = "fixture"
        scenario["fixture"] = "../outside"

        errors = check.validate_suite(suite, EVALS_ROOT)

        self.assert_has_error(errors, "fixture must stay inside")

    def test_required_mode_must_have_scenario_coverage(self) -> None:
        suite = copy.deepcopy(self.suite)
        suite["scenarios"] = [
            scenario
            for scenario in suite["scenarios"]
            if scenario["mode"] != "investment-research"
        ]
        suite["release"]["scenario_count"] = len(suite["scenarios"])
        suite["release"]["minimum_pass_count"] = len(suite["scenarios"])

        errors = check.validate_suite(suite, EVALS_ROOT)

        self.assert_has_error(errors, "required mode has no scenario")

    def test_external_mutation_allowlist_must_be_empty_for_v2(self) -> None:
        suite = copy.deepcopy(self.suite)
        suite["scenarios"][0]["allowed_mutations"]["external"] = ["push branch"]

        errors = check.validate_suite(suite, EVALS_ROOT)

        self.assert_has_error(errors, "external mutations are not allowed")


class PackageVersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.package_root = Path(self.temporary_directory.name)
        self.manifest_path = self.package_root / ".codex-plugin" / "plugin.json"
        self.skill_path = (
            self.package_root / "skills" / "personal-work-agent" / "SKILL.md"
        )
        self.suite_path = self.package_root / "evals" / "scenarios.yaml"
        self.suite = check.load_document(EVALS_ROOT / "scenarios.yaml")
        self.suite["candidate_version"] = "0.3.0"
        self.manifest_path.parent.mkdir(parents=True)
        self.skill_path.parent.mkdir(parents=True)
        self.suite_path.parent.mkdir(parents=True)
        shutil.copytree(EVALS_ROOT / "fixtures", self.suite_path.parent / "fixtures")
        self.manifest_path.write_text(
            json.dumps({"name": "personal-work-agent", "version": "0.3.0"}),
            encoding="utf-8",
        )
        self.skill_path.write_text(
            '---\nname: personal-work-agent\nmetadata:\n  version: "0.3.0"\n---\n',
            encoding="utf-8",
        )
        self.suite_path.write_text(json.dumps(self.suite), encoding="utf-8")

    def validate(self) -> list[str]:
        self.assertTrue(
            callable(getattr(check, "validate_package_versions", None)),
            "package version validation must be available",
        )
        return check.validate_package_versions(self.suite, self.package_root)

    def assert_error(self, fragment: str) -> None:
        errors = self.validate()
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected {fragment!r} in errors, got {errors}",
        )

    def test_matching_package_versions_are_valid(self) -> None:
        self.assertEqual(self.validate(), [])

    def test_supported_skill_scalar_styles_are_valid(self) -> None:
        for scalar in ("0.3.0", "'0.3.0'", '"0.3.0" # release'):
            with self.subTest(scalar=scalar):
                self.skill_path.write_text(
                    f"---\nmetadata:\n  version: {scalar}\n---\n", encoding="utf-8"
                )
                self.assertEqual(self.validate(), [])

    def test_manifest_allows_codex_build_suffix(self) -> None:
        self.manifest_path.write_text(
            json.dumps({"version": "0.3.0+codex.20260917123456"}), encoding="utf-8"
        )
        self.assertEqual(self.validate(), [])

    def test_package_versions_reject_invalid_semver_identifiers(self) -> None:
        for version in ("0.3.0-01", "0.3.0-beta.01", "1١.3.0"):
            with self.subTest(version=version):
                self.suite["candidate_version"] = version
                self.manifest_path.write_text(
                    json.dumps({"version": version}), encoding="utf-8"
                )
                self.skill_path.write_text(
                    f'---\nmetadata:\n  version: "{version}"\n---\n', encoding="utf-8"
                )

                for label in (
                    "candidate_version", "plugin manifest version", "SKILL.md metadata.version"
                ):
                    self.assert_error(f"{label} must be strict semantic versioning")

    def test_package_allows_alphanumeric_prerelease_and_zero_prefixed_build(self) -> None:
        self.suite["candidate_version"] = "0.3.0-alpha.01a"
        self.manifest_path.write_text(
            json.dumps({"version": "0.3.0-alpha.01a+codex.001"}), encoding="utf-8"
        )
        self.skill_path.write_text(
            '---\nmetadata:\n  version: "0.3.0-alpha.01a"\n---\n', encoding="utf-8"
        )

        self.assertEqual(self.validate(), [])

    def test_candidate_must_match_manifest_base_version(self) -> None:
        self.suite["candidate_version"] = "9.9.9"
        self.assert_error("plugin manifest base version")

    def test_candidate_must_match_skill_metadata_version(self) -> None:
        self.skill_path.write_text(
            '---\nmetadata:\n  version: "0.2.0"\n---\n', encoding="utf-8"
        )
        self.assert_error("SKILL.md metadata.version")

    def test_candidate_and_skill_do_not_allow_build_suffixes(self) -> None:
        self.suite["candidate_version"] = "0.3.0+codex.123"
        self.skill_path.write_text(
            '---\nmetadata:\n  version: "0.3.0+codex.123"\n---\n', encoding="utf-8"
        )
        self.assert_error("candidate_version must not include build metadata")
        self.assert_error("SKILL.md metadata.version must not include build metadata")

    def test_manifest_rejects_unrecognized_build_suffix(self) -> None:
        self.manifest_path.write_text(
            json.dumps({"version": "0.3.0+other.123"}), encoding="utf-8"
        )
        self.assert_error("plugin manifest build metadata must use codex.<build>")

    def test_missing_manifest_is_reported(self) -> None:
        self.manifest_path.unlink()
        self.assert_error("unable to read")
        self.assert_error("plugin.json")

    def test_malformed_manifest_is_reported(self) -> None:
        self.manifest_path.write_text("{broken", encoding="utf-8")
        self.assert_error("plugin.json")
        self.assert_error("JSON-compatible")

    def test_manifest_missing_version_is_reported(self) -> None:
        self.manifest_path.write_text("{}", encoding="utf-8")
        self.assert_error("plugin manifest version must be a non-empty string")

    def test_non_utf8_manifest_is_reported_with_its_path(self) -> None:
        self.manifest_path.write_bytes(b"\xff")
        self.assert_error("plugin.json")
        self.assert_error("unable to read")

    def test_missing_skill_file_is_reported(self) -> None:
        self.skill_path.unlink()
        self.assert_error("unable to read")
        self.assert_error("SKILL.md")

    def test_skill_requires_metadata_version_in_frontmatter(self) -> None:
        for contents in (
            "# Skill\nmetadata:\n  version: 0.3.0\n",
            "---\nversion: 0.3.0\n---\n",
            "---\nmetadata:\n  author: someone\n---\nversion: 0.3.0\n",
        ):
            with self.subTest(contents=contents):
                self.skill_path.write_text(contents, encoding="utf-8")
                self.assert_error("SKILL.md metadata.version")

    def test_duplicate_metadata_sections_are_rejected(self) -> None:
        self.skill_path.write_text(
            "---\nmetadata:\n  version: 0.3.0\nmetadata:\n  version: 0.2.0\n---\n",
            encoding="utf-8",
        )
        self.assert_error("SKILL.md metadata.version")

    def test_duplicate_metadata_versions_are_rejected(self) -> None:
        self.skill_path.write_text(
            "---\nmetadata:\n  version: 0.3.0\n  version: 0.2.0\n---\n",
            encoding="utf-8",
        )
        self.assert_error("SKILL.md metadata.version")

    def test_unindented_comment_does_not_hide_duplicate_metadata_version(self) -> None:
        self.skill_path.write_text(
            '---\nmetadata:\n  version: "0.3.0"\n# release comment\n'
            '  version: "0.2.0"\n---\n',
            encoding="utf-8",
        )

        self.assert_error("SKILL.md metadata.version")

    def test_unindented_comment_before_metadata_version_is_supported(self) -> None:
        self.skill_path.write_text(
            '---\nmetadata:\n# release comment\n  version: "0.3.0"\n---\n',
            encoding="utf-8",
        )

        self.assertEqual(self.validate(), [])

    def test_cli_rejects_candidate_version_drift(self) -> None:
        self.suite["candidate_version"] = "9.9.9"
        self.suite_path.write_text(json.dumps(self.suite), encoding="utf-8")
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = check.main([str(self.suite_path)])

        self.assertEqual(exit_code, 1)
        self.assertIn("plugin manifest base version", output.getvalue())

    def test_cli_can_validate_a_different_package_root(self) -> None:
        self.assertTrue(
            callable(getattr(check, "validate_package_versions", None)),
            "package version validation must be available",
        )
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = check.main(
                [str(self.suite_path), "--package-root", str(self.package_root)]
            )

        self.assertEqual(exit_code, 0, output.getvalue())


if __name__ == "__main__":
    unittest.main()
