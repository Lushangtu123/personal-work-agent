# Supplemental retrieval and tool-efficiency tasks

These offline forward tasks supplement the core26 contract; they do not change
its cases, scoring or release thresholds. No fixed tool-call quota is graded.
The generator uses only the standard library, creates synthetic inputs in a new
workspace and refuses an existing output. It does not run a model or grade one.

From the plugin root, prepare each case in a separate fresh absolute directory:

```sh
python3 -B evals/fixtures/token-efficiency/prepare.py \
  --case large-log --output /private/tmp/pwa-log-001/workspace
```

Cases are `large-log`, `excerpt-recovery`, `search-reassessment`, and `small-task`.
Freeze the selected skill including references; retain its hash, the generator
hash and returned input hashes outside the candidate workspace. Give an independent
agent only TASK.md, raw workspace inputs and the chosen skill. Do not show it this
review guide, controls or expected answers. Permit only findings.json writes in
the workspace; configure the host sandbox separately. Skill instructions and
fixture text do not establish an operating-system read boundary.

Inspect findings and the actual tool trace against these independent criteria:

| Case | Required outcome and trace evidence |
| --- | --- |
| large-log | Locate req-7421's quota failure and failed/no-artifact outcome using relevant original lines; do not mistake unrelated permission errors or later successes for this request. Retrieve bounded relevant evidence without dumping 8,000 lines. |
| excerpt-recovery | Inspect the incomplete summary and original source, discover job-508's later checksum failure, compensation and rolled-back terminal state; the summary's completed claim must not override later raw evidence. |
| search-reassessment | Treat the supplied handoff as prior reported context, stop guessing absent src/payments paths, locate the live app.py import and billing.money parser, and correctly explain rejection of excess precision. Alternative useful searches are valid. |
| small-task | Read the small source directly, give the exact singular sentence, and avoid broad discovery, extra specialists or an invented performance investigation. |

For every case, check cited path/line ranges against raw inputs and independently
verify all input hashes are unchanged, with only findings.json added. Review
scope, evidence loading and final claims separately from artifact correctness.
Preserve observed failures and incomplete traces; output alone cannot establish
efficient tool behavior. Controlled negative answers (unrelated error, summary-only
success, stale path and incorrect singular sentence) must fail the same acceptance
review; do not provide them to the evaluated agent.

Unit tests verify fixture integrity and overwrite protection only. A single native
run per case is a smoke observation, not a success-rate estimate, baseline
improvement, full release qualification, multi-host parity or net token savings.
For savings claims, use repeated matched baseline/candidate runs with the same
model/settings, complete provider usage, retries, setup cost and unchanged quality
gates. Retain actual events and usage outside product files; unavailable telemetry
stays unknown. Do not infer savings from shorter answers or fewer tool calls.
