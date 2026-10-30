"""Module 13 exercises.  pytest 13_performance

Each function below is CORRECT and SLOW. Rewrite the body so it stays correct and gets
fast. The tests check behaviour first, then time a large input against a strict budget —
so only an algorithmic fix will pass, not a micro-optimisation.

Keep the signature. Read the "currently" note, work out the complexity, then fix it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


def count_common(a: Sequence[Any], b: Sequence[Any]) -> int:
    """Count how many items of `a` also appear in `b` (counting duplicates in `a`).

    >>> count_common([1, 2, 2, 3], [2, 3])
    3

    Currently O(len(a) * len(b)) — a linear scan of `b` for every item of `a`.
    Target: O(len(a) + len(b)).
    """
    return sum(1 for item in a if item in b)  # <- fix this


def join_records(
    left: Sequence[dict[str, Any]], right: Sequence[dict[str, Any]], key: str
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Inner-join two record lists on `key`, preserving `left` order.

    Assume `key` is unique in `right`. Records in `left` with no match are dropped;
    records missing the key entirely are also dropped.

    Currently O(n*m). Target: O(n+m) by indexing `right` once.
    """
    out = []
    for a in left:
        for b in right:
            if key in a and key in b and a[key] == b[key]:
                out.append((a, b))
    return out  # <- fix this


def build_report(rows: Iterable[tuple[str, int]]) -> str:
    """Render "name=value" lines separated by newlines, in input order.

    >>> build_report([("a", 1), ("b", 2)])
    'a=1\\nb=2'

    Currently built with `+=` in a loop. CPython special-cases that when the string's
    refcount is 1, so it is not actually quadratic *here* — but it is on PyPy and other
    implementations, and the moment anything else holds a reference to the string. Rewrite
    it with a single `"\n".join(...)`, which is O(n) everywhere and needs no caveat.
    """
    report = ""
    for name, value in rows:
        if report:
            report += "\n"
        report += f"{name}={value}"
    return report  # <- fix this


def top_k(scores: Iterable[float], k: int) -> list[float]:
    """Return the k largest scores, highest first.

    >>> top_k([5, 1, 9, 3], 2)
    [9, 5]

    - k <= 0 returns [].
    - k larger than the input returns everything, sorted descending.

    Currently sorts the whole input. Note carefully: on a million ints `sorted()` is
    actually FASTER than `heapq.nlargest` — C sorting is very fast. The win here is
    MEMORY: sorting materialises the entire stream (~40 MB for 1M ints) while nlargest
    holds k items. The test measures peak allocation, not time.

    Target: `heapq.nlargest`, O(n log k) time and O(k) memory, over a one-shot iterator.
    """
    return sorted(scores, reverse=True)[: max(k, 0)]  # <- fix this


def deduplicate_in_order(items: Iterable[Any]) -> list[Any]:
    """Drop duplicates, keeping first-seen order. Items are hashable.

    Currently O(n^2): `in` on a growing list. Target: O(n) with a `set` alongside.
    """
    out: list[Any] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out  # <- fix this


def running_maximum(values: Sequence[float]) -> list[float]:
    """For each position, the maximum of everything up to and including it.

    >>> running_maximum([1, 3, 2, 5])
    [1, 3, 3, 5]

    Currently O(n^2): `max()` over a growing slice at every step. Target: O(n) with a
    single carried variable (or `itertools.accumulate`).
    """
    return [max(values[: i + 1]) for i in range(len(values))]  # <- fix this


def group_totals(rows: Iterable[tuple[str, float]]) -> dict[str, float]:
    """Sum the values per group, preserving first-seen group order.

    >>> group_totals([("a", 1), ("b", 2), ("a", 3)])
    {'a': 4, 'b': 2}

    Currently walks every row again for each distinct group: O(g*n).
    Target: one pass, O(n).
    """
    rows = list(rows)
    groups = []
    for name, _ in rows:
        if name not in groups:
            groups.append(name)
    return {g: sum(v for n, v in rows if n == g) for g in groups}  # <- fix this


class Inventory:
    """A stock ledger with a fast "what's low?" query.

    - `add(sku, quantity)` adds (or tops up) a SKU.
    - `remove(sku)` deletes it; unknown SKU raises KeyError.
    - `quantity(sku)` returns the current count, 0 for unknown SKUs.
    - `low_stock(threshold)` returns the SKUs with quantity < threshold, sorted by
      quantity ascending then SKU ascending.
    - `total` is the sum of all quantities.

    Currently `total` recomputes a full sum on every access. With thousands of calls that
    dominates the workload — maintain it incrementally instead. (`low_stock` genuinely
    has to scan; that one is fine.)
    """

    def __init__(self) -> None:
        self._items: dict[str, int] = {}

    def add(self, sku: str, quantity: int) -> None:
        self._items[sku] = self._items.get(sku, 0) + quantity

    def remove(self, sku: str) -> None:
        del self._items[sku]

    def quantity(self, sku: str) -> int:
        return self._items.get(sku, 0)

    def low_stock(self, threshold: int) -> list[str]:
        return sorted(
            (s for s, q in self._items.items() if q < threshold),
            key=lambda s: (self._items[s], s),
        )

    @property
    def total(self) -> int:
        return sum(self._items.values())  # <- fix this
