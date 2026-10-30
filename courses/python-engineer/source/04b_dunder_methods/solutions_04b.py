"""Module 04b — reference solutions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any


class Pipeline:
    def __init__(self, *steps: Callable[[Any], Any]) -> None:
        self.steps = tuple(steps)

    def __call__(self, value: Any) -> Any:
        for step in self.steps:
            value = step(value)
        return value

    def __or__(self, other: Any) -> Pipeline:
        if isinstance(other, Pipeline):
            return Pipeline(*self.steps, *other.steps)
        if callable(other):
            return Pipeline(*self.steps, other)
        return NotImplemented

    def __ror__(self, other: Any) -> Pipeline:
        # Reached for `func | pipeline`: plain functions have no __or__.
        if callable(other):
            return Pipeline(other, *self.steps)
        return NotImplemented

    def __len__(self) -> int:
        return len(self.steps)

    def __repr__(self) -> str:
        names = ", ".join(getattr(s, "__name__", repr(s)) for s in self.steps)
        return f"Pipeline({names})"


class FrozenBox:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        wrapped = {
            key: FrozenBox(value) if isinstance(value, dict) else value
            for key, value in (data or {}).items()
        }
        object.__setattr__(self, "_data", wrapped)  # our __setattr__ would reject this

    def __getattr__(self, name: str) -> Any:
        # Guard private names FIRST. copy/pickle create the instance without calling
        # __init__, so `_data` is missing; `self._data` would then re-enter __getattr__
        # forever. Same reason dunder probes (__deepcopy__, __setstate__) must fail fast.
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"{type(self).__name__!r} has no attribute {name!r}") from None

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("FrozenBox is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("FrozenBox is immutable")

    def __getitem__(self, key: str) -> Any:
        return self._data[key]  # a missing key must raise KeyError here

    def __setitem__(self, key: str, value: Any) -> None:
        raise TypeError("FrozenBox is immutable")

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __dir__(self) -> list[str]:
        return sorted(set(super().__dir__()) | set(self._data))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FrozenBox):
            return self._data == other._data
        if isinstance(other, dict):
            return self == FrozenBox(other)
        return NotImplemented

    def __repr__(self) -> str:
        return f"FrozenBox({self._data!r})"


class CountingDict(dict):
    def __init__(self, factory: Callable[[], Any], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Plain attributes, not dict entries.
        self.factory = factory
        self.misses = 0

    def __missing__(self, key: Any) -> Any:
        # Consulted by dict.__getitem__ only — .get() bypasses it entirely.
        self.misses += 1
        value = self.factory()
        self[key] = value
        return value


class Interval:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end

    @property
    def length(self) -> float:
        return max(0, self.end - self.start)

    def __contains__(self, value: object) -> bool:
        if not isinstance(value, int | float):
            return False
        return self.start <= value < self.end

    def __bool__(self) -> bool:
        return self.start < self.end

    def __and__(self, other: object) -> Interval:
        if not isinstance(other, Interval):
            return NotImplemented
        return Interval(max(self.start, other.start), min(self.end, other.end))

    def __or__(self, other: object) -> Interval:
        if not isinstance(other, Interval):
            return NotImplemented
        if not (self & other) and self.end != other.start and other.end != self.start:
            raise ValueError("cannot union disjoint intervals")
        return Interval(min(self.start, other.start), max(self.end, other.end))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Interval):
            return NotImplemented
        return (self.start, self.end) == (other.start, other.end)

    def __hash__(self) -> int:
        return hash((self.start, self.end))

    def __str__(self) -> str:
        return f"[{self.start}, {self.end})"

    def __repr__(self) -> str:
        return f"Interval({self.start!r}, {self.end!r})"

    def __format__(self, spec: str) -> str:
        if not spec:
            return str(self)
        return f"[{self.start:{spec}}, {self.end:{spec}})"


class Recorder:
    def __init__(self) -> None:
        # Set through the normal machinery: found by __getattribute__, so __getattr__
        # never fires for "calls" and it stays a real list.
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Callable[..., None]:
        if name.startswith("_"):
            # Never fake dunders — copy/pickle/inspect probe for them.
            raise AttributeError(name)

        def record(*args: Any, **kwargs: Any) -> None:
            self.calls.append((name, args, kwargs))

        return record

    def was_called(self, name: str) -> bool:
        return any(call[0] == name for call in self.calls)

    def __len__(self) -> int:
        return len(self.calls)

    def __repr__(self) -> str:
        n = len(self.calls)
        return f"Recorder({n} call{'' if n == 1 else 's'})"
