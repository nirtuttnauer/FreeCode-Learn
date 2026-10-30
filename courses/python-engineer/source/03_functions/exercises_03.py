"""Module 03 exercises.  pytest 03_functions"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


def compose(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose single-argument functions RIGHT TO LEFT, like maths.

    >>> compose(str, lambda n: n + 1)(41)   # str(41 + 1)
    '42'
    >>> compose()(7)                        # no functions == identity
    7
    """
    raise NotImplementedError


def memoize(func: Callable[..., Any]) -> Callable[..., Any]:
    """A hand-rolled `functools.cache`. Write it once so you know what's inside.

    Requirements:
    - Caches on both positional AND keyword arguments; f(1, b=2) and f(1, 2) may be
      treated as different keys (that's what the stdlib does too).
    - Exposes `.cache` — the underlying dict — and `.cache_clear()`.
    - Preserves `__name__`, `__doc__` and `__wrapped__` (use `functools.wraps`).

    Hint for the key: kwargs is a dict (unhashable). `tuple(sorted(kwargs.items()))` makes
    it hashable and order-insensitive.
    """
    raise NotImplementedError


def make_accumulator(start: int = 0) -> Callable[[int], int]:
    """Return a function that accumulates a running total and returns it.

    >>> acc = make_accumulator(10)
    >>> acc(5), acc(5)
    (15, 20)

    Two independent accumulators must not share state. The returned function also gets a
    `.reset()` attribute that puts the total back to `start` (functions are objects — you
    can just assign attributes to them).
    """
    raise NotImplementedError


def append_to(item: Any, target: list[Any] | None = None) -> list[Any]:
    """Append `item` to `target`, creating a NEW list when target is omitted.

    The whole point: two calls with no target must not share a list.

    >>> append_to(1), append_to(2)
    ([1], [2])
    """
    raise NotImplementedError


def retry(
    times: int,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    delay: float = 0.0,
    sleeper: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator FACTORY: retry the wrapped call up to `times` attempts total.

    - Only exceptions in `exceptions` trigger a retry; anything else propagates at once.
    - `sleeper(delay)` is called after each failed attempt EXCEPT the last one
      (that injectable sleeper is what makes this testable without real waiting —
      a pattern you'll formalise in module 09).
    - When every attempt fails, re-raise the last exception.
    - Raise ValueError at decoration time if times < 1.
    - Preserve the wrapped function's metadata.
    """
    raise NotImplementedError


def curry(func: Callable[..., Any]) -> Callable[..., Any]:
    """Return a curried version of a fixed-arity positional function.

    >>> add3 = curry(lambda a, b, c: a + b + c)
    >>> add3(1)(2)(3), add3(1, 2)(3), add3(1, 2, 3)
    (6, 6, 6)

    A partially applied result is reusable and must NOT accumulate state across uses:

    >>> f = add3(1)
    >>> f(2)(3), f(10)(10)
    (6, 21)

    Hint: get the arity with `len(inspect.signature(func).parameters)` and recurse with
    `functools.partial`.
    """
    raise NotImplementedError
