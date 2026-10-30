"""Module 06 exercises.  pytest 06_iterators_generators

Every function here must be LAZY where laziness is possible — the tests feed several of
them infinite iterators, so materialising the input will hang the suite, not just fail it.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable, Iterator
from typing import Any, TypeVar

T = TypeVar("T")


def sliding_window(iterable: Iterable[T], n: int) -> Iterator[tuple[T, ...]]:
    """Yield overlapping windows of length n as tuples.

    >>> list(sliding_window([1, 2, 3, 4], 2))
    [(1, 2), (2, 3), (3, 4)]

    - Works on ANY iterable, including one-shot generators (so no indexing, no len()).
    - Yields nothing if the input is shorter than n.
    - Raise ValueError if n < 1.
    - Must be lazy: `next(sliding_window(itertools.count(), 3))` has to return.

    `collections.deque(maxlen=n)` does the buffering for you.
    """
    raise NotImplementedError


def interleave(*iterables: Iterable[T]) -> Iterator[T]:
    """Round-robin the inputs, dropping each one as it runs out.

    >>> list(interleave([1, 2, 3], [4, 5], [6]))
    [1, 4, 6, 2, 5, 3]

    - Lazy: interleaving with an infinite iterable must still yield.
    - No inputs -> yields nothing.
    """
    raise NotImplementedError


def running_average() -> Generator[float | None, float, None]:
    """A generator COROUTINE that receives numbers and yields the running mean.

    >>> avg = running_average()
    >>> next(avg)          # prime it — runs to the first yield
    >>> avg.send(10)
    10.0
    >>> avg.send(20)
    15.0

    - The first `next()` yields None (no data yet).
    - Each `send(x)` yields the mean of everything sent so far, as a float.
    - After `.close()`, sending raises StopIteration.
    """
    raise NotImplementedError


def first(
    iterable: Iterable[T],
    predicate: Callable[[T], bool] | None = None,
    default: Any = None,
) -> Any:
    """Return the first item satisfying `predicate` (or just the first item), else `default`.

    >>> first([1, 2, 3, 4], lambda n: n > 2)
    3
    >>> first([], default="empty")
    'empty'

    Must consume no more of the iterable than necessary — the tests pass
    `itertools.count()` and then check that the source is only partly consumed.
    """
    raise NotImplementedError


def unique_everseen(
    iterable: Iterable[T], key: Callable[[T], Any] | None = None
) -> Iterator[T]:
    """Lazily yield items whose key has not been seen before, in original order.

    >>> list(unique_everseen("AAAABBBCCDAABBB"))
    ['A', 'B', 'C', 'D']
    >>> list(unique_everseen(["a", "A", "b"], key=str.lower))
    ['a', 'b']

    Lazy, so it works on an infinite input.
    """
    raise NotImplementedError


def tail(iterable: Iterable[T], n: int) -> list[T]:
    """Return the last n items of any iterable using O(n) memory — not O(len(iterable)).

    >>> tail(range(1000), 3)
    [997, 998, 999]
    >>> tail([1, 2], 5)
    [1, 2]
    >>> tail([1, 2], 0)
    []

    Works on one-shot iterators. Raise ValueError if n < 0.
    """
    raise NotImplementedError
