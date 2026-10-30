"""Benchmark your exercises_13 against the slow originals.

    python 13_performance/bench_13.py

Shows the speedup you actually achieved on each task. The reference solutions are the
target; being within ~2x of them is a pass.
"""

from __future__ import annotations

import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import exercises_13 as yours  # noqa: E402
import solutions_13 as reference  # noqa: E402

RNG = random.Random(42)


def measure(fn, *args, repeat: int = 3) -> float:
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        fn(*args)
        best = min(best, time.perf_counter() - start)
    return best


CASES: list[tuple[str, str, tuple]] = [
    (
        "count_common",
        "count_common",
        (list(range(30_000)), list(range(15_000, 45_000))),
    ),
    (
        "join_records",
        "join_records",
        ([{"id": i} for i in range(8_000)], [{"id": i} for i in range(8_000)], "id"),
    ),
    ("build_report", "build_report", ([(f"k{i}", i) for i in range(60_000)],)),
    ("deduplicate_in_order", "deduplicate_in_order", (list(range(40_000)) * 2,)),
    ("running_maximum", "running_maximum", ([RNG.randint(0, 1000) for _ in range(30_000)],)),
    ("group_totals", "group_totals", ([(f"g{i % 300}", 1) for i in range(60_000)],)),
]


def main() -> None:
    print(f"{'task':<24}{'yours':>12}{'reference':>12}{'speedup':>10}")
    print("-" * 58)
    for label, attr, args in CASES:
        try:
            mine = measure(getattr(yours, attr), *args)
        except NotImplementedError:
            print(f"{label:<24}{'not implemented':>34}")
            continue
        theirs = measure(getattr(reference, attr), *args)
        ratio = mine / theirs if theirs else float("inf")
        verdict = "ok" if ratio < 2 else "SLOW"
        print(f"{label:<24}{mine * 1000:>10.2f}ms{theirs * 1000:>10.2f}ms{ratio:>8.1f}x {verdict}")

    # top_k gets its own case: the input is an iterator, so it can't be reused.
    for label, module in (("top_k (yours)", yours), ("top_k (reference)", reference)):
        start = time.perf_counter()
        module.top_k(iter(range(1_000_000)), 10)
        print(f"{label:<24}{(time.perf_counter() - start) * 1000:>10.2f}ms")

    print("\nInventory.total, 20k skus x 5k reads:")
    for label, module in (("yours", yours), ("reference", reference)):
        inv = module.Inventory()
        for i in range(20_000):
            inv.add(f"sku{i}", 1)
        elapsed = measure(lambda inv=inv: sum(inv.total for _ in range(5_000)), repeat=1)
        print(f"  {label:<20}{elapsed * 1000:>10.2f}ms")


if __name__ == "__main__":
    os.environ.pop("SOLUTIONS", None)
    main()
