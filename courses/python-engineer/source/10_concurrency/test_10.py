import threading
import time

import pytest

from courselib import impl

m = impl("10")


def slow_double(n):
    time.sleep(0.02)
    return n * 2


def fails_on_three(n):
    if n == 3:
        raise ValueError(f"bad item {n}")
    return n * 2


class TestParallelMap:
    def test_results_in_input_order(self):
        assert m.parallel_map(slow_double, [1, 2, 3, 4]) == [2, 4, 6, 8]

    def test_actually_concurrent(self):
        start = time.perf_counter()
        m.parallel_map(slow_double, range(10), max_workers=10)
        # 10 x 20ms serially would be 200ms.
        assert time.perf_counter() - start < 0.15

    def test_empty_input(self):
        assert m.parallel_map(slow_double, []) == []

    def test_exception_propagates(self):
        with pytest.raises(ValueError, match="bad item 3"):
            m.parallel_map(fails_on_three, [1, 2, 3, 4])

    def test_first_failure_by_position_wins(self):
        def fails_on_even(n):
            time.sleep(0.05 if n == 2 else 0)  # 4 fails first in wall-clock time
            if n % 2 == 0:
                raise ValueError(f"item {n}")
            return n

        with pytest.raises(ValueError, match="item 2"):
            m.parallel_map(fails_on_even, [1, 2, 3, 4])

    def test_accepts_any_iterable(self):
        assert m.parallel_map(lambda n: n, (x for x in range(3))) == [0, 1, 2]

    def test_rejects_bad_workers(self):
        with pytest.raises(ValueError):
            m.parallel_map(slow_double, [1], max_workers=0)


class TestGatherResults:
    def test_all_succeed(self):
        results, failures = m.gather_results(slow_double, [1, 2])
        assert results == [2, 4]
        assert failures == []

    def test_partial_failure(self):
        results, failures = m.gather_results(fails_on_three, [1, 2, 3, 4])
        assert results == [2, 4, 8]
        assert len(failures) == 1
        item, exc = failures[0]
        assert item == 3
        assert isinstance(exc, ValueError)

    def test_never_raises(self):
        results, failures = m.gather_results(lambda n: 1 / 0, [1, 2])
        assert results == []
        assert len(failures) == 2

    def test_empty(self):
        assert m.gather_results(slow_double, []) == ([], [])

    def test_every_item_is_attempted(self):
        seen = []
        lock = threading.Lock()

        def record(n):
            with lock:
                seen.append(n)
            raise RuntimeError

        m.gather_results(record, range(10))
        assert sorted(seen) == list(range(10))


class TestSafeCounter:
    def test_basic(self):
        c = m.SafeCounter()
        assert c.increment() == 1
        assert c.increment(5) == 6
        assert c.decrement(2) == 4
        assert c.value == 4

    def test_start_value(self):
        assert m.SafeCounter(10).value == 10

    def test_reset(self):
        c = m.SafeCounter(5)
        c.reset()
        assert c.value == 0

    def test_no_lost_updates_under_contention(self):
        c = m.SafeCounter()

        def hammer():
            for _ in range(20_000):
                c.increment()

        threads = [threading.Thread(target=hammer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert c.value == 80_000

    def test_context_manager_groups_operations(self):
        c = m.SafeCounter()
        with c:
            c.increment()  # re-entrant: must not deadlock
            c.increment()
        assert c.value == 2

    def test_context_manager_blocks_other_threads(self):
        c = m.SafeCounter()
        observed = []

        def waiter():
            with c:
                observed.append(c.value)

        with c:
            t = threading.Thread(target=waiter)
            t.start()
            time.sleep(0.05)
            c.increment(100)
        t.join()
        assert observed == [100]  # the waiter only got in after the block finished


class TestRunPipeline:
    def test_processes_everything(self):
        assert sorted(m.run_pipeline(range(20), lambda n: n * 2)) == [n * 2 for n in range(20)]

    def test_empty_input(self):
        assert m.run_pipeline([], lambda n: n) == []

    def test_single_worker(self):
        assert sorted(m.run_pipeline(range(5), lambda n: n, workers=1)) == list(range(5))

    def test_bounded_queue_creates_backpressure(self):
        produced = []

        def slow_worker(n):
            time.sleep(0.01)
            return n

        def items():
            for n in range(50):
                produced.append(n)
                yield n

        m.run_pipeline(items(), slow_worker, workers=2, queue_size=2)
        assert len(produced) == 50

    def test_no_threads_left_running(self):
        before = threading.active_count()
        m.run_pipeline(range(10), lambda n: n, workers=4)
        time.sleep(0.05)
        assert threading.active_count() <= before

    def test_failures_become_an_exception_group(self):
        with pytest.raises(ExceptionGroup) as info:
            m.run_pipeline(range(10), fails_on_three, workers=2)
        assert len(info.value.exceptions) == 1

    def test_drains_everything_despite_failures(self):
        done = []
        lock = threading.Lock()

        def worker(n):
            with lock:
                done.append(n)
            if n % 2 == 0:
                raise ValueError(n)
            return n

        with pytest.raises(ExceptionGroup) as info:
            m.run_pipeline(range(10), worker, workers=3)
        assert sorted(done) == list(range(10))
        assert len(info.value.exceptions) == 5

    @pytest.mark.parametrize(("workers", "queue_size"), [(0, 5), (2, 0), (-1, 5)])
    def test_rejects_bad_config(self, workers, queue_size):
        with pytest.raises(ValueError):
            m.run_pipeline([1], lambda n: n, workers=workers, queue_size=queue_size)


class TestOnce:
    def test_runs_once(self):
        calls = []
        once = m.Once(lambda: calls.append(1) or "result")
        assert once() == "result"
        assert once() == "result"
        assert len(calls) == 1

    def test_called_flag(self):
        once = m.Once(lambda: None)
        assert not once.called
        once()
        assert once.called

    def test_arguments_are_passed_on_the_first_call(self):
        once = m.Once(lambda a, b=0: a + b)
        assert once(1, b=2) == 3
        assert once(99) == 3  # later args ignored — the result is cached

    def test_exactly_one_call_under_contention(self):
        calls = []
        lock = threading.Lock()
        barrier = threading.Barrier(50)

        def initialise():
            time.sleep(0.01)  # widen the race window
            with lock:
                calls.append(1)
            return "done"

        once = m.Once(initialise)
        results = []

        def racer():
            barrier.wait()  # all 50 threads start at the same instant
            results.append(once())

        threads = [threading.Thread(target=racer) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(calls) == 1
        assert results == ["done"] * 50

    def test_failure_can_be_retried(self):
        attempts = []

        def flaky():
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError("first call fails")
            return "ok"

        once = m.Once(flaky)
        with pytest.raises(RuntimeError):
            once()
        assert not once.called
        assert once() == "ok"


@pytest.mark.slow
class TestProcessMap:
    def test_squares(self):
        assert m.process_map([1, 2, 3, 4]) == [1, 4, 9, 16]

    def test_empty_starts_no_processes(self):
        start = time.perf_counter()
        assert m.process_map([]) == []
        assert time.perf_counter() - start < 0.05  # spawning would cost far more

    def test_order_is_preserved(self):
        assert m.process_map(range(10)) == [n * n for n in range(10)]
