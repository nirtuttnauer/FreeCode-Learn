"""Module 11 — reference solutions."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, TypeVar

T = TypeVar("T")
R = TypeVar("R")


async def gather_with_concurrency(limit: int, *awaitables: Awaitable[T]) -> list[T]:
    if limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")
    if not awaitables:
        return []

    semaphore = asyncio.Semaphore(limit)

    async def bounded(awaitable: Awaitable[T]) -> T:
        async with semaphore:
            return await awaitable

    # gather keeps input order and cancels nothing on failure, so wrap each awaitable.
    return await asyncio.gather(*(bounded(a) for a in awaitables))


async def async_retry(
    factory: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.01,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    if attempts < 1:
        raise ValueError(f"attempts must be >= 1, got {attempts}")

    for attempt in range(attempts):
        try:
            return await factory()  # a fresh awaitable every time
        except exceptions:
            if attempt == attempts - 1:
                raise
            await sleeper(base_delay * 2**attempt)
    raise AssertionError("unreachable")


async def run_with_timeout(
    awaitable: Awaitable[T], timeout: float, default: Any = None
) -> Any:
    if timeout <= 0:
        raise ValueError(f"timeout must be > 0, got {timeout}")
    try:
        async with asyncio.timeout(timeout):
            return await awaitable
    except TimeoutError:
        return default


async def async_pipeline(
    items: Iterable[T],
    worker: Callable[[T], Awaitable[R]],
    *,
    workers: int = 4,
    queue_size: int = 10,
) -> list[R]:
    if workers < 1:
        raise ValueError(f"workers must be >= 1, got {workers}")
    if queue_size < 1:
        raise ValueError(f"queue_size must be >= 1, got {queue_size}")

    SENTINEL = object()
    queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=queue_size)
    results: list[R] = []
    errors: list[BaseException] = []

    async def consume() -> None:
        while True:
            item = await queue.get()
            if item is SENTINEL:
                return
            try:
                results.append(await worker(item))
            except Exception as exc:  # noqa: BLE001 — collect, keep draining
                errors.append(exc)

    async with asyncio.TaskGroup() as tg:
        for _ in range(workers):
            tg.create_task(consume())
        for item in items:
            await queue.put(item)  # awaits when full: backpressure
        for _ in range(workers):
            await queue.put(SENTINEL)

    if errors:
        raise ExceptionGroup("pipeline failures", errors)
    return results


async def first_completed(*awaitables: Awaitable[T]) -> T:
    if not awaitables:
        raise ValueError("need at least one awaitable")

    tasks = [asyncio.ensure_future(a) for a in awaitables]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    if pending:
        # Await the cancelled tasks so cancellation actually settles before we return.
        await asyncio.gather(*pending, return_exceptions=True)
    return next(iter(done)).result()
