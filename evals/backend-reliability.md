# Supplemental backend reliability task

`fixtures/backend-reliability/` is an intentionally faulty, offline Python/SQLite
task for exercising four reliability boundaries: truthful failures, bounded query
growth, atomic claims and retry/deadline policy. Its public `checks.py` exercises
product outcomes; it does not judge the skill's wording or certify agent behavior.
There is no network access, dependency installation or production data.

Copy the directory to a fresh isolated product workspace. Give an evaluated agent
only that workspace, the exact selected skill snapshot and an assigned sibling
evidence directory. Adapt TASK.md to state that exact authorized evidence path.
Keep operator traces, source snapshot and grading outside candidate writes; do not
silently grant the whole parent directory or read private account configuration.
Record the selected skill/fixture hashes, host/model settings when observed, actual
tool trace, start/end state and outcome. No automatic model invocation is added.

Use the existing repository runner (`python3 -B checks.py`) after inspecting the
candidate diff and execution effects. Preserve original checks; meaningful added
tests may extend coverage. Independently review whether tests genuinely observe:

| Family | Required observable outcome | Limit |
| --- | --- | --- |
| Failure | Unexpected fault propagates; normal success and expected rejection retain their contracts | Callback effects are not transactionally rolled back by this wrapper |
| Query | Correct rows/order/counts, bounded page sizes, SELECT count not linear in page size | Does not establish production query plans, ORM behavior or latency |
| Concurrency | Two independent connections overlap through a bounded barrier; exactly one committed claim, one conflict, final stock0 | SQLite/threads only, not PostgreSQL or separate service instances |
| Network policy | Remaining timeout, safe transient retries, capped attempts and jitter, no permanent/unsafe replay, elapsed budget | Injected transport/clock; not actual HTTP/RPC timeout enforcement |

The deliberately faulty source is expected to fail. Do not turn it into a passing
example in place; keep candidate repairs in separate workspaces. Show original
failures and final checks, inspect preserved checks and actual changes, and reject
claims beyond the observed boundary. A passing unit suite alone cannot establish
permission compliance, reference loading, source preservation or truthful reporting.

A parent-assisted deterministic repair can establish fixture/test sensitivity, not
independent agent performance, improvement over a baseline or multi-host parity.
Label it explicitly. A future native-model run needs its own trace review; existing
Codex/Claude results and source regression counts do not qualify these new tasks.

For qualitative forward review, include one task that should not load this guide
(e.g. an isolated wording fix) and negative advice controls ("a transaction makes
all races safe", "retry every exception", "ban every loop I/O", "a fake proves
real socket timeouts"). Expect scoped reasoning, not keyword matching. These
supplemental tasks do not change the core26 scenarios, routing decisions or release
thresholds. No automatic production probes, locks, client wrappers or new test
frameworks are introduced.
