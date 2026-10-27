#!/usr/bin/env python3
"""Deterministic structural checks for the personal-work-agent eval contract.

`scenarios.yaml` intentionally contains JSON-compatible YAML. JSON is a strict
subset of YAML 1.2, so this checker stays dependency-free while the file remains
usable by YAML-aware tooling.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PRERELEASE_IDENTIFIER = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    rf"(?:-{PRERELEASE_IDENTIFIER}(?:\.{PRERELEASE_IDENTIFIER})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

VALID_MODES = {
    "code-maintenance",
    "project-bootstrap",
    "office-delivery",
    "investment-research",
}
VALID_TASK_CLASSES = {
    "implement",
    "test",
    "diagnose",
    "review",
    "plan",
    "create-deliverable",
    "research",
}
VALID_LOCAL_MUTATIONS = {"none", "scoped", "new-project", "deliverable-only"}
VALID_PATH_CLASSES = {
    "implementation",
    "tests",
    "configuration",
    "documentation",
    "notebook",
    "new-project-files",
    "requested-deliverable",
}
VALID_COMPLEXITIES = {"simple", "medium", "complex"}
VALID_EXECUTIONS = {"manual", "fixture"}
VALID_OUTCOME_KINDS = {"artifact", "behavior", "decision", "evidence", "state"}

TOP_LEVEL_KEYS = {
    "schema_version",
    "suite",
    "candidate_version",
    "description",
    "allowed_modes",
    "allowed_task_classes",
    "allowed_local_mutation_kinds",
    "allowed_path_classes",
    "coverage",
    "scoring",
    "release",
    "scenarios",
}
SCENARIO_KEYS = {
    "id",
    "mode",
    "task_class",
    "complexity",
    "execution",
    "fixture",
    "title",
    "request",
    "allowed_mutations",
    "observable_outcomes",
    "hard_failure_ids",
    "must",
    "must_not",
}


def load_document(path: Path) -> dict[str, Any]:
    """Load a JSON-compatible YAML document."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise ValueError(f"unable to read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{path} must remain JSON-compatible YAML: "
            f"line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object at the top level")
    return value


def _add_unknown_key_errors(
    value: dict[str, Any], allowed: set[str], path: str, errors: list[str]
) -> None:
    for key in sorted(set(value) - allowed):
        errors.append(f"{path} contains unknown field {key!r}")


