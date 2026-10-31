# Backend reliability at the affected boundary

Read the relevant sections when implementing, diagnosing or reviewing backend
error handling, database access, shared-state transitions, jobs/webhooks or
outbound HTTP/RPC calls. Mere presence of a backend does not trigger a whole-service
audit. Skip for isolated wording, frontend presentation or pure computation that
does not affect these boundaries. Review/diagnosis alone remains read-only.

Reuse the actual framework, database, client, versions, service contract and
repository tests. These checks apply to Spring Boot, FastAPI, Express and other
stacks; they do not prescribe an ORM, transaction manager, queue or retry library.
Inspect configuration and call paths before adding machinery. Existing SDK/pool/
proxy behavior is part of the effective policy, not evidence that it is correct.

## Errors and truthful outcomes

- Separate expected business outcomes, dependency failures, cancellation and
  unexpected faults. Preserve the API/job contract: rejected, accepted/queued,
  partially completed, degraded and completed are different states. Do not return
  success, an empty result or synthetic data to hide a failed required operation.
- Catch at a boundary that can recover, translate or report the failure. Broad
  capture may be appropriate in framework handlers, worker isolation or cleanup;
  it is not permission to continue as if work succeeded. Preserve useful cause and
  context internally, return a safe public error, and do not leak secrets, request
  bodies or stack traces to clients. Avoid duplicate logging at every layer.
- A fallback must be an explicit supported outcome with visible limitations.
  Preserve cancellation/interruption and release resources. For partial writes,
  determine actual committed state and rollback/compensation guarantees; logging
  an exception does not undo a side effect. Do not invent compensation behavior.
- Check both required-dependency failure and normal/expected business outcomes.
  Observe returned status, final stored/job state and relevant nonsecret error
  evidence. An HTTP200 or successful exception handler alone does not verify work.

## Query and fan-out cost

- Trace database and external-service calls, including lazy ORM relationships,
  serializer access and helpers inside loops. Compare call count and fetched rows
  as the selected parent set grows; a single fast response does not rule out N+1.
- Use a suitable join, preloading, aggregation or bounded batch when repeated
  I/O is avoidable. Check join cardinality, duplicates, required ordering and
  response equivalence. A small justified loop, streaming job or deliberately
  bounded fan-out is not automatically a defect.
- Bound public list sizes, batch payloads and concurrent fan-out according to the
  contract. Use stable pagination/order or bounded streaming/chunks for large jobs.
  Do not replace N+1 with an unbounded eager load, huge IN list, unlimited parallel
  requests or silent truncation. Existing exports may need streaming, not paging.
- Verify representative small/larger cardinalities with actual query/call counters
  and result assertions. Query plans and latency are useful when relevant, not
  substitutes for output correctness or call growth. A mocked repository call
  count cannot certify ORM/SQL execution; identify that narrower boundary.

## Concurrent state transitions

- State the invariant and contention scope first: stock cannot go negative, one
  owner claims a job, a permitted transition occurs once, or a uniqueness rule
  holds. Include final state and number of successful operations in acceptance.
- For read-check-write or duplicate delivery, choose a mechanism that protects that
  invariant in the actual store: atomic conditional update/CAS with affected-row
  handling, uniqueness constraint/upsert, suitable locking or isolation. A zero-row
  update is a failed claim/conflict, not success. Inspect commit/rollback boundaries.
- A transaction annotation or async function alone does not prevent lost updates
  or write skew. Verify isolation semantics and which reads/writes it covers.
  In-process locks do not coordinate multiple worker processes/instances; distributed
  locks need ownership/expiry/failure semantics. Do not introduce one reflexively.
- Do not hold a database transaction/lock across slow external I/O without a
  justified design. Cross-system atomicity is not provided by a local transaction.
  Reuse documented idempotency/deduplication and durable state where required;
  deduplication checks must themselves be atomic with the protected effect.
- Reproduce contention with bounded barriers/events or a controlled schedule, not
  a serial test or arbitrary sleeps. Verify success/conflict counts, committed
  state and legitimate uncontended behavior. Use the real relevant database and
  independent connections/processes when its semantics matter; a SQLite/thread
  substitute does not prove PostgreSQL or multi-instance correctness. Bound worker
  waits and retain worker exceptions. Deadlock/serialization retries require a
  bounded policy and a safe replay boundary; do not replay external effects blindly.

## Outbound calls, deadlines and retries

- Inspect the resolved HTTP/RPC client, pool, SDK, proxy and service defaults.
  Establish a bounded total operation budget/deadline, and appropriate connect,
  read/write/pool or per-attempt limits where that client's API supports them.
  A read/inactivity timeout may not bound the whole operation. Budget DNS/TLS,
  connection acquisition, attempts and waits as relevant; propagate remaining
  deadline and cancellation to downstream work where supported. Do not impose one
  fixed timeout value or parameter shape across clients and streaming operations.
- Decide whether to retry before implementing a loop. Classify transient versus
  permanent faults and inspect documented retryable statuses/exceptions. Invalid
  input, denied access or cancellation do not become retryable by default. An
  operation may correctly use zero retries; document that decision when material.
- For safe transient retries, cap attempts (say whether the initial call counts),
  per-attempt time and total elapsed budget. Use appropriate capped exponential
  backoff with jitter; honor documented server pushback/Retry-After within budget.
  Stop on cancellation/deadline. Avoid retry multiplication across application,
  SDK and proxy layers; reuse one effective policy instead of stacking loops.
- Retry only when operation semantics and the failure boundary make replay safe.
  An HTTP method, a supplied key or a timeout alone does not prove server-side
  idempotency. A timed-out mutation may already have committed. Follow
  [permissions.md](permissions.md): reconcile the outcome or reuse a documented
  idempotency mechanism before any uncertain external-mutation retry.
- Test transient-then-success, permanent failure, exhausted budget, cancellation
  and unsafe-to-replay outcomes where applicable. Observe actual attempts, elapsed
  budget, timeout/deadline passed and downstream side-effect count. Use injected
  clocks/jitter for deterministic policy checks; separately exercise the actual
  client and slow/failed dependency when claiming timeout enforcement. A fake
  transport accepting a timeout argument does not establish real network behavior.

## Review and verification handoff

For the affected risks, record the contract/invariant, chosen mechanism, native
review evidence and executed check. Keep the scope compact:

| Risk | Review question | Useful evidence |
| --- | --- | --- |
| False success | What does a failed required dependency return and commit? | Forced failure + expected error/state; legitimate success |
| N+1/unbounded I/O | How do calls/rows grow with input size? | Small/larger sets, query counters, bounds and output/order assertions |
| Race | What enforces the invariant across contenders? | Controlled overlapping work, success/conflict counts and final state |
| Timeout/retry | What bounds total time and prevents unsafe replay? | Client policy, attempts/waits, observed deadline/cancel and effect count |

Confirm the check detects the original defect when available, then rerun on final
code. Report observed outcomes, substitutions and unavailable checks separately;
reading these rules or passing a syntax check is not reliability validation.
Follow [functional-qa.md](functional-qa.md) for a cross-boundary acceptance flow
and [test-strategy.md](test-strategy.md) for proportional tests. No automatic
dependency install, load test against production, migration or live probe is
authorized by this reference. Do not expand a narrow repair into a framework rewrite.

Primary references (reviewed2026-10-30; use documentation matching the repository):
[ORM loading strategies](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html),
[transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html),
[RPC deadlines](https://grpc.io/docs/guides/deadlines/) and
[retry policy](https://grpc.io/docs/guides/retry/). These are examples of mechanisms,
not a requirement to adopt those libraries or backends.
