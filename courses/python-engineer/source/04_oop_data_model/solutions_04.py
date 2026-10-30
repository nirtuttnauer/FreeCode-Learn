"""Module 04 — reference solutions."""

from __future__ import annotations

import functools
import math
from collections import deque
from collections.abc import Iterable, Iterator, Mapping, MutableMapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

# =============================================================================
# Warmup solutions
# =============================================================================


class Point2D:
    def __init__(self, x: float | int, y: float | int) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Point2D({self.x}, {self.y})"

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point2D):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __add__(self, other: object) -> Point2D:
        if not isinstance(other, Point2D):
            return NotImplemented
        return Point2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: object) -> Point2D:
        if not isinstance(other, Point2D):
            return NotImplemented
        return Point2D(self.x - other.x, self.y - other.y)

    def __mul__(self, factor: object) -> Point2D:
        if not isinstance(factor, int | float):
            return NotImplemented
        return Point2D(self.x * factor, self.y * factor)

    __rmul__ = __mul__

    def __abs__(self) -> float:
        return (self.x**2 + self.y**2) ** 0.5


class Rectangle:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        if value <= 0:
            raise ValueError("dimensions must be positive")
        self._width = float(value)

    @property
    def height(self) -> float:
        return self._height

    @height.setter
    def height(self, value: float) -> None:
        if value <= 0:
            raise ValueError("dimensions must be positive")
        self._height = float(value)

    @property
    def area(self) -> float:
        return self._width * self._height

    @property
    def perimeter(self) -> float:
        return 2 * (self._width + self._height)

    def __repr__(self) -> str:
        return f"Rectangle(width={self._width}, height={self._height})"


class BankAccount:
    def __init__(self, owner: str, balance: float = 0.0) -> None:
        if balance < 0:
            raise ValueError("starting balance cannot be negative")
        self.owner = owner
        self.balance = float(balance)

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("deposit amount must be positive")
        self.balance += float(amount)

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("insufficient funds")
        self.balance -= float(amount)

    def __str__(self) -> str:
        return f"${self.balance:.2f} ({self.owner})"

    def __repr__(self) -> str:
        return f"BankAccount(owner={self.owner!r}, balance={self.balance})"


class Multiplier:
    def __init__(self, factor: float | int) -> None:
        self.factor = factor

    def __call__(self, x: float | int) -> float | int:
        return x * self.factor

    def __repr__(self) -> str:
        return f"Multiplier(factor={self.factor})"


class Playlist:
    def __init__(self, tracks: Iterable[str] | None = None) -> None:
        self._tracks: list[str] = list(tracks) if tracks is not None else []

    def add(self, track: str) -> None:
        self._tracks.append(track)

    def __len__(self) -> int:
        return len(self._tracks)

    def __getitem__(self, index: int) -> str:
        return self._tracks[index]

    def __iter__(self) -> Iterator[str]:
        return iter(self._tracks)

    def __contains__(self, item: object) -> bool:
        return item in self._tracks

    def __repr__(self) -> str:
        return f"Playlist(tracks={self._tracks!r})"


class Color:
    def __init__(self, r: int, g: int, b: int) -> None:
        for channel, name in ((r, "r"), (g, "g"), (b, "b")):
            if not isinstance(channel, int) or not (0 <= channel <= 255):
                raise ValueError(f"{name} must be an integer between 0 and 255, got {channel!r}")
        self._r = r
        self._g = g
        self._b = b

    @property
    def r(self) -> int:
        return self._r

    @property
    def g(self) -> int:
        return self._g

    @property
    def b(self) -> int:
        return self._b

    @property
    def hex_code(self) -> str:
        return f"#{self._r:02x}{self._g:02x}{self._b:02x}"

    def __repr__(self) -> str:
        return f"Color(r={self._r}, g={self._g}, b={self._b})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Color):
            return NotImplemented
        return (self._r, self._g, self._b) == (other._r, other._g, other._b)

    def __hash__(self) -> int:
        return hash((self._r, self._g, self._b))


@dataclass
class InventoryItem:
    name: str
    unit_price: float
    quantity: int = 0
    tags: list[str] = field(default_factory=list)

    def total_value(self) -> float:
        return self.unit_price * self.quantity

    def in_stock(self) -> bool:
        return self.quantity > 0


