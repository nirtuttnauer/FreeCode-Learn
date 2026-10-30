"""Module 04b — runnable lesson. `python 04b_dunder_methods/lesson_04b.py`"""

from __future__ import annotations

import copy
from typing import Any

INTRO = """Here's the trick behind Python's magic: `len(x)` doesn't know anything about x. It just
asks x, "do you have a `__len__`?" The whole language is a set of questions like that.
Answer them and your object behaves like a built-in type."""


def lookups_go_through_the_type() -> None:
    print("\n== implicit dunder lookup skips the instance ==")

    class Thing:
        pass

    t = Thing()
    t.__len__ = lambda: 42  # instance attribute
    try:
        len(t)
    except TypeError as exc:
        print(f"  len(t) -> TypeError: {exc}")
    print(f"  ...but t.__len__() works: {t.__len__()}")
    print("  reason: len(x) is type(x).__len__(x)")


def construction() -> None:
    print("\n== __new__ vs __init__ ==")

    class UpperStr(str):
        def __new__(cls, value: str) -> UpperStr:
            # str is immutable, so customisation must happen at CREATION time.
            return super().__new__(cls, value.upper())

    print(f"  UpperStr('hi') = {UpperStr('hi')!r}")

    class Singleton:
        _instance = None

        def __new__(cls) -> Singleton:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    print(f"  singleton: {Singleton() is Singleton()}")


def representation() -> None:
    print("\n== repr / str / format ==")

    class Duration:
        def __init__(self, seconds: float) -> None:
            self.seconds = seconds

        def __repr__(self) -> str:
            return f"Duration({self.seconds!r})"

        def __str__(self) -> str:
            return f"{self.seconds:.1f}s"

        def __format__(self, spec: str) -> str:
            if spec == "hms":
                m, s = divmod(int(self.seconds), 60)
                h, m = divmod(m, 60)
                return f"{h:02d}:{m:02d}:{s:02d}"
            return format(self.seconds, spec)  # delegate anything else

    d = Duration(3725.4)
    print(f"  repr: {d!r}")
    print(f"  str:  {d}")
    print(f"  custom spec: {d:hms}")
    print(f"  delegated spec: {d:,.2f}")
    print(f"  containers use repr: {[d]}")


def operators_and_reflection() -> None:
    print("\n== operators, reflected and in-place ==")

    class Meters:
        def __init__(self, value: float) -> None:
            self.value = value

        def __repr__(self) -> str:
            return f"Meters({self.value})"

        def __add__(self, other: Any) -> Any:
            print("    __add__ called")
            if isinstance(other, Meters):
                return Meters(self.value + other.value)
            return NotImplemented  # signal, don't raise

        def __mul__(self, k: Any) -> Any:
            return Meters(self.value * k) if isinstance(k, int | float) else NotImplemented

        def __rmul__(self, k: Any) -> Any:
            print("    __rmul__ called (left operand didn't know how)")
            return self.__mul__(k)

    print(f"  {Meters(1) + Meters(2)}")
    print(f"  {3 * Meters(2)}")
    try:
        Meters(1) + 5
    except TypeError as exc:
        print(f"  NotImplemented becomes a clean TypeError: {exc}")

    class Bag:
        def __init__(self, items: list[int]) -> None:
            self.items = items

        def __iadd__(self, other: list[int]) -> Bag:
            self.items.extend(other)  # mutate in place...
            return self  # ...and return self

        def __repr__(self) -> str:
            return f"Bag({self.items})"

    b = Bag([1])
    original = b
    b += [2, 3]
    print(f"  += mutated in place, same object: {b} {b is original}")


def attribute_protocol() -> None:
    print("\n== __getattr__ / __setattr__ / __dir__ ==")

    class Box:
        def __init__(self, data: dict[str, Any]) -> None:
            object.__setattr__(self, "_data", data)  # bypass our own __setattr__

        def __getattr__(self, name: str) -> Any:  # only for FAILED normal lookups
            print(f"    __getattr__({name!r})")
            try:
                return self._data[name]
            except KeyError:
                raise AttributeError(name) from None  # must be AttributeError

        def __setattr__(self, name: str, value: Any) -> None:
            raise AttributeError("Box is immutable")

        def __dir__(self):
            return sorted(set(super().__dir__()) | set(self._data))

    box = Box({"host": "localhost", "port": 8080})
    print(f"  box.host = {box.host}")
    print(f"  _data found normally, so no __getattr__ call: {box._data.keys()}")
    print(f"  hasattr(box, 'nope') = {hasattr(box, 'nope')}   (relies on AttributeError)")
    print(f"  dir() shows the keys: {[n for n in dir(box) if not n.startswith('_')]}")
    try:
        box.host = "other"
    except AttributeError as exc:
        print(f"  immutable: {exc}")


def container_protocol() -> None:
    print("\n== containers, slicing, __missing__ ==")

    class Grid:
        def __init__(self, rows: list[list[int]]) -> None:
            self.rows = rows

        def __len__(self) -> int:
            return len(self.rows)

        def __getitem__(self, index: int | slice) -> Any:
            if isinstance(index, slice):  # slicing gives you a slice OBJECT
                return Grid(self.rows[index])
            return self.rows[index]

        def __contains__(self, value: int) -> bool:
            return any(value in row for row in self.rows)

        def __repr__(self) -> str:
            return f"Grid({self.rows})"

    g = Grid([[1, 2], [3, 4], [5, 6]])
    print(f"  len={len(g)}  g[1]={g[1]}  g[:2]={g[:2]}  4 in g -> {4 in g}")

    class Defaults(dict):
        def __missing__(self, key):  # dict subclasses only
            print(f"    __missing__({key!r})")
            value = self[key] = f"<{key}>"
            return value

    d = Defaults(a=1)
    print(f"  d['a']={d['a']}  d['zz']={d['zz']}  now stored: {dict(d)}")
    print(f"  .get() does NOT trigger __missing__: {d.get('other')}")


def callable_and_copy() -> None:
    print("\n== __call__ and copy hooks ==")

    class Multiplier:
        def __init__(self, factor: int) -> None:
            self.factor = factor
            self.calls = 0

        def __call__(self, value: int) -> int:
            self.calls += 1
            return value * self.factor

    triple = Multiplier(3)
    print(f"  {triple(5)=} {triple(6)=} {triple.calls=}  (a function with memory)")
    print(f"  {callable(triple)=}")

    class Session:
        def __init__(self) -> None:
            self.token = "secret"
            self.connection = "<open socket>"

        def __getstate__(self):  # what gets pickled/deep-copied
            state = self.__dict__.copy()
            del state["connection"]  # never copy a live handle
            return state

        def __setstate__(self, state):
            self.__dict__.update(state)
            self.connection = "<reconnected>"

    s = copy.deepcopy(Session())
    print(f"  after deepcopy: token={s.token!r} connection={s.connection!r}")


if __name__ == "__main__":
    print(INTRO)
    lookups_go_through_the_type()
    construction()
    representation()
    operators_and_reflection()
    attribute_protocol()
    container_protocol()
    callable_and_copy()
