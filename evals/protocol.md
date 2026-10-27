# Evaluation Protocol

## Deterministic gate

Run from the plugin root:

```bash
python3 evals/check.py
python3 -m unittest discover -s evals -p 'test_*.py'
```

The checker is read-only and uses only the Python standard library. It validates
the scenario contract, score arithmetic, coverage, mutation boundaries,
observable-outcome structure, hard-failure references, fixture containment, and
release threshold. The CLI also checks that candidate, skill metadata, and plugin
base versions agree; only the manifest may carry a Codex cachebuster suffix.
Booleans are not accepted as integer scores or counts. The unit suite includes positive and negative controls so a
passing validator is also shown to reject malformed contracts.

`scenarios.yaml` is deliberately JSON-compatible YAML. Preserve strict JSON
syntax: double-quoted keys and strings, no comments, and no trailing commas.
This keeps the release gate portable without adding PyYAML.

The separate Codex Skill and plugin validators remain required packaging checks.
They require a Python environment with PyYAML; use the Python path returned by
the Codex workspace-dependency loader rather than a user-specific absolute path.

## Forward evaluation

Before a run, record which tool/event types its export actually retains. Keep
CLI stdout JSONL and stderr separately, plus native image/interaction events
when the host exposes them. Missing tool-event coverage is an evidence gap,
not proof that an action occurred or that the agent fabricated it. For final
claims, reference the actual command receipt or native observation; a generated
inspection summary is not independent evidence. Evaluate command history and
visual coverage separately from successful artifact generation. Supplemental
review remains a new observation and never backfills the original run.

The deterministic gate does not run an agent and does not claim that natural
language behavior is correct. Evaluate each scenario in an isolated task or
temporary fixture with the same candidate Skill version, model, reasoning level,
tool availability, and permission policy.

For every run, retain:

- scenario ID, candidate version, Skill hash, model version, and Codex version;
- fixture commit or source revision and initial dirty-worktree state;
- actual changed paths and any external mutations;
- commands or inspections used as evidence, including exit status and scope;
- outcome observations, per-dimension scores, hard-failure IDs, and reviewer
  notes.

Use the scenario's `allowed_mutations` as an upper bound, not a requirement to
edit. A diagnostic scenario with `local: none` must leave the workspace
unchanged. The contract scenarios allow no external mutation.

The optional `allowed_mutations.verification_evidence` is `none` when omitted.
`runner-provided-directory` authorizes verification records only in the exact
task-owned directory assigned outside the product workspace and named in the
prepared request. It does not add a product `path_classes` entry or authorize
remote changes. The operator must also provide that exact sandbox write path;
the contract field alone grants no filesystem access. Without an assigned path,
the field is not permission to choose another directory. Review evidence content
and the actual trace separately; merely placing a file there does not justify it.

When a fixture-backed scenario is added, its path must resolve inside `evals/`.
Fixture checkers should copy the fixture to a temporary directory, use argument
arrays rather than shell command strings, set fixed working directories and
timeouts, and verify outcomes rather than exact implementation text.

## Executable smoke fixtures

See [behavior.md](behavior.md) for the dependency-free `behavior.py` prepare/grade
workflow. It covers a real dirty Git worktree, a contract-sized routing exercise,
and pinned-revision PR feedback classification. Preparation makes an isolated
workspace; an independent agent performs the request; grading inspects the
result. Unit tests of the grader are not agent runs.

Give the evaluating agent only the request, selected skill, and prepared
workspace, not the intended answer, grading implementation, or control record.
Keep control records outside its permitted writes. These directories are an
ownership boundary, not an OS sandbox: review the host's actual tool trace for
unobserved reads, writes, network activity, and permission decisions.

For a baseline/candidate comparison, prepare a fresh workspace for each run and
pin the matching skill snapshot/hash. Do not silently let a catalog-provided old
copy replace the candidate. Keep model configuration and available tools equal,
record unavailable metadata honestly, and retain raw outcomes separately from
aggregate counts. Use three repetitions per version for a release comparison.

These three focused fixtures supplement rather than replace `scenarios.yaml`.
They do not exercise every office, investment, authorization, or live GitHub
case. Report artifact checks, routing choices, trace review, manual-contract
coverage, and baseline comparison separately. A smoke pass permits a local
development trial, not a claim that all declared scenarios or the release
rubric passed. A hard failure blocks that claim regardless of averages.

## Limits of automation

Do not treat structural validation as evidence that the Skill was selected,
loaded the right reference, found the true root cause, made a sound investment
inference, produced a good narrative, or paused at the correct live approval UI.
Those require independent forward runs and human review. Model-generated runs
are nondeterministic and consume account resources; they are not part of the
default deterministic gate.

## Retain and check a behavioral results ledger

Use [results.md](results.md) and the read-only `results.py` validator to record
one row for every declared scenario, including unexecuted and blocked tasks.
The validator derives counts and thresholds from the frozen contract. It does
not run an agent, produce scores, or authenticate a reviewer's evidence.
Preserve the original contract and skills snapshot for each historical run;
never relabel a 0.8.0 trial as a 0.8.1 run after changing package metadata.

The [recovery probes](recovery.md) supplement the release cases. Their supplied
histories exercise reconciliation and next-action decisions; they are not
proof of recovery from a real process crash, live tool outage, or queue failure.

The [targeted maintenance probes](maintenance-probes.md) add command-chain,
safe-execution and environment-plan checks. Use repeated fresh runs, a semantic
holdout and a pinned real-repository subset when evaluating these corrections.
Report these lanes separately, with reviewer independence and human-review
limits. Do not rewrite old-version results, mix assisted and autonomous runs,
or call a targeted pass a full-suite or packaging qualification.

The [workflow probes](workflow-probes.md) exercise scoped architecture
assessment, issue-to-brief intake and approved-change continuation. They add
no live tracker, install or external-write permission and retain the same
separation between tool tests, agent observations and release qualification.
