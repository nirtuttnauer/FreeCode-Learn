"""Module 23 — runnable lesson. `python 23_numpy/lesson_23.py`"""

from __future__ import annotations

import math
import sys
import time

import numpy as np

INTRO = """A Python list of a million numbers is a million separately-wrapped objects scattered across
memory. A NumPy array is one tightly packed block. That's the whole reason it's fast — and
why you stop writing loops and start operating on entire arrays at once."""

rng = np.random.default_rng(42)  # the modern API: an explicit generator, not a global seed


def bench(label: str, fn, number: int = 3) -> float:
    fn()  # warm up: the first call pays for imports, allocation and cache misses
    start = time.perf_counter()
    for _ in range(number):
        fn()
    elapsed = (time.perf_counter() - start) / number
    print(f"  {label:<34} {elapsed * 1000:>9.3f} ms")
    return elapsed


def the_array() -> None:
    print("\n== what an ndarray actually is ==")
    a = np.array([[1, 2, 3], [4, 5, 6]])
    print(f"  {a.shape=} {a.ndim=} {a.size=} {a.dtype=}")
    print(f"  strides (bytes to the next row / column): {a.strides}")
    print(f"  nbytes={a.nbytes}")

    py = list(range(1_000_000))
    np_a = np.arange(1_000_000)
    py_bytes = sys.getsizeof(py) + sum(sys.getsizeof(x) for x in py[:1000]) / 1000 * 1_000_000
    print(f"\n  1M ints as a list:  ~{py_bytes / 1e6:>6.1f} MB (pointers + int objects)")
    print(f"  1M ints as ndarray:  {np_a.nbytes / 1e6:>6.1f} MB (one typed block)")


def dtypes() -> None:
    print("\n== dtype traps ==")
    small = np.array([127], dtype=np.int8)
    print(f"  int8(127) + 1 = {small + 1}   <- wrapped, silently")

    f32 = np.full(10_000_000, 0.1, dtype=np.float32)
    print(f"  sum of 10M float32 0.1s: {f32.sum():.3f}  (should be 1,000,000.000)")
    print(f"  with dtype=float64 accumulator: {f32.sum(dtype=np.float64):.3f}")

    values = np.array([1.0, np.nan, 3.0])
    print(f"\n  {np.nan == np.nan=}")
    print(f"  mean with a NaN: {values.mean()}  vs nanmean: {np.nanmean(values)}")
    print(f"  np.isnan(values) = {np.isnan(values)}")


def vectorisation() -> None:
    print("\n== vectorisation ==")
    # Compare like for like: the SAME number of elements each way.
    for size in (100_000, 1_000_000):
        a, b = rng.random(size), rng.random(size)
        loop_a, loop_b = a.tolist(), b.tolist()
        print(f"  n = {size:,}")
        py = bench(
            "  python loop",
            lambda la=loop_a, lb=loop_b: [math.sqrt(x * x + y * y) for x, y in zip(la, lb, strict=True)],
        )
        vec = bench("  numpy", lambda x=a, y=b: np.sqrt(x**2 + y**2))
        print(f"    -> {py / vec:.0f}x")
    print("  the gap SHRINKS at 1M: the expression allocates three temporaries and")
    print("  becomes memory-bandwidth-bound. Speedups are workload-specific — measure.")

    a, b = rng.random(1_000_000), rng.random(1_000_000)

    print("\n  np.vectorize is NOT vectorisation:")
    slow = np.vectorize(lambda x, y: math.sqrt(x * x + y * y))
    bench("np.vectorize (100k)", lambda: slow(a[:100_000], b[:100_000]))
    print("  it's a convenience wrapper around a Python loop")


def broadcasting() -> None:
    print("\n== broadcasting ==")
    matrix = np.arange(12).reshape(3, 4)
    print(f"  (3,4) + (4,)   -> {(matrix + np.array([10, 20, 30, 40])).shape}  row added to every row")
    print(f"  (3,4) + (3,1)  -> {(matrix + np.array([[100], [200], [300]])).shape}  column to every column")
    try:
        matrix + np.array([1, 2, 3])
    except ValueError as exc:
        print(f"  (3,4) + (3,)   -> ValueError: {exc}")

    print("\n  np.newaxis makes the shapes line up:")
    a, b = rng.random((4, 2)), rng.random((5, 2))
    distances = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=-1))
    print(f"  all pairwise distances between (4,2) and (5,2): {distances.shape}, no loops")
    print("  BUT the intermediate is (4,5,2) — on 10k x 10k that's 800 GB. Watch the OUTPUT shape.")


