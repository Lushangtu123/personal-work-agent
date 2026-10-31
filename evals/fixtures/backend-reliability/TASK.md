# Repair this offline backend fixture

Use the supplied PWA workflow to repair `service.py` and verify the four affected
boundaries. Preserve public signatures and the existing checks. No packages,
network service, framework, commit, migration or live data is needed/authorized.
All data is synthetic. Put receipts in the runner-assigned sibling evidence
directory, never inside this product tree; use native outputs if none is assigned.

Contract:

- `run_job(write)`: return the successful value; translate `ExpectedRejection`
  into a failed business outcome. An unexpected exception must reach the caller,
  never become a successful empty value. This wrapper cannot undo callback effects.
- `list_accounts(db, limit=20, after=0)`: return account ID/name/event count in ID
  order, after the exclusive cursor. Permit limits1..100; reject others. Bound
  returned rows and avoid query count growing linearly with result count. Preserve
  accounts without events. No requirement to adopt an ORM or a specific query.
- `claim(db, key, before_write)`: one available unit can be claimed by at most one
  contender. Return False for missing/exhausted key, True only for a committed
  decrement. Contenders use independent SQLite connections. `before_write()` is
  an existing deterministic test rendezvous and must execute once before the
  mutation; do not remove it. Do not change the schema or add a global thread lock.
- `fetch(send, retry_safe, deadline, now, sleep, jitter, max_attempts=3)`:
  deadline is absolute monotonic time; pass remaining positive time as the
  transport's `timeout`. Retry only `TransientFailure` and only when replay is
  explicitly safe. Initial attempt counts toward the maximum. Before each attempt
  and wait, honor remaining budget. The fixture's specified wait policy is full
  jitter in `[0, min(1, 0.2 * 2**retry_index)]`, where retry_index starts0 and
  jitter() supplies a fraction0..1. Do not begin a wait that consumes the entire
  remaining budget; fail rather than start a known-over-budget attempt. Allow
  max_attempts1..5, reject invalid values. Permanent errors and exhausted transient
  attempts propagate. An expired deadline raises TimeoutError without another call.

Run `python3 -B checks.py`. Show the original failures before repair and the final
results. Add meaningful neighboring tests only where warranted; do not weaken
checks or replace worker errors with success. Record what real SQLite contention
and an injected transport/clock establish separately; no actual HTTP/RPC timeout,
Spring transaction or PostgreSQL correctness claim follows from this fixture.
