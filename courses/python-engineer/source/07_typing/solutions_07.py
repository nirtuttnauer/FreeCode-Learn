"""Module 07 — reference solutions."""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any, ParamSpec, Protocol, Self, TypedDict, TypeVar, runtime_checkable

P = ParamSpec("P")
R = TypeVar("R")


class Stack[T]:
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> Self:
        self._items.append(item)
        return self

    def pop(self) -> T:
        if not self._items:
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self) -> T:
        if not self._items:
            raise IndexError("peek from empty stack")
        return self._items[-1]

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(reversed(self._items))  # top first

    def __repr__(self) -> str:
        return f"Stack({self._items!r})"


@runtime_checkable
class SupportsClose(Protocol):
    def close(self) -> None: ...


def close_all(items: Iterable[SupportsClose]) -> list[BaseException]:
    errors: list[BaseException] = []
    for item in items:
        try:
            item.close()
        except Exception as exc:  # noqa: BLE001 — cleanup must not stop at the first failure
            errors.append(exc)
    return errors


class UserRecord(TypedDict):
    id: int
    name: str
    email: str


def parse_user(raw: dict[str, Any]) -> UserRecord:
    raw_id = raw.get("id")
    if isinstance(raw_id, bool) or not isinstance(raw_id, int | str | float):
        raise ValueError("invalid id")
    try:
        user_id = int(raw_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid id") from exc

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("invalid name")

    email = raw.get("email")
    if not isinstance(email, str) or "@" not in email:
        raise ValueError("invalid email")

    return {"id": user_id, "name": name.strip(), "email": email}


def counted(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        wrapper.calls += 1  # type: ignore[attr-defined]
        return func(*args, **kwargs)

    def reset() -> None:
        wrapper.calls = 0  # type: ignore[attr-defined]

    wrapper.calls = 0  # type: ignore[attr-defined]
    wrapper.reset = reset  # type: ignore[attr-defined]
    return wrapper


@dataclass(frozen=True)
class Ok[T]:
    value: T


@dataclass(frozen=True)
class Err[E]:
    error: E


type Result[T, E] = Ok[T] | Err[E]


def is_ok(result: Any) -> bool:
    match result:
        case Ok():
            return True
        case _:
            return False


def unwrap_or(result: Any, default: Any) -> Any:
    match result:
        case Ok(value=value):
            return value
        case _:
            return default


def map_ok(result: Any, func: Callable[[Any], Any]) -> Any:
    match result:
        case Ok(value=value):
            try:
                return Ok(func(value))
            except Exception as exc:  # noqa: BLE001 — errors become part of the value
                return Err(exc)
        case _:
            return result
