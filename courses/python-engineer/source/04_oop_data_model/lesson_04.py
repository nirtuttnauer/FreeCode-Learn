"""Module 04 — runnable lesson. `python 04_oop_data_model/lesson_04.py`"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import ClassVar

INTRO = """Python objects can plug into the language itself. Write a method called `__len__` and
suddenly `len(your_object)` works. You're not overriding a framework — you're teaching
Python what your object means."""


def dunder_protocols() -> None:
    print("\n== implement protocols, get syntax for free ==")

    class Vector:
        def __init__(self, *components: float) -> None:
            self.components = tuple(components)

        def __repr__(self) -> str:  # unambiguous, ideally eval-able
            return f"Vector{self.components}"

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Vector):
                return NotImplemented  # let the other operand try
            return self.components == other.components

        def __hash__(self) -> int:
            return hash(self.components)

        def __add__(self, other: Vector) -> Vector:
            return Vector(*(a + b for a, b in zip(self.components, other.components, strict=True)))

        def __mul__(self, scalar: float) -> Vector:
            return Vector(*(a * scalar for a in self.components))

        __rmul__ = __mul__  # makes `2 * v` work

        def __abs__(self) -> float:
            return sum(a * a for a in self.components) ** 0.5

        def __len__(self) -> int:
            return len(self.components)

        def __getitem__(self, index: int) -> float:
            return self.components[index]

        def __iter__(self):
            return iter(self.components)

        def __format__(self, spec: str) -> str:
            if not spec:
                return repr(self)
            return "(" + ", ".join(format(c, spec) for c in self.components) + ")"

    v, w = Vector(3, 4), Vector(1, 1)
    print(f"  {v=}  {v + w=}  {2 * v=}  {abs(v)=}")
    print(f"  len={len(v)} v[0]={v[0]} unpack={list(v)}  x, y = v -> {tuple(v)}")
    print(f"  __format__: {v:.2f}")
    print(f"  hashable, so usable in a set: {len({v, Vector(3, 4)})=}")


def eq_and_hash() -> None:
    print("\n== __eq__ removes __hash__ ==")

    class Mutable:
        def __init__(self, n: int) -> None:
            self.n = n

        def __eq__(self, other: object) -> bool:
            return isinstance(other, Mutable) and self.n == other.n

    try:
        {Mutable(1)}
    except TypeError as exc:
        print(f"  {exc}  <- correct! a mutable value object should not be hashable")

    print("  if you DO add __hash__, hash only immutable parts, or sets silently break")


def dataclasses_tour() -> None:
    print("\n== dataclasses ==")

    @dataclass(frozen=True, slots=True, order=True)
    class Money:
        amount: int
        currency: str = "USD"

        def __post_init__(self) -> None:
            if self.amount < 0:
                raise ValueError(f"negative amount: {self.amount}")

    m = Money(100)
    print(f"  free __repr__/__eq__: {m=}  {m == Money(100)=}")
    print(f"  order=True gives sorting: {sorted([Money(5), Money(1)])}")
    print(f"  frozen => hashable: {hash(m) == hash(Money(100))}")
    try:
        m.amount = 5  # type: ignore[misc]
    except Exception as exc:
        print(f"  frozen assignment: {type(exc).__name__}: {exc}")
    try:
        Money(-1)
    except ValueError as exc:
        print(f"  __post_init__ validation: {exc}")

    @dataclass
    class Config:
        name: str
        tags: list[str] = field(default_factory=list)  # a bare [] is a ValueError here
        secret: str = field(default="", repr=False, compare=False)

    c = Config("svc", secret="hunter2")
    print(f"  field() options: {c}  (secret hidden from repr)")

    # slots=True removes __dict__: less memory, no ad-hoc attributes.
    print(f"  Money has __dict__? {hasattr(m, '__dict__')}")
    print(f"  size with slots: {sys.getsizeof(m)} bytes")


def properties() -> None:
    print("\n== properties ==")

    class Celsius:
        def __init__(self, degrees: float) -> None:
            self.degrees = degrees  # runs the setter, so validation applies at construction

        @property
        def degrees(self) -> float:
            return self._degrees

        @degrees.setter
        def degrees(self, value: float) -> None:
            if value < -273.15:
                raise ValueError(f"{value} is below absolute zero")
            self._degrees = float(value)

        @property
        def fahrenheit(self) -> float:
            return self._degrees * 9 / 5 + 32

    t = Celsius(25)
    print(f"  {t.degrees=} {t.fahrenheit=}")
    try:
        t.degrees = -300
    except ValueError as exc:
        print(f"  setter validation: {exc}")
    try:
        t.fahrenheit = 100
    except AttributeError as exc:
        print(f"  read-only property: {exc}")


def mro_and_super() -> None:
    print("\n== MRO and cooperative super() ==")

    class Base:
        def __init__(self, **kwargs) -> None:
            self.trace = ["Base"]

        def describe(self) -> str:
            return "base"

    class LoggingMixin(Base):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)  # "next in the MRO", not "my parent"
            self.trace.append("LoggingMixin")

        def describe(self) -> str:
            return f"logged({super().describe()})"

    class CachingMixin(Base):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.trace.append("CachingMixin")

        def describe(self) -> str:
            return f"cached({super().describe()})"

    class Service(LoggingMixin, CachingMixin):
        pass

    s = Service()
    print(f"  MRO: {[c.__name__ for c in Service.__mro__]}")
    print(f"  __init__ ran: {s.trace}  (mixins chained without knowing about each other)")
    print(f"  describe(): {s.describe()}")


def class_vs_instance() -> None:
    print("\n== class attributes are shared ==")

    class Widget:
        registry: ClassVar[list[str]] = []
        default_size: ClassVar[int] = 10

        def __init__(self, name: str) -> None:
            self.name = name
            Widget.registry.append(name)

        @classmethod
        def from_spec(cls, spec: str) -> Widget:
            return cls(spec.split(":")[0])  # cls, not Widget => subclass-friendly

        @staticmethod
        def is_valid(spec: str) -> bool:
            return ":" in spec

    class FancyWidget(Widget):
        pass

    Widget("a")
    fancy = FancyWidget.from_spec("b:blue")
    print(f"  shared registry: {Widget.registry}")
    print(f"  classmethod returns the right type: {type(fancy).__name__}")

    w = Widget("c")
    w.default_size = 99  # creates an INSTANCE attribute, shadowing the class one
    print(f"  {w.default_size=} but {Widget.default_size=}")


def name_mangling() -> None:
    print("\n== name mangling ==")

    class A:
        def __init__(self) -> None:
            self._internal = 1
            self.__mangled = 2

    a = A()
    print(f"  attributes: {sorted(vars(a))}")
    print(f"  __mangled is reachable as _A__mangled = {a._A__mangled}")
    print("  single underscore = convention; double = collision avoidance, NOT security")


if __name__ == "__main__":
    print(INTRO)
    dunder_protocols()
    eq_and_hash()
    dataclasses_tour()
    properties()
    mro_and_super()
    class_vs_instance()
    name_mangling()
