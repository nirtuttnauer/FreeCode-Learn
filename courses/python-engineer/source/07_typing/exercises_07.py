"""Module 07 exercises.  pytest 07_typing  AND  make typecheck

This module is graded twice: the tests check runtime behaviour, mypy checks your
annotations. Fully annotate everything you write here — `disallow_untyped_defs` is on
for this file in pyproject.toml.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, ParamSpec, Protocol, TypedDict, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class Stack[T]:
    """A generic LIFO stack, using the 3.12 type-parameter syntax.

    - `push(item) -> Self` so calls chain: `Stack[int]().push(1).push(2)`.
    - `pop() -> T` raises IndexError("pop from empty stack") when empty.
    - `peek() -> T` returns the top without removing it; same error when empty.
    - `__len__`, `__bool__` (free via `__len__`), `__iter__` top-to-bottom,
      `__repr__` == "Stack([1, 2])" (bottom-to-top, like the underlying list).
    - `.clear()` empties it.

    mypy must be able to prove that `Stack[int]().pop()` is an `int`.
    """

    def __init__(self) -> None:
        raise NotImplementedError


class SupportsClose(Protocol):
    """Structural interface: anything with a no-argument `close()` satisfies it.

    Leave the body as `...` — a Protocol declares shape, it doesn't implement it.
    Mark it `@runtime_checkable` so the tests can use `isinstance`.
    """

    def close(self) -> None: ...


def close_all(items: Iterable[SupportsClose]) -> list[BaseException]:
    """Close every item, and keep going even if some raise.

    Returns the list of exceptions raised, in order. An empty list means all clean.
    Every item must get its `close()` called, regardless of earlier failures — that's
    the whole point of a cleanup routine.
    """
    raise NotImplementedError


class UserRecord(TypedDict):
    """The shape of a validated user."""

    id: int
    name: str
    email: str


def parse_user(raw: dict[str, Any]) -> UserRecord:
    """Validate an untrusted dict into a UserRecord.

    - "id" must be present and int-convertible (a bool is NOT acceptable) -> else ValueError
    - "name" must be a non-empty string after stripping                  -> else ValueError
    - "email" must be a string containing "@"                            -> else ValueError
    - Extra keys are dropped.
    - The returned "name" is stripped.
    - Error messages must name the offending field, e.g. "invalid email".

    This is the hand-rolled version of what pydantic does for you in module 15 —
    do it once by hand so you know what the library is buying you.
    """
    raise NotImplementedError


def counted(func: Callable[P, R]) -> Callable[P, R]:
    """A decorator that counts calls WITHOUT destroying the wrapped signature.

    - `func.calls` starts at 0 and increments on every call.
    - `func.reset()` sets it back to 0.
    - Uses `ParamSpec` so mypy still checks arguments at every call site
      (a plain `Callable[..., Any]` would silently disable that).
    - Preserves metadata with `functools.wraps`.
    - Exceptions still propagate — and still count as a call.
    """
    raise NotImplementedError


class Result[T, E]:
    """A tiny Rust-style Result: either a value or an error, never both.

    Build it as TWO generic dataclasses plus a type alias:

        @dataclass(frozen=True)
        class Ok[T]: value: T
        @dataclass(frozen=True)
        class Err[E]: error: E
        type Result[T, E] = Ok[T] | Err[E]

    Then implement the free functions below. Replace this placeholder class entirely —
    the tests import `Ok`, `Err`, `is_ok`, `unwrap_or` and `map_ok` by name.
    """


def is_ok(result: Any) -> bool:
    """True for an Ok, False for an Err. Use `isinstance` — or `match`, which is nicer."""
    raise NotImplementedError


def unwrap_or(result: Any, default: Any) -> Any:
    """The value for Ok, `default` for Err."""
    raise NotImplementedError


def map_ok(result: Any, func: Callable[[Any], Any]) -> Any:
    """Apply `func` to an Ok's value, returning a new Ok. Pass an Err through untouched.

    If `func` raises, return `Err(exception)` — mapping must never blow up the pipeline.
    """
    raise NotImplementedError