@functools.total_ordering
class HighScore:
    def __init__(self, player: str, score: int) -> None:
        self.player = player
        self.score = score

    def __repr__(self) -> str:
        return f"HighScore(player={self.player!r}, score={self.score})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HighScore):
            return NotImplemented
        return self.score == other.score

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, HighScore):
            return NotImplemented
        return self.score < other.score


class Percentage:
    def __init__(self, ratio: float) -> None:
        self.ratio = float(ratio)

    def __float__(self) -> float:
        return self.ratio

    def __str__(self) -> str:
        return f"{self.ratio * 100:.1f}%"

    def __format__(self, format_spec: str) -> str:
        if not format_spec:
            return str(self)
        val = self.ratio * 100
        formatted = format(val, format_spec)
        return f"{formatted}%"

    def __repr__(self) -> str:
        return f"Percentage({self.ratio})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Percentage):
            return NotImplemented
        return self.ratio == other.ratio


class Employee:
    count: int = 0

    def __init__(self, name: str, department: str = "General") -> None:
        Employee.count += 1
        self.id = Employee.count
        self.name = name
        self.department = department

    def __repr__(self) -> str:
        return f"Employee(id={self.id}, name={self.name!r}, department={self.department!r})"


class Person:
    def __init__(self, first_name: str, last_name: str) -> None:
        self.first_name = first_name
        self.last_name = last_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @classmethod
    def from_full_name(cls, full_name: str) -> Person:
        parts = full_name.strip().split(" ", 1)
        if len(parts) < 2:
            raise ValueError("full name must contain a space separating first and last name")
        return cls(parts[0], parts[1])

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> Person:
        return cls(data["first_name"], data["last_name"])

    def __repr__(self) -> str:
        return f"Person(first_name={self.first_name!r}, last_name={self.last_name!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Person):
            return NotImplemented
        return (self.first_name, self.last_name) == (other.first_name, other.last_name)


class Shape:
    def area(self) -> float:
        raise NotImplementedError

    def perimeter(self) -> float:
        raise NotImplementedError


class Circle(Shape):
    def __init__(self, radius: float) -> None:
        if radius <= 0:
            raise ValueError("radius must be positive")
        self.radius = float(radius)

    def area(self) -> float:
        return math.pi * self.radius**2

    def perimeter(self) -> float:
        return 2 * math.pi * self.radius

    def __repr__(self) -> str:
        return f"Circle(radius={self.radius})"


class Square(Shape):
    def __init__(self, side: float) -> None:
        if side <= 0:
            raise ValueError("side must be positive")
        self.side = float(side)

    def area(self) -> float:
        return self.side**2

    def perimeter(self) -> float:
        return 4 * self.side

    def __repr__(self) -> str:
        return f"Square(side={self.side})"


class TagSet:
    def __init__(self, tags: Iterable[str] | None = None) -> None:
        self._tags: frozenset[str] = (
            frozenset(t.strip().casefold() for t in tags) if tags is not None else frozenset()
        )

    @property
    def tags(self) -> frozenset[str]:
        return self._tags

    def __len__(self) -> int:
        return len(self._tags)

    def __contains__(self, item: object) -> bool:
        if not isinstance(item, str):
            return False
        return item.strip().casefold() in self._tags

    def __iter__(self) -> Iterator[str]:
        return iter(self._tags)

    def __or__(self, other: object) -> TagSet:
        if not isinstance(other, TagSet):
            return NotImplemented
        return TagSet(self._tags | other._tags)

    def __and__(self, other: object) -> TagSet:
        if not isinstance(other, TagSet):
            return NotImplemented
        return TagSet(self._tags & other._tags)

    def __sub__(self, other: object) -> TagSet:
        if not isinstance(other, TagSet):
            return NotImplemented
        return TagSet(self._tags - other._tags)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TagSet):
            return NotImplemented
        return self._tags == other._tags

    def __repr__(self) -> str:
        return f"TagSet({set(self._tags)!r})"


