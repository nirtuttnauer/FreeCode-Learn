# Project 04 — `forge`: a durable task queue and scheduler

Celery, if you had to write it. A job queue that survives a crash, delivers at least once,
retries with backoff, respects concurrency limits, and can be inspected while running.

This is the hardest project in the set, because it is concurrent **and** stateful **and**
has to be correct under failure. Which is exactly why it's worth doing.

**Modules it draws on**: 05 (errors, atomic writes, context managers), 06 (generators),
09 (injected clocks — you cannot test a scheduler with a real one), 10 (threads/processes),
11 (asyncio), 12 (registries), 13 (performance), 17 (observability).

---

## Milestone 1 — jobs and the registry

```python
@task(name="send_email", max_retries=3, timeout=30)
def send_email(to: str, subject: str) -> None: ...

send_email.delay(to="a@b.c", subject="hi")            # enqueue
send_email.apply_async(eta=in_5_minutes, priority=9)  # schedule
```

- `@task` registers by name (module 12) and attaches `.delay` / `.apply_async`.
- `Job`: id (uuid7-ish, sortable), task name, args, kwargs, priority, `eta`, attempt
  count, state, timestamps, result, error.
- States: `pending → running → succeeded | failed | dead`, plus `retrying` and
  `cancelled`. Illegal transitions raise `InvalidTransition` — encode the state machine
  explicitly, don't scatter `if job.state == ...` around.
- Arguments must be JSON-serialisable; reject anything else **at enqueue time**, with a
  clear error naming the offending argument.

## Milestone 2 — the broker Protocol

```python
class Broker(Protocol):
    async def enqueue(self, job: Job) -> None: ...
    async def reserve(self, timeout: float) -> Job | None: ...   # atomically claim one
    async def ack(self, job_id: str, result: Any) -> None: ...
    async def nack(self, job_id: str, error: str, retry_at: float | None) -> None: ...
```

Three implementations, all passing the **same** contract test suite:
- `MemoryBroker` — heap ordered by (priority, eta, id).
- `SQLiteBroker` — durable, `SELECT ... FOR UPDATE`-style claiming via an immediate
  transaction, WAL mode.
- `RedisBroker` (optional) — sorted sets plus a reliable-queue pattern.

Correctness requirements:
- **Reservation is atomic.** Two workers must never claim the same job. Prove it with a
  test that runs 50 concurrent reservations against 50 jobs and asserts each id appears
  exactly once.
- **Visibility timeout**: a reserved job whose worker dies becomes available again after
  `lease_seconds`. This is what makes delivery at-least-once.
- Therefore: **tasks must be idempotent**, and you must say so loudly in the README.

## Milestone 3 — the worker

- `Worker(broker, registry, concurrency=8, poll_interval=0.1)` with an asyncio main loop.
- Sync tasks run in a thread pool, async tasks on the loop, CPU-bound tasks (declared
  with `@task(cpu_bound=True)`) in a process pool (module 10).
- Per-task timeout, enforced with `asyncio.timeout`, cancelling cleanly.
- Retries: exponential backoff with jitter, capped, `max_retries` then → dead-letter.
- **Graceful shutdown**: SIGTERM stops reserving, finishes in-flight jobs within
  `grace_period`, then cancels. No job is lost or silently dropped.
- Heartbeats so a stalled worker's leases expire and its jobs get re-delivered.

## Milestone 4 — scheduling

- `Scheduler` for periodic jobs: cron expressions (`* * * * *`, with ranges, steps and
  lists) and simple intervals.
- **Injected clock throughout** — the tests advance time by an hour instantly.
- A distributed lock so N schedulers produce exactly one job per tick, not N.
- Catch-up policy: after downtime, run missed ticks once, or skip them — configurable,
  documented, and tested.
- `next_run_at(cron, after)` must be a pure function. Property-test it: the next run is
  always strictly after `after`, and always matches the expression.

## Milestone 5 — reliability and flow control

- Rate limiting per task (`@task(rate_limit="10/s")`) with the token bucket from module 09.
- A circuit breaker per task: after N consecutive failures, stop pulling that task for a
  cool-down, then half-open.
- Bounded in-flight work — a full internal queue must stop reservation, not grow memory
  (module 10's backpressure lesson).
- Job chaining: `chain(a, b, c)`, `group(...)` (fan-out) and `chord(group, callback)`
  (fan-in). Design the state machine before you write it.
- A dead-letter queue with `forge dlq list` / `replay`.

## Milestone 6 — operations

- CLI (`argparse` or `typer`): `worker`, `scheduler`, `enqueue`, `inspect`, `dlq`, `purge`.
- OTel spans per job with the trace context **propagated from the enqueuer**, so a job's
  span joins the HTTP request that created it. This is the single most valuable trace in
  any queue system.
- Metrics: queue depth, reservation latency, execution duration, retry and failure
  counts, worker saturation.
- Structured logs with `job_id`, `task`, `attempt`.
- Benchmark: jobs/sec for a no-op task on each broker, and where the bottleneck is.

## Going further

- Priority inversion protection and fair scheduling per tenant.
- Exactly-once semantics via an idempotency-key table, and an honest write-up of what
  "exactly once" can and cannot mean.
- A live web dashboard (reuse project 03's Jinja2 skills).
- Chaos tests: kill workers mid-job, corrupt the store, skew the clock — assert no job is
  lost and none runs twice without an idempotency key.

## What "done" means

The concurrency test proves no double-delivery, killing a worker mid-job re-delivers it,
the scheduler's cron maths passes property tests, and `forge inspect` shows you the truth
about a running system.