def views_and_copies() -> None:
    print("\n== views vs copies: the #1 bug source ==")
    a = np.arange(10)

    view = a[2:5]  # basic slicing
    view[0] = 999
    print(f"  after writing to a SLICE:        a = {a}")
    print(f"  np.shares_memory(a, slice) = {np.shares_memory(a, view)}")

    a = np.arange(10)
    fancy = a[[2, 3, 4]]  # fancy indexing
    fancy[0] = 999
    print(f"\n  after writing to FANCY indexing: a = {a}   <- unchanged, it was a copy")
    print(f"  np.shares_memory(a, fancy) = {np.shares_memory(a, fancy)}")

    a = np.arange(10)
    masked = a[a > 5]
    masked[0] = 999
    print(f"  after writing to a BOOLEAN mask: a = {a}   <- also a copy")

    a = np.arange(10)
    a[a > 5] = 0  # __setitem__, not __getitem__
    print(f"\n  but assignment THROUGH a mask writes back: a = {a}")


def axes() -> None:
    print("\n== axis = the axis you COLLAPSE ==")
    a = np.arange(12).reshape(3, 4)
    print(f"  a.shape = {a.shape}")
    print(f"  a.sum(axis=0) -> {a.sum(axis=0)}  shape {a.sum(axis=0).shape}  (down the rows)")
    print(f"  a.sum(axis=1) -> {a.sum(axis=1)}  shape {a.sum(axis=1).shape}  (across the columns)")
    print(f"  keepdims=True -> shape {a.sum(axis=1, keepdims=True).shape}, still broadcastable")

    row_normalised = a / a.sum(axis=1, keepdims=True)
    print(f"  a / a.sum(axis=1, keepdims=True) row sums: {row_normalised.sum(axis=1)}")
    try:
        a / a.sum(axis=1)
    except ValueError as exc:
        print(f"  without keepdims: ValueError: {exc}")


def useful_functions() -> None:
    print("\n== the working set ==")
    a = rng.integers(0, 100, size=12)
    print(f"  a = {a}")
    print(f"  np.where(a > 50, a, 0)   = {np.where(a > 50, a, 0)}")
    print(f"  np.clip(a, 20, 80)       = {np.clip(a, 20, 80)}")
    values, counts = np.unique(a % 3, return_counts=True)
    print(f"  np.unique(a % 3, counts) = {dict(zip(values.tolist(), counts.tolist(), strict=True))}")
    print(f"  3 largest via argpartition: {a[np.argpartition(a, -3)[-3:]]}")

    big = rng.random(2_000_000)
    bench("np.sort (2M)", lambda: np.sort(big))
    bench("np.argpartition top-10 (2M)", lambda: np.argpartition(big, -10)[-10:])

    windows = np.lib.stride_tricks.sliding_window_view(np.arange(8), 3)
    print(f"\n  sliding_window_view(arange(8), 3) -> shape {windows.shape}, a VIEW (no copy)")
    print(f"  its rolling means: {windows.mean(axis=1)}")


def performance() -> None:
    print("\n== allocation is the hidden cost ==")
    a = rng.random(5_000_000)
    b = rng.random(5_000_000)

    bench("a = a + b (allocates a new array)", lambda: a + b)
    bench("a += b   (in place, no temporary)", lambda: np.add(a, b, out=a))

    contiguous = rng.random((3000, 3000))
    transposed = contiguous.T
    print(f"  .T is a free view with swapped strides: {transposed.flags['C_CONTIGUOUS']=}")
    bench("copy of a contiguous array", contiguous.copy)
    bench("np.ascontiguousarray(a.T)", lambda: np.ascontiguousarray(transposed))
    print("  reading strided memory is fine; MATERIALISING it in a new layout is what costs.")
    print("  (element-wise ops on a transpose are barely slower — measure, don't assume.)")


if __name__ == "__main__":
    print(INTRO)
    the_array()
    dtypes()
    vectorisation()
    broadcasting()
    views_and_copies()
    axes()
    useful_functions()
    performance()