class StepCounter:
    def __init__(self, steps: int = 0) -> None:
        if steps < 0:
            raise ValueError("steps cannot be negative")
        self.steps = int(steps)

    def __iadd__(self, increment: object) -> StepCounter:
        if not isinstance(increment, int):
            raise TypeError("increment must be an integer")
        if increment <= 0:
            raise ValueError("increment must be positive")
        self.steps += increment
        return self

    def __int__(self) -> int:
        return self.steps

    def __bool__(self) -> bool:
        return self.steps > 0

    def reset(self) -> None:
        self.steps = 0

    def __repr__(self) -> str:
        return f"StepCounter(steps={self.steps})"


# =============================================================================
# Advanced solutions
# =============================================================================


@functools.total_ordering
@dataclass(frozen=True)
class Money:
    amount: Decimal = Decimal(0)
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not (len(self.currency) == 3 and self.currency.isalpha() and self.currency.isupper()):
            raise ValueError(f"bad currency code: {self.currency!r}")
        if not isinstance(self.amount, Decimal):
            # str() first: Decimal(0.1) is 0.1000000000000000055511151231257827
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

    def _check_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other: object) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: object) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: object) -> Money:
        if isinstance(factor, Money) or not isinstance(factor, int | Decimal):
            return NotImplemented
        return Money(self.amount * factor, self.currency)

    __rmul__ = __mul__

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return self.amount < other.amount

    def __str__(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"


class Temperature:
    ABSOLUTE_ZERO = -273.15

    def __init__(self, celsius: float) -> None:
        self.celsius = celsius  # through the property, so validation runs here too

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < self.ABSOLUTE_ZERO:
            raise ValueError(f"{value} is below absolute zero")
        self._celsius = float(value)

    @property
    def fahrenheit(self) -> float:
        return self._celsius * 9 / 5 + 32

    @fahrenheit.setter
    def fahrenheit(self, value: float) -> None:
        self.celsius = (value - 32) * 5 / 9  # reuse the validating setter

    @property
    def kelvin(self) -> float:  # no setter defined => assignment raises AttributeError
        return self._celsius - self.ABSOLUTE_ZERO

    @classmethod
    def from_fahrenheit(cls, value: float) -> Temperature:
        return cls((value - 32) * 5 / 9)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._celsius!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Temperature):
            return NotImplemented
        return self._celsius == other._celsius

    def __hash__(self) -> int:
        return hash(self._celsius)


class CircularBuffer:
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        self._capacity = capacity
        self._items: deque[Any] = deque(maxlen=capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def full(self) -> bool:
        return len(self._items) == self._capacity

    def append(self, item: Any) -> Any:
        evicted = self._items[0] if self.full else None
        self._items.append(item)  # deque(maxlen) drops the head for us
        return evicted

    def extend(self, items: Iterable[Any]) -> None:
        for item in items:
            self.append(item)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._items)

    def __getitem__(self, index: int) -> Any:
        return self._items[index]

    def __contains__(self, item: object) -> bool:
        return item in self._items

    def __repr__(self) -> str:
        return f"CircularBuffer(capacity={self._capacity}, items={list(self._items)})"


class CaseInsensitiveDict(MutableMapping[str, Any]):
    def __init__(self, data: Any = None, **kwargs: Any) -> None:
        self._store: dict[str, tuple[str, Any]] = {}
        if data:
            self.update(data)  # update() comes free from MutableMapping
        self.update(kwargs)

    def __getitem__(self, key: str) -> Any:
        return self._store[key.casefold()][1]

    def __setitem__(self, key: str, value: Any) -> None:
        self._store[key.casefold()] = (key, value)  # remember the latest casing

    def __delitem__(self, key: str) -> None:
        del self._store[key.casefold()]

    def __iter__(self) -> Iterator[str]:
        return (original for original, _ in self._store.values())

    def __len__(self) -> int:
        return len(self._store)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mapping):
            return NotImplemented
        if len(self) != len(other):
            return False
        try:
            folded = {k.casefold(): v for k, v in other.items()}
        except AttributeError:  # non-string keys can't be case-folded
            return False
        return {k: v for k, (_, v) in self._store.items()} == folded

    def __repr__(self) -> str:
        return f"CaseInsensitiveDict({dict(self)!r})"
