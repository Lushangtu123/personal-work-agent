# Operational readiness at the requested boundary

Read for a service-readiness plan/review or changes affecting runtime lifecycle,
capacity/resource limits, observability, backup/restore, or rollout/recovery.
Mere presence of a server does not trigger every check. Skip unrelated local fixes.
Use [quality-contract.md](quality-contract.md) for targets and authority; retain
the repository's own runbooks, SLOs, deployment constraints and native tools.

## Select the applicable checks

For each relevant row retain `target → exact revision/config/environment → check
and bounds → observation → passed/failed/blocked/not-run`. Explain genuine
not-applicability. Out-of-scope is not passed, unknown is not zero, and a script
or configuration existing is not an exercised control. An old passing record is
usable only where the relevant code, config, workload and environment still match.

| Concern | Evidence to seek when applicable |
| --- | --- |
| Startup and shutdown | Readiness reflects ability to serve, distinct from process liveness. Startup/dependency failure, termination, draining, cancellation, resource release and in-flight work follow the contract; a 200 health endpoint alone is insufficient. |
| Capacity and sustained operation | Representative data, concurrency, request rate and duration; latency/throughput plus error rates and CPU/memory/queue/storage trends. Bound overload and backpressure at the actual resource. A short unit test or one fast request does not establish steady-state behavior or absence of leaks. |
| Dependency failure and recovery | Controlled timeout/disconnect/restart under the agreed workload, observable fault activation and recovery, bounded retries and correct durable state. Reuse [backend-reliability.md](backend-reliability.md); do not stack a circuit breaker or retry library without a need. |
| Data recovery | Restore an owned backup into an isolated target, validate integrity and authorized access, and observe recovery time and actual lost/replayed data against RTO/RPO. Backup-file existence, a successful backup command or a scheduled restore job does not prove restoration. |
| Observability and response | Useful nonsecret errors, request/job correlation, agreed service/resource signals, actionable thresholds and response ownership. Exercise an alert path in an authorized test sink if claiming alert delivery; configuration alone proves no delivery or response. |
| Release and rollback | Artifact/config identity, applicable old/new schema/consumer compatibility, a bounded rollout and a credible rollback or forward-recovery path. Exercise relevant migration/recovery on disposable data when authorized; reverting code alone may not reverse data changes. |

Tests must cover useful legitimate behavior alongside failure handling. Choose
only the checks justified by the service contract and changed risks; do not demand
every scenario, a new monitoring service or production-grade availability from a
personal prototype. If a goal matters but is unspecified, keep readiness for that
goal unresolved; a proposed threshold is not a verified requirement.

## Safe execution and evidence

Inspect script chains, fixtures and dependencies under [permissions.md](permissions.md)
and [execution-preflight.md](execution-preflight.md) before execution. A request to
review readiness authorizes source/evidence inspection, not live fault injection,
load tests against shared systems, restore over existing data, migrations, deployment,
alert delivery to people or external probes. Use owned synthetic targets within
the actual host limits; missing tools or isolation do not authorize installation,
credentials, network expansion or disabled safeguards.

Bound workers, data volume, rate, disk/memory use and elapsed time for the intended
check. Name how it stops and how only this run's fixtures are cleaned up. A model's
claimed budget is not an OS resource limit. Retain the actual command/interaction,
source and fixture identities, initial/final state, observed faults and diagnostics.
Capture command facts using [command-evidence.md](command-evidence.md); native
interaction and semantic acceptance still require their own observations.

Prefer one meaningful controlled failure/recovery per affected boundary over a
large ceremonial checklist. Keep substitute tests useful but labeled: a fake
clock can establish retry arithmetic, not real elapsed service recovery; local
SQLite restore does not establish production PostgreSQL restore. Failed setup and
an untriggered fault are blocked/unexercised, not successful recovery.

## Readiness statement

Report the highest state demonstrated: plan prepared, implemented, locally
functionally verified, or operationally verified for the named environment and
goals. Do not combine unrelated passing fragments into an end-to-end claim or
carry a worker's green summary across a changed configuration. Show the remaining
failed, blocked and not-run goals, owner/next check and required authorization.
An agreed local release may be complete while production readiness remains open;
this does not waive an agreed production requirement or authorize deployment.
