"""Module 13 — reference solutions."""

from __future__ import annotations

import heapq
import itertools
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any


def count_common(a: Sequence[Any], b: Sequence[Any]) -> int:
    lookup = set(b)  # O(m) once, then O(1) per test
    return sum(1 for item in a if item in lookup)


def join_records(
    left: Sequence[dict[str, Any]], right: Sequence[dict[str, Any]], key: str
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    index = {b[key]: b for b in right if key in b}  # index the smaller side once
    return [(a, index[a[key]]) for a in left if key in a and a[key] in index]


def build_report(rows: Iterable[tuple[str, int]]) -> str:
    # One allocation for the result instead of one per row.
    return "\n".join(f"{name}={value}" for name, value in rows)


def top_k(scores: Iterable[float], k: int) -> list[float]:
    if k <= 0:
        return []
    return heapq.nlargest(k, scores)  # O(n log k), and never materialises the input


def deduplicate_in_order(items: Iterable[Any]) -> list[Any]:
    seen: set[Any] = set()
    out: list[Any] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def running_maximum(values: Sequence[float]) -> list[float]:
    return list(itertools.accumulate(values, max))


def group_totals(rows: Iterable[tuple[str, float]]) -> dict[str, float]:
    totals: defaultdict[str, float] = defaultdict(float)
    for name, value in rows:  # dict preserves first-seen insertion order
        totals[name] += value
    return dict(totals)


class Inventory:
    def __init__(self) -> None:
        self._items: dict[str, int] = {}
        self._total = 0  # maintained incrementally

    def add(self, sku: str, quantity: int) -> None:
        self._items[sku] = self._items.get(sku, 0) + quantity
        self._total += quantity

    def remove(self, sku: str) -> None:
        self._total -= self._items.pop(sku)  # KeyError propagates before _total changes

    def quantity(self, sku: str) -> int:
        return self._items.get(sku, 0)

    def low_stock(self, threshold: int) -> list[str]:
        return sorted(
            (s for s, q in self._items.items() if q < threshold),
            key=lambda s: (self._items[s], s),
        )

    @property
    def total(self) -> int:
        return self._total
