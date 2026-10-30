import random
import time

import pytest

from courselib import impl

m = impl("22")


def timed(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


class TestBinarySearch:
    def test_found(self):
        assert m.binary_search([1, 3, 5, 7], 5) == 2

    def test_first_and_last(self):
        assert m.binary_search([1, 3, 5, 7], 1) == 0
        assert m.binary_search([1, 3, 5, 7], 7) == 3

    def test_not_found(self):
        assert m.binary_search([1, 3, 5, 7], 4) == -1

    def test_empty(self):
        assert m.binary_search([], 1) == -1

    def test_single(self):
        assert m.binary_search([5], 5) == 0
        assert m.binary_search([5], 1) == -1

    def test_duplicates_return_a_valid_index(self):
        items = [1, 2, 2, 2, 3]
        assert items[m.binary_search(items, 2)] == 2

    def test_strings(self):
        assert m.binary_search(["a", "c", "e"], "c") == 1

    def test_matches_bruteforce(self):
        rng = random.Random(7)
        for _ in range(50):
            items = sorted(rng.sample(range(200), rng.randint(0, 40)))
            target = rng.randint(0, 200)
            got = m.binary_search(items, target)
            assert (got == -1) == (target not in items)
            if got != -1:
                assert items[got] == target

    def test_is_logarithmic(self):
        items = list(range(5_000_000))
        assert timed(lambda: [m.binary_search(items, n) for n in range(0, 5_000_000, 250_000)]) < 0.1


class TestMergeIntervals:
    def test_basic(self):
        assert m.merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)]) == [(1, 6), (8, 10), (15, 18)]

    def test_touching_merges(self):
        assert m.merge_intervals([(1, 4), (4, 5)]) == [(1, 5)]

    def test_unsorted_input(self):
        assert m.merge_intervals([(8, 10), (1, 3), (2, 6)]) == [(1, 6), (8, 10)]

    def test_contained_interval(self):
        assert m.merge_intervals([(1, 10), (3, 5)]) == [(1, 10)]

    def test_identical(self):
        assert m.merge_intervals([(1, 2), (1, 2)]) == [(1, 2)]

    def test_empty(self):
        assert m.merge_intervals([]) == []

    def test_single(self):
        assert m.merge_intervals([(1, 2)]) == [(1, 2)]

    def test_zero_width(self):
        assert m.merge_intervals([(1, 1), (2, 2)]) == [(1, 1), (2, 2)]

    def test_invalid_interval(self):
        with pytest.raises(ValueError):
            m.merge_intervals([(5, 1)])

    def test_is_n_log_n(self):
        rng = random.Random(1)
        intervals = [(s := rng.randint(0, 10**6), s + rng.randint(0, 100)) for _ in range(200_000)]
        assert timed(lambda: m.merge_intervals(intervals)) < 2.0


class TestLRUCache:
    def test_get_and_put(self):
        cache = m.LRUCache(2)
        cache.put("a", 1)
        assert cache.get("a") == 1

    def test_missing_returns_default(self):
        cache = m.LRUCache(2)
        assert cache.get("nope") is None
        assert cache.get("nope", "fallback") == "fallback"

    def test_evicts_least_recently_used(self):
        cache = m.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # "a" is now the most recently used
        cache.put("c", 3)
        assert cache.get("b") is None
        assert cache.get("a") == 1

    def test_update_refreshes_recency(self):
        cache = m.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)
        cache.put("c", 3)
        assert cache.get("b") is None
        assert cache.get("a") == 10

    def test_capacity_one(self):
        cache = m.LRUCache(1)
        cache.put("a", 1)
        cache.put("b", 2)
        assert cache.get("a") is None and cache.get("b") == 2

    def test_len_and_contains(self):
        cache = m.LRUCache(2)
        cache.put("a", 1)
        assert len(cache) == 1
        assert "a" in cache
        assert "b" not in cache

    def test_contains_is_not_a_use(self):
        cache = m.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        assert "a" in cache  # must not refresh "a"
        cache.put("c", 3)
        assert "a" not in cache

    def test_counters(self):
        cache = m.LRUCache(1)
        cache.put("a", 1)
        cache.get("a")
        cache.get("missing")
        cache.put("b", 2)
        assert (cache.hits, cache.misses, cache.evictions) == (1, 1, 1)

    def test_clear(self):
        cache = m.LRUCache(2)
        cache.put("a", 1)
        cache.clear()
        assert len(cache) == 0

    def test_rejects_bad_capacity(self):
        with pytest.raises(ValueError):
            m.LRUCache(0)

    def test_operations_are_constant_time(self):
        cache = m.LRUCache(1000)

        def hammer():
            for n in range(200_000):
                cache.put(n, n)
                cache.get(n - 500)

        assert timed(hammer) < 2.0  # an O(n) eviction scan would take minutes


