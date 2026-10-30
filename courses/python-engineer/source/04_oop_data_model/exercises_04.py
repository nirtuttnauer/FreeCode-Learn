"""Module 04 exercises.  pytest 04_oop_data_model

Warmup exercises start simple with fundamental dunders, properties, and dataclasses,
building up to more advanced data model patterns.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Iterable, Iterator, MutableMapping
from dataclasses import dataclass, field
from decimal import Decimal
from operator import truediv
from typing import Any

# =============================================================================
# Warmup exercises — start here!
# =============================================================================


class Point2D:
    """A 2D point with coordinate arithmetic and representation.

    - `Point2D(1, 2)` initializes `x` and `y` coordinates (accessible via `p.x` and `p.y`).
    - `repr(p)` == "Point2D(1, 2)"
    - `str(p)` == "(1, 2)"
    - `p1 == p2`: True if coordinates match; return NotImplemented for non-Point2D objects.
    - `p1 + p2`: returns a new `Point2D` with summed coordinates; return NotImplemented if other
      is not a Point2D.
    - `p1 - p2`: returns a new `Point2D` with subtracted coordinates; return NotImplemented if other
      is not a Point2D.
    - `p * 3` and `3 * p`: returns a new `Point2D` scaled by factor (scalar int or float);
      return NotImplemented for invalid types.
    - `abs(p)`: Euclidean distance from origin: `(x**2 + y**2) ** 0.5`.
    """

    def __init__(self, x: float | int, y: float | int) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Point2D({self.x}, {self.y})"

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other,Point2D):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __add__(self,other:object) -> Point2D:
        if not isinstance(other,Point2D):
            return NotImplemented
        return Point2D(self.x + other.x, self.y + other.y)

    def __sub__(self,other:object) -> Point2D:
         if not isinstance(other,Point2D):
             return NotImplemented
         return Point2D(self.x - other.x, self.y - other.y)

    def __mul__(self, factor: object) -> Point2D:
        if not isinstance(factor,int) and not isinstance(factor,float):
            return NotImplemented
        return Point2D(self.x * factor, self.y * factor)

    __rmul__ = __mul__

    def __abs__(self) -> float:
        return (self.x ** 2 +self.y ** 2) ** 0.5

class Rectangle:
    """A rectangle with validated dimensions and computed properties.

    - `Rectangle(4, 5)` -> `.width == 4.0`, `.height == 5.0` (stored as floats).
    - `.width` and `.height` are properties. Setting either <= 0 raises ValueError.
    - Validation must also run during `__init__` (assign through properties).
    - `.area` is a read-only property returning `width * height`.
    - `.perimeter` is a read-only property returning `2 * (width + height)`.
    - `repr(r)` == "Rectangle(width=4.0, height=5.0)".
    """

    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, value) -> None:
        if value <= 0:
            raise ValueError
        self._width = float(value)

    @property
    def height(self) -> float:
        return self._height

    @height.setter
    def height(self, value) -> None:
        if value <= 0:
            raise ValueError
        self._height = float(value)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

    def __repr__(self) -> str:
        return f"Rectangle(width={self.width}, height={self.height})"

class BankAccount:
    """A bank account with balance tracking and transaction validation.

    - `BankAccount("Alice", 100.0)` or `BankAccount("Bob")` (balance defaults to 0.0).
    - Starting balance < 0 raises ValueError.
    - `.owner` is the owner string.
    - `.balance` is the current balance (float).
    - `.deposit(amount)`: amount must be > 0 (else ValueError); adds to balance.
    - `.withdraw(amount)`: amount must be > 0 (else ValueError); cannot exceed balance
      (raises ValueError("insufficient funds")); subtracts from balance.
    - `str(acc)` == "$100.00 (Alice)".
    - `repr(acc)` == "BankAccount(owner='Alice', balance=100.0)".
    """

    def __init__(self, owner: str, balance: float = 0.0) -> None:
        if balance < 0 :
            raise ValueError
        self.owner = owner
        self.balance = float(balance)

    def deposit(self, amount: float) -> None:
        if amount >= 0 and amount <= self.balance and amount:
            self.balance += amount
        else:
            raise ValueError

    def withdraw(self, amount: float) -> None:
        if amount >= 0 and amount <= self.balance and amount:
            self.balance -= amount
        else:
            raise ValueError

    def __repr__(self) -> str:
        return f"BankAccount(owner='{self.owner}', balance={self.balance})"

    def __str__(self) -> str:
        return f"${self.balance} ({self.owner})"

class Multiplier:
    """A callable object that multiplies input numbers by a stored factor.

    - `m = Multiplier(3)`
    - `m(10) == 30` and `m(2.5) == 7.5` via `__call__`.
    - `repr(m)` == "Multiplier(factor=3)".
    """

    def __init__(self, factor: float | int) -> None:
        self.factor = factor

    def __call__(self, x: float | int) -> float | int:
        return x * self.factor

    def __repr__(self) -> str:
        return f"Multiplier(factor={self.factor})"

class Playlist:
    """A sequence container for music tracks.

    - `Playlist(["Song 1", "Song 2"])` or `Playlist()` (defaults to empty).
    - `.add(track)` appends a track string.
    - `len(p)` returns number of tracks (`__len__`).
    - `p[i]` returns track by index (`__getitem__`), raises IndexError if out of bounds.
    - `track in p` checks membership (`__contains__`).
    - `for track in p` yields tracks in order (`__iter__`).
    - `bool(p)` is False when empty, True when non-empty (free from `__len__`).
    - `repr(p)` == "Playlist(tracks=['Song 1', 'Song 2'])".
    """

    def __init__(self, tracks: Iterable[str] | None = None) -> None:
        raise NotImplementedError

    def add(self, track: str) -> None:
        raise NotImplementedError


class Color:
    """An immutable RGB color value object with hex formatting.

    - `Color(255, 128, 0)`: r, g, b must each be integers in 0..255, else ValueError.
    - Attributes `.r`, `.g`, `.b` are properties.
    - `.hex_code` is a read-only property returning formatted lowercase hex, e.g. "#ff8000".
    - `repr(c)` == "Color(r=255, g=128, b=0)".
    - Equality: two Colors with the same r, g, b are equal (`__eq__`).
    - Hashable: can be stored in sets or used as dict keys (`__hash__`).
    """

    def __init__(self, r: int, g: int, b: int) -> None:
        self.r = r
        self.g = g
        self.b = b

    @property
    def r(self) -> int:
        return self._r

    @r.setter
    def r(self, value:int) -> None:
        if not 0 <= value <= 255:
            raise ValueError
        self._r = value

    @property
    def g(self) -> int:
        return self._g

    @g.setter
    def g(self, value:int) -> None:
        if not 0 <= value <= 255:
            raise ValueError
        self._g = value

    @property
    def b(self) -> int:
        return self._b

    @b.setter
    def b(self, value:int) -> None:
        if not 0 <= value <= 255:
            raise ValueError
        self._b = value

    def hex_code(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def __repr__(self) -> str:
        return f"Color(r={self.r}, g={self.g}, b={self.b})"

    def __eq__(self, other:object) -> bool:
        if not isinstance(other, Color):
            return NotImplemented
        return self.r == other.r and self.g == other.g and self.b == other.b

    def __hash__(self) -> int:
       return hash((self.r, self.g, self.b))

@dataclass
class InventoryItem:
    """A dataclass representing an item in stock.

    - Fields:
      - `name: str`
      - `unit_price: float`
      - `quantity: int = 0`
      - `tags: list[str] = field(default_factory=list)`
    - Methods:
      - `.total_value() -> float`: returns `unit_price * quantity`.
      - `.in_stock() -> bool`: returns `quantity > 0`.
    - Dataclass automatically supplies `__init__`, `__repr__`, and `__eq__`.
    """

    name: str
    unit_price: float
    quantity: int = 0
    tags: list[str] = field(default_factory=list)

    def total_value(self) -> float:
        raise NotImplementedError

    def in_stock(self) -> bool:
        raise NotImplementedError


class HighScore:
    """A game score with total ordering comparison.

    - `HighScore("Alice", 100)` stores `player: str` and `score: int`.
    - `repr(h)` == "HighScore(player='Alice', score=100)".
    - Equality (`__eq__`): scores are equal if `.score` matches (and other is HighScore).
    - Ordering (`__lt__`): compares `.score` (and other is HighScore).
    - Decorate with `@functools.total_ordering` to derive `<=`, `>`, `>=`.
    """

    def __init__(self, player: str, score: int) -> None:
        raise NotImplementedError


class Percentage:
    """A floating-point ratio with percentage formatting.

    - `Percentage(0.852)` stores `.ratio == 0.852` (float).
    - `float(p)` == 0.852 via `__float__`.
    - `str(p)` == "85.2%" via `__str__` (rounds to 1 decimal place followed by '%').
    - `f"{p:.0f}"` == "85%" and `f"{p:.2f}"` == "85.20%" via `__format__`.
      When format spec is empty, falls back to `str(p)`.
    - `repr(p)` == "Percentage(0.852)".
    - Equality (`__eq__`): two Percentage objects are equal if their ratios are equal.
    """

    def __init__(self, ratio: float) -> None:
        raise NotImplementedError


class Employee:
    """An employee with an automatically incremented ID tracked by a class variable.

    - Class attribute `count: int = 0` tracks total employees created so far.
    - Each instance receives an auto-incremented `.id: int` starting at 1.
    - `Employee("Alice", "Engineering")` or `Employee("Bob")` (department defaults to "General").
    - `.name: str` and `.department: str`.
    - `repr(e)` == "Employee(id=1, name='Alice', department='Engineering')".
    """

    count: int = 0

    def __init__(self, name: str, department: str = "General") -> None:
        raise NotImplementedError


class Person:
    """A person with first/last names and alternative classmethod constructors.

    - `Person("Ada", "Lovelace")` stores `.first_name` and `.last_name`.
    - `.full_name` is a read-only property returning `f"{self.first_name} {self.last_name}"`.
    - `@classmethod from_full_name(cls, full_name: str) -> Person`:
      splits on the first space. If no space is present, raises ValueError.
      Returns an instance of `cls`.
    - `@classmethod from_dict(cls, data: dict[str, str]) -> Person`:
      extracts "first_name" and "last_name" from data dict (missing keys raise KeyError).
      Returns an instance of `cls`.
    - `repr(p)` == "Person(first_name='Ada', last_name='Lovelace')".
    - `p1 == p2` if first and last names match.
    """

    def __init__(self, first_name: str, last_name: str) -> None:
        raise NotImplementedError


class Shape:
    """Base class for geometric shapes."""

    def area(self) -> float:
        raise NotImplementedError

    def perimeter(self) -> float:
        raise NotImplementedError


class Circle(Shape):
    """A circle with radius validation and geometric calculations.

    - `Circle(5.0)`: radius <= 0 raises ValueError("radius must be positive").
    - Stored `.radius: float`.
    - `.area()` returns `math.pi * self.radius ** 2`.
    - `.perimeter()` returns `2 * math.pi * self.radius`.
    - `repr(c)` == "Circle(radius=5.0)".
    """

    def __init__(self, radius: float) -> None:
        raise NotImplementedError


class Square(Shape):
    """A square with side validation and geometric calculations.

    - `Square(4.0)`: side <= 0 raises ValueError("side must be positive").
    - Stored `.side: float`.
    - `.area()` returns `self.side ** 2`.
    - `.perimeter()` returns `4 * self.side`.
    - `repr(s)` == "Square(side=4.0)".
    """

    def __init__(self, side: float) -> None:
        raise NotImplementedError


class TagSet:
    """A collection of unique, normalized (lowercased) string tags.

    - `TagSet(["Python", "Coding"])` or `TagSet()` (defaults to empty).
    - Tags are stripped and casefolded to lowercase: " Python " -> "python".
    - `.tags` is a read-only property returning a frozenset of tags.
    - `len(ts)` returns number of tags (`__len__`).
    - `tag in ts` checks membership (`__contains__`), case-insensitively.
    - `for tag in ts` yields tags (`__iter__`).
    - `ts1 | ts2` returns a new TagSet with union of tags (`__or__`).
    - `ts1 & ts2` returns a new TagSet with intersection of tags (`__and__`).
    - `ts1 - ts2` returns a new TagSet with difference of tags (`__sub__`).
    - `repr(ts)` == "TagSet({'coding', 'python'})".
    - `ts1 == ts2` if their tag sets are identical (`__eq__`).
    """

    def __init__(self, tags: Iterable[str] | None = None) -> None:
        raise NotImplementedError


class StepCounter:
    """A step counter supporting in-place accumulation and type conversions.

    - `StepCounter(100)` or `StepCounter()` (defaults to 0 steps).
    - Initial steps < 0 raises ValueError.
    - `.steps: int` is accessible.
    - `sc += 50` via `__iadd__`: adds steps in-place and returns `self`.
      Adding non-positive or non-integer values raises ValueError / TypeError.
    - `int(sc)` returns `self.steps` (`__int__`).
    - `bool(sc)` returns True if `self.steps > 0`, else False (`__bool__`).
    - `.reset()` resets steps back to 0.
    - `repr(sc)` == "StepCounter(steps=150)".
    """

    def __init__(self, steps: int = 0) -> None:
        raise NotImplementedError


# =============================================================================
# Advanced exercises
# =============================================================================


class Money:
    """An immutable, hashable, orderable amount of a single currency.

    Build it as a FROZEN DATACLASS. Required behaviour:

    - `Money(1)`, `Money("1.10")`, `Money(Decimal("1.10"))` all work; `amount` is always
      stored as a `Decimal` (coerce through `str` so floats don't poison you).
      On a frozen dataclass you must assign via `object.__setattr__(self, ...)` inside
      `__post_init__`.
    - `currency` defaults to "USD" and must be exactly 3 uppercase letters, else ValueError.
    - `+` and `-` between two Money of the SAME currency; mixed currencies raise ValueError.
      Money + non-Money returns NotImplemented (so Python raises TypeError for you).
    - `*` by an int/Decimal on either side (`m * 3` and `3 * m`); Money * Money is a TypeError.
    - `-m` and `abs(m)`.
    - Ordering (`<`, `<=`, `>`, `>=`) within a currency; across currencies raise ValueError.
      Write only `__lt__` and let `functools.total_ordering` derive the rest.
    - `str(m)` == "1,234.50 USD"; `repr(m)` is the dataclass default.
    - Hashable and usable in sets/dicts.
    """

    def __init__(self, amount: Decimal | int | str, currency: str = "USD") -> None:
        raise NotImplementedError


class Temperature:
    """A temperature with a validated Celsius value and computed scales.

    - `Temperature(25)` -> `.celsius == 25.0` (stored as float).
    - `.celsius` is a property; setting below -273.15 raises ValueError. Validation must
      also apply in `__init__` (assign through the property, don't bypass it).
    - `.fahrenheit` is a property with a getter AND a setter (setting it updates celsius,
      and still validates).
    - `.kelvin` is READ-ONLY: assigning raises AttributeError.
    - `Temperature.from_fahrenheit(212)` is a classmethod alternative constructor that
      returns an instance of `cls` (so subclasses get their own type back).
    - `repr(t)` == "Temperature(25.0)".
    - Two temperatures with the same celsius are equal and hash equal.
    """

    def __init__(self, celsius: float) -> None:
        raise NotImplementedError


class CircularBuffer:
    """A fixed-capacity FIFO that overwrites its oldest item when full.

    - `CircularBuffer(3)`; capacity < 1 raises ValueError.
    - `.append(item)` returns the EVICTED item when the buffer was full, else None.
    - `.extend(iterable)` appends each item.
    - `len(buf)`, `for x in buf` (oldest -> newest), `x in buf`, `buf[0]` (oldest),
      `buf[-1]` (newest), out-of-range index raises IndexError.
    - `.full` is a read-only property.
    - `bool(buf)` is False when empty (you get this free from `__len__` — know why).
    - `repr(buf)` == "CircularBuffer(capacity=3, items=[1, 2, 3])".

    `collections.deque(maxlen=...)` does the hard part; you supply the protocol methods
    and the eviction return value.
    """

    def __init__(self, capacity: int) -> None:
        raise NotImplementedError


class CaseInsensitiveDict(MutableMapping[str, Any]):
    """A mapping practical for headers whose string keys compare case-insensitively.

    - `d["Content-Type"]` and `d["content-type"]` are the same slot.
    - Iteration and `repr` yield the casing used by the most recent assignment.
    - Subclass `collections.abc.MutableMapping` and implement exactly five methods:
      `__getitem__`, `__setitem__`, `__delitem__`, `__iter__`, `__len__`.
      Everything else (`get`, `pop`, `update`, `setdefault`, `keys`, `items`, `in`)
      comes free from the ABC — that's the payoff.
    - `CaseInsensitiveDict({"A": 1})` and `CaseInsensitiveDict(a=1)` both work.
    - Equality with any Mapping compares keys case-insensitively.
    - `repr(d)` == "CaseInsensitiveDict({'A': 1})".

    Store `{casefolded_key: (original_key, value)}` internally.
    """

    def __init__(self, data: Any = None, **kwargs: Any) -> None:
        raise NotImplementedError

    def __getitem__(self, key: str) -> Any:
        raise NotImplementedError

    def __setitem__(self, key: str, value: Any) -> None:
        raise NotImplementedError

    def __delitem__(self, key: str) -> None:
        raise NotImplementedError

    def __iter__(self) -> Iterator[str]:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError


def _unused(*_: Any) -> None:
    """Keeps linters quiet about the imports above while stubs are unimplemented."""
    _unused(functools, math)
