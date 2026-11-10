#!/usr/bin/env python3
"""Generate synthetic, offline forward tasks; no model calls or grading."""

import argparse
import hashlib
import json
from pathlib import Path


CASES = ("large-log", "excerpt-recovery", "search-reassessment", "small-task")


def files_for(case):
    common = (
        "Use the selected Personal Work Agent skill to complete this read-only "
        "investigation. All inputs are synthetic. Write only findings.json in this "
        "workspace; do not edit inputs, install tools, access external services or "
        "change Git state. Return an object with target, outcome, explanation, "
        "evidence (an array of {path, start_line, end_line}), and limitations. "
        "Cite local evidence for the conclusion.\n\n"
    )
    if case in ("large-log", "excerpt-recovery"):
        lines = [
            f"2026-10-31T12:{n // 60 % 60:02}:{n % 60:02}Z INFO "
            f"request=background-{n:05} event=health status=ok worker=synthetic\n"
            for n in range(1, 8001)
        ]
        if case == "large-log":
            events = {
                117: "ERROR request=other-17 cause=PermissionError path=/unrelated",
                6821: "INFO request=req-7421 event=export_started",
                6822: "ERROR request=req-7421 event=write_failed cause=OSError errno=122 message=Disk_quota_exceeded",
                6823: "TRACE request=req-7421 frame=export.py:write_archive",
                6824: "INFO request=req-7421 event=export_finished outcome=failed artifact_created=false",
                7999: "INFO request=other-99 event=export_finished outcome=success artifact_created=true",
            }
            task = "Determine why export req-7421 failed and whether it created an artifact. The service log is logs/service.log. Diagnose only.\n"
        else:
            events = {
                22: "INFO job=job-508 event=request_accepted http_status=202",
                35: "INFO job=job-508 event=write_committed status=completed",
                7761: "ERROR job=job-508 event=post_commit_validation reason=checksum_mismatch",
                7762: "INFO job=job-508 event=compensation_completed artifact_removed=true",
                7763: "INFO job=job-508 event=job_terminal final_state=rolled_back",
                7999: "INFO job=other-509 event=job_terminal final_state=completed",
            }
            task = "Establish the final state of job-508 from the supplied summary and original log. Decide whether its output is retained. Diagnose only.\n"
        for line, event in events.items():
            lines[line - 1] = f"2026-10-31T14:00:00Z {event}\n"
        result = {"logs/service.log": "".join(lines), "TASK.md": common + task}
        if case == "excerpt-recovery":
            result["summary.json"] = json.dumps({
                "source": "logs/service.log", "job": "job-508",
                "reported_state": "completed", "covered_lines": [1, 40],
                "excerpt": [lines[21].strip(), lines[34].strip()],
            }, indent=2) + "\n"
        return result
    if case == "search-reassessment":
        return {
            "TASK.md": common + "Continue from HANDOFF.md. Locate the invoice amount parser actually used by app.py and explain how it handles '12.345'. Do not fix or refactor it.\n",
            "HANDOFF.md": (
                "Synthetic prior-session record supplied as task context:\n"
                "1. Looked for src/payments/amount.py: path absent.\n"
                "2. Looked for src/payments/amounts.py: path absent.\n"
                "3. Searched parse_amount under src/payments: directory absent.\n"
                "The old README location has not located the live parser. No changes made.\n"
            ),
            "README.md": "Legacy location: src/payments/amount.py, parse_amount. This note predates the package move.\n",
            "app.py": "from billing.money import parse_minor\n\ndef invoice_amount(text):\n    return parse_minor(text)\n",
            "billing/__init__.py": "",
            "billing/money.py": (
                "from decimal import Decimal\n\ndef parse_minor(text):\n"
                "    amount = Decimal(text)\n"
                "    if not amount.is_finite():\n"
                "        raise ValueError('finite amount required')\n"
                "    minor = amount * 100\n"
                "    if minor != minor.to_integral_value():\n"
                "        raise ValueError('at most two decimal places')\n"
                "    return int(minor)\n"
            ),
        }
    if case == "small-task":
        return {
            "TASK.md": common + "In summary.py, what exact string does summarize(1) return? Explain only; no performance investigation is requested.\n",
            "summary.py": (
                "def summarize(count):\n"
                "    noun = 'category' if count == 1 else 'categories'\n"
                "    return f'{count} suspicious {noun} detected.'\n"
            ),
        }
    raise ValueError("Unknown case")


def prepare(case, output):
    if not output.is_absolute():
        raise ValueError("Output must be a fresh absolute workspace path")
    files = files_for(case)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name, content in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = content.encode("utf-8")
        path.write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    return {"case": case, "workspace": str(output), "input_sha256": hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.case, args.output), indent=2))


if __name__ == "__main__":
    main()
