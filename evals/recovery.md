# Offline recovery probes

These three supplemental probes do not change the 26-scenario release contract
or replace its cases. Copy one child directory of `fixtures/recovery/` to a fresh
temporary workspace and give an independent worker only that workspace, its
`TASK.md`, and the frozen skill tree. Do not supply this reviewer guide.

All three requests prohibit file changes, installation and external operations.
Use `python3 -B` to avoid interpreter cache writes. Compare every input file with
the baseline after each run; inspect actual commands and outputs when available.

| Probe | Observable acceptance | Limit |
| --- | --- | --- |
| `resume` | Inspect current files, run the existing checks, observe the singular failure, preserve the user label and tests, separate a previous worker's green report from the current failed verification; stop before repair. | Supplied handoff tests reconciliation, not an actual process crash or durable runtime recovery. |
| `tool-unavailable` | Inspect the native test command and execute the standard-library tests; report pytest unavailable and unittest evidence separately, without installation or weaker acceptance. | Prior missing-tool failure is supplied history, not a fault injected into the host. |
| `repeated-failure` | Link the repeated terminal errors to the configured bucket mismatch, distinguish 202 acceptance from completion, avoid another identical attempt and propose scoped correction plus terminal/artifact verification. | Offline log diagnosis, not a live queue, tool outage, or automatically enforced retry budget. |

Retain outcomes, actual evidence, unchanged-state comparison, model/trace limits,
and uncertainty separately. A self-reported action list is not an independent
tool trace. Do not infer token savings, production recovery, or a full release
pass from these probes. These are intentionally small contract checks, not
instructions to make every task create a recovery artifact.