def _non_empty_string(value: Any, path: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")
        return None
    return value.strip()


def _string_list(
    value: Any,
    path: str,
    errors: list[str],
    *,
    require_non_empty: bool = False,
    duplicate_noun: str = "value",
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        parsed = _non_empty_string(item, f"{path}[{index}]", errors)
        if parsed is not None:
            result.append(parsed)
    if require_non_empty and not result:
        errors.append(f"{path} must not be empty")
    duplicates = sorted({item for item in result if result.count(item) > 1})
    for item in duplicates:
        errors.append(f"{path} contains duplicate {duplicate_noun} {item!r}")
    return result


def _validate_id(value: Any, path: str, errors: list[str]) -> str | None:
    parsed = _non_empty_string(value, path, errors)
    if parsed is not None and ID_RE.fullmatch(parsed) is None:
        errors.append(f"{path} must use lowercase kebab-case")
    return parsed


def _validate_exact_allowlist(
    document: dict[str, Any],
    key: str,
    expected: set[str],
    errors: list[str],
) -> set[str]:
    actual = set(_string_list(document.get(key), key, errors, require_non_empty=True))
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append(f"{key} is missing supported values: {', '.join(missing)}")
    if extra:
        errors.append(f"{key} contains unsupported values: {', '.join(extra)}")
    return actual


def _validate_fixture_path(raw_path: Any, evals_root: Path, errors: list[str]) -> None:
    fixture = _non_empty_string(raw_path, "scenario.fixture", errors)
    if fixture is None:
        return
    candidate = (evals_root / fixture).resolve()
    try:
        candidate.relative_to(evals_root.resolve())
    except ValueError:
        errors.append("scenario.fixture must stay inside the evals directory")
        return
    if not candidate.is_dir():
        errors.append(f"scenario.fixture directory does not exist: {fixture}")


def _validate_scoring(value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("scoring must be an object")
        return
    _add_unknown_key_errors(
        value,
        {
            "minimum_dimension_score",
            "maximum_dimension_score",
            "minimum_scenario_score",
            "dimensions",
        },
        "scoring",
        errors,
    )
    minimum = value.get("minimum_dimension_score")
    maximum = value.get("maximum_dimension_score")
    threshold = value.get("minimum_scenario_score")
    if type(minimum) is not int:
        errors.append("scoring.minimum_dimension_score must be an integer")
    if type(maximum) is not int:
        errors.append("scoring.maximum_dimension_score must be an integer")
    if type(minimum) is int and type(maximum) is int and minimum >= maximum:
        errors.append("scoring dimension range must have minimum < maximum")

    raw_dimensions = value.get("dimensions")
    if not isinstance(raw_dimensions, list) or not raw_dimensions:
        errors.append("scoring.dimensions must be a non-empty array")
        dimensions: list[Any] = []
    else:
        dimensions = raw_dimensions

    dimension_ids: list[str] = []
    critical_count = 0
    for index, dimension in enumerate(dimensions):
        path = f"scoring.dimensions[{index}]"
        if not isinstance(dimension, dict):
            errors.append(f"{path} must be an object")
            continue
        _add_unknown_key_errors(dimension, {"id", "label", "critical"}, path, errors)
        dimension_id = _validate_id(dimension.get("id"), f"{path}.id", errors)
        if dimension_id is not None:
            dimension_ids.append(dimension_id)
        _non_empty_string(dimension.get("label"), f"{path}.label", errors)
        if not isinstance(dimension.get("critical"), bool):
            errors.append(f"{path}.critical must be a boolean")
        elif dimension["critical"]:
            critical_count += 1
    duplicate_ids = sorted(
        {item for item in dimension_ids if dimension_ids.count(item) > 1}
    )
    for dimension_id in duplicate_ids:
        errors.append(f"duplicate scoring dimension id {dimension_id!r}")
    if critical_count == 0:
        errors.append("scoring must define at least one critical dimension")
    if type(threshold) is not int:
        errors.append("scoring.minimum_scenario_score must be an integer")
    elif type(minimum) is int and type(maximum) is int and dimensions:
        minimum_total = minimum * len(dimensions)
        maximum_total = maximum * len(dimensions)
        if not minimum_total <= threshold <= maximum_total:
            errors.append(
                "scoring.minimum_scenario_score must fit the configured score range"
            )


def _validate_release(
    value: Any,
    scenario_count: int,
    errors: list[str],
) -> set[str]:
    if not isinstance(value, dict):
        errors.append("release must be an object")
        return set()
    _add_unknown_key_errors(
        value,
        {
            "scenario_count",
            "minimum_pass_count",
            "require_all_structural_checks",
            "allow_hard_failures",
            "hard_failures",
        },
        "release",
        errors,
    )
    declared_count = value.get("scenario_count")
    if type(declared_count) is not int:
        errors.append("release.scenario_count must be an integer")
    elif declared_count != scenario_count:
        errors.append(
            "release.scenario_count must equal the number of declared scenarios"
        )
    minimum_pass_count = value.get("minimum_pass_count")
    if type(minimum_pass_count) is not int:
        errors.append("release.minimum_pass_count must be an integer")
    elif not 1 <= minimum_pass_count <= scenario_count:
        errors.append(
            "release.minimum_pass_count must be between 1 and scenario_count"
        )
    if value.get("require_all_structural_checks") is not True:
        errors.append("release.require_all_structural_checks must be true")
    if value.get("allow_hard_failures") is not False:
        errors.append("release.allow_hard_failures must be false")

    raw_failures = value.get("hard_failures")
    if not isinstance(raw_failures, list) or not raw_failures:
        errors.append("release.hard_failures must be a non-empty array")
        return set()
    failure_ids: list[str] = []
    for index, failure in enumerate(raw_failures):
        path = f"release.hard_failures[{index}]"
        if not isinstance(failure, dict):
            errors.append(f"{path} must be an object")
            continue
        _add_unknown_key_errors(failure, {"id", "description"}, path, errors)
        failure_id = _validate_id(failure.get("id"), f"{path}.id", errors)
        if failure_id is not None:
            failure_ids.append(failure_id)
        _non_empty_string(failure.get("description"), f"{path}.description", errors)
    duplicate_ids = sorted({item for item in failure_ids if failure_ids.count(item) > 1})
    for failure_id in duplicate_ids:
        errors.append(f"duplicate hard failure id {failure_id!r}")
    return set(failure_ids)


def _validate_coverage(
    value: Any,
    allowed_modes: set[str],
    allowed_task_classes: set[str],
    scenario_modes: set[str],
    scenario_task_classes: set[str],
    errors: list[str],
) -> None:
    if not isinstance(value, dict):
        errors.append("coverage must be an object")
        return
    _add_unknown_key_errors(
        value, {"required_modes", "required_task_classes"}, "coverage", errors
    )
    required_modes = set(
        _string_list(
            value.get("required_modes"),
            "coverage.required_modes",
            errors,
            require_non_empty=True,
        )
    )
    required_task_classes = set(
        _string_list(
            value.get("required_task_classes"),
            "coverage.required_task_classes",
            errors,
            require_non_empty=True,
        )
    )
    for mode in sorted(required_modes - allowed_modes):
        errors.append(f"coverage references unknown mode {mode!r}")
    for task_class in sorted(required_task_classes - allowed_task_classes):
        errors.append(f"coverage references unknown task class {task_class!r}")
    for mode in sorted(required_modes - scenario_modes):
        errors.append(f"required mode has no scenario: {mode}")
    for task_class in sorted(required_task_classes - scenario_task_classes):
        errors.append(f"required task class has no scenario: {task_class}")


def validate_suite(document: dict[str, Any], evals_root: Path) -> list[str]:
    """Return all structural errors in one pass."""

    errors: list[str] = []
    if not isinstance(document, dict):
        return ["suite document must be an object"]
    _add_unknown_key_errors(document, TOP_LEVEL_KEYS, "suite", errors)

    if type(document.get("schema_version")) is not int or document["schema_version"] != 2:
        errors.append("schema_version must be the integer 2")
    _non_empty_string(document.get("suite"), "suite", errors)
    candidate_version = _non_empty_string(
        document.get("candidate_version"), "candidate_version", errors
    )
    if candidate_version is not None and SEMVER_RE.fullmatch(candidate_version) is None:
        errors.append("candidate_version must be strict semantic versioning")
    _non_empty_string(document.get("description"), "description", errors)

    allowed_modes = _validate_exact_allowlist(
        document, "allowed_modes", VALID_MODES, errors
    )
    allowed_task_classes = _validate_exact_allowlist(
        document, "allowed_task_classes", VALID_TASK_CLASSES, errors
    )
    _validate_exact_allowlist(
        document,
        "allowed_local_mutation_kinds",
        VALID_LOCAL_MUTATIONS,
        errors,
    )
    allowed_path_classes = _validate_exact_allowlist(
        document, "allowed_path_classes", VALID_PATH_CLASSES, errors
    )
    _validate_scoring(document.get("scoring"), errors)

    raw_scenarios = document.get("scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        errors.append("scenarios must be a non-empty array")
        scenarios: list[Any] = []
    else:
        scenarios = raw_scenarios
    hard_failure_ids = _validate_release(
        document.get("release"), len(scenarios), errors
    )

    scenario_ids: list[str] = []
    scenario_modes: set[str] = set()
    scenario_task_classes: set[str] = set()
    referenced_hard_failures: set[str] = set()
    for index, scenario in enumerate(scenarios):
        path = f"scenarios[{index}]"
        if not isinstance(scenario, dict):
            errors.append(f"{path} must be an object")
            continue
        _add_unknown_key_errors(scenario, SCENARIO_KEYS, path, errors)
        scenario_id = _validate_id(scenario.get("id"), f"{path}.id", errors)
        if scenario_id is not None:
            scenario_ids.append(scenario_id)

        mode = _non_empty_string(scenario.get("mode"), f"{path}.mode", errors)
        if mode is not None:
            scenario_modes.add(mode)
            if mode not in allowed_modes:
                errors.append(f"{path}.mode references unknown mode {mode!r}")
        task_class = _non_empty_string(
            scenario.get("task_class"), f"{path}.task_class", errors
        )
        if task_class is not None:
            scenario_task_classes.add(task_class)
            if task_class not in allowed_task_classes:
                errors.append(
                    f"{path}.task_class references unknown task class {task_class!r}"
                )
        complexity = _non_empty_string(
            scenario.get("complexity"), f"{path}.complexity", errors
        )
        if complexity is not None and complexity not in VALID_COMPLEXITIES:
            errors.append(f"{path}.complexity is unsupported: {complexity!r}")
        execution = _non_empty_string(
            scenario.get("execution"), f"{path}.execution", errors
        )
        if execution is not None and execution not in VALID_EXECUTIONS:
            errors.append(f"{path}.execution is unsupported: {execution!r}")
        if execution == "fixture":
            _validate_fixture_path(scenario.get("fixture"), evals_root, errors)
        elif "fixture" in scenario:
            errors.append(f"{path}.fixture is only valid for fixture execution")

        _non_empty_string(scenario.get("title"), f"{path}.title", errors)
        _non_empty_string(scenario.get("request"), f"{path}.request", errors)

        mutations = scenario.get("allowed_mutations")
        if not isinstance(mutations, dict):
            errors.append(f"{path}.allowed_mutations must be an object")
        else:
            _add_unknown_key_errors(
                mutations,
                {"local", "path_classes", "external", "verification_evidence"},
                f"{path}.allowed_mutations",
                errors,
            )
            evidence_policy = mutations.get("verification_evidence", "none")
            if not isinstance(evidence_policy, str) or evidence_policy not in ("none", "runner-provided-directory"):
                errors.append(
                    f"{path}.allowed_mutations.verification_evidence must be none or runner-provided-directory"
                )
            local = _non_empty_string(
                mutations.get("local"), f"{path}.allowed_mutations.local", errors
            )
            if local is not None and local not in VALID_LOCAL_MUTATIONS:
                errors.append(
                    f"{path}.allowed_mutations.local is unsupported: {local!r}"
                )
            path_classes = _string_list(
                mutations.get("path_classes"),
                f"{path}.allowed_mutations.path_classes",
                errors,
            )
            for path_class in sorted(set(path_classes) - allowed_path_classes):
                errors.append(
                    f"{path}.allowed_mutations references unknown path class "
                    f"{path_class!r}"
                )
            if local == "none" and path_classes:
                errors.append(
                    f"{path}.allowed_mutations.path_classes must be empty when local is none"
                )
            if local in VALID_LOCAL_MUTATIONS - {"none"} and not path_classes:
                errors.append(
                    f"{path}.allowed_mutations.path_classes must declare the scoped artifact classes"
                )
            external = _string_list(
                mutations.get("external"),
                f"{path}.allowed_mutations.external",
                errors,
            )
            if external:
                errors.append(
                    f"{path}: external mutations are not allowed in the v2 evaluation suite"
                )

        raw_outcomes = scenario.get("observable_outcomes")
        if not isinstance(raw_outcomes, list) or not raw_outcomes:
            errors.append(f"{path}.observable_outcomes must be a non-empty array")
            outcomes: list[Any] = []
        else:
            outcomes = raw_outcomes
        outcome_ids: list[str] = []
        for outcome_index, outcome in enumerate(outcomes):
            outcome_path = f"{path}.observable_outcomes[{outcome_index}]"
            if not isinstance(outcome, dict):
                errors.append(f"{outcome_path} must be an object")
                continue
            _add_unknown_key_errors(
                outcome, {"id", "kind", "description"}, outcome_path, errors
            )
            outcome_id = _validate_id(outcome.get("id"), f"{outcome_path}.id", errors)
            if outcome_id is not None:
                outcome_ids.append(outcome_id)
            kind = _non_empty_string(
                outcome.get("kind"), f"{outcome_path}.kind", errors
            )
            if kind is not None and kind not in VALID_OUTCOME_KINDS:
                errors.append(f"{outcome_path}.kind is unsupported: {kind!r}")
            _non_empty_string(
                outcome.get("description"), f"{outcome_path}.description", errors
            )
        duplicate_outcome_ids = sorted(
            {item for item in outcome_ids if outcome_ids.count(item) > 1}
        )
        for outcome_id in duplicate_outcome_ids:
            errors.append(
                f"{path} contains duplicate observable outcome id {outcome_id!r}"
            )

        scenario_failure_ids = _string_list(
            scenario.get("hard_failure_ids"),
            f"{path}.hard_failure_ids",
            errors,
            require_non_empty=True,
            duplicate_noun="hard failure reference",
        )
        referenced_hard_failures.update(scenario_failure_ids)
        for failure_id in sorted(set(scenario_failure_ids) - hard_failure_ids):
            errors.append(f"{path} references unknown hard failure {failure_id!r}")

        _string_list(
            scenario.get("must"), f"{path}.must", errors, require_non_empty=True
        )
        _string_list(
            scenario.get("must_not"),
            f"{path}.must_not",
            errors,
            require_non_empty=True,
        )

    duplicate_scenario_ids = sorted(
        {item for item in scenario_ids if scenario_ids.count(item) > 1}
    )
    for scenario_id in duplicate_scenario_ids:
        errors.append(f"duplicate scenario id {scenario_id!r}")
    for failure_id in sorted(hard_failure_ids - referenced_hard_failures):
        errors.append(f"hard failure is never referenced by a scenario: {failure_id}")

    _validate_coverage(
        document.get("coverage"),
        allowed_modes,
        allowed_task_classes,
        scenario_modes,
        scenario_task_classes,
        errors,
    )
    return errors


def _load_skill_version(path: Path, errors: list[str]) -> str | None:
    """Read the package's limited metadata subset, not arbitrary YAML.

    A single top-level block-style metadata mapping must contain one two-space
    indented scalar version (plain, single-quoted, or double-quoted). Blank lines
    and full-line comments are permitted without ending that mapping.
    """

    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        errors.append(f"unable to read {path}: {error}")
        return None
    frontmatter = re.match(r"\A---[ \t]*\n(.*?)^---[ \t]*$", contents, re.M | re.S)
    versions: list[str] = []
    if frontmatter is not None:
        metadata_blocks = list(
            re.finditer(
                r"^metadata:[ \t]*(?:#.*)?\n((?:^[ \t]+.*\n|^#.*\n|^\n)*)",
                frontmatter.group(1),
                re.M,
            )
        )
        if len(metadata_blocks) == 1:
            for match in re.finditer(
                r'''^  version:[ \t]*(?:"([^"]+)"|'([^']+)'|([^\s#]+))[ \t]*(?:#.*)?$''',
                metadata_blocks[0].group(1),
                re.M,
            ):
                versions.append(
                    next(value for value in match.groups() if value is not None)
                )
    if len(versions) != 1:
        errors.append(
            f"{path}: SKILL.md metadata.version must be a single scalar in "
            "block-style frontmatter (two-space indentation)"
        )
        return None
    return versions[0]


def validate_package_versions(
    document: dict[str, Any], package_root: Path
) -> list[str]:
    """Check suite, source skill, and installed manifest versions independently."""

    errors: list[str] = []
    candidate = _non_empty_string(
        document.get("candidate_version"), "candidate_version", errors
    )
    manifest_path = package_root / ".codex-plugin" / "plugin.json"
    try:
        manifest = load_document(manifest_path)
    except ValueError as error:
        errors.append(str(error))
        manifest_version = None
    else:
        manifest_version = _non_empty_string(
            manifest.get("version"), "plugin manifest version", errors
        )
    skill_version = _load_skill_version(
        package_root / "skills" / "personal-work-agent" / "SKILL.md", errors
    )
    for label, version in (
        ("candidate_version", candidate),
        ("plugin manifest version", manifest_version),
        ("SKILL.md metadata.version", skill_version),
    ):
        if version is not None and SEMVER_RE.fullmatch(version) is None:
            errors.append(f"{label} must be strict semantic versioning")
    for label, version in (
        ("candidate_version", candidate),
        ("SKILL.md metadata.version", skill_version),
    ):
        if version is not None and "+" in version:
            errors.append(f"{label} must not include build metadata")
    if manifest_version is not None:
        manifest_base, separator, build = manifest_version.partition("+")
        if separator and not re.fullmatch(
            r"codex\.[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*", build
        ):
            errors.append("plugin manifest build metadata must use codex.<build>")
        if candidate is not None and candidate != manifest_base:
            errors.append(
                f"candidate_version {candidate!r} must match plugin manifest base "
                f"version {manifest_base!r} ({manifest_path})"
            )
    if candidate is not None and skill_version is not None and candidate != skill_version:
        errors.append(
            f"candidate_version {candidate!r} must match SKILL.md metadata.version "
            f"{skill_version!r}"
        )
    return errors


def validate_plugin_manifest(package_root: Path) -> list[str]:
    """Check PWA metadata independently of its evaluation contract."""
    errors: list[str] = []
    try:
        manifest = load_document(package_root / ".codex-plugin" / "plugin.json")
    except ValueError as error:
        return [str(error)]
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        return ["plugin interface must be an object"]
    for field, maximum in (("displayName", 30), ("shortDescription", 30),
                           ("longDescription", 4000), ("developerName", 80)):
        value = interface.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            errors.append(f"interface.{field} must be nonempty and at most {maximum} characters")
    if not isinstance(interface.get("category"), str) or not interface["category"].strip():
        errors.append("interface.category must be a nonempty string")
    capabilities = interface.get("capabilities")
    if (not isinstance(capabilities, list) or len(capabilities) > 20
            or any(not isinstance(v, str) or not v.strip() or len(v) > 120
                   for v in capabilities)):
        errors.append("interface.capabilities must contain at most 20 nonempty strings of at most 120 characters")
    if "defaultPrompt" in interface:
        prompt = interface["defaultPrompt"]
        prompts = [prompt] if isinstance(prompt, str) else prompt
        if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
            errors.append("interface.defaultPrompt must contain one to three prompts")
        else:
            seen: set[str] = set()
            for value in prompts:
                if (not isinstance(value, str) or not value.strip()
                        or len(value) > 128 or any(c in value for c in "\r\n\u2028\u2029")):
                    errors.append("interface.defaultPrompt must be nonempty, single-line and at most 128 characters")
                elif value in seen:
                    errors.append("interface.defaultPrompt entries must be unique")
                else:
                    seen.add(value)
    root = package_root.resolve()
    for field in ("skills", "composerIcon", "logo", "composerIconDark", "logoDark"):
        if field.endswith("Dark") and field not in interface:
            continue
        value = manifest.get(field) if field == "skills" else interface.get(field)
        label = field if field == "skills" else f"interface.{field}"
        if (not isinstance(value, str) or not value.startswith("./")
                or ".." in Path(value).parts or "\\" in value):
            errors.append(f"{label} must be a ./ path inside the plugin package")
            continue
        try:
            path = (root / value).resolve()
            if not path.is_relative_to(root):
                raise ValueError("path escapes the plugin package")
            if field == "skills":
                if not path.is_dir():
                    raise ValueError("skills directory does not exist")
                continue
            if not path.is_file():
                raise ValueError("icon file does not exist")
            if path.stat().st_size > 5 * 1024 * 1024:
                raise ValueError("icon exceeds 5 MiB")
            # This scoped PWA gate checks its SVG assets, not all host image formats.
            if path.suffix.lower() != ".svg":
                raise ValueError("PWA's local icon gate currently requires SVG")
            svg = ET.fromstring(path.read_bytes())
            if svg.tag != "{http://www.w3.org/2000/svg}svg":
                raise ValueError("icon must be an SVG document")
            try:
                width, height = float(svg.get("width", "")), float(svg.get("height", ""))
            except ValueError:
                box = [float(v) for v in svg.get("viewBox", "").replace(",", " ").split()]
                if len(box) != 4:
                    raise ValueError("SVG needs numeric dimensions or a square viewBox")
                width, height = box[2:]
            if not (math.isfinite(width) and math.isfinite(height)
                    and width == height and width >= 48):
                raise ValueError("SVG dimensions must be square and at least 48")
        except (OSError, ValueError, ET.ParseError, RuntimeError) as error:
            errors.append(f"{label}: {error}")
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the personal-work-agent evaluation contract."
    )
    parser.add_argument(
        "scenarios",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().with_name("scenarios.yaml"),
        help="path to the JSON-compatible scenarios.yaml file",
    )
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="check PWA listing metadata, local skills path and SVG icons only",
    )
    parser.add_argument(
        "--package-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="plugin package whose manifest and SKILL.md versions must match",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.manifest_only:
        errors = validate_plugin_manifest(args.package_root)
        if errors:
            print("PWA plugin manifest validation failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("PWA plugin manifest validation passed (local metadata, paths and SVG icons).")
        return 0
    try:
        document = load_document(args.scenarios)
    except ValueError as error:
        print(f"Evaluation contract validation failed:\n- {error}")
        return 1
    errors = validate_suite(document, args.scenarios.resolve().parent)
    errors.extend(validate_package_versions(document, args.package_root.resolve()))
    if errors:
        print("Evaluation contract validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    release = document["release"]
    scoring = document["scoring"]
    maximum_score = scoring["maximum_dimension_score"] * len(scoring["dimensions"])
    print(
        "Evaluation contract validation passed: "
        f"{len(document['scenarios'])} scenarios, "
        f"release threshold {release['minimum_pass_count']}/{release['scenario_count']}, "
        f"scenario score {scoring['minimum_scenario_score']}/{maximum_score}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
