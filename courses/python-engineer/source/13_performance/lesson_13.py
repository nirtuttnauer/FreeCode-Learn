"""Module 13 — runnable lesson. `python 13_performance/lesson_13.py`"""

from __future__ import annotations

import cProfile
import functools
import io
import pstats
import sys
import timeit
import tracemalloc
from dataclasses import dataclass

INTRO = """Making code fast is about doing LESS WORK, not doing work faster. Measure first — your
intuition is wrong, and so is mine. Fixing the approach beats micro-tuning by a factor of
hundreds, and this file measures every claim it makes."""


def bench(label: str, stmt, number: int = 1) -> float:
    elapsed = min(timeit.repeat(stmt, number=number, repeat=3)) / number
    print(f"  {label:<38} {elapsed * 1000:>9.3f} ms")
    return elapsed


def algorithmic_wins() -> None:
    print("\n== algorithm beats everything ==")
    haystack = list(range(20_000))
    needles = list(range(0, 20_000, 20))

    slow = bench("membership via list", lambda: [n for n in needles if n in haystack])
    lookup = set(haystack)
    fast = bench("membership via set", lambda: [n for n in needles if n in lookup])
    print(f"  -> {slow / fast:.0f}x, and the gap GROWS with n")

    parts = ["chunk"] * 20_000

    def concat() -> str:
        out = ""
        for p in parts:
            out += p
        return out

    slow = bench("string += in a loop", concat)
    fast = bench('"".join(parts)', lambda: "".join(parts))
    print(f"  -> {slow / fast:.0f}x")

    print("\n  joining two datasets:")
    left = [{"id": i, "v": i} for i in range(2_000)]
    right = [{"id": i, "w": i * 2} for i in range(2_000)]

    def nested_loop():
        return [(a, b) for a in left for b in right if a["id"] == b["id"]]

    def dict_join():
        index = {b["id"]: b for b in right}
        return [(a, index[a["id"]]) for a in left if a["id"] in index]

    slow = bench("nested loop O(n*m)", nested_loop)
    fast = bench("dict join O(n+m)", dict_join)
    print(f"  -> {slow / fast:.0f}x")


def caching() -> None:
    print("\n== caching ==")

    def fib(n: int) -> int:
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    @functools.cache
    def fib_cached(n: int) -> int:
        return n if n < 2 else fib_cached(n - 1) + fib_cached(n - 2)

    bench("fib(28) naive", lambda: fib(28))
    bench("fib(28) @cache", lambda: fib_cached(28))
    print(f"  {fib_cached.cache_info()}")
    print("  a hit rate near zero means the cache is pure overhead — always check")


def memory() -> None:
    print("\n== memory ==")

    class Regular:
        def __init__(self, x: int, y: int) -> None:
            self.x, self.y = x, y

    @dataclass(slots=True)
    class Slotted:
        x: int
        y: int

    regular = Regular(1, 2)
    slotted = Slotted(1, 2)
    regular_total = sys.getsizeof(regular) + sys.getsizeof(regular.__dict__)
    print(f"  regular instance + __dict__: {regular_total} bytes")
    print(f"  slots=True instance:         {sys.getsizeof(slotted)} bytes")

    print(f"\n  an int object:   {sys.getsizeof(0)} bytes (vs 8 in a C array)")
    print(f"  an empty list:   {sys.getsizeof([])} bytes")
    print(f"  an empty dict:   {sys.getsizeof({})} bytes")
    print("  sys.getsizeof is SHALLOW: a list of lists reports only the outer object")

    tracemalloc.start()
    materialised = [x * x for x in range(200_000)]
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"\n  list comprehension of 200k: {peak / 1e6:.1f} MB peak")
    del materialised

    tracemalloc.start()
    total = sum(x * x for x in range(200_000))
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"  generator, same result:     {peak / 1e3:.1f} KB peak  (sum={total:,})")


def profiling() -> None:
    print("\n== cProfile ==")

    def inner(n: int) -> int:
        return sum(i * i for i in range(n))

    def middle(n: int) -> int:
        return sum(inner(100) for _ in range(n))

    def outer() -> int:
        return middle(300)

    profiler = cProfile.Profile()
    profiler.enable()
    outer()
    profiler.disable()

    buffer = io.StringIO()
    pstats.Stats(profiler, stream=buffer).sort_stats("tottime").print_stats(5)
    for line in buffer.getvalue().splitlines()[4:11]:
        print(f"  {line}")
    print("  tottime = in the function itself; cumtime = including everything it calls")


def micro_optimisations() -> None:
    print("\n== micro-optimisations (worth 10-50%, not 100x) ==")
    data = list(range(200_000))

    def with_append():
        out = []
        for n in data:
            out.append(n * 2)
        return out

    def with_local_append():
        out = []
        append = out.append  # hoist the attribute lookup out of the loop
        for n in data:
            append(n * 2)
        return out

    def with_comprehension():
        return [n * 2 for n in data]

    a = bench("for + list.append", with_append)
    b = bench("for + hoisted append", with_local_append)
    c = bench("list comprehension", with_comprehension)
    print(f"  hoisting: {a / b:.2f}x   comprehension: {a / c:.2f}x")
    print("  real, but only worth doing where the profiler pointed")


if __name__ == "__main__":
    print(INTRO)
    algorithmic_wins()
    caching()
    memory()
    profiling()
    micro_optimisations()
