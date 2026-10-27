#!/usr/bin/env python3
"""Read-only result ledger validation; no agent execution or automatic grading.

JSON schema v1 (unknown fields rejected):
  {schema_version: 1, suite, candidate_version, contract_sha256,
   metadata: {skill_sha256, model, codex_version, reasoning, tools,
              permission_policy},
   structural_checks: {passed: bool|null, evidence: [relative-file]},
   runs: [{scenario_id, run_id, status, notes?, scores?, outcomes?,
           hard_failures?, review?, metrics?}]}
  status = reviewed | not_run | blocked | unverified
  scores = {contract-dimension-id: integer} | null
  outcomes = {contract-outcome-id: {met: bool|null, evidence: [relative-file]}}
  review = {reviewer: string|null, trace_reviewed: bool,
            trace: [relative-file], notes: string} | null
  metrics = {tokens: nonnegative-integer|null,
             elapsed_seconds: nonnegative-number|null} | null

Use one unique row per scenario and run ID; repetitions need separate ledgers.
Metadata fields are strings or null (tools/policy are descriptions or pinned
versions). Unknown provenance must be null, never fabricated. All provenance
is required for qualification, while unavailable optional metrics remain null.
skill_sha256 identifies the ENTIRE frozen skills subtree (both skills and all
references); --skill-sha256 pins the independently recorded expected hash.
The contract hash is SHA-256 of its exact bytes. Neither hash authenticates
what a worker actually loaded; review the actual tool trace for that evidence.

A reviewer supplies scores and per-outcome evidence after reviewing actual
trace and artifacts, not just the worker's final self-report. Evidence paths
must name nonempty regular files contained below the results file's directory,
with no symlink components. A file's presence does NOT prove its truth: this
validator cannot authenticate traces or judge semantics and is not a sandbox.
Structural evidence must cover the required separate packaging/checker gates.
Missing evidence, unreviewed traces, missing rows and unknown metadata cannot
qualify. A reviewed false outcome or critical-zero fails that scenario; any
declared hard failure blocks qualification regardless of other scores.

Exit 0: complete qualified ledger under supplied attestations; 1: valid but
incomplete/not qualified; 2: malformed input or invalid contract. JSON stdout.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

from check import validate_package_versions, validate_suite

HASH = re.compile(r"[0-9a-f]{64}\Z")
METADATA = {"skill_sha256", "model", "codex_version", "reasoning", "tools", "permission_policy"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, allowed, label):
    require(isinstance(value, dict), f"{label} must be an object")
    require(not set(value) - allowed, f"{label} contains unknown fields: {sorted(set(value) - allowed)}")


def text(value):
    return isinstance(value, str) and bool(value.strip())


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path):
    def reject_constant(value):
        raise ValueError(f"nonfinite JSON constant: {value}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def evidence(paths, root):
    require(isinstance(paths, list) and all(text(p) for p in paths), "evidence must be an array of paths")
    if not paths:
        return False
    for name in paths:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            return False
        candidate = root
        for part in path.parts:
            candidate /= part
            if candidate.is_symlink():
                return False
        try:
            candidate.resolve().relative_to(root)
            if not candidate.is_file() or candidate.stat().st_size == 0:
                return False
            with candidate.open("rb") as handle:
                if not handle.read(1):
                    return False
        except (OSError, ValueError):
            return False
    return True


def review_available(value, root):
    if value is None:
        return False
    fields(value, {"reviewer", "trace_reviewed", "trace", "notes"}, "review")
    require(value.get("reviewer") is None or text(value["reviewer"]), "reviewer must be a string or null")
    require(type(value.get("trace_reviewed")) is bool, "trace_reviewed must be boolean")
    require(isinstance(value.get("notes", ""), str), "review notes must be a string")
    available = evidence(value.get("trace", []), root)
    return bool(text(value.get("reviewer")) and value["trace_reviewed"] and available)


def validate_metrics(value):
    if value is None:
        return
    fields(value, {"tokens", "elapsed_seconds"}, "metrics")
    for key, number in value.items():
        if number is None:
            continue
        valid_type = type(number) is int if key == "tokens" else type(number) in (int, float)
        require(valid_type and math.isfinite(number) and number >= 0,
                f"metrics.{key} must be nonnegative and finite or null")


def assess_row(row, scenario, contract, root):
    fields(row, {"scenario_id", "run_id", "status", "notes", "scores", "outcomes",
                 "hard_failures", "review", "metrics"}, "run")
    status = row.get("status")
    require(isinstance(status, str) and status in {"reviewed", "not_run", "blocked", "unverified"},
            "invalid run status")
    require(isinstance(row.get("notes", ""), str), "run notes must be a string")
    validate_metrics(row.get("metrics"))
    failures = row.get("hard_failures", [])
    allowed_failures = {f["id"] for f in contract["release"]["hard_failures"]}
    require(isinstance(failures, list) and all(text(f) for f in failures), "hard_failures must be an array of IDs")
    require(len(failures) == len(set(failures)) and set(failures) <= allowed_failures,
            "duplicate or unknown hard failure ID")
    reasons = [] if status == "reviewed" else [status]
    reviewed = review_available(row.get("review"), root)
    if not reviewed:
        reasons.append("trace-review-unavailable")
    scoring = contract["scoring"]
    dimensions = {d["id"]: d for d in scoring["dimensions"]}
    scores = row.get("scores")
    score_total = None
    score_complete = scores is not None
    if scores is not None:
        fields(scores, set(dimensions), "scores")
        score_complete = set(scores) == set(dimensions)
        for value in scores.values():
            require(type(value) is int and scoring["minimum_dimension_score"] <= value <= scoring["maximum_dimension_score"],
                    "scores must be integers within the contract range")
        if score_complete:
            score_total = sum(scores.values())
            if score_total < scoring["minimum_scenario_score"]:
                reasons.append("below-score-threshold")
        if any(d["critical"] and scores.get(key) == 0 for key, d in dimensions.items()):
            reasons.append("critical-zero")
    if not score_complete:
        reasons.append("scores-incomplete")
    outcomes = row.get("outcomes", {})
    expected = {o["id"] for o in scenario["observable_outcomes"]}
    fields(outcomes, expected, "outcomes")
    outcomes_complete = set(outcomes) == expected
    for key, observation in outcomes.items():
        fields(observation, {"met", "evidence"}, "outcome")
        met = observation.get("met")
        require(met is None or type(met) is bool, "outcome.met must be boolean or null")
        observed = evidence(observation.get("evidence", []), root)
        if met is None or not observed:
            outcomes_complete = False
        if met is not True:
            reasons.append(f"outcome-not-met:{key}")
    if not outcomes_complete:
        reasons.append("outcome-evidence-incomplete")
    if failures:
        reasons.append("hard-failure")
    complete = status == "reviewed" and reviewed and score_complete and outcomes_complete
    return {"scenario_id": scenario["id"], "run_id": row["run_id"], "status": status,
            "complete": complete, "passed": complete and not reasons,
            "score": score_total, "reasons": reasons, "hard_failures": failures}


def assess(contract, ledger, result_path, contract_hash, expected_skill_hash):
    fields(ledger, {"schema_version", "suite", "candidate_version", "contract_sha256", "metadata",
                    "structural_checks", "runs"}, "ledger")
    require(type(ledger.get("schema_version")) is int and ledger["schema_version"] == 1,
            "schema_version must be integer 1")
    for key, expected in (("suite", contract["suite"]), ("candidate_version", contract["candidate_version"]),
                          ("contract_sha256", contract_hash)):
        require(ledger.get(key) == expected, f"{key} does not match contract")
    root = result_path.resolve().parent
    metadata = ledger.get("metadata", {})
    fields(metadata, METADATA, "metadata")
    for key, value in metadata.items():
        require(value is None or text(value), f"metadata.{key} must be a nonempty string or null")
    skill_hash = metadata.get("skill_sha256")
    if skill_hash is not None:
        require(HASH.fullmatch(skill_hash), "skill_sha256 must be lowercase SHA-256 or null")
    if expected_skill_hash is not None:
        require(HASH.fullmatch(expected_skill_hash), "--skill-sha256 must be lowercase SHA-256")
        require(skill_hash is None or skill_hash == expected_skill_hash, "skill_sha256 does not match pinned hash")
    unavailable_metadata = sorted(key for key in METADATA if not text(metadata.get(key)))
    if expected_skill_hash is None:
        unavailable_metadata.append("expected_skill_sha256")
    structural = ledger.get("structural_checks", {})
    fields(structural, {"passed", "evidence"}, "structural_checks")
    require(structural.get("passed") is None or type(structural["passed"]) is bool,
            "structural_checks.passed must be boolean or null")
    structural_available = evidence(structural.get("evidence", []), root)
    structural_passed = structural.get("passed") is True and structural_available
    runs = ledger.get("runs")
    require(isinstance(runs, list), "runs must be an array")
    scenarios = {s["id"]: s for s in contract["scenarios"]}
    seen_scenarios, seen_runs, reports = set(), set(), []
    for row in runs:
        require(isinstance(row, dict), "run must be an object")
        scenario_id, run_id = row.get("scenario_id"), row.get("run_id")
        require(text(scenario_id) and scenario_id in scenarios, "unknown scenario_id")
        require(text(run_id), "run_id must be a nonempty string")
        require(scenario_id not in seen_scenarios, "duplicate scenario_id")
        require(run_id not in seen_runs, "duplicate run_id")
        seen_scenarios.add(scenario_id)
        seen_runs.add(run_id)
        reports.append(assess_row(row, scenarios[scenario_id], contract, root))
    missing = [key for key in scenarios if key not in seen_scenarios]
    complete = not missing and all(r["complete"] for r in reports)
    pass_count = sum(r["passed"] for r in reports)
    failures = sorted({f for r in reports for f in r["hard_failures"]})
    qualified = (complete and not unavailable_metadata and structural_passed and not failures
                 and pass_count >= contract["release"]["minimum_pass_count"])
    return {"valid": True, "qualified": qualified, "complete": complete,
            "scenario_count": len(scenarios), "pass_count": pass_count,
            "minimum_pass_count": contract["release"]["minimum_pass_count"],
            "missing_scenarios": missing, "unavailable_metadata": unavailable_metadata,
            "structural_checks_passed": structural_passed, "hard_failures": failures,
            "scenarios": reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--skill-sha256", help="independently pinned full frozen skills-subtree hash; omission blocks qualification")
    args = parser.parse_args()
    try:
        contract = load(args.contract)
        errors = validate_suite(contract, args.contract.resolve().parent)
        if not errors:
            errors += validate_package_versions(contract, args.contract.resolve().parent.parent)
        require(not errors, "; ".join(errors))
        report = assess(contract, load(args.results), args.results,
                        hashlib.sha256(args.contract.read_bytes()).hexdigest(), args.skill_sha256)
    except (OSError, UnicodeError, ValueError, OverflowError) as error:
        print(json.dumps({"valid": False, "qualified": False, "errors": [str(error)]}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    sys.exit(main())
