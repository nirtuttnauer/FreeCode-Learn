"""Module 10 exercises.  pytest 10_concurrency"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def square(n: int) -> int:
    """A top-level worker for the process-pool exercise.

    It has to live at module scope: `ProcessPoolExecutor` pickles the function by
    qualified name, and lambdas / closures / locally-defined functions can't be pickled.
    """
    return n * n


def parallel_map(
    func: Callable[[T], R], items: Iterable[T], *, max_workers: int = 8
) -> list[R]:
    """Run `func` over `items` in a thread pool, returning results IN INPUT ORDER.

    - Uses `concurrent.futures.ThreadPoolExecutor`.
    - If any call raises, the exception propagates (the first one by input position,
      so the failure is deterministic regardless of scheduling).
    - An empty input returns [] without starting a pool.
    - max_workers < 1 raises ValueError.
    """
    raise NotImplementedError


def gather_results(
    func: Callable[[T], R], items: Iterable[T], *, max_workers: int = 8
) -> tuple[list[R], list[tuple[T, BaseException]]]:
    """Like `parallel_map`, but never raises: returns (results, failures).

    - `results` holds the successful values, in input order.
    - `failures` holds `(item, exception)` pairs, in input order.
    - Every item is attempted, even after earlier ones fail.

    This is the shape you want for batch jobs: one bad record must not abort the batch.
    """
    raise NotImplementedError


class SafeCounter:
    """A counter that stays correct under concurrent access.

    - `.increment(by=1)` and `.decrement(by=1)` return the new value.
    - `.value` reads the current value.
    - `.reset()` sets it to 0.
    - Must use a `threading.Lock` — `self._value += 1` is three bytecodes and races.
    - `with counter:` acquires the same lock, so callers can group operations atomically
      (implement `__enter__`/`__exit__`; make the lock re-entrant so `increment()` can be
      called inside such a block without deadlocking).
    """

    def __init__(self, start: int = 0) -> None:
        raise NotImplementedError


def run_pipeline(
    items: Iterable[T],
    worker: Callable[[T], R],
    *,
    workers: int = 4,
    queue_size: int = 10,
) -> list[R]:
    """Classic producer/consumer: feed `items` through a BOUNDED queue to N worker threads.

    - Use `queue.Queue(maxsize=queue_size)` — the bound is the point. An unbounded queue
      lets a fast producer exhaust memory before a slow consumer catches up.
    - Return every result (order is not specified — the tests compare sorted output).
    - Shut down cleanly: no thread may be left running when this returns.
    - If any worker raises, still drain the rest, then raise
      `ExceptionGroup("pipeline failures", [...])` with every exception collected.
    - Results are appended from several threads, so guard the list with a lock
      (or hand results back through a second queue).
    - workers < 1 or queue_size < 1 raises ValueError.
    """
    raise NotImplementedError


class Once:
    """Run a function exactly once, no matter how many threads call it.

    >>> setup = Once(lambda: "initialised")
    >>> setup(), setup()
    ('initialised', 'initialised')

    - The wrapped callable runs at most once; later calls return the cached result.
    - `.called` is a bool.
    - Thread-safe: 50 threads racing must produce exactly ONE underlying call. Use
      double-checked locking — a fast unlocked read first, then the lock, then a
      re-check inside it (the first check alone is a race; the lock alone is a
      bottleneck).
    - If the function raises, the exception propagates and the call does NOT count —
      the next caller retries.
    """

    def __init__(self, func: Callable[..., Any]) -> None:
        raise NotImplementedError


def process_map(items: Iterable[int], *, max_workers: int = 2) -> list[int]:
    """Square every item using a PROCESS pool, so the work is genuinely parallel.

    Use `ProcessPoolExecutor` with the module-level `square` function above.
    Results in input order. Empty input returns [] without starting any process
    (spawning is expensive — don't pay it for nothing).
    """
    raise NotImplementedError