class TestTopologicalSort:
    def test_chain(self):
        assert m.topological_sort({"a": ["b"], "b": ["c"], "c": []}) == ["a", "b", "c"]

    def test_diamond(self):
        order = m.topological_sort({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []})
        assert order.index("a") < order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_independent_nodes(self):
        assert sorted(m.topological_sort({"a": [], "b": []})) == ["a", "b"]

    def test_empty(self):
        assert m.topological_sort({}) == []

    def test_node_only_appearing_as_a_successor(self):
        assert m.topological_sort({"a": ["b"]}) == ["a", "b"]

    def test_cycle_raises(self):
        with pytest.raises(ValueError, match="cycle"):
            m.topological_sort({"a": ["b"], "b": ["a"]})

    def test_self_loop_raises(self):
        with pytest.raises(ValueError):
            m.topological_sort({"a": ["a"]})

    def test_partial_cycle_raises(self):
        with pytest.raises(ValueError):
            m.topological_sort({"a": ["b"], "b": ["c"], "c": ["b"]})

    def test_every_edge_is_respected(self):
        rng = random.Random(3)
        nodes = list(range(200))
        graph = {n: [] for n in nodes}
        for n in nodes:
            for target in rng.sample(nodes[n + 1 :], min(3, len(nodes) - n - 1)):
                graph[n].append(target)
        order = m.topological_sort(graph)
        position = {node: i for i, node in enumerate(order)}
        assert all(position[a] < position[b] for a, targets in graph.items() for b in targets)


class TestShortestPaths:
    GRAPH = {"a": [("b", 4), ("c", 2)], "b": [("d", 5)], "c": [("b", 1), ("d", 8)], "d": []}

    def test_distances(self):
        assert m.shortest_paths(self.GRAPH, "a") == {"a": 0, "b": 3, "c": 2, "d": 8}

    def test_prefers_the_cheaper_route(self):
        assert m.shortest_paths(self.GRAPH, "a")["b"] == 3  # a->c->b beats a->b

    def test_start_has_distance_zero(self):
        assert m.shortest_paths(self.GRAPH, "d") == {"d": 0}

    def test_unreachable_nodes_are_absent(self):
        graph = {"a": [], "b": [("a", 1)]}
        assert m.shortest_paths(graph, "a") == {"a": 0}

    def test_unknown_start(self):
        with pytest.raises(KeyError):
            m.shortest_paths(self.GRAPH, "zzz")

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError):
            m.shortest_paths({"a": [("b", -1)], "b": []}, "a")

    def test_zero_weights(self):
        assert m.shortest_paths({"a": [("b", 0)], "b": []}, "a") == {"a": 0, "b": 0}

    def test_scales(self):
        # A 100k-node chain: fine with a heap, hopeless with a linear-scan minimum.
        graph = {n: [(n + 1, 1)] for n in range(100_000)}
        graph[100_000] = []
        assert timed(lambda: m.shortest_paths(graph, 0)) < 2.0


class TestEditDistance:
    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            ("kitten", "sitting", 3),
            ("flaw", "lawn", 2),
            ("", "abc", 3),
            ("abc", "", 3),
            ("", "", 0),
            ("same", "same", 0),
            ("a", "b", 1),
            ("abcdef", "abcdef", 0),
        ],
    )
    def test_cases(self, a, b, expected):
        assert m.edit_distance(a, b) == expected

    def test_symmetric(self):
        assert m.edit_distance("kitten", "sitting") == m.edit_distance("sitting", "kitten")

    def test_large_inputs(self):
        rng = random.Random(11)
        a = "".join(rng.choice("abcd") for _ in range(2000))
        b = "".join(rng.choice("abcd") for _ in range(2000))
        assert timed(lambda: m.edit_distance(a, b)) < 5.0


class TestLongestIncreasingSubsequence:
    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            ([10, 9, 2, 5, 3, 7, 101, 18], 4),
            ([1, 2, 3, 4], 4),
            ([4, 3, 2, 1], 1),
            ([], 0),
            ([5], 1),
            ([2, 2, 2], 1),  # strictly increasing, so duplicates don't extend it
            ([1, 3, 2, 4], 3),
        ],
    )
    def test_cases(self, values, expected):
        assert m.longest_increasing_subsequence(values) == expected

    def test_is_n_log_n(self):
        rng = random.Random(5)
        values = [rng.randint(0, 10**9) for _ in range(100_000)]
        assert timed(lambda: m.longest_increasing_subsequence(values)) < 2.0
