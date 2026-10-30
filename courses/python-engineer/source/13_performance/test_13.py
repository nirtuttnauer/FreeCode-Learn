"""Correctness first, then a timing budget that only an algorithmic fix can meet.

The budgets are deliberately loose (10-50x slack on a modern laptop) so they don't flake,
but they are far too tight for a quadratic implementation.
"""

import random
import time

import pytest

from courselib import impl

m = impl("13")


def timed(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


class TestCountCommon:
    def test_correct(self):
        assert m.count_common([1, 2, 2, 3], [2, 3]) == 3

    def test_no_overlap(self):
        assert m.count_common([1, 2], [3, 4]) == 0

    def test_empty(self):
        assert m.count_common([], [1]) == 0
        assert m.count_common([1], []) == 0

    def test_strings(self):
        assert m.count_common("hello", "lo") == 3

    def test_is_linear(self):
        a = list(range(15_000))
        b = list(range(7_500, 22_500))
        # The scanning version takes ~300ms here and grows quadratically from there.
        assert timed(lambda: m.count_common(a, b)) < 0.05


class TestJoinRecords:
    def test_correct(self):
        left = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
        right = [{"id": 2, "w": "y"}, {"id": 1, "w": "x"}]
        got = m.join_records(left, right, "id")
        assert [(a["v"], b["w"]) for a, b in got] == [("a", "x"), ("b", "y")]

    def test_drops_unmatched(self):
        assert m.join_records([{"id": 1}], [{"id": 2}], "id") == []

    def test_drops_records_missing_the_key(self):
        assert m.join_records([{"other": 1}], [{"id": 1}], "id") == []

    def test_preserves_left_order(self):
        left = [{"id": i} for i in [3, 1, 2]]
        right = [{"id": i} for i in [1, 2, 3]]
        assert [a["id"] for a, _ in m.join_records(left, right, "id")] == [3, 1, 2]

    def test_is_linear(self):
        left = [{"id": i} for i in range(3_000)]
        right = [{"id": i} for i in range(3_000)]
        assert timed(lambda: m.join_records(left, right, "id")) < 0.05


class TestBuildReport:
    def test_correct(self):
        assert m.build_report([("a", 1), ("b", 2)]) == "a=1\nb=2"

    def test_empty(self):
        assert m.build_report([]) == ""

    def test_single(self):
        assert m.build_report([("a", 1)]) == "a=1"

    def test_accepts_a_generator(self):
        assert m.build_report((n, i) for i, n in enumerate(["a", "b"])) == "a=0\nb=1"

    def test_handles_a_large_input(self):
        # Honest note: CPython special-cases `s += t` when `s` has a refcount of 1, so the
        # naive loop is not actually quadratic HERE. It is on other implementations, and
        # the moment anything else holds a reference to the string. join() is correct
        # everywhere and never needs that caveat.
        rows = [(f"key{i}", i) for i in range(200_000)]
        assert timed(lambda: m.build_report(rows)) < 1.0


class TestTopK:
    def test_correct(self):
        assert m.top_k([5, 1, 9, 3], 2) == [9, 5]

    def test_k_zero_or_negative(self):
        assert m.top_k([1, 2], 0) == []
        assert m.top_k([1, 2], -1) == []

    def test_k_larger_than_input(self):
        assert m.top_k([1, 2], 5) == [2, 1]

    def test_duplicates(self):
        assert m.top_k([5, 5, 1], 2) == [5, 5]

    def test_works_on_a_one_shot_iterator(self):
        assert m.top_k(iter([3, 1, 2]), 2) == [3, 2]

    def test_small_k_over_a_large_stream_is_memory_bounded(self):
        # The real win is MEMORY, not time: sorted() materialises the whole stream
        # (~40 MB for 1M ints) while nlargest holds k items.
        import tracemalloc

        tracemalloc.start()
        m.top_k(iter(range(1_000_000)), 10)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert peak < 5_000_000, f"peaked at {peak / 1e6:.1f} MB — the input was materialised"


class TestDeduplicateInOrder:
    def test_correct(self):
        assert m.deduplicate_in_order([3, 1, 3, 2, 1]) == [3, 1, 2]

    def test_empty(self):
        assert m.deduplicate_in_order([]) == []

    def test_strings(self):
        assert m.deduplicate_in_order("abracadabra") == list("abrcd")

    def test_is_linear(self):
        data = list(range(8_000)) * 2
        assert timed(lambda: m.deduplicate_in_order(data)) < 0.05


class TestRunningMaximum:
    def test_correct(self):
        assert m.running_maximum([1, 3, 2, 5]) == [1, 3, 3, 5]

    def test_empty(self):
        assert m.running_maximum([]) == []

    def test_decreasing(self):
        assert m.running_maximum([5, 4, 3]) == [5, 5, 5]

    def test_matches_bruteforce(self):
        rng = random.Random(7)
        values = [rng.randint(-100, 100) for _ in range(200)]
        expected = [max(values[: i + 1]) for i in range(len(values))]
        assert m.running_maximum(values) == expected

    def test_is_linear(self):
        values = list(range(6_000))
        assert timed(lambda: m.running_maximum(values)) < 0.05


class TestGroupTotals:
    def test_correct(self):
        assert m.group_totals([("a", 1), ("b", 2), ("a", 3)]) == {"a": 4, "b": 2}

    def test_preserves_first_seen_order(self):
        assert list(m.group_totals([("b", 1), ("a", 1)])) == ["b", "a"]

    def test_empty(self):
        assert m.group_totals([]) == {}

    def test_accepts_a_generator(self):
        assert m.group_totals(("a", i) for i in range(3)) == {"a": 3}

    def test_is_linear(self):
        rows = [(f"g{i % 400}", 1) for i in range(40_000)]
        assert timed(lambda: m.group_totals(rows)) < 0.05


class TestInventory:
    def test_add_and_quantity(self):
        inv = m.Inventory()
        inv.add("a", 5)
        inv.add("a", 3)
        assert inv.quantity("a") == 8

    def test_unknown_sku_is_zero(self):
        assert m.Inventory().quantity("nope") == 0

    def test_remove(self):
        inv = m.Inventory()
        inv.add("a", 5)
        inv.remove("a")
        assert inv.quantity("a") == 0

    def test_remove_unknown_raises(self):
        with pytest.raises(KeyError):
            m.Inventory().remove("nope")

    def test_total(self):
        inv = m.Inventory()
        inv.add("a", 5)
        inv.add("b", 3)
        assert inv.total == 8
        inv.remove("a")
        assert inv.total == 3

    def test_total_after_topups(self):
        inv = m.Inventory()
        inv.add("a", 1)
        inv.add("a", 1)
        assert inv.total == 2

    def test_low_stock_sorting(self):
        inv = m.Inventory()
        inv.add("c", 1)
        inv.add("a", 1)
        inv.add("b", 5)
        inv.add("d", 10)
        assert inv.low_stock(6) == ["a", "c", "b"]

    def test_low_stock_empty(self):
        assert m.Inventory().low_stock(5) == []

    def test_total_is_o1(self):
        inv = m.Inventory()
        for i in range(10_000):
            inv.add(f"sku{i}", 1)

        def hammer():
            return sum(inv.total for _ in range(4_000))

        # Recomputing the sum each time is 10k*4k = 40M additions.
        assert timed(hammer) < 0.05
