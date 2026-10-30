"""Module 04b exercises.  pytest 04b_dunder_methods

Five objects, each built around dunders that module 04 did not use.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Pipeline:
    """A callable chain of single-argument functions, composable with `|`.

    - `Pipeline(f, g)(x)` == `g(f(x))` — LEFT TO RIGHT, like a shell pipe (note this is
      the opposite of `compose` in module 03; both conventions exist in the wild).
    - `Pipeline()` is the identity.
    - `pipeline | func` -> new Pipeline with func appended  (`__or__`)
    - `func | pipeline` -> new Pipeline with func prepended (`__ror__` — plain functions
      have no `__or__`, so Python asks the right operand)
    - `p1 | p2` -> the concatenation of both step lists
    - `|` never mutates either operand.
    - `len(p)` is the number of steps; an empty Pipeline is falsy.
    - `repr(p)` == "Pipeline(strip, upper)" using each step's `__name__`.
    """

    def __init__(self, *steps: Callable[[Any], Any]) -> None:
        raise NotImplementedError


class FrozenBox:
    """Immutable dict wrapper with attribute access, built on the attribute protocol.

    - `FrozenBox({"host": "x", "db": {"port": 1}})` — nested dicts become FrozenBoxes.
    - `box.host` and `box["host"]` both work; `box.db.port` chains.
    - Unknown attribute -> AttributeError. Unknown key -> KeyError. (Getting these two
      right is the exercise: `__getattr__` must translate one into the other.)
    - Any assignment or deletion (`box.x = 1`, `box["x"] = 1`, `del box.x`) raises
      AttributeError/TypeError — pick AttributeError for attributes.
    - `len(box)`, `"host" in box`, `iter(box)` over keys.
    - `dir(box)` includes the data keys — makes it introspectable in a REPL.
    - `box == FrozenBox({...})` and `box == {...}` compare by data.
    - `repr(box)` == "FrozenBox({'host': 'x'})".

    Two traps the tests will spring on you:
    1. In `__init__` you cannot write `self._data = ...` (your own `__setattr__` blocks
       it). Use `object.__setattr__(self, "_data", ...)`.
    2. `copy.deepcopy(box)` builds the instance WITHOUT calling `__init__`, then probes
       it for `__deepcopy__`/`__setstate__`. At that moment `_data` doesn't exist, so
       `self._data` inside `__getattr__` re-enters `__getattr__`... forever. Guard names
       starting with "_" at the top of `__getattr__` and raise AttributeError.
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        raise NotImplementedError


class CountingDict(dict):
    """A `dict` subclass that fills in missing keys and counts how often it had to.

    - `CountingDict(lambda: 0)` — the factory produces the default value.
    - `d["absent"]` calls the factory, STORES the value, increments `d.misses`,
      and returns it (this is exactly how `defaultdict` works: `__missing__`).
    - `d.get("absent")` returns None and does NOT count a miss or store anything —
      know why: `__missing__` is only consulted by `dict.__getitem__`.
    - Existing keys never count as misses.
    - `d.misses` starts at 0 and is not a dict key.
    """

    def __init__(self, factory: Callable[[], Any], *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


class Interval:
    """A half-open numeric interval [start, end).

    - `x in Interval(1, 5)` is True for 1 <= x < 5 (`__contains__`).
    - `bool(interval)` is False when start >= end (`__bool__`) — an empty interval.
    - `a & b` is the intersection, itself an Interval, possibly empty (`__and__`).
    - `a | b` is the smallest interval covering both — but raise ValueError if they are
      disjoint (the union wouldn't be an interval).
    - `.length` property: `max(0, end - start)`.
    - `str(i)` == "[1, 5)"; `f"{i:.2f}"` == "[1.00, 5.00)" (`__format__` applies the
      spec to both bounds).
    - Equality by bounds, and hashable.
    """

    def __init__(self, start: float, end: float) -> None:
        raise NotImplementedError


class Recorder:
    """A minimal spy object: every attribute is a callable that records the call.

    >>> r = Recorder()
    >>> r.save(1, mode="w")
    >>> r.calls
    [('save', (1,), {'mode': 'w'})]

    - Any attribute access returns a function; calling it appends
      `(name, args, kwargs)` to `.calls` and returns None.
    - `.calls` itself must be a real list, not a recorded call — think about WHEN
      `__getattr__` fires versus `__getattribute__`.
    - Names starting with "_" raise AttributeError, so `copy`, `pickle` and `inspect`
      don't get fooled by fake dunders.
    - `.was_called("save")` -> bool.
    - `len(r)` is the number of recorded calls; `repr(r)` == "Recorder(1 call)" /
      "Recorder(2 calls)" / "Recorder(0 calls)".
    """

    def __init__(self) -> None:
        raise NotImplementedError
