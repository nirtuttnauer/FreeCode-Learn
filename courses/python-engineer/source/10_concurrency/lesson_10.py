"""Module 10 — runnable lesson. `python 10_concurrency/lesson_10.py`

Numbers on your machine will differ; the RATIOS are the lesson.
"""

from __future__ import annotations

import multiprocessing
import os
import queue
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

INTRO = """Picture an office with one microphone. Ten people can be in the room, but only one talks
at a time — that's the GIL. Fine if they're mostly WAITING (downloads, files). Useless if
they all need to talk (calculations); for that you need separate rooms: processes."""


def cpu_bound(n: int) -> int:
    """Deliberately pure-Python: no C library that could release the GIL."""
    return sum(i * i for i in range(n))


def io_bound(seconds: float) -> str:
    time.sleep(seconds)  # sleep releases the GIL
    return "done"


def the_gil() -> None:
    print("\n== the GIL ==")
    print(f"  CPUs: {os.cpu_count()}  start method: {multiprocessing.get_start_method()}")
    if hasattr(sys, "_is_gil_enabled"):
        print(f"  GIL enabled: {sys._is_gil_enabled()}  (False only on a free-threaded build)")

    work = [2_000_000] * 4

    t0 = time.perf_counter()
    [cpu_bound(n) for n in work]
    serial = time.perf_counter() - t0

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(cpu_bound, work))
    threaded = time.perf_counter() - t0

    print(f"  CPU work serial:  {serial:.2f}s")
    print(f"  CPU work threads: {threaded:.2f}s  <- no faster (often slower): GIL")

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(io_bound, [0.2] * 4))
    io_threaded = time.perf_counter() - t0
    print(f"  I/O work threads: {io_threaded:.2f}s  <- 4x0.2s of sleeping in ~0.2s: WINS")


def processes() -> None:
    print("\n== processes for CPU work ==")
    work = [2_000_000] * 4
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(cpu_bound, work))
    print(f"  CPU work processes: {time.perf_counter() - t0:.2f}s  <- real parallelism")
    print("  cost: pickling arguments/results, and a fresh interpreter per worker")
    print("  requirement: the worker function must be importable at module top level")


def futures_api() -> None:
    print("\n== futures: results as they land, errors when you ask ==")

    def task(n: int) -> int:
        time.sleep(0.05 * n)
        if n == 3:
            raise ValueError("task 3 always fails")
        return n * 10

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(task, n): n for n in range(1, 5)}
        for future in as_completed(futures):
            n = futures[future]
            try:
                print(f"  task {n} -> {future.result()}")
            except ValueError as exc:
                print(f"  task {n} raised: {exc}")

    print("\n  the silent-failure trap:")
    with ThreadPoolExecutor() as pool:
        pool.submit(task, 3)  # nobody calls .result()
    print("  a worker raised ValueError and nothing was printed. Always inspect futures.")


def races_and_locks() -> None:
    print("\n== += is not atomic ==")

    class Counter:
        def __init__(self) -> None:
            self.value = 0
            self.lock = threading.Lock()

        def unsafe(self) -> None:
            for _ in range(50_000):
                self.value += 1  # LOAD, ADD, STORE — interruptible between them

        def safe(self) -> None:
            for _ in range(50_000):
                with self.lock:
                    self.value += 1

    for name in ("unsafe", "safe"):
        counter = Counter()
        threads = [threading.Thread(target=getattr(counter, name)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        status = "correct" if counter.value == 200_000 else "LOST UPDATES"
        print(f"  {name:>6}: {counter.value:>7,} / 200,000  {status}")


def producer_consumer() -> None:
    print("\n== queue.Queue with backpressure ==")
    SENTINEL = object()
    work: queue.Queue = queue.Queue(maxsize=5)  # bounded: a slow consumer throttles the producer
    results: list[int] = []
    lock = threading.Lock()

    def consumer() -> None:
        while True:
            item = work.get()
            try:
                if item is SENTINEL:
                    return
                with lock:
                    results.append(item * 2)
            finally:
                work.task_done()

    consumers = [threading.Thread(target=consumer) for _ in range(3)]
    for c in consumers:
        c.start()

    for n in range(20):
        work.put(n)
    work.join()  # wait for every task_done()

    for _ in consumers:
        work.put(SENTINEL)
    for c in consumers:
        c.join()

    print(f"  processed {len(results)} items, sum={sum(results)}")
    print("  maxsize is what stops a fast producer from OOM-ing the process")


def cooperative_cancellation() -> None:
    print("\n== you cannot kill a thread ==")
    stop = threading.Event()
    ticks = []

    def poller() -> None:
        while not stop.is_set():  # the ONLY way out: the worker checks and returns
            ticks.append(1)
            stop.wait(0.01)  # sleep that wakes immediately on set()

    thread = threading.Thread(target=poller)
    thread.start()
    time.sleep(0.05)
    stop.set()
    thread.join(timeout=1)
    print(f"  polled {len(ticks)} times, then exited cleanly: alive={thread.is_alive()}")
    print("  daemon=True would just abandon it at process exit — no cleanup")


if __name__ == "__main__":  # mandatory: spawn re-imports this module in every worker
    print(INTRO)
    the_gil()
    processes()
    futures_api()
    races_and_locks()
    producer_consumer()
    cooperative_cancellation()
