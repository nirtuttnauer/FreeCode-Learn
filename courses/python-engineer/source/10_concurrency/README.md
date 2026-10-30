# 10 — Threads, processes, and the GIL

## In plain English

Concurrency is about doing several things at once. Python has two ways, and picking the
wrong one makes your program *slower*, so it's worth understanding the difference.

Picture an office with **one microphone**. Ten people can be in the room, but only one can
speak at a time. That microphone is the **GIL** (Global Interpreter Lock), and it's why
Python threads can't do two calculations simultaneously.

But here's the thing: if those ten people are mostly *waiting* — for a website to reply, for
a file to load, for a database — they're not using the microphone anyway. They can all wait
at the same time perfectly happily. So:

- **Waiting on the internet or disk?** Threads. Ten downloads take as long as one.
- **Actually crunching numbers?** Threads won't help at all. You need separate
  **processes** — separate rooms, each with their own microphone.

Getting this backwards is one of the most common performance mistakes in Python, and the
lesson measures both so you can see it rather than take my word for it.

**Watch out for:** when two threads update the same number at once, they can both read "5",
both add one, and both write "6" — and you've silently lost a count. That's a *race
condition*, and the lesson shows 200,000 increments turning into fewer than 200,000.

## 1. The decision, in one table

| Workload | Use | Why |
|---|---|---|
| Network / disk I/O, few tasks | `ThreadPoolExecutor` | threads release the GIL while waiting |
| Network I/O, thousands of tasks | `asyncio` (module 11) | one thread, no per-task stack |
| Pure CPU work | `ProcessPoolExecutor` | sidesteps the GIL entirely |
| CPU work in numpy/pandas/polars | threads are often fine | those libraries release the GIL in C |
| Fire-and-forget background job | a task queue, not a thread | threads die with the process |

Get this wrong and threads make CPU work *slower* (contention + context switches) while
processes make I/O work slower (pickling + spawn cost).

## 2. The GIL, precisely

One lock per interpreter allows exactly one thread to execute Python bytecode at a time.
It is released:
- during blocking I/O (sockets, files, `time.sleep`),
- inside C extensions that explicitly release it (numpy, hashlib, compression, DB drivers),
- every few milliseconds, to let other threads run.

So threads give you **concurrency** for I/O, never **parallelism** for Python-level CPU work.

**3.13+**: a free-threaded build (`python3.13t`, PEP 703) removes the GIL. It's opt-in,
still experimental, single-thread performance is slightly lower, and most C extensions
need updating. Check `sys._is_gil_enabled()`. Don't design around it yet — but know it
exists, because it's where the language is going.

**3.12+**: per-interpreter GILs (PEP 684) via `interpreters` — another route to
parallelism without processes.

## 3. `concurrent.futures` — the API to reach for

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(fetch, url): url for url in urls}
    for future in as_completed(futures):        # results as they finish
        url = futures[future]
        try:
            data = future.result()              # re-raises the worker's exception HERE
        except TimeoutError:
            ...
```

- `pool.map(f, items)` is simpler but returns results **in order** and swallows nothing —
  the first exception surfaces when you iterate.
- The `with` block joins every worker on exit.
- **An exception inside a worker is invisible until you call `.result()`.** Futures you
  never inspect fail silently. This is the #1 concurrency bug in real code.
- Sizing: threads ≈ `min(32, os.cpu_count() + 4)` for I/O; processes ≈ `os.cpu_count()`.

For processes, everything crossing the boundary must be **picklable**: no lambdas, no
local functions, no open sockets. Worker functions must be defined at module top level.

## 4. Synchronisation

| Primitive | Use |
|---|---|
| `Lock` | mutual exclusion; always via `with` |
| `RLock` | re-entrant — the same thread can acquire it twice |
| `Semaphore(n)` | limit concurrency to n |
| `Event` | one-shot broadcast ("we're ready") |
| `Condition` | wait for a predicate |
| `Barrier(n)` | rendezvous |
| `queue.Queue` | the safest way to move data between threads |
| `threading.local()` | per-thread state |

```python
counter = 0
lock = threading.Lock()

def worker():
    global counter
    with lock:
        counter += 1      # NOT atomic without the lock: read, add, write
```

`x += 1` compiles to several bytecodes and can be interrupted between them. `list.append`
*is* atomic (single bytecode + GIL), but never rely on that — lock, or use a `Queue`.

**Deadlock**: always acquire multiple locks in the same global order, and prefer a timeout
(`lock.acquire(timeout=5)`) in code that must not hang.

## 5. Producer/consumer with `queue.Queue`

```python
q = queue.Queue(maxsize=100)      # maxsize gives you BACKPRESSURE

def consumer():
    while (item := q.get()) is not SENTINEL:
        handle(item)
        q.task_done()

q.join()                          # wait until every task_done() has landed
```

An unbounded queue turns a slow consumer into an out-of-memory crash. Always set `maxsize`.

## 6. Shutdown and daemons

- `thread.daemon = True` means the process may exit with the thread mid-work — no cleanup.
  Use it for pure background pollers only.
- Prefer a `threading.Event` "stop flag" the worker polls, plus `join(timeout=...)`.
- There is **no way to kill a thread**. Design for cooperative cancellation from day one.
- `ProcessPoolExecutor.shutdown(cancel_futures=True)` (3.9+) drops queued work.

## 7. Multiprocessing specifics

- Start methods: **spawn** (default on macOS/Windows, and on Linux from 3.14) starts a
  fresh interpreter and re-imports your module — so module-level side effects run again
  in every worker. **fork** (Linux legacy) is fast but unsafe with threads.
- Always guard entry points: `if __name__ == "__main__":` — without it, spawn recurses.
- Sharing data: `multiprocessing.Queue`, `Pipe`, `Value`/`Array`, `shared_memory` for
  large buffers, or a `Manager` for convenience at a big speed cost.

## Exercises

`exercises_10.py`, then `pytest 10_concurrency`.

## Further reading

- [`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html)
- [PEP 703 — making the GIL optional](https://peps.python.org/pep-0703/)
