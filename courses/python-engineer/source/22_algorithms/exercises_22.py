"""Module 22 exercises.  pytest 22_algorithms

The tests check complexity as well as correctness: several of them run inputs large
enough that a quadratic answer times out. Reach for `heapq`, `bisect`, `deque` and
`functools.cache` — and hand-roll only where the exercise says to.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Sequence
from typing import Any, TypeVar

T = TypeVar("T")
Node = TypeVar("Node", bound=Hashable)


def binary_search(items: Sequence[Any], target: Any) -> int:
    """Return the index of `target` in a sorted sequence, or -1.

    >>> binary_search([1, 3, 5, 7], 5)
    2
    >>> binary_search([1, 3, 5, 7], 4)
    -1

    Write the loop yourself (this one IS the learning exercise), then note that
    `bisect.bisect_left` plus a bounds check is the production answer.

    Get the invariant right: `lo <= hi`, and `mid = lo + (hi - lo) // 2`. Duplicates may
    return any matching index.
    """
    raise NotImplementedError


def merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or touching intervals.

    >>> merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)])
    [(1, 6), (8, 10), (15, 18)]
    >>> merge_intervals([(1, 4), (4, 5)])
    [(1, 5)]

    - Input order is arbitrary; output is sorted by start.
    - Touching counts as overlapping ((1,4) and (4,5) merge).
    - An interval with start > end raises ValueError.
    - Empty input -> [].

    Sort once, then a single pass: O(n log n) total, no nested loop.
    """
    raise NotImplementedError


class LRUCache:
    """A fixed-capacity LRU cache with O(1) get and put.

    >>> cache = LRUCache(2)
    >>> cache.put("a", 1); cache.put("b", 2); cache.get("a")
    1
    >>> cache.put("c", 3)      # evicts "b", the least recently used
    >>> cache.get("b") is None
    True

    - `get(key, default=None)` returns the value and marks it most-recently-used.
    - `put(key, value)` inserts or updates, evicting the LRU entry when over capacity.
      Updating an existing key also refreshes it.
    - `len(cache)`, `key in cache` (which must NOT count as a use), `.clear()`.
    - `.hits` and `.misses` counters, and `.evictions`.
    - capacity < 1 raises ValueError.

    `collections.OrderedDict.move_to_end` and `popitem(last=False)` give you O(1). A list
    scan for the LRU entry is O(n) and the tests will catch it.
    """

    def __init__(self, capacity: int) -> None:
        raise NotImplementedError


def topological_sort(graph: dict[Node, list[Node]]) -> list[Node]:
    """Return an order where every node precedes its dependents. Raise ValueError on a cycle.

    `graph[node]` lists the nodes that `node` points TO (its successors).

    >>> topological_sort({"a": ["b"], "b": ["c"], "c": []})
    ['a', 'b', 'c']

    - Implement Kahn's algorithm: compute in-degrees, seed a queue with the zero-degree
      nodes, and peel. Do NOT just call `graphlib` — you're writing it once so you know
      what it does.
    - Ties are broken by insertion order of the graph dict, so the result is deterministic.
    - A node that only appears as a successor is still part of the graph.
    - A cycle raises ValueError listing the nodes still unprocessed.
    """
    raise NotImplementedError


def shortest_paths(
    graph: dict[Node, list[tuple[Node, float]]], start: Node
) -> dict[Node, float]:
    """Dijkstra: shortest distance from `start` to every reachable node.

    >>> shortest_paths({"a": [("b", 4), ("c", 2)], "c": [("b", 1)], "b": []}, "a")
    {'a': 0, 'c': 2, 'b': 3}

    - Use `heapq` with the LAZY deletion trick: push `(distance, node)` and skip a popped
      node you've already settled. Python's heap has no decrease-key.
    - Unreachable nodes are absent from the result (not infinity).
    - A negative weight raises ValueError — Dijkstra is simply wrong with those, and
      silently returning a wrong answer is the worst possible behaviour.
    - An unknown `start` raises KeyError.
    """
    raise NotImplementedError


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance: the fewest insert/delete/substitute edits from `a` to `b`.

    >>> edit_distance("kitten", "sitting")
    3

    Use the BOTTOM-UP form with only two rows of memory. The tests compare 2,000-character
    strings, so a naive recursion (exponential) or a full n*m table (400 MB) both fail.
    """
    raise NotImplementedError


def longest_increasing_subsequence(values: Sequence[int]) -> int:
    """Length of the longest strictly increasing subsequence (not substring).

    >>> longest_increasing_subsequence([10, 9, 2, 5, 3, 7, 101, 18])
    4

    The O(n^2) DP is the obvious answer; the tests use 100,000 elements, so you need the
    O(n log n) one: keep a list of the smallest possible tail for each length and place
    each value with `bisect_left`. That list is NOT the subsequence itself — only its
    length is meaningful.
    """
    raise NotImplementedError
