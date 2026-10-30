"""Module 07 — runnable lesson. `python 07_typing/lesson_07.py`

Types are checked by mypy, not by the interpreter — so this file both RUNS and is meant to
be read with `mypy 07_typing/lesson_07.py` in the other window.
"""

from __future__ import annotations

import dataclasses
import functools
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import (
    Annotated,
    Any,
    ClassVar,
    Final,
    Literal,
    ParamSpec,
    Protocol,
    Self,
    TypedDict,
    TypeVar,
    cast,
    overload,
    runtime_checkable,
)

INTRO = """Type hints are notes saying what you actually meant. Python ignores them completely at
runtime — but mypy reads them and tells you "line 84 will break" BEFORE you run anything.
A spell-checker for your code's plumbing."""

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")

MAX_RETRIES: Final = 3
Mode = Literal["read", "write", "append"]
type Json = str | int | float | bool | None | list["Json"] | dict[str, "Json"]  # 3.12 alias


def annotations_are_not_enforced() -> None:
    print("\n== hints are documentation the machine can check ==")

    def add(a: int, b: int) -> int:
        return a + b

    print(f"  add('x', 'y') = {add('x', 'y')!r}   <- runs fine; mypy flags it")  # type: ignore[arg-type]
    print(f"  annotations live here: {add.__annotations__}")


def generics() -> None:
    print("\n== generics ==")

    class Stack[Item]:  # 3.12 syntax — no TypeVar declaration needed
        def __init__(self) -> None:
            self._items: list[Item] = []

        def push(self, item: Item) -> Self:  # Self keeps fluent chaining typed
            self._items.append(item)
            return self

        def pop(self) -> Item:
            return self._items.pop()

        def __len__(self) -> int:
            return len(self._items)

    numbers = Stack[int]().push(1).push(2)
    print(f"  Stack[int]: len={len(numbers)} pop={numbers.pop()}")

    def first[X](items: Sequence[X]) -> X:
        return items[0]

    print(f"  first([1,2]) is an int: {first([1, 2])}; first('ab') is a str: {first('ab')}")

    # Variance: accept the widest thing that works.
    def total(values: Iterable[float]) -> float:  # Iterable, not list
        return sum(values)

    print(f"  works on list/tuple/set/genexp: {total({1, 2})} {total(n for n in [1, 2])}")


def protocols() -> None:
    print("\n== structural typing with Protocol ==")

    @runtime_checkable
    class SupportsClose(Protocol):
        def close(self) -> None: ...

    class Socket:
        def close(self) -> None:
            print("    socket closed")

    class Cursor:  # unrelated class, no shared base
        def close(self) -> None:
            print("    cursor closed")

    def cleanup(items: Iterable[SupportsClose]) -> None:
        for item in items:
            item.close()

    cleanup([Socket(), Cursor()])
    print(f"  runtime_checkable isinstance: {isinstance(Socket(), SupportsClose)}")
    print("  note: isinstance only checks method NAMES, not signatures")


class UserRecord(TypedDict):
    id: int
    name: str
    email: str


class PartialUser(TypedDict, total=False):
    id: int
    name: str


def typed_dicts_and_literals() -> None:
    print("\n== TypedDict / Literal / Annotated ==")
    user: UserRecord = {"id": 1, "name": "ada", "email": "a@b.c"}
    print(f"  it IS a plain dict at runtime: {type(user).__name__} {user}")

    def open_file(path: str, mode: Mode = "read") -> str:
        return f"{path}:{mode}"

    print(f"  Literal restricts values: {open_file('/tmp/x', 'write')}")
    Age = Annotated[int, "must be >= 0"]  # metadata riders — pydantic/FastAPI read these
    print(f"  Annotated carries metadata: {Age}")


def paramspec_decorator() -> None:
    print("\n== ParamSpec keeps decorated signatures ==")

    def counted(func: Callable[P, R]) -> Callable[P, R]:
        calls = 0

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal calls
            calls += 1
            print(f"    call #{calls} to {func.__name__}")
            return func(*args, **kwargs)

        return wrapper

    @counted
    def greet(name: str, punct: str = "!") -> str:
        return f"hi {name}{punct}"

    greet("ada")
    greet("bob", punct="?")
    print("  mypy still knows greet takes (name: str, punct: str) -> str")


@overload
def parse(value: str) -> str: ...
@overload
def parse(value: int) -> int: ...
def parse(value: str | int) -> str | int:
    """One implementation, several precise signatures for the checker."""
    return value * 2


def narrowing() -> None:
    print("\n== narrowing ==")
    values: list[Any] = [1, "two", None, 3.0]
    for v in values:
        if isinstance(v, str):
            print(f"  str branch: {v.upper()}")  # mypy knows v is str here
        elif v is None:
            print("  None branch")
        else:
            print(f"  number branch: {v + 1}")

    print(f"  overloads: parse('a')={parse('a')!r} parse(2)={parse(2)!r}")

    raw: Any = {"id": 1, "name": "ada", "email": "e"}
    user = cast(UserRecord, raw)  # zero runtime cost — a promise to the checker
    print(f"  cast() is a no-op at runtime: {user['name']}")


@dataclass
class Config:
    ENV: ClassVar[str] = "prod"  # not an __init__ field
    host: str
    port: int = 8080


def class_level_hints() -> None:
    print("\n== ClassVar / Final ==")
    c = Config(host="localhost")
    # dataclasses.fields() excludes ClassVar; __dataclass_fields__ still lists it as a
    # pseudo-field, which is a classic source of confusion.
    print(f"  {c=}  real fields: {[f.name for f in dataclasses.fields(c)]}")
    print(f"  Final constant: MAX_RETRIES={MAX_RETRIES}")


if __name__ == "__main__":
    print(INTRO)
    annotations_are_not_enforced()
    generics()
    protocols()
    typed_dicts_and_literals()
    paramspec_decorator()
    narrowing()
    class_level_hints()
