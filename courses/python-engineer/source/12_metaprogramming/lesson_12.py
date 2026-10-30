"""Module 12 — runnable lesson. `python 12_metaprogramming/lesson_12.py`"""

from __future__ import annotations

import functools
import inspect
from typing import Any, get_type_hints

INTRO = """Code that writes code. It's how every framework you've used gives you validation and
database columns you never wrote. A descriptor is an attribute with a brain; a class can
be built at runtime with no `class` statement at all."""


def descriptors() -> None:
    print("\n== descriptors ==")

    class Typed:
        """One validator class, reused for any number of fields."""

        def __init__(self, expected: type) -> None:
            self.expected = expected

        def __set_name__(self, owner: type, name: str) -> None:
            self.name = name  # PEP 487: the class tells us our own attribute name
            self.slot = f"_{name}"

        def __get__(self, obj: Any, objtype: type | None = None) -> Any:
            if obj is None:
                return self  # accessed on the class itself
            return getattr(obj, self.slot)

        def __set__(self, obj: Any, value: Any) -> None:
            if not isinstance(value, self.expected):
                raise TypeError(f"{self.name} must be {self.expected.__name__}")
            setattr(obj, self.slot, value)

    class Order:
        quantity = Typed(int)
        label = Typed(str)

        def __init__(self, quantity: int, label: str) -> None:
            self.quantity = quantity  # goes through __set__
            self.label = label

    order = Order(3, "widgets")
    print(f"  valid: quantity={order.quantity} label={order.label!r}")
    try:
        order.quantity = "three"
    except TypeError as exc:
        print(f"  rejected: {exc}")
    print(f"  accessed on the class: {Order.quantity}")

    print("\n  data vs non-data descriptors:")

    class Demo:
        @functools.cached_property  # NO __set__ => the instance dict wins after first access
        def expensive(self) -> int:
            print("    computing...")
            return 42

    d = Demo()
    print(f"    first:  {d.expensive}")
    print(f"    second: {d.expensive}  (served from __dict__: {'expensive' in d.__dict__})")
    print("    a descriptor WITH __set__ would win over __dict__ every time")


def init_subclass() -> None:
    print("\n== __init_subclass__ replaces most metaclasses ==")

    class Plugin:
        registry: dict[str, type] = {}

        def __init_subclass__(cls, /, name: str | None = None, **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)  # cooperate with other hooks
            key = name or cls.__name__.lower()
            if key in cls.registry:
                raise ValueError(f"duplicate plugin {key!r}")
            cls.registry[key] = cls

    class CsvPlugin(Plugin, name="csv"):
        pass

    class JsonPlugin(Plugin):
        pass

    print(f"  auto-registered: {Plugin.registry}")
    print("  class keyword args (name='csv') are forwarded to __init_subclass__")

    try:

        class Duplicate(Plugin, name="csv"):
            pass

    except ValueError as exc:
        print(f"  validation at class-definition time: {exc}")


def class_decorators() -> None:
    print("\n== class decorators ==")

    def auto_repr(cls: type) -> type:
        def __repr__(self: Any) -> str:
            fields = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
            return f"{cls.__name__}({fields})"

        cls.__repr__ = __repr__  # type: ignore[method-assign]
        return cls

    @auto_repr
    class Point:
        def __init__(self, x: int, y: int) -> None:
            self.x, self.y = x, y

    print(f"  {Point(1, 2)}")
    print("  @dataclass is this idea, industrialised: read __annotations__, exec() methods")


def metaclasses() -> None:
    print("\n== metaclasses ==")

    class Sealed(type):
        """Forbid subclassing of any class that declares itself sealed."""

        def __new__(mcls, name, bases, namespace, **kwargs):
            for base in bases:
                if getattr(base, "_sealed", False):
                    raise TypeError(f"{base.__name__} is sealed and cannot be subclassed")
            cls = super().__new__(mcls, name, bases, namespace)
            cls.created_by = mcls.__name__
            return cls

    class Final(metaclass=Sealed):
        _sealed = True

    print(f"  metaclass injected an attribute: {Final.created_by}")
    print(f"  type(Final) is {type(Final).__name__}, type(type(Final)) is {type(type(Final)).__name__}")
    try:

        class Sneaky(Final):
            pass

    except TypeError as exc:
        print(f"  blocked: {exc}")

    print("\n  the same rule with __init_subclass__ — simpler, and composes:")

    class Base:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            if getattr(cls.__mro__[1], "_sealed", False):
                raise TypeError("sealed")

    print("  prefer that unless you need __prepare__ or __instancecheck__")


def dynamic_creation() -> None:
    print("\n== building classes at runtime ==")
    Dynamic = type(
        "Dynamic",
        (object,),
        {"greeting": "hi", "greet": lambda self, who: f"{self.greeting} {who}"},
    )
    print(f"  type(name, bases, namespace): {Dynamic().greet('there')!r}")
    print(f"  same thing a class statement does: {Dynamic.__mro__}")


def introspection() -> None:
    print("\n== introspection ==")

    def handler(request: str, retries: int = 3) -> dict[str, int]:
        """Handle a request."""
        return {"ok": 1}

    sig = inspect.signature(handler)
    print(f"  signature: {sig}")
    print(f"  parameters: {[(p.name, p.default) for p in sig.parameters.values()]}")
    print(f"  raw __annotations__: {handler.__annotations__}")
    print(f"  get_type_hints (resolved): {get_type_hints(handler)}")
    print("  ^ with `from __future__ import annotations`, raw annotations are STRINGS.")
    print("    Frameworks must use typing.get_type_hints to get real objects.")

    bound = sig.bind("GET /users")
    bound.apply_defaults()
    print(f"  bind + apply_defaults: {dict(bound.arguments)}")


if __name__ == "__main__":
    print(INTRO)
    descriptors()
    init_subclass()
    class_decorators()
    metaclasses()
    dynamic_creation()
    introspection()
