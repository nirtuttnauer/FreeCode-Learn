"""Module 06 — reference solutions."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Generator, Iterable, Iterator
from typing import Any, TypeVar

T = TypeVar("T")


def sliding_window(iterable: Iterable[T], n: int) -> Iterator[tuple[T, ...]]:
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    window: deque[T] = deque(maxlen=n)
    for item in iterable:
        window.append(item)
        if len(window) == n:
            yield tuple(window)  # copy — the deque keeps mutating


def interleave(*iterables: Iterable[T]) -> Iterator[T]:
    iterators = [iter(it) for it in iterables]
    while iterators:
        alive = []
        for iterator in iterators:
            try:
                yield next(iterator)
            except StopIteration:
                continue  # drop it from the next round
            alive.append(iterator)
        iterators = alive


def running_average() -> Generator[float | None, float, None]:
    total = 0.0
    count = 0
    average: float | None = None
    while True:
        value = yield average  # yields, then receives what send() passes in
        total += value
        count += 1
        average = total / count


def first(
    iterable: Iterable[T],
    predicate: Callable[[T], bool] | None = None,
    default: Any = None,
) -> Any:
    iterator = iter(iterable)
    if predicate is None:
        return next(iterator, default)
    # A genexp keeps this lazy: next() stops at the first match.
    return next((item for item in iterator if predicate(item)), default)


def unique_everseen(
    iterable: Iterable[T], key: Callable[[T], Any] | None = None
) -> Iterator[T]:
    seen: set[Any] = set()
    for item in iterable:
        marker = item if key is None else key(item)
        if marker not in seen:
            seen.add(marker)
            yield item


def tail(iterable: Iterable[T], n: int) -> list[T]:
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if n == 0:
        return []
    return list(deque(iterable, maxlen=n))  # the deque discards everything older
