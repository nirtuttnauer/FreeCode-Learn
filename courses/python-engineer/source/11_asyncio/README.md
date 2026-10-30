# 11 — asyncio and structured concurrency

Threads give you concurrency the OS schedules preemptively. asyncio gives you concurrency
**you** schedule cooperatively: one thread, one event loop, thousands of tasks, and
switches only at `await`.

That last part is the whole model: **between two `await`s, nothing else runs.** No data
races on ordinary state. But one blocking call freezes everything.

## In plain English

Picture a restaurant. The bad version: one waiter per table, and each waiter stands frozen
at their table doing nothing while the kitchen cooks. Need to serve 100 tables? Hire 100
waiters.

`asyncio` is the good version: **one waiter, many tables.** Take an order, hand it to the
kitchen, and while that's cooking go take the next table's order. The waiter is never idle,
and one person serves the whole room.

The word `await` marks the moments where the waiter says "this'll take a while — I'll go do
something else and come back". That's it. That's the whole idea.

This buys you enormous scale for anything that spends its time *waiting* — web servers, API
clients, chat bots, scrapers — using one thread instead of thousands.

**Watch out for:** the one unforgivable sin is doing something slow *without* an `await`.
Call a normal blocking function in the middle of your async code and the waiter stands
frozen again — except now there's only one waiter, so **the entire restaurant stops.** The
lesson shows the fix (`asyncio.to_thread`).

## 1. Coroutines, tasks, futures

```python
async def fetch(url): ...        # calling it returns a COROUTINE; nothing runs yet
await fetch(url)                 # runs it, blocking this coroutine until done
task = asyncio.create_task(fetch(url))   # schedules it CONCURRENTLY, returns immediately
result = await task
```

- `await` on a coroutine = sequential. Concurrency only starts when you create tasks.
- An un-awaited coroutine is a bug: "coroutine was never awaited".
- Keep a reference to every task you create — the loop only holds weak references, so a
  fire-and-forget task can be garbage-collected mid-flight. `TaskGroup` handles this.

## 2. `TaskGroup` — the default since 3.11

```python
async with asyncio.TaskGroup() as tg:
    a = tg.create_task(fetch("/a"))
    b = tg.create_task(fetch("/b"))
# both are finished here — the block does not exit until they do
print(a.result(), b.result())
```

If any task fails, the others are **cancelled** and you get an `ExceptionGroup`
(module 05). This is *structured concurrency*: tasks cannot outlive their scope, so there
are no orphans.

Compare with the older `gather`:

```python
results = await asyncio.gather(*coros)                       # first error cancels nothing
results = await asyncio.gather(*coros, return_exceptions=True)  # errors become results
```

Use `TaskGroup` for new code; `gather` when you specifically want
`return_exceptions=True` semantics or ordered results without a group.

## 3. Timeouts and cancellation

```python
async with asyncio.timeout(5):        # 3.11+, the modern form
    await slow_thing()

result = await asyncio.wait_for(slow_thing(), timeout=5)   # older equivalent
```

Cancellation is delivered as `CancelledError` raised **at the current `await`**.

- `CancelledError` inherits from `BaseException`, so `except Exception` doesn't catch it —
  by design.
- If you catch it for cleanup, **re-raise**. Swallowing it breaks the whole cancellation
  chain.
- Protect a critical section with `asyncio.shield(coro)`.
- `finally` blocks still run, so use `try/finally` (or an async CM) for cleanup.

```python
try:
    await work()
except asyncio.CancelledError:
    await rollback()
    raise                      # <- never omit this
```

## 4. Limiting concurrency

Unbounded `create_task` over 10,000 URLs will open 10,000 sockets and get you rate-limited
or OOM-ed. Bound it:

```python
sem = asyncio.Semaphore(10)

async def bounded(url):
    async with sem:
        return await fetch(url)
```

Or use an `asyncio.Queue(maxsize=n)` with a fixed pool of worker tasks — same
backpressure argument as module 10.

## 5. Async iteration and context managers

```python
async def stream(rows):
    for row in rows:
        yield row               # async generator

async for row in stream(rows): ...

@asynccontextmanager
async def session():
    conn = await connect()
    try:
        yield conn
    finally:
        await conn.close()

async with session() as conn: ...
```

`contextlib.aclosing`, `AsyncExitStack`, and `anext(it, default)` all exist too.

## 6. The cardinal sin: blocking the loop

```python
time.sleep(1)          # freezes EVERY task
requests.get(url)      # ditto
heavy_cpu_work()       # ditto
```

Fix with:

```python
await asyncio.sleep(1)
await client.get(url)                                   # httpx / aiohttp
await asyncio.to_thread(blocking_call, arg)             # 3.9+, for blocking I/O
await loop.run_in_executor(process_pool, cpu_work, arg) # for CPU work
```

`asyncio.run(main(), debug=True)` warns about callbacks that take too long — turn it on
when something feels stalled.

## 7. Sync ↔ async boundaries

- `asyncio.run(main())` — one per program, at the top. Never call it inside a running loop.
- `asyncio.to_thread(fn, *args)` — sync function from async code.
- `asyncio.run_coroutine_threadsafe(coro, loop)` — async work from another thread.
- Don't sprinkle `async` everywhere: a function that never awaits shouldn't be `async`.
  "Function colour" is contagious and hard to undo.

## 8. Ecosystem

`httpx`/`aiohttp` (HTTP), `asyncpg`/`psycopg3` (Postgres), `redis.asyncio`,
`aiofiles`, `uvicorn`/`FastAPI` (module 15), `anyio`/`trio` (a stricter structured
concurrency model that also runs on asyncio).

## Exercises

`exercises_11.py`, then `pytest 11_asyncio`. The tests call `asyncio.run` directly —
no plugin needed.

## Further reading

- [asyncio docs](https://docs.python.org/3/library/asyncio.html)
- [PEP 654 / TaskGroup](https://docs.python.org/3/library/asyncio-task.html#task-groups)
