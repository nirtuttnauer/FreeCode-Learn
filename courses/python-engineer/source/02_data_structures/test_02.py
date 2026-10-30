import random

import pytest

from courselib import impl

m = impl("02")


class TestGroupBy:
    def test_basic(self):
        got = m.group_by(["apple", "avocado", "banana"], key=lambda w: w[0])
        assert got == {"a": ["apple", "avocado"], "b": ["banana"]}

    def test_preserves_order(self):
        got = m.group_by([5, 1, 6, 2], key=lambda n: n % 2)
        assert list(got) == [1, 0]  # first key seen is 5 -> 1
        assert got[1] == [5, 1]

    def test_empty(self):
        assert m.group_by([], key=len) == {}

    def test_accepts_any_iterable(self):
        assert m.group_by(range(4), key=lambda n: n % 2) == {0: [0, 2], 1: [1, 3]}

    def test_returns_plain_dict_not_defaultdict(self):
        got = m.group_by([1], key=bool)
        with pytest.raises(KeyError):
            got["missing"]


class TestTopNWords:
    def test_basic(self):
        assert m.top_n_words("the cat the hat", 2) == [("the", 2), ("cat", 1)]

    def test_case_insensitive(self):
        assert m.top_n_words("The THE the", 1) == [("the", 3)]

    def test_punctuation_splits_words(self):
        assert dict(m.top_n_words("don't stop", 5)) == {"don": 1, "t": 1, "stop": 1}

    def test_ties_broken_alphabetically(self):
        assert m.top_n_words("b a c", 3) == [("a", 1), ("b", 1), ("c", 1)]

    def test_n_larger_than_vocabulary(self):
        assert len(m.top_n_words("a b", 10)) == 2

    def test_empty_text(self):
        assert m.top_n_words("", 3) == []


class TestFlatten:
    def test_nested(self):
        assert m.flatten([1, [2, (3, [4])], 5]) == [1, 2, 3, 4, 5]

    def test_strings_are_atoms(self):
        assert m.flatten(["ab", ["cd", ["e"]]]) == ["ab", "cd", "e"]

    def test_already_flat(self):
        assert m.flatten([1, 2, 3]) == [1, 2, 3]

    def test_empty_and_empty_nests(self):
        assert m.flatten([]) == []
        assert m.flatten([[], [[]], ()]) == []

    def test_deep_nesting(self):
        deep = [1]
        for _ in range(50):
            deep = [deep]
        assert m.flatten(deep) == [1]


class TestDedupe:
    def test_preserves_first_seen_order(self):
        assert m.dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]

    def test_strings(self):
        assert m.dedupe("abracadabra") == list("abrcd")

    def test_empty(self):
        assert m.dedupe([]) == []

    def test_is_linear_not_quadratic(self):
        # 200k items would take minutes with an `if x in out` list scan.
        data = list(range(200_000)) * 2
        assert len(m.dedupe(data)) == 200_000


class TestDeepMerge:
    def test_nested_merge(self):
        assert m.deep_merge({"db": {"host": "x", "port": 1}}, {"db": {"port": 2}}) == {
            "db": {"host": "x", "port": 2}
        }

    def test_scalar_override_wins(self):
        assert m.deep_merge({"a": {"b": 1}}, {"a": 5}) == {"a": 5}

    def test_none_overrides(self):
        assert m.deep_merge({"a": 1}, {"a": None}) == {"a": None}

    def test_new_keys_added(self):
        assert m.deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_inputs_not_mutated(self):
        base = {"db": {"host": "x"}}
        override = {"db": {"port": 2}}
        m.deep_merge(base, override)
        assert base == {"db": {"host": "x"}}
        assert override == {"db": {"port": 2}}

    def test_result_does_not_alias_inputs(self):
        base = {"db": {"host": "x"}}
        result = m.deep_merge(base, {})
        result["db"]["host"] = "CHANGED"
        assert base["db"]["host"] == "x"

    def test_three_levels(self):
        a = {"a": {"b": {"c": 1, "d": 2}}}
        b = {"a": {"b": {"c": 9}}}
        assert m.deep_merge(a, b) == {"a": {"b": {"c": 9, "d": 2}}}


class TestSlidingMax:
    def test_classic(self):
        assert m.sliding_max([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]

    def test_k_of_one_is_identity(self):
        assert m.sliding_max([4, 2, 9], 1) == [4, 2, 9]

    def test_k_equals_length(self):
        assert m.sliding_max([4, 2, 9], 3) == [9]

    def test_k_larger_than_input(self):
        assert m.sliding_max([1, 2], 5) == []

    def test_empty(self):
        assert m.sliding_max([], 3) == []

    def test_duplicates(self):
        assert m.sliding_max([2, 2, 2, 2], 2) == [2, 2, 2]

    def test_rejects_bad_k(self):
        with pytest.raises(ValueError):
            m.sliding_max([1, 2, 3], 0)

    def test_matches_bruteforce_on_random_input(self):
        rng = random.Random(1234)
        for _ in range(30):
            nums = [rng.randint(-50, 50) for _ in range(rng.randint(1, 40))]
            k = rng.randint(1, len(nums))
            expected = [max(nums[i : i + k]) for i in range(len(nums) - k + 1)]
            assert m.sliding_max(nums, k) == expected

    def test_is_linear(self):
        # 10^5 items with k=10^4: O(n*k) would be a billion comparisons.
        nums = list(range(100_000))
        assert m.sliding_max(nums, 10_000)[0] == 9_999
