import itertools

import pytest

from courselib import impl

m = impl("06")


def counter(limit=None):
    """A one-shot generator that records how far it was consumed."""
    n = 0
    while limit is None or n < limit:
        yield n
        n += 1


class TestSlidingWindow:
    def test_basic(self):
        assert list(m.sliding_window([1, 2, 3, 4], 2)) == [(1, 2), (2, 3), (3, 4)]

    def test_window_of_one(self):
        assert list(m.sliding_window([1, 2], 1)) == [(1,), (2,)]

    def test_exact_length(self):
        assert list(m.sliding_window([1, 2, 3], 3)) == [(1, 2, 3)]

    def test_input_shorter_than_window(self):
        assert list(m.sliding_window([1, 2], 3)) == []

    def test_empty_input(self):
        assert list(m.sliding_window([], 2)) == []

    def test_works_on_one_shot_iterators(self):
        assert list(m.sliding_window(iter([1, 2, 3]), 2)) == [(1, 2), (2, 3)]

    def test_is_lazy(self):
        windows = m.sliding_window(itertools.count(), 3)
        assert next(windows) == (0, 1, 2)
        assert next(windows) == (1, 2, 3)

    def test_yields_tuples_not_shared_buffers(self):
        got = list(m.sliding_window([1, 2, 3], 2))
        assert all(isinstance(w, tuple) for w in got)
        assert got[0] != got[1]

    def test_rejects_bad_n(self):
        with pytest.raises(ValueError):
            list(m.sliding_window([1, 2], 0))


class TestInterleave:
    def test_ragged(self):
        assert list(m.interleave([1, 2, 3], [4, 5], [6])) == [1, 4, 6, 2, 5, 3]

    def test_equal_lengths(self):
        assert list(m.interleave("ab", "cd")) == ["a", "c", "b", "d"]

    def test_single_iterable(self):
        assert list(m.interleave([1, 2])) == [1, 2]

    def test_no_iterables(self):
        assert list(m.interleave()) == []

    def test_empty_iterables_are_skipped(self):
        assert list(m.interleave([], [1], [])) == [1]

    def test_is_lazy_with_infinite_input(self):
        mixed = m.interleave(itertools.count(), ["a"])
        assert list(itertools.islice(mixed, 4)) == [0, "a", 1, 2]


class TestRunningAverage:
    def test_priming_yields_none(self):
        avg = m.running_average()
        assert next(avg) is None

    def test_running_mean(self):
        avg = m.running_average()
        next(avg)
        assert avg.send(10) == 10.0
        assert avg.send(20) == 15.0
        assert avg.send(30) == 20.0

    def test_returns_floats(self):
        avg = m.running_average()
        next(avg)
        assert isinstance(avg.send(1), float)

    def test_independent_instances(self):
        a, b = m.running_average(), m.running_average()
        next(a)
        next(b)
        a.send(100)
        assert b.send(2) == 2.0

    def test_send_before_priming_is_a_type_error(self):
        with pytest.raises(TypeError):
            m.running_average().send(1)

    def test_after_close(self):
        avg = m.running_average()
        next(avg)
        avg.send(1)
        avg.close()
        with pytest.raises(StopIteration):
            avg.send(2)


class TestFirst:
    def test_first_matching(self):
        assert m.first([1, 2, 3, 4], lambda n: n > 2) == 3

    def test_no_predicate_returns_first_item(self):
        assert m.first([9, 8]) == 9

    def test_default_when_empty(self):
        assert m.first([], default="empty") == "empty"

    def test_default_when_nothing_matches(self):
        assert m.first([1, 2], lambda n: n > 10, default=-1) == -1

    def test_default_is_none_by_default(self):
        assert m.first([]) is None

    def test_stops_early_on_infinite_input(self):
        assert m.first(itertools.count(), lambda n: n > 5) == 6

    def test_consumes_only_what_it_needs(self):
        source = counter()
        assert m.first(source, lambda n: n == 2) == 2
        assert next(source) == 3  # only 0,1,2 were consumed

    def test_falsy_first_item_is_returned(self):
        assert m.first([0, 1], default="wrong") == 0


class TestUniqueEverseen:
    def test_basic(self):
        assert list(m.unique_everseen("AAAABBBCCDAABBB")) == ["A", "B", "C", "D"]

    def test_with_key(self):
        assert list(m.unique_everseen(["a", "A", "b"], key=str.lower)) == ["a", "b"]

    def test_preserves_order(self):
        assert list(m.unique_everseen([3, 1, 3, 2, 1])) == [3, 1, 2]

    def test_empty(self):
        assert list(m.unique_everseen([])) == []

    def test_is_lazy(self):
        uniq = m.unique_everseen(itertools.cycle([1, 2, 3]))
        assert [next(uniq) for _ in range(3)] == [1, 2, 3]

    def test_works_on_generators(self):
        assert list(m.unique_everseen(n % 3 for n in range(10))) == [0, 1, 2]


class TestTail:
    def test_basic(self):
        assert m.tail(range(1000), 3) == [997, 998, 999]

    def test_shorter_than_n(self):
        assert m.tail([1, 2], 5) == [1, 2]

    def test_zero(self):
        assert m.tail([1, 2], 0) == []

    def test_empty_input(self):
        assert m.tail([], 3) == []

    def test_works_on_one_shot_generators(self):
        assert m.tail(counter(10), 2) == [8, 9]

    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            m.tail([1], -1)

    def test_bounded_memory(self):
        # If this materialised the input it would allocate ~2M ints.
        assert m.tail(iter(range(2_000_000)), 2) == [1_999_998, 1_999_999]
