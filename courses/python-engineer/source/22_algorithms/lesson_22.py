"""Module 22 — runnable lesson. `python 22_algorithms/lesson_22.py`"""

from __future__ import annotations

import bisect
import functools
import graphlib
import heapq
import sys
import time
from collections import deque

INTRO = """Big-O asks one question: when the input gets bigger, how much worse does this get? O(n) at
100 items and at 100,000 items is fine. O(n squared) is instant at 100 and appears to hang
forever at 100,000. Same code — different shape."""

GRAPH = {
    "a": ["b", "c"],
    "b": ["d"],
    "c": ["d", "e"],
    "d": ["f"],
    "e": ["f"],
    "f": [],
}
WEIGHTED = {
    "a": [("b", 4), ("c", 2)],
    "b": [("d", 5)],
    "c": [("b", 1), ("d", 8)],
    "d": [],
}


def batteries_included() -> None:
    print("\n== the stdlib already has it ==")
    heap = [5, 1, 9]
    heapq.heapify(heap)
    heapq.heappush(heap, 3)
    print(f"  heapq:      pop-min sequence {[heapq.heappop(heap) for _ in range(4)]}")
    print(f"  nlargest:   {heapq.nlargest(3, [5, 1, 9, 7, 3])}  (O(n log k), not a full sort)")
    print(f"  merge:      {list(heapq.merge([1, 4], [2, 3], [5]))}  (lazy, sorted streams)")

    scores = [10, 20, 30, 40]
    print(f"  bisect:     insertion point for 25 is {bisect.bisect_left(scores, 25)}")
    bisect.insort(scores, 25)
    print(f"              after insort: {scores}")

    window = deque(maxlen=3)
    for n in range(6):
        window.append(n)
    print(f"  deque:      ring buffer of 3 -> {list(window)}, O(1) at both ends")

    order = graphlib.TopologicalSorter(
        {node: set(deps) for node, deps in GRAPH.items()}
    ).static_order()
    print(f"  graphlib:   topological order {list(order)}")


def complexity_in_practice() -> None:
    print("\n== constant factors are real ==")
    data = list(range(200_000))

    start = time.perf_counter()
    result = deque()
    for n in data:
        result.appendleft(n)
    deque_time = time.perf_counter() - start

    small = data[:20_000]
    start = time.perf_counter()
    result_list = []
    for n in small:
        result_list.insert(0, n)
    list_time = time.perf_counter() - start

    print(f"  deque.appendleft x200,000: {deque_time * 1000:>8.1f} ms  (O(1) each)")
    print(f"  list.insert(0)  x 20,000: {list_time * 1000:>8.1f} ms  (O(n) each)")
    print(f"  ten times fewer items and still {list_time / deque_time:.0f}x slower")


def recursion() -> None:
    print("\n== recursion has a hard floor ==")
    print(f"  sys.getrecursionlimit() = {sys.getrecursionlimit()}")

    def depth(n: int) -> int:
        return 0 if n == 0 else 1 + depth(n - 1)

    try:
        depth(10_000)
    except RecursionError:
        print("  depth(10_000): RecursionError — no tail-call optimisation in CPython")

    def depth_iterative(n: int) -> int:
        count = 0
        stack = [n]
        while stack:
            value = stack.pop()
            if value:
                count += 1
                stack.append(value - 1)
        return count

    print(f"  the same thing with an explicit stack: {depth_iterative(100_000):,}")

    @functools.cache
    def fib(n: int) -> int:
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    def fib_slow(n: int) -> int:
        return n if n < 2 else fib_slow(n - 1) + fib_slow(n - 2)

    start = time.perf_counter()
    fib_slow(27)
    slow = time.perf_counter() - start
    start = time.perf_counter()
    fib(27)
    fast = time.perf_counter() - start
    print(f"  fib(27): naive {slow * 1000:.1f} ms vs @cache {fast * 1000:.3f} ms "
          f"({slow / fast:.0f}x) — exponential becomes linear")


def graph_algorithms() -> None:
    print("\n== BFS: shortest path in an unweighted graph ==")

    def bfs_path(graph, start, goal):
        queue = deque([[start]])
        seen = {start}
        while queue:
            path = queue.popleft()
            node = path[-1]
            if node == goal:
                return path
            for neighbour in graph[node]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append([*path, neighbour])
        return None

    print(f"  a -> f: {bfs_path(GRAPH, 'a', 'f')}")

    print("\n== DFS: iterative, with an explicit stack ==")

    def dfs(graph, start):
        stack, seen, order = [start], set(), []
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            order.append(node)
            stack.extend(reversed(graph[node]))
        return order

    print(f"  visit order: {dfs(GRAPH, 'a')}")

    print("\n== Dijkstra with heapq (the lazy variant) ==")

    def dijkstra(graph, start):
        distances = {start: 0}
        heap = [(0, start)]
        settled = set()
        while heap:
            distance, node = heapq.heappop(heap)
            if node in settled:  # a stale entry — skip it instead of decrease-key
                continue
            settled.add(node)
            for neighbour, weight in graph[node]:
                candidate = distance + weight
                if candidate < distances.get(neighbour, float("inf")):
                    distances[neighbour] = candidate
                    heapq.heappush(heap, (candidate, neighbour))
        return distances

    print(f"  distances from 'a': {dijkstra(WEIGHTED, 'a')}")
    print("  note a->c->b (3) beats the direct a->b (4)")

    print("\n== cycles break a topological sort ==")
    try:
        graphlib.TopologicalSorter({"a": {"b"}, "b": {"a"}}).prepare()
    except graphlib.CycleError as exc:
        print(f"  CycleError: {exc.args[0]}")


def dynamic_programming() -> None:
    print("\n== DP: two ways to write the same recurrence ==")

    @functools.cache
    def edit_top_down(a: str, b: str) -> int:
        if not a:
            return len(b)
        if not b:
            return len(a)
        if a[0] == b[0]:
            return edit_top_down(a[1:], b[1:])
        return 1 + min(
            edit_top_down(a[1:], b),  # delete
            edit_top_down(a, b[1:]),  # insert
            edit_top_down(a[1:], b[1:]),  # substitute
        )

    def edit_bottom_up(a: str, b: str) -> int:
        previous = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            current = [i]
            for j, cb in enumerate(b, 1):
                current.append(
                    previous[j - 1] if ca == cb
                    else 1 + min(previous[j], current[j - 1], previous[j - 1])
                )
            previous = current  # only ever two rows in memory
        return previous[-1]

    for a, b in [("kitten", "sitting"), ("flaw", "lawn"), ("", "abc")]:
        print(f"  edit({a!r}, {b!r}) = {edit_top_down(a, b)} == {edit_bottom_up(a, b)}")
    print("  top-down: the recurrence + one decorator. bottom-up: O(width) memory.")


if __name__ == "__main__":
    print(INTRO)
    batteries_included()
    complexity_in_practice()
    recursion()
    graph_algorithms()
    dynamic_programming()
