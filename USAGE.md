# Personal Work Agent

This source package contains two automatically discoverable skills: `personal-work-agent` for orchestration across code and knowledge work, and `project-builder` for new software projects from brief to verified first release.

## Validate the source

Run validation from this plugin directory with a Python interpreter that can import both `yaml` and `jsonschema`:

```bash
python3 -c 'import yaml, jsonschema'
```

If the default interpreter cannot import them, use a project virtual environment or, in Codex Desktop, load the workspace dependencies and use the Python executable it reports. Installing packages is not required when a suitable existing interpreter is available.

Locate the system Skill Creator directory under the active Codex home and run its validator. Run the plugin validator too when Plugin Creator is actually available:

```bash
PYTHON_BIN=/path/to/python3
SKILL_CREATOR_DIR=/path/to/skill-creator

"${PYTHON_BIN}" "${SKILL_CREATOR_DIR}/scripts/quick_validate.py" skills/personal-work-agent
"${PYTHON_BIN}" "${SKILL_CREATOR_DIR}/scripts/quick_validate.py" skills/project-builder
python3 -B evals/check.py
python3 -B evals/check.py --manifest-only
python3 -B -m unittest discover -s evals -p 'test_*.py'
```

Skill Creator checks skill packaging. If available, run Plugin Creator's `scripts/validate_plugin.py` on this package using the resolved interpreter. If absent, report that packaging-check limitation and validate the manifest, paths, and installed result using supported host tooling; do not invent a helper path or install another plugin merely to validate. The last three commands run the dependency-free evaluation-contract/version gate, the PWA manifest gate, and unit tests. Passing those unit tests does not mean the agent passed the task scenarios. See `evals/protocol.md` and `evals/behavior.md` before running independent model-based forward evaluations.

Version 0.9.1 repairs listing metadata and adds the explicit `--manifest-only` gate for field types/lengths, prompt forms, the local skills directory and bundled SVG icon paths, size and square dimensions. This gate currently supports PWA's SVG icons; it is not the complete host schema or a public-directory submission certificate. It follows the [official listing limits](https://developers.openai.com/plugins/deploy/submission). Workflow instructions and scenario criteria are unchanged apart from version metadata. Frozen 0.9.0 run records remain historical evidence, not a fresh 0.9.1 qualification.

The behavioral tool prepares isolated dirty-worktree, skill-routing, and PR-feedback tasks, then grades actual agent-produced outputs. It does not launch a model or contact GitHub. Keep grader/control files outside the evaluated agent's allowed writes and review its tool trace separately. The release rubric and thresholds in `evals/scenarios.yaml` remain a separate, broader requirement. Additional offline property-contract and security-patch fixtures require independent inspection rather than this artifact grader.

The [0.3.0 local smoke record](evals/results/2026-09-17-v0.3.0-smoke.json) retains actual independent-agent artifacts and final grader outputs. It is scoped evidence, not a claim that the full behavioral release gate or a baseline comparison passed.

Version 0.8.1 added a [behavioral result ledger](evals/results.md). It retains the full scenario denominator, requires evidence and trace review before a case can count as passed, and keeps missing provenance or blocked work explicit. The [offline recovery probes](evals/recovery.md) check stale handoffs, unavailable tooling, and repeated failed jobs. These additions support verification; they do not establish a full-suite pass or add background execution.

Version 0.8.2 adds conditional [execution preflight](skills/personal-work-agent/references/execution-preflight.md): inspect relevant command implementations/hooks, ground citations in actually read source, distinguish missing prerequisites from product failures, and recover in an explicitly authorized environment. See [maintenance regression probes](evals/maintenance-probes.md) for repeated, control, holdout and real-repository checks. Historical runs and later reviewer-assisted verification stay separate. This does not add a scheduler, autonomous runtime, automatic installs, or new external-action permissions.

The usual system-skill locations are beneath `${CODEX_HOME}/skills/.system/` when `CODEX_HOME` is set, or the corresponding `.codex/skills/.system/` directory in the current user's home directory.

Version 0.8.3 adds a bundled [command evidence helper](skills/personal-work-agent/references/command-evidence.md) for multi-command verification, retries and precise runtime versions. It captures authorized commands and derives facts from records, marking missing/mismatched evidence unverified instead of accepting model-supplied result values. It is not a sandbox or a universal free-text interceptor, and adds no automatic hook, retry or dependency. Tests of this helper are not a new full-suite qualification.

