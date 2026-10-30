"""Module 02 exercises.  pytest 02_data_structures"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Mapping
from typing import Any, TypeVar

T = TypeVar("T")
K = TypeVar("K", bound=Hashable)


def group_by(items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    """Group items by key(item), preserving both group order and within-group order.

    >>> group_by(["apple", "avocado", "banana"], key=lambda w: w[0])
    {'a': ['apple', 'avocado'], 'b': ['banana']}

    `collections.defaultdict` makes this three lines.
    """
    raise NotImplementedError


def top_n_words(text: str, n: int) -> list[tuple[str, int]]:
    """Return the n most frequent words as (word, count), highest first.

    - Case-insensitive; report words lowercased.
    - A "word" is a maximal run of alphanumeric characters ("don't" -> "don", "t").
    - Ties are broken alphabetically, so the output is fully deterministic.

    >>> top_n_words("the cat the hat", 2)
    [('the', 2), ('cat', 1)]

    Hint: `re.findall(r"\\w+", ...)` plus `collections.Counter`. Note that `Counter.most_common`
    alone does NOT give you the alphabetical tie-break — you need your own sort key.
    """
    raise NotImplementedError


def flatten(nested: Iterable[Any]) -> list[Any]:
    """Recursively flatten arbitrarily nested lists/tuples into a flat list.

    Strings and bytes are ATOMS — never iterate into them (otherwise you recurse forever
    on single characters).

    >>> flatten([1, [2, (3, [4])], 5])
    [1, 2, 3, 4, 5]
    >>> flatten(["ab", ["cd"]])
    ['ab', 'cd']
    """
    raise NotImplementedError


def dedupe(items: Iterable[K]) -> list[K]:
    """Remove duplicates, preserving first-seen order. Items are hashable. O(n).

    >>> dedupe([3, 1, 3, 2, 1])
    [3, 1, 2]
    """
    raise NotImplementedError


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge `override` into `base`, returning a NEW dict.

    - When both sides hold a mapping for a key, merge them recursively.
    - Otherwise the override value wins outright (including when it is None).
    - Neither input may be mutated, and nested dicts of the inputs must not be shared
      in a way that lets a later mutation of the result leak back.

    >>> deep_merge({"db": {"host": "x", "port": 1}}, {"db": {"port": 2}})
    {'db': {'host': 'x', 'port': 2}}
    """
    raise NotImplementedError


def sliding_max(nums: list[int], k: int) -> list[int]:
    """Maximum of every full window of length k, in O(n) total — not O(n*k).

    >>> sliding_max([1, 3, -1, -3, 5, 3, 6, 7], 3)
    [3, 3, 5, 5, 6, 7]

    - Only full windows count, so the result has len(nums) - k + 1 items (or none).
    - Raise ValueError if k < 1.

    The O(n) trick: keep a `collections.deque` of INDICES whose values are strictly
    decreasing. Before appending index i, pop from the right while the tail's value is
    <= nums[i]; pop from the left when the head falls out of the window. The head is
    always the current window's max.
    """
    raise NotImplementedError
