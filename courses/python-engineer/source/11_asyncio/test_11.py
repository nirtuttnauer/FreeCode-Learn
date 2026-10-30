import asyncio
import time

import pytest

from courselib import impl

m = impl("11")


def run(coro):
    """Drive a coroutine from a sync test — no pytest-asyncio needed."""
    return asyncio.run(coro)


async def work(value, delay=0.01):
    await asyncio.sleep(delay)
    return value


async def boom(delay=0.01, exc=ValueError("boom")):
    await asyncio.sleep(delay)
    raise exc


class TestGatherWithConcurrency:
    def test_results_in_order(self):
        async def main():
            return await m.gather_with_concurrency(2, work(1, 0.03), work(2, 0.01), work(3, 0.02))

        assert run(main()) == [1, 2, 3]

    def test_respects_the_limit(self):
        state = {"now": 0, "peak": 0}

        async def tracked():
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
            await asyncio.sleep(0.02)
            state["now"] -= 1
            return 1

        async def main():
            return await m.gather_with_concurrency(3, *(tracked() for _ in range(20)))

        assert len(run(main())) == 20
        assert state["peak"] == 3

    def test_is_actually_concurrent(self):
        async def main():
            start = time.perf_counter()
            await m.gather_with_concurrency(10, *(work(n, 0.05) for n in range(10)))
            return time.perf_counter() - start

        assert run(main()) < 0.2  # serial would be 0.5s

    def test_empty(self):
        assert run(m.gather_with_concurrency(2)) == []

    def test_exception_propagates(self):
        async def main():
            return await m.gather_with_concurrency(2, work(1), boom())

        with pytest.raises(ValueError, match="boom"):
            run(main())

    def test_rejects_bad_limit(self):
        coro = work(1)
        with pytest.raises(ValueError):
            run(m.gather_with_concurrency(0, coro))
        coro.close()  # validation rejected it before it was ever awaited


class TestAsyncRetry:
    def test_first_attempt_succeeds(self):
        assert run(m.async_retry(lambda: work("ok"))) == "ok"

    def test_retries_until_success(self):
        calls = []

        async def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise TimeoutError
            return "recovered"

        assert run(m.async_retry(lambda: flaky(), base_delay=0)) == "recovered"
        assert len(calls) == 3

    def test_exhausts_and_reraises(self):
        calls = []

        async def always():
            calls.append(1)
            raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            run(m.async_retry(lambda: always(), attempts=4, base_delay=0))
        assert len(calls) == 4

    def test_backoff_delays(self):
        slept = []

        async def record(delay):
            slept.append(delay)

        async def always():
            raise ValueError

        with pytest.raises(ValueError):
            run(
                m.async_retry(
                    lambda: always(), attempts=4, base_delay=1, sleeper=record
                )
            )
        assert slept == [1, 2, 4]  # no sleep after the final attempt

    def test_unlisted_exception_not_retried(self):
        calls = []

        async def wrong():
            calls.append(1)
            raise KeyError

        with pytest.raises(KeyError):
            run(m.async_retry(lambda: wrong(), exceptions=(ValueError,), base_delay=0))
        assert len(calls) == 1

    def test_cancellation_is_not_retried(self):
        calls = []

        async def cancelled():
            calls.append(1)
            raise asyncio.CancelledError

        async def main():
            return await m.async_retry(lambda: cancelled(), attempts=5, base_delay=0)

        with pytest.raises(asyncio.CancelledError):
            run(main())
        assert len(calls) == 1

    def test_rejects_bad_attempts(self):
        with pytest.raises(ValueError):
            run(m.async_retry(lambda: work(1), attempts=0))