Version 0.8.4 repairs handled cancellation of the command group on POSIX, adds Python `-B` version-query support, and narrows output evidence to a captured text snapshot. It writes v2 receipts but can read existing v1 receipts. Interrupted execution remains uncertain for remote effects; capture does not supervise background jobs or prove whole-task completion. See the [helper's cancellation and snapshot limits](skills/personal-work-agent/references/command-evidence.md).

## Use during development

Version 0.9.5 moves verification preflight before the first check, keeps missing evidence unverified, and narrows the separate CodeGraph companion to explicit configuration files with a content-free DSH probe. These remain task-time instructions/helpers, not automatic host enforcement; actual model behavior needs separate acceptance.

Version 0.9.4 adds [host compatibility](skills/personal-work-agent/references/host-compatibility.md). Claude Desktop imports one ZIP per skill through Customize > Skills; copying the Codex plugin cache into `~/.claude/skills` is not a Desktop account-skill install. DeepSeek Harness loads the selected direct skill directories from its verified provider roots. Local CodeGraph MCP and hosted chat execution remain separate capabilities. Exported packages and local folder updates do not establish live connection, task success or token savings on a new host.

Version 0.9.3 adds conditional [CodeGraph navigation](skills/personal-work-agent/references/codegraph-navigation.md) for substantial cross-file call paths and impact discovery. PWA uses an already-available graph capability, checks its freshness limits, reconciles relevant source, and retains normal tests. A missing graph falls back to native search; ordinary work does not install CodeGraph, index repositories, register MCP or add hooks. The separate `../skill-overrides/codegraph-bootstrap/` companion describes native setup for macOS/Linux/Windows with Codex as the default target. Updating this plugin alone does not install the companion or CodeGraph runtime. Token savings and unchanged quality require a separate matched pilot; the historical 0.9.2 full-suite result is not a 0.9.3 qualification.

Version 0.9.0 adds conditional [architecture assessment](skills/personal-work-agent/references/architecture-assessment.md) and [issue intake](skills/personal-work-agent/references/issue-intake.md), not another orchestrator or a bulk installation of upstream skills. Assessments and triage remain read-only unless the concrete implementation or tracker action is authorized. Existing clarification, TDD and handoff reuse the same accepted contract. The [offline workflow probes](evals/workflow-probes.md) provide scoped forward checks, not a full release qualification.

```text
用 $personal-work-agent 评估导入模块最值得改善的架构问题，只给建议，不修改代码。
用 $personal-work-agent 整理这个 Issue：核对现状、重复问题和验收标准，形成执行简报，不发评论或改标签。
用 $personal-work-agent 根据已确认的任务简报继续修复，先核对当前文件与旧交接证据，不重新访谈。
```

The entry skill is `personal-work-agent`. Its default prompt is:

```text
Use $personal-work-agent to route and complete this task with the appropriate workflow, permissions, and fresh verification evidence.
```

Edit `skills/personal-work-agent/references/user-profile.md` to add non-secret personal preferences. Do not store passwords, tokens, cookies, private keys, recovery codes, or one-time codes.

### Build a project from scratch

Use either entry, resolving its actual namespace from the current skill catalog:

```text
用 $personal-work-agent 从零构建一个个人阅读清单工具，先完成可本地运行和验证的首版。
用 $project-builder 在指定目录构建一个 Python CLI，复用下面已确认的需求，不安装第三方依赖。
```

PWA routes new projects and unfinished initial builds to Project Builder when available. The builder can also work directly; it does not require an extra worker, MCP server, or cloud connection. It reuses confirmed decisions, checks the target directory, builds end-to-end slices, verifies their observable outcomes, and returns setup/evidence/gaps. After the first release, PWA normally handles later work as maintenance. Plan-only requests do not create a scaffold. No dependency installation, commit, push, or deployment is automatically authorized.

PWA passes relevant personal preferences as defaults, not mandatory dependencies; explicit platform and product requirements take priority. If the new skill is not yet visible in the current session, use a fresh task after installation or PWA's native bootstrap fallback. The routing rule is not proof that a session has actually loaded the skill.

### Review the workflow and retain project knowledge

Version 0.8 adds two conditional references, not another orchestrator or a bulk install of AI Hero skills:

```text
用 $personal-work-agent 复盘这次任务：只根据实际记录提出改进，先不要修改任何文件。
用 $personal-work-agent 把刚才确认的术语和重要设计决策更新到项目现有文档，保留未决问题，不改代码。
```

Retrospectives cite concrete evidence, may find no actionable change, and keep suggestions separate from authorized implementation. They do not run after every task or install hooks. Vocabulary and lasting decisions reuse existing project docs; no fixed `GLOSSARY.md`/ADR layout is required. Project Builder consumes the same guidance without routing back to PWA, and carries exact requirements and document pointers through handoff. Plan/review-only requests remain read-only unless a saved deliverable was requested. These locally authored adaptations are inspired by AI Hero's public methodology; no upstream skill code or new runtime dependency is bundled.

For coding work, the orchestrator checks specialist availability before delegation, handles PR comments against the current revision, uses version-aware maintenance guidance, and applies a minimal-correct-change ladder when token or implementation size matters. It may use Ponytail or Caveman when they are already installed and applicable, but neither is required. MarkItDown remains an optional semantic extraction helper, and Caveman 2 or another interception layer is never installed or globally enabled implicitly.

The token-efficiency policy keeps the original quality gates: fewer tokens, fewer lines, or a smaller converted artifact do not establish correctness. Savings claims require matched provider-level measurements, and compressed or converted inputs must remain recoverable.

For transformations with meaningful invariants, conditional test-strategy guidance adds replayable property checks using existing tools. For identified security repairs, conditional validation checks the original defect, same-root variants, legitimate behavior, and nearby regressions. Neither workflow automatically installs a testing framework or launches a broad security audit. Optional Trail of Bits specialists are used only when actually available and applicable.

Reusable output templates live under `skills/personal-work-agent/assets/templates/`. The copies in the plugin-level `templates/` directory are retained for backward compatibility.

Version 0.6 adds proportional clarification, lightweight test-value review, and conditional cross-boundary functional acceptance. Clear localized requests still receive normal verification; a successful HTTP response is not proof of an asynchronous business outcome. Skill inventory/update requests additionally check provenance, complete affected-package coverage, side effects, and rollback material without automatically migrating the library or syncing other agents.

The companion personal brainstorming source is maintained outside this plugin at `../skill-overrides/brainstorming/SKILL.md`. Updating the PWA plugin alone does not replace an independently installed brainstorming skill. Review and update that exact installed skill separately, with a backup and host approval, when adopting the companion change.

## Update the installed local plugin

First validate the edited source. Then confirm that the personal marketplace entry points to the local plugin source being updated. If this working copy is not that source, deliberately sync the validated files to the referenced local source before continuing; do not edit the generated Codex cache directly.

Read the configured marketplace and resolved source with the supported local CLI:

```bash
codex plugin marketplace list
codex plugin list
```

Set the manifest's base version for the update, keeping skill metadata and the evaluation candidate version aligned. If a same-version refresh needs a cachebuster and Plugin Creator supplies `scripts/update_plugin_cachebuster.py`, use that helper on the marketplace-referenced source instead of inventing a suffix. Its absence does not block a new base-version update.

```bash
codex plugin add --help
codex plugin add personal-work-agent@<verified-marketplace-name>
codex plugin list
```

Use the installed CLI's supported install command, or the desktop Plugins Directory when needed. The default personal marketplace is discovered automatically; do not add it again. Updating the marketplace source and reinstalling modify Codex state outside this working copy, so obtain required host approval immediately before those actions. Check the installed version and content, then start a new task; restart the app if its catalog remains stale. Never claim a current session has reloaded based only on source edits. See the [official local-plugin packaging guidance](https://developers.openai.com/plugins/build/plugins).

## Evidence reports in 0.9.2

The command helper can render a verification block with `report --format markdown`
and compare a saved block with original receipts using `--check-markdown`.
Schema-v2 plans keep missing native visuals, interactions, command history and
acceptance as explicit gaps. See the skill's `references/command-evidence.md`.
These are explicit task-time checks, not an automatic final-message hook or a
claim that every exported CLI trace includes every native tool event. The
0.9.1 full-suite report remains historical; 0.9.2 needs its own behavioral evidence.

For lifecycle reports, current success does not establish an uninterrupted history. PWA 0.9.6 separates observed calls, event occurrence and recovery, preserving unknown history when same-run evidence is unavailable. This is task-time guidance, not an automatic host-level response interceptor.

PWA 0.9.7 also separates source/response agreement from cache behavior: changed responses and matching source do not establish a cache miss or bypass. Cache conclusions require same-run telemetry scoped to the relevant layer and requests.
