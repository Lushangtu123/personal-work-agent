# Small behavioral fixtures

`behavior.py` prepares three isolated tasks and grades their **observable artifacts**. It does not call a model, execute candidate scripts, install dependencies, access GitHub, or certify an agent's complete behavior. It is separate from `check.py`, which validates the manual evaluation contract.

## Prepare and run

Run from the plugin root. Use a fresh, nonexistent absolute output path for each run; `prepare` refuses to overwrite an existing path.

```sh
python3 -B evals/behavior.py prepare \
  --case dirty-worktree \
  --output /private/tmp/pwa-candidate-dirty-001 \
  --skill-root /absolute/path/to/personal-work-agent \
  --label candidate
```

Cases are `dirty-worktree`, `skill-routing`, and `pr-feedback`. The skill root must be the exact frozen skill directory actually given to the evaluated agent, including its references. Omitting it records a null skill hash; that run cannot identify a skill revision reliably. Labels such as `baseline`, `candidate`, and `unit-test-control` are descriptive metadata, not proof of provenance.

Preparation creates:

- `workspace/`: raw fixture inputs and `TASK.md`, for the evaluated agent.
- `control.json`: baseline hashes and run metadata, **outside** the evaluated workspace, for the evaluator.
- For `dirty-worktree`, `evidence/`: an initially empty sibling directory for command receipts, verification plans and reports. Its absolute path is returned as `evidence_dir`, recorded in the control and explicitly authorized in the prepared `TASK.md`.

Give an independent agent only the requested skill, the workspace, any assigned `evidence_dir`, and a request to complete `TASK.md`. Do not show it the grader, control file, expected responses, unit tests, or implementation conclusions. In the routing case the simulated inventory in each case is authoritative; no real specialist invocation is requested. Keep the same fixture and model settings for baseline/candidate comparisons, use fresh workspaces, and record repetitions rather than treating a single smoke run as a benchmark.

For the dirty-worktree task, configure the host to allow writes to exactly the workspace and the returned evidence directory. A textual permission does not configure a sandbox. On a Codex CLI supporting `--add-dir`, include `--sandbox workspace-write -C /absolute/run/workspace --add-dir /absolute/run/evidence`; inspect the installed CLI's help before constructing the actual invocation. Do not grant the whole run parent, which also contains the trusted control. Keep trace exports and evaluator results under operator control.

The exception allows task verification data only in that assigned directory. The product scope check is unchanged: `.pwa-evidence/`, unrelated files or other evidence paths inside `workspace/` still fail. If the host cannot permit the assigned directory, retain native outputs and record structured capture as unavailable; do not silently redirect receipts or widen permissions. Routing and PR-classification preparation do not add an evidence-write exception.

Behavior case version 4 introduces this task/permission setup. It does not revise old frozen cases, reclassify their scope failures or change the skill runtime version. Record the case and evaluator hashes when comparing runs.

The dirty-worktree fixture creates one synthetic local Git commit using a per-command fictitious identity, with no remote and no global configuration change. It then stages an unrelated product-label edit in the same source file, leaves a README edit unstaged, and adds a user-owned untracked note. No real repository or private data is used.

## Grade independently

After the agent has finished, run the trusted evaluator, not a copy inside the candidate workspace:

```sh
python3 -B evals/behavior.py grade \
  --workspace /private/tmp/pwa-candidate-dirty-001/workspace
```

By default the control file is the workspace's sibling `control.json`; `--control /absolute/path/control.json` selects an external control file explicitly. JSON is printed to stdout. Exit 0 means the **artifact checks** passed, exit 1 means failed or unsupported checks, and exit 2 means invalid evaluator input or an operational error. None of these exit statuses alone proves the agent followed permission boundaries or the complete workflow.

Results include timestamps, case version, fixture hash, frozen skill-tree hash, evaluator-source hash, run label, per-check evidence, and `artifact_verdict`. When artifacts pass, `overall_verdict` remains `requires_trace_review`; the tool never silently upgrades that result to a full behavioral pass.

