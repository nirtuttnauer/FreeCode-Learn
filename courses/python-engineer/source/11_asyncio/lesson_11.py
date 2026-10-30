"""Module 11 — runnable lesson. `python 11_asyncio/lesson_11.py`"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

INTRO = """One waiter serving many tables, instead of one waiter per table standing frozen while the
kitchen cooks. `await` is where the waiter says "this'll take a moment, I'll go be useful
elsewhere". Never do anything slow WITHOUT an await, or the whole restaurant stops."""


async def fake_fetch(name: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return f"{name}({delay}s)"


async def sequential_vs_concurrent() -> None:
    print("\n== await is sequential; tasks are concurrent ==")

    t0 = time.perf_counter()
    await fake_fetch("a", 0.1)
    await fake_fetch("b", 0.1)
    print(f"  two awaits:      {time.perf_counter() - t0:.2f}s")

    t0 = time.perf_counter()
    async with asyncio.TaskGroup() as tg:
        a = tg.create_task(fake_fetch("a", 0.1))
        b = tg.create_task(fake_fetch("b", 0.1))
    print(f"  two tasks:       {time.perf_counter() - t0:.2f}s -> {a.result()}, {b.result()}")

    coro = fake_fetch("never", 0)
    print(f"  a bare call just builds a coroutine object: {coro!r}")
    coro.close()  # otherwise: "coroutine was never awaited"


async def task_groups_and_errors() -> None:
    print("\n== TaskGroup cancels siblings and raises an ExceptionGroup ==")

    async def good() -> str:
        try:
            await asyncio.sleep(1)
            return "finished"
        except asyncio.CancelledError:
            print("    good() was cancelled because its sibling failed")
            raise  # ALWAYS re-raise

    async def bad() -> str:
        await asyncio.sleep(0.05)
        raise ValueError("bad task failed")

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(good())
            tg.create_task(bad())
    except* ValueError as group:
        print(f"  caught: {[str(e) for e in group.exceptions]}")

    print("\n  gather() by comparison:")
    results = await asyncio.gather(
        fake_fetch("ok", 0.01), bad(), return_exceptions=True
    )
    print(f"  gather(return_exceptions=True) -> {results}")


async def timeouts_and_cancellation() -> None:
    print("\n== timeouts ==")

    async def slow() -> str:
        try:
            await asyncio.sleep(10)
            return "never"
        finally:
            print("    slow() cleanup ran (finally always executes)")

    try:
        async with asyncio.timeout(0.05):
            await slow()
    except TimeoutError:
        print("  asyncio.timeout raised TimeoutError")

    print("\n  shield protects a critical section:")

    async def critical() -> str:
        await asyncio.sleep(0.1)
        return "committed"

    inner = asyncio.create_task(critical())

    async def waiter() -> str:
        # shield() returns a Future, not a coroutine — it has to be awaited, not
        # handed to create_task().
        return await asyncio.shield(inner)

    task = asyncio.create_task(waiter())
    await asyncio.sleep(0.01)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("  the awaiting side saw CancelledError...")
    print(f"  ...but the shielded coroutine still completed: {await inner!r}")


async def bounded_concurrency() -> None:
    print("\n== bounding concurrency with a Semaphore ==")
    in_flight = 0
    peak = 0
    sem = asyncio.Semaphore(3)

    async def worker(n: int) -> int:
        nonlocal in_flight, peak
        async with sem:
            in_flight += 1
            peak = max(peak, in_flight)  # safe: no await between read and write
            await asyncio.sleep(0.02)
            in_flight -= 1
            return n

    async with asyncio.TaskGroup() as tg:
        for n in range(20):
            tg.create_task(worker(n))
    print(f"  20 tasks, limit 3 -> peak concurrency was {peak}")


async def async_iteration_and_context() -> None:
    print("\n== async generators and async context managers ==")

    async def stream(n: int):
        for i in range(n):
            await asyncio.sleep(0.005)
            yield i

    collected = [value async for value in stream(4)]
    print(f"  async comprehension: {collected}")

    @asynccontextmanager
    async def session(name: str):
        print(f"    opening {name}")
        try:
            yield {"name": name}
        finally:
            print(f"    closing {name}")

    async with session("db") as conn:
        print(f"    using {conn['name']}")


async def blocking_the_loop() -> None:
    print("\n== never block the loop ==")

    def blocking_io() -> str:
        time.sleep(0.1)  # a real, loop-freezing sleep
        return "blocking done"

    t0 = time.perf_counter()
    async with asyncio.TaskGroup() as tg:
        offloaded = tg.create_task(asyncio.to_thread(blocking_io))
        ticker = tg.create_task(fake_fetch("concurrent-work", 0.1))
    print(f"  to_thread kept the loop free: {time.perf_counter() - t0:.2f}s")
    print(f"  both finished: {offloaded.result()!r}, {ticker.result()!r}")
    print("  calling blocking_io() directly would have serialised them")


async def main() -> None:
    await sequential_vs_concurrent()
    await task_groups_and_errors()
    await timeouts_and_cancellation()
    await bounded_concurrency()
    await async_iteration_and_context()
    await blocking_the_loop()


if __name__ == "__main__":
    print(INTRO)
    asyncio.run(main())  # exactly one of these, at the top of the program
