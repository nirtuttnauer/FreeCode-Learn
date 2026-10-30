"""Module 10 — reference solutions."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def square(n: int) -> int:
    return n * n


def parallel_map(
    func: Callable[[T], R], items: Iterable[T], *, max_workers: int = 8
) -> list[R]:
    if max_workers < 1:
        raise ValueError(f"max_workers must be >= 1, got {max_workers}")
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(func, item) for item in items]
        # Iterating in submission order makes the raised exception deterministic.
        return [future.result() for future in futures]


def gather_results(
    func: Callable[[T], R], items: Iterable[T], *, max_workers: int = 8
) -> tuple[list[R], list[tuple[T, BaseException]]]:
    items = list(items)
    if not items:
        return [], []

    results: list[R] = []
    failures: list[tuple[T, BaseException]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(func, item) for item in items]
        for item, future in zip(items, futures, strict=True):
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 — the whole point is to keep going
                failures.append((item, exc))
    return results, failures


class SafeCounter:
    def __init__(self, start: int = 0) -> None:
        self._value = start
        # RLock so a caller inside `with counter:` can still call increment().
        self._lock = threading.RLock()

    def increment(self, by: int = 1) -> int:
        with self._lock:
            self._value += by
            return self._value

    def decrement(self, by: int = 1) -> int:
        return self.increment(-by)

    @property
    def value(self) -> int:
        with self._lock:
            return self._value

    def reset(self) -> None:
        with self._lock:
            self._value = 0

    def __enter__(self) -> SafeCounter:
        self._lock.acquire()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._lock.release()


def run_pipeline(
    items: Iterable[T],
    worker: Callable[[T], R],
    *,
    workers: int = 4,
    queue_size: int = 10,
) -> list[R]:
    if workers < 1:
        raise ValueError(f"workers must be >= 1, got {workers}")
    if queue_size < 1:
        raise ValueError(f"queue_size must be >= 1, got {queue_size}")

    SENTINEL = object()
    work: queue.Queue[Any] = queue.Queue(maxsize=queue_size)
    results: list[R] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def consume() -> None:
        while True:
            item = work.get()
            try:
                if item is SENTINEL:
                    return
                value = worker(item)
            except Exception as exc:  # noqa: BLE001 — collect and drain the rest
                with lock:
                    errors.append(exc)
            else:
                with lock:
                    results.append(value)
            finally:
                work.task_done()

    threads = [threading.Thread(target=consume) for _ in range(workers)]
    for thread in threads:
        thread.start()
    try:
        for item in items:
            work.put(item)  # blocks once the queue is full — that's the backpressure
    finally:
        for _ in threads:
            work.put(SENTINEL)
        for thread in threads:
            thread.join()

    if errors:
        raise ExceptionGroup("pipeline failures", errors)
    return results


class Once:
    def __init__(self, func: Callable[..., Any]) -> None:
        self._func = func
        self._lock = threading.Lock()
        self._called = False
        self._result: Any = None

    @property
    def called(self) -> bool:
        return self._called

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._called:  # fast path, no lock
            return self._result
        with self._lock:
            if not self._called:  # re-check: another thread may have won the race
                self._result = self._func(*args, **kwargs)
                self._called = True  # set AFTER success, so a failure can be retried
        return self._result


def process_map(items: Iterable[int], *, max_workers: int = 2) -> list[int]:
    items = list(items)
    if not items:
        return []  # never pay spawn cost for nothing
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(square, items))
