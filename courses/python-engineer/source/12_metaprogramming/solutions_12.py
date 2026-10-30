"""Module 12 — reference solutions."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any


class Validated:
    def __init__(
        self,
        expected_type: type,
        predicate: Callable[[Any], bool] | None = None,
        message: str = "invalid value",
    ) -> None:
        self.expected_type = expected_type
        self.predicate = predicate
        self.message = message

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.slot = f"__validated_{name}"  # private key, so two fields never collide

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self  # accessed on the class
        try:
            return obj.__dict__[self.slot]
        except KeyError:
            raise AttributeError(f"{self.name} is not set") from None

    def __set__(self, obj: Any, value: Any) -> None:
        if not isinstance(value, self.expected_type):
            raise TypeError(f"{self.name} must be {self.expected_type.__name__}")
        if self.predicate is not None and not self.predicate(value):
            raise ValueError(f"{self.name} {self.message}")
        obj.__dict__[self.slot] = value

    def __delete__(self, obj: Any) -> None:
        obj.__dict__.pop(self.slot, None)


class Registry:
    registry: dict[str, type] = {}

    def __init_subclass__(
        cls, /, key: str | None = None, abstract: bool = False, **kwargs: Any
    ) -> None:
        super().__init_subclass__(**kwargs)  # cooperate — never swallow kwargs
        if abstract:
            return
        name = key or cls.__name__.lower()
        if name in Registry.registry:
            raise ValueError(f"duplicate key {name!r}")
        Registry.registry[name] = cls

    @classmethod
    def get(cls, key: str) -> type:
        try:
            return Registry.registry[key]
        except KeyError:
            known = ", ".join(sorted(Registry.registry)) or "<none>"
            raise KeyError(f"unknown key {key!r}; known keys: {known}") from None


def auto_slots(cls: type) -> type:
    annotations = dict(getattr(cls, "__annotations__", {}))
    namespace = dict(vars(cls))
    # A name can't be both a slot and a class attribute.
    slots = tuple(n for n in annotations if n not in namespace)
    for key in ("__dict__", "__weakref__"):
        namespace.pop(key, None)
    namespace["__slots__"] = slots
    namespace["__annotations__"] = annotations

    rebuilt = type(cls.__name__, cls.__bases__, namespace)
    rebuilt.__doc__ = cls.__doc__
    rebuilt.__module__ = cls.__module__
    rebuilt.__qualname__ = cls.__qualname__
    return rebuilt


def call_logger(sink: list[str]) -> Callable[[type], type]:
    def decorate(cls: type) -> type:
        for name, attr in list(vars(cls).items()):
            if name.startswith("_") or not callable(attr):
                continue
            if isinstance(vars(cls)[name], staticmethod | classmethod):
                continue

            def make_wrapper(func: Any, func_name: str) -> Any:
                @functools.wraps(func)
                def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                    rendered = [repr(a) for a in args]
                    rendered += [f"{k}={v!r}" for k, v in kwargs.items()]
                    sink.append(f"{func_name}({', '.join(rendered)})")
                    return func(self, *args, **kwargs)

                return wrapper

            # A factory, not a closure over the loop variable — module 03's late binding.
            setattr(cls, name, make_wrapper(attr, name))
        return cls

    return decorate


def build_model(name: str, fields: dict[str, type]) -> type:
    field_names = tuple(fields)

    def __init__(self: Any, **kwargs: Any) -> None:
        missing = [f for f in field_names if f not in kwargs]
        if missing:
            raise TypeError(f"missing required fields: {', '.join(missing)}")
        unknown = [k for k in kwargs if k not in fields]
        if unknown:
            raise TypeError(f"unknown fields: {', '.join(unknown)}")
        for key, expected in fields.items():
            value = kwargs[key]
            if not isinstance(value, expected):
                raise TypeError(f"{key} must be {expected.__name__}")
            object.__setattr__(self, key, value)

    def __repr__(self: Any) -> str:
        rendered = ", ".join(f"{f}={getattr(self, f)!r}" for f in field_names)
        return f"{name}({rendered})"

    def __eq__(self: Any, other: object) -> Any:
        if type(other) is not type(self):
            return NotImplemented
        return self._values() == other._values()

    def _values(self: Any) -> tuple[Any, ...]:
        return tuple(getattr(self, f) for f in field_names)

    def __hash__(self: Any) -> int:
        return hash((name, self._values()))

    namespace: dict[str, Any] = {
        "__init__": __init__,
        "__repr__": __repr__,
        "__eq__": __eq__,
        "__hash__": __hash__,
        "_values": _values,
        "_fields": field_names,
        "__annotations__": dict(fields),
        "__slots__": field_names,
    }
    return type(name, (object,), namespace)
