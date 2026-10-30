"""Module 22 — reference solutions."""

from __future__ import annotations

import bisect
import heapq
from collections import OrderedDict, deque
from collections.abc import Hashable, Iterable, Sequence
from typing import Any, TypeVar

T = TypeVar("T")
Node = TypeVar("Node", bound=Hashable)


def binary_search(items: Sequence[Any], target: Any) -> int:
    lo, hi = 0, len(items) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2  # avoids overflow in languages that can overflow
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    ordered = sorted(intervals)
    for start, end in ordered:
        if start > end:
            raise ValueError(f"invalid interval: ({start}, {end})")

    merged: list[tuple[int, int]] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:  # <= so touching intervals merge
            last_start, last_end = merged[-1]
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


class LRUCache:
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        self.capacity = capacity
        self._data: OrderedDict[Any, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: Any, default: Any = None) -> Any:
        if key not in self._data:
            self.misses += 1
            return default
        self.hits += 1
        self._data.move_to_end(key)  # O(1): most recently used goes to the end
        return self._data[key]

    def put(self, key: Any, value: Any) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)  # pop the least recently used
            self.evictions += 1

    def clear(self) -> None:
        self._data.clear()

    def __contains__(self, key: object) -> bool:
        return key in self._data  # a membership test is not a use

    def __len__(self) -> int:
        return len(self._data)


def topological_sort(graph: dict[Node, list[Node]]) -> list[Node]:
    in_degree: dict[Node, int] = {}
    for node, successors in graph.items():
        in_degree.setdefault(node, 0)
        for successor in successors:
            in_degree[successor] = in_degree.get(successor, 0) + 1

    queue = deque(node for node, degree in in_degree.items() if degree == 0)
    order: list[Node] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for successor in graph.get(node, []):
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                queue.append(successor)

    if len(order) != len(in_degree):
        stuck = sorted(str(n) for n, d in in_degree.items() if d > 0)
        raise ValueError(f"graph has a cycle involving: {', '.join(stuck)}")
    return order


def shortest_paths(
    graph: dict[Node, list[tuple[Node, float]]], start: Node
) -> dict[Node, float]:
    if start not in graph:
        raise KeyError(start)

    distances: dict[Node, float] = {start: 0}
    heap: list[tuple[float, Any]] = [(0, start)]
    settled: set[Node] = set()

    while heap:
        distance, node = heapq.heappop(heap)
        if node in settled:  # a stale entry left behind by lazy deletion
            continue
        settled.add(node)
        for neighbour, weight in graph.get(node, []):
            if weight < 0:
                raise ValueError(f"negative weight {weight} on edge {node}->{neighbour}")
            candidate = distance + weight
            if candidate < distances.get(neighbour, float("inf")):
                distances[neighbour] = candidate
                heapq.heappush(heap, (candidate, neighbour))
    return distances


def edit_distance(a: str, b: str) -> int:
    if len(a) < len(b):  # keep the inner row as short as possible
        a, b = b, a

    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            if char_a == char_b:
                current.append(previous[j - 1])
            else:
                current.append(1 + min(previous[j], current[j - 1], previous[j - 1]))
        previous = current  # only two rows ever exist
    return previous[-1]


def longest_increasing_subsequence(values: Sequence[int]) -> int:
    # tails[k] is the smallest possible tail of an increasing subsequence of length k+1.
    tails: list[int] = []
    for value in values:
        index = bisect.bisect_left(tails, value)
        if index == len(tails):
            tails.append(value)
        else:
            tails[index] = value
    return len(tails)
