"""Module 03 — reference solutions."""

from __future__ import annotations

import functools
import inspect
import time
from collections.abc import Callable
from typing import Any


def compose(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    def composed(value: Any) -> Any:
        for func in reversed(funcs):  # right-to-left
            value = func(value)
        return value

    return composed


def memoize(func: Callable[..., Any]) -> Callable[..., Any]:
    cache: dict[tuple[Any, ...], Any] = {}

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = (args, tuple(sorted(kwargs.items())))
        if key not in cache:  # not `cache.get(key)` — a cached None must still be a hit
            cache[key] = func(*args, **kwargs)
        return cache[key]

    wrapper.cache = cache  # type: ignore[attr-defined]
    wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
    return wrapper


def make_accumulator(start: int = 0) -> Callable[[int], int]:
    total = start

    def add(amount: int) -> int:
        nonlocal total
        total += amount
        return total

    def reset() -> None:
        nonlocal total
        total = start

    add.reset = reset  # type: ignore[attr-defined]
    return add


def append_to(item: Any, target: list[Any] | None = None) -> list[Any]:
    if target is None:
        target = []
    target.append(item)
    return target


def retry(
    times: int,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    delay: float = 0.0,
    sleeper: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    if times < 1:
        raise ValueError(f"times must be >= 1, got {times}")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == times:
                        raise  # bare raise keeps the original traceback
                    sleeper(delay)
            raise AssertionError("unreachable")

        return wrapper

    return decorator


def curry(func: Callable[..., Any]) -> Callable[..., Any]:
    arity = len(inspect.signature(func).parameters)

    def collect(*collected: Any) -> Any:
        if len(collected) >= arity:
            return func(*collected)
        # partial() makes a fresh callable each time, so branches never share state.
        return functools.partial(collect, *collected)

    return collect