class TestRunWithTimeout:
    def test_returns_result_in_time(self):
        assert run(m.run_with_timeout(work("fast", 0.01), timeout=1)) == "fast"

    def test_returns_default_on_timeout(self):
        assert run(m.run_with_timeout(work("slow", 5), timeout=0.05, default="fallback")) == (
            "fallback"
        )

    def test_default_is_none(self):
        assert run(m.run_with_timeout(work("slow", 5), timeout=0.05)) is None

    def test_actually_cancels_the_work(self):
        cleaned = []

        async def slow():
            try:
                await asyncio.sleep(5)
            finally:
                cleaned.append("cleanup ran")

        run(m.run_with_timeout(slow(), timeout=0.05))
        assert cleaned == ["cleanup ran"]

    def test_returns_promptly(self):
        async def main():
            start = time.perf_counter()
            await m.run_with_timeout(work("slow", 10), timeout=0.05)
            return time.perf_counter() - start

        assert run(main()) < 0.5

    def test_other_exceptions_propagate(self):
        with pytest.raises(ValueError):
            run(m.run_with_timeout(boom(), timeout=1))

    def test_rejects_bad_timeout(self):
        coro = work(1)
        with pytest.raises(ValueError):
            run(m.run_with_timeout(coro, timeout=0))
        coro.close()


class TestAsyncPipeline:
    def test_processes_everything(self):
        async def double(n):
            await asyncio.sleep(0.001)
            return n * 2

        assert sorted(run(m.async_pipeline(range(20), double))) == [n * 2 for n in range(20)]

    def test_empty(self):
        assert run(m.async_pipeline([], work)) == []

    def test_single_worker(self):
        async def echo(n):
            return n

        assert sorted(run(m.async_pipeline(range(5), echo, workers=1))) == list(range(5))

    def test_concurrency_helps(self):
        async def slow(n):
            await asyncio.sleep(0.02)
            return n

        async def main():
            start = time.perf_counter()
            await m.async_pipeline(range(20), slow, workers=10, queue_size=5)
            return time.perf_counter() - start

        assert run(main()) < 0.2  # serial would be 0.4s

    def test_failures_become_an_exception_group(self):
        async def worker(n):
            if n % 3 == 0:
                raise ValueError(n)
            return n

        with pytest.raises(ExceptionGroup) as info:
            run(m.async_pipeline(range(10), worker, workers=3))
        assert len(info.value.exceptions) == 4

    def test_drains_everything_despite_failures(self):
        seen = []

        async def worker(n):
            seen.append(n)
            raise ValueError(n)

        with pytest.raises(ExceptionGroup):
            run(m.async_pipeline(range(10), worker, workers=2))
        assert sorted(seen) == list(range(10))

    def test_no_tasks_left_pending(self):
        async def main():
            await m.async_pipeline(range(10), work, workers=4)
            return [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

        assert run(main()) == []

    @pytest.mark.parametrize(("workers", "queue_size"), [(0, 5), (2, 0)])
    def test_rejects_bad_config(self, workers, queue_size):
        with pytest.raises(ValueError):
            run(m.async_pipeline([1], work, workers=workers, queue_size=queue_size))


class TestFirstCompleted:
    def test_returns_the_fastest(self):
        async def main():
            return await m.first_completed(work("slow", 0.2), work("fast", 0.01))

        assert run(main()) == "fast"

    def test_returns_promptly(self):
        async def main():
            start = time.perf_counter()
            await m.first_completed(work("slow", 5), work("fast", 0.01))
            return time.perf_counter() - start

        assert run(main()) < 0.3

    def test_losers_are_cancelled(self):
        cancelled = []

        async def loser():
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                cancelled.append(1)
                raise

        async def main():
            return await m.first_completed(loser(), work("winner", 0.01))

        assert run(main()) == "winner"
        assert cancelled == [1]

    def test_no_pending_tasks_afterwards(self):
        async def main():
            await m.first_completed(work("a", 5), work("b", 0.01))
            await asyncio.sleep(0)
            return [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

        assert run(main()) == []

    def test_winner_exception_propagates(self):
        async def main():
            return await m.first_completed(boom(0.01), work("slow", 1))

        with pytest.raises(ValueError):
            run(main())

    def test_single_awaitable(self):
        assert run(m.first_completed(work("only"))) == "only"

    def test_no_awaitables(self):
        with pytest.raises(ValueError):
            run(m.first_completed())
