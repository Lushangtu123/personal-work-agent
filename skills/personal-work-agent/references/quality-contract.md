# Quality goals for the agreed project

Read when defining a maintained project's first release, a material architectural
or operating change, or an explicit quality/readiness plan. Skip for a localized
wording, presentation or pure-logic task with an already clear contract. Reuse the
existing brief, service objectives, tests and operating constraints; do not launch
a second intake or create a separate quality document by default.

## Turn relevant risks into observable goals

Identify prototype versus maintained product, local versus shared service, data
sensitivity, expected workload and promised recovery. Select only dimensions that
can change architecture or acceptance:

| Dimension | Useful contract detail |
| --- | --- |
| Reliability | Required final state, failure/cancellation behavior, duplicate handling and data invariants |
| Capacity and responsiveness | Workload/data size, concurrency, latency percentile or throughput, duration and CPU/memory/storage bounds |
| Recovery | What data must survive, backup scope, maximum tolerated data loss (RPO) and restoration time (RTO), where required |
| Security | Actors, protected assets, authorization/trust boundaries and sensitive-data handling |
| Maintainability | Supported runtimes/consumers, existing design and dependency constraints, public interfaces and regression protection |
| Usability/accessibility | Relevant user journeys, keyboard/error states and agreed platform requirements |

For each relevant goal record `requirement/source → target with units → workload
and environment → verification → status`. Mark its authority as `accepted`,
`proposed` or `unknown`; an agent's suggested number is not user approval. Keep an
existing exact target through implementation and handoff. A percentile needs a
sample/window and workload; an RTO/RPO needs a recovery scenario and data boundary.
Do not invent universal availability, p95, memory, coverage or retention thresholds.

Ask only when a missing value materially changes scope, architecture, cost or the
meaning of readiness. Otherwise state a bounded assumption/proposal and continue
independent work; do not repeatedly ask for settled requirements. A requirement
cannot silently become a non-goal because the environment prevents verification.
Do not impose distributed infrastructure, telemetry, a database or 24/7 service
objectives on a small local tool merely to populate the table.

## Carry the goals into slices and acceptance

Pass accepted targets and exact constraints to the responsible specialist with
the current user journey. Separate implementation owner from verification owner
when useful; a skill name is not evidence that work was delegated or completed.
Keep one authoritative contract, not separate conflicting specs for each skill.

Choose evidence that observes the actual boundary: a unit/fake can test policy,
not real-store contention, network deadlines, production capacity or restore.
For affected backend mechanisms use [backend-reliability.md](backend-reliability.md);
for service lifecycle, capacity, observability, rollout or data recovery use
[operational-readiness.md](operational-readiness.md) when those concerns are in scope.
Use [security-audit.md](security-audit.md) for an audit or concrete trust-boundary
review, not automatically for every new project.

At handoff retain target, source authority, environment, observation and remaining
gap. A completed plan, implemented mechanism and verified target are different
states. Change the agreed target only with supported scope direction, not to make
the result pass. These instructions do not enforce runtime gates or certify a
project; the host and actual evidence determine what can be claimed.
