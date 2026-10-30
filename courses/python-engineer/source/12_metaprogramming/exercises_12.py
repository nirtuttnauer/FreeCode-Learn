"""Module 12 exercises.  pytest 12_metaprogramming

Build the machinery frameworks are made of. Annotate everything — mypy runs strict on
this file.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Validated:
    """A reusable data descriptor that validates on assignment.

    >>> class Order:
    ...     quantity = Validated(int, lambda v: v > 0, "must be positive")
    >>> o = Order(); o.quantity = 5; o.quantity
    5

    Requirements:
    - `Validated(expected_type, predicate=None, message="invalid value")`
    - `__set_name__` learns the attribute name; store the value in the instance's
      `__dict__` under a private key so two fields never collide.
    - Wrong type -> TypeError("<name> must be <type>"); failing predicate ->
      ValueError("<name> <message>").
    - Reading before any assignment -> AttributeError("<name> is not set").
    - Accessing it on the CLASS (`Order.quantity`) returns the descriptor itself —
      that's what `obj is None` inside `__get__` means.
    - It IS a data descriptor (it defines `__set__`), so it must win over an entry the
      user pokes directly into `instance.__dict__`.
    """

    def __init__(
        self,
        expected_type: type,
        predicate: Callable[[Any], bool] | None = None,
        message: str = "invalid value",
    ) -> None:
        raise NotImplementedError


class Registry:
    """A base class whose subclasses register themselves automatically.

    >>> class Handler(Registry): pass          # doctest: +SKIP
    >>> class Json(Handler, key="json"): pass  # doctest: +SKIP
    >>> Handler.registry["json"] is Json       # doctest: +SKIP
    True

    Requirements, all via `__init_subclass__` (no metaclass):
    - Subclasses register under the `key=` class keyword argument, defaulting to the
      lowercased class name.
    - `Registry.registry` is a dict[str, type].
    - Registering a duplicate key raises ValueError at class-definition time.
    - `abstract=True` as a class keyword skips registration (for intermediate bases).
    - Always call `super().__init_subclass__(**kwargs)` so the hook composes with others.
    - `Registry.get(key)` returns the class, raising KeyError with a message listing the
      known keys.
    """

    registry: dict[str, type] = {}


def auto_slots(cls: type) -> type:
    """A CLASS DECORATOR that rebuilds `cls` with `__slots__` from its annotations.

    >>> @auto_slots                       # doctest: +SKIP
    ... class Point:
    ...     x: int
    ...     y: int

    - The returned class must have `__slots__ == ("x", "y")` and no `__dict__`.
    - You cannot add `__slots__` to an existing class — the layout is fixed at creation.
      Rebuild it with `type(cls.__name__, cls.__bases__, namespace)`, copying the
      original namespace, dropping `__dict__`/`__weakref__`, and adding `__slots__`.
    - Class-level attributes that have a VALUE (defaults, methods) must be excluded from
      `__slots__` — a slot and a class attribute of the same name conflict.
    - Preserve `__doc__`, `__module__`, and `__qualname__`.
    """
    raise NotImplementedError


def call_logger(sink: list[str]) -> Callable[[type], type]:
    """A class-decorator FACTORY that logs every public method call into `sink`.

    >>> log = []                                   # doctest: +SKIP
    >>> @call_logger(log)                          # doctest: +SKIP
    ... class Service:
    ...     def run(self, n): return n * 2
    >>> Service().run(2); log                      # doctest: +SKIP
    (4, ['run(2)'])

    - Wrap every callable attribute whose name doesn't start with "_".
    - Log entries are "<name>(<comma-separated reprs of args and kwargs>)", where `self`
      is not included and kwargs are rendered as "k=v" after the positional args.
    - Return values and exceptions pass through untouched (log the call either way).
    - Use `functools.wraps`; `staticmethod` and `classmethod` may be left alone.
    """
    raise NotImplementedError


def build_model(name: str, fields: dict[str, type]) -> type:
    """Create a class at runtime from a field spec — a miniature ORM model factory.

    >>> User = build_model("User", {"id": int, "name": str})   # doctest: +SKIP
    >>> u = User(id=1, name="ada"); repr(u)                    # doctest: +SKIP
    "User(id=1, name='ada')"

    The generated class must:
    - Take all fields as KEYWORD-ONLY arguments; a missing one raises TypeError,
      an unknown one raises TypeError.
    - Validate types on construction: wrong type raises TypeError.
    - Provide `__repr__` as "Name(field=value, ...)" in declaration order.
    - Compare by value (`==`) against other instances of the same generated class, and
      be hashable.
    - Expose `__annotations__` equal to `fields`, and a `_fields` tuple of names.

    Use `type(name, bases, namespace)`. This is the exercise where you feel why
    `@dataclass` exists.
    """
    raise NotImplementedError
