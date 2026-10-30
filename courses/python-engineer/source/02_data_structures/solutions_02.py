"""Module 02 — reference solutions."""

from __future__ import annotations

import re
from collections import Counter, defaultdict, deque
from collections.abc import Callable, Hashable, Iterable, Mapping
from typing import Any, TypeVar

T = TypeVar("T")
K = TypeVar("K", bound=Hashable)

_WORD = re.compile(r"\w+")


def group_by(items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    groups: defaultdict[K, list[T]] = defaultdict(list)
    for item in items:
        groups[key(item)].append(item)
    return dict(groups)  # return a plain dict so callers don't get surprise auto-vivification


def top_n_words(text: str, n: int) -> list[tuple[str, int]]:
    counts = Counter(_WORD.findall(text.lower()))
    # -count sorts descending, word ascending: deterministic ties.
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:n]


def flatten(nested: Iterable[Any]) -> list[Any]:
    out: list[Any] = []
    for item in nested:
        if isinstance(item, list | tuple):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out


def dedupe(items: Iterable[K]) -> list[K]:
    seen: set[K] = set()
    out: list[K] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    # `deep_merge({}, m)` doubles as "recursively copy m", which is how we guarantee the
    # result never aliases a nested dict of either input.
    merged: dict[str, Any] = {
        k: deep_merge({}, v) if isinstance(v, Mapping) else v for k, v in base.items()
    }
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key] = deep_merge(current, value)
        elif isinstance(value, Mapping):
            merged[key] = deep_merge({}, value)
        else:
            merged[key] = value
    return merged


def sliding_max(nums: list[int], k: int) -> list[int]:
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if k > len(nums):
        return []

    out: list[int] = []
    window: deque[int] = deque()  # indices, values strictly decreasing
    for i, value in enumerate(nums):
        while window and nums[window[-1]] <= value:
            window.pop()
        window.append(i)
        if window[0] <= i - k:  # head slid out of the window
            window.popleft()
        if i >= k - 1:
            out.append(nums[window[0]])
    return out
