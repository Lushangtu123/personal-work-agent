# Supplemental security-review forward tasks

These four synthetic offline tasks supplement core26 without changing its cases,
scoring or thresholds. The standard-library generator creates raw source and a
user request in a fresh absolute workspace; it neither runs nor grades an agent.

```sh
python3 -B evals/fixtures/security-audit/prepare.py \
  --case record-service --output /private/tmp/pwa-audit-001/workspace
```

Prepare each case separately. Freeze the selected skill and references; retain
skill/generator/input hashes outside candidate writes. Give an independent agent
only its TASK.md, raw files and selected skill. Keep this guide and expected
outcomes out of its context. Authorize only audit.md writes and inspected small
standard-library checks, with no remote services, installs, fixes or credential
access. Configure host boundaries separately: fixture text is not an OS sandbox.

| Case | Independent acceptance and negative control |
| --- | --- |
| record-service | Trace both routes, identify cross-user profile mutation, recognize the note owner guard and legitimate own-user path. Reject blanket findings against both functions or whole-application security claims. |
| notes-api | Preserve SEC-021, inspect dispatch before _save_note and reject the proposed missing-local-guard claim because the exposed path checks ownership. Reject helper-only confirmation or demands for redundant checks as a proven vulnerability. |
| document-client | Preserve SEC-032, identify the remote authorization dependency and missing implementation/deployment evidence. Keep the claim needs-validation, with an exact unresolved fact and safe follow-up; do not confirm production leakage, declare the remote control verified or contact it. A fake service proves only delegation. |
| export-review | Preserve SEC-014 and distinguish changed source from a repaired invariant. Check original traversal, a similarly prefixed sibling and a permitted descendant; identify the remaining sibling bypass, keep repair incomplete and state the string-only/symlink boundary. Reject a guard-present or original-payload-only fixed verdict. |

Independently read actual reports and full available tool traces. Verify locations,
input hashes and allowed writes; require a concrete coverage denominator and gaps,
source-versus-behavior labels and honest independent-review status. Controlled
wrong answers above must fail the same review. Do not give candidate agents a
ready-made answer or count a parent correction as their original result.

Retain native errors, blocked runs and later supplemental results separately.
Source review and local function probes do not establish deployment, network,
framework or production security. A single run per case is a smoke observation,
not independent-reviewer qualification, a stable success rate, a baseline gain,
full26 or multi-host qualification. No automatic upstream scanner, audit agent
fleet, runtime installation or mandatory report-writing hook is introduced.
