"""Module 11 exercises.  pytest 11_asyncio

Every function here is a coroutine. The tests drive them with `asyncio.run`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, TypeVar

T = TypeVar("T")
R = TypeVar("R")


async def gather_with_concurrency(limit: int, *awaitables: Awaitable[T]) -> list[T]:
    """Await everything, but never run more than `limit` at once. Results in input order.

    - Use an `asyncio.Semaphore`.
    - The first exception propagates (like plain `gather`), and no awaitable may be
      left un-awaited afterwards.
    - `limit < 1` raises ValueError. No awaitables -> [].

    This is the single most useful asyncio helper there is: unbounded `create_task` over
    10k URLs is how you DDoS your own dependencies.
    """
    raise NotImplementedError


async def async_retry(
    factory: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.01,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Retry an awaitable with exponential backoff.

    - `factory()` produces a FRESH awaitable per attempt — you cannot await a coroutine
      twice, which is exactly why the parameter is a factory rather than a coroutine.
    - Delay before retry n (0-based) is `base_delay * 2**n`; no sleep after the last try.
    - Only `exceptions` are retried; the last failure is re-raised.
    - `asyncio.CancelledError` must NEVER be retried — it inherits from BaseException,
      so the default `(Exception,)` already excludes it. Don't break that by catching
      BaseException.
    - `attempts < 1` raises ValueError.
    """
    raise NotImplementedError


async def run_with_timeout(
    awaitable: Awaitable[T], timeout: float, default: Any = None
) -> Any:
    """Await with a timeout, returning `default` instead of raising when it expires.

    - Use `asyncio.timeout` (3.11+), not `wait_for`.
    - On timeout the underlying task must actually be cancelled — the tests assert that
      its `finally` block ran.
    - Any other exception propagates unchanged.
    - `timeout <= 0` raises ValueError.
    """
    raise NotImplementedError


async def async_pipeline(
    items: Iterable[T],
    worker: Callable[[T], Awaitable[R]],
    *,
    workers: int = 4,
    queue_size: int = 10,
) -> list[R]:
    """The asyncio twin of module 10's `run_pipeline`.

    - Feed `items` through an `asyncio.Queue(maxsize=queue_size)` to `workers` worker tasks.
    - Return every result (order unspecified; the tests sort).
    - Shut down cleanly — no task may be left pending when this returns.
    - Collect worker exceptions and raise `ExceptionGroup("pipeline failures", [...])`
      at the end, after every item has been attempted.
    - `workers < 1` or `queue_size < 1` raises ValueError.

    Use `asyncio.TaskGroup` for the workers and a sentinel per worker to stop them.
    """
    raise NotImplementedError


async def first_completed(*awaitables: Awaitable[T]) -> T:
    """Return the result of whichever awaitable finishes first; cancel the rest.

    - Losers must be cancelled AND awaited, so cancellation actually settles before
      returning (otherwise you get "Task was destroyed but it is pending!").
    - If the winner raises, that exception propagates.
    - No awaitables -> ValueError.

    `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)` gives you (done, pending).
    """
    raise NotImplementedError