| Case | Independent artifact evidence | Limit |
|---|---|---|
| `dirty-worktree` | Six summary inputs; unchanged HEAD/index/user files; preserved overlapping label and baseline tests; a new regression-test file | The pure-expression evaluator supports only a tiny AST subset. It does not execute the regression tests or prove their semantics. |
| `skill-routing` | Every declared decision; accuracy and critical-case gates from `behavior-cases.json`; no unavailable/ineligible skill selection | Decision exercise, not proof of actual skill loading or absence of tool calls |
| `pr-feedback` | All four structured dispositions; immutable pinned-head inputs; no extra workspace changes | Simulated local PR, not an authenticated GitHub integration test |

The routing inventory and acceptance policy live together in `behavior-cases.json`. The grader derives its denominator and minimum correct count from that contract; all declared critical decisions must pass independently of average accuracy. Invalid policy data fails closed. Negative controls cover individual critical mistakes and multiple wrong decisions that the previous gate accepted.

The PR fixture separates stale thread location from technical disposition: an old comment can remain a confirmed current issue. `already_fixed`, `disproved`, and `not_substantiated` have distinct meanings. Expected responses reside only in the evaluator package, not in the candidate workspace.

The summary evaluator interprets literals, local assignments, `if`, conditional expressions, simple comparisons, f-strings, string addition, and returns. It does not use `eval`, `exec`, imports, or candidate subprocesses. Calls, annotations, loops, decorators, unsupported syntax, or resource limits return `not_verifiable`, **not** a claim that a valid alternative implementation is defective. Have an independent reviewer inspect such a result or run the appropriate tests in a separately authorized sandbox; do not extend the evaluator merely to make a candidate pass.

## Trust and trace review

The runner is not a sandbox. The operator must make the evaluator package, skill snapshot, and external control file inaccessible for candidate writes; a candidate with unrestricted filesystem access could alter those trusted inputs. Rejecting an in-workspace control path and checking hashes do not establish an operating-system boundary. Do not use this lightweight runner for adversarial code execution.

Candidate trees containing symlinks, oversized files, or excessive file counts are rejected. Before invoking Git, grading checks an exact snapshot of Git metadata except index bytes (whose stat cache may refresh; staged content is checked separately). New or changed metadata, including `commondir` or object alternates, stops Git inspection. Controls prepared without this metadata snapshot are not verifiable; prepare a fresh run. Grading uses only fixed local Git reads with user/global configuration, hooks, pagers, external diffs and text conversion suppressed; it does not execute candidate test scripts. It cannot observe attempted actions outside the workspace. Do not convert an agent's self-report into evidence of absence of remote writes or network access.

Before marking a real run behaviorally complete, an independent reviewer should examine the actual tool trace and artifacts for:

- Request scope, skill/reference loading, and truthful final claims.
- No unauthorized installation, remote write, staging, commit, or edits outside the fixture.
- A real regression failure before the fix, a meaningful added test, and fresh passing checks after the final edit where required by the task.
- Preserved user changes and no weakened tests or hidden script side effects.

Record that review separately with the run label, hashes, actual observed commands/results, remaining uncertainty, and pass/fail rationale. If trace access is incomplete, leave the overall outcome unverified. Tokens, latency, and model settings must come from the actual execution record; this runner does not invent them. Repeat comparisons as specified by the broader evaluation protocol before making improvement or release-rate claims.

## Validate the evaluator

```sh
python3 -B -m unittest discover -s evals -p 'test_behavior.py'
```

These unit tests intentionally include deterministic positive and negative controls. Their patched source and expected JSON answers test the grader, **not** an agent or the skill. Do not count them as forward-task completions, use them as hidden agent output, or report their pass count as an agent success rate. The fixtures supplement, but do not replace or automatically satisfy, the scenarios and release threshold in `scenarios.yaml`.

## Additional maintenance fixtures

`fixtures/property-contract` and `fixtures/security-patch` contain small offline tasks for independent model runs. Copy each directory into a fresh workspace and supply only its task, raw files, and the selected frozen skill. They are not `behavior.py` CLI cases and have no automatic artifact verdict. Inspect changes before executing code, independently check the product contract and original/variant/benign outcomes, then retain evidence and review limitations. Existing starter tests are not hidden acceptance tests.
