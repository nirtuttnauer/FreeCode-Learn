"""Module 03 — runnable lesson. `python 03_functions/lesson_03.py`"""

from __future__ import annotations

import functools
import inspect
import time

INTRO = """Functions are things you can carry around, not just call. A closure is a function that
secretly remembers something you gave it earlier; a decorator is gift-wrapping that adds
behaviour without touching the original. Both are below, plus the famous default-argument
trap that eats afternoons."""


def parameter_grammar() -> None:
    print("\n== the full parameter grammar ==")

    def demo(pos_only, /, standard, *args, kw_only, **kwargs):
        return {
            "pos_only": pos_only,
            "standard": standard,
            "args": args,
            "kw_only": kw_only,
            "kwargs": kwargs,
        }

    print(f"  {demo(1, 2, 3, 4, kw_only=5, extra='x')}")

    try:
        demo(pos_only=1, standard=2, kw_only=3)
    except TypeError as exc:
        print(f"  positional-only enforced: {exc}")

    print(f"  signature: {inspect.signature(demo)}")

    # Keyword-only flags make call sites self-documenting.
    def resize(image: str, *, upscale: bool = False) -> str:
        return f"{image}{'+up' if upscale else ''}"

    print(f"  {resize('img', upscale=True)=}   (resize('img', True) is a TypeError)")


def mutable_defaults() -> None:
    print("\n== mutable default arguments ==")

    def bad(item, target=[]):
        target.append(item)
        return target

    print(f"  bad(1) -> {bad(1)}")
    print(f"  bad(2) -> {bad(2)}   <-- same list!")
    print(f"  proof: bad.__defaults__ = {bad.__defaults__}")

    def good(item, target=None):
        if target is None:
            target = []
        target.append(item)
        return target

    print(f"  good(1) -> {good(1)}, good(2) -> {good(2)}")

    # When None is a legal value you need a private sentinel.
    _MISSING = object()

    def fetch(key, default=_MISSING):
        store = {"a": None}
        if key in store:
            return store[key]
        if default is _MISSING:
            raise KeyError(key)
        return default

    print(f"  sentinel lets None be a real value: {fetch('a')=}, {fetch('z', None)=}")


def closures_and_late_binding() -> None:
    print("\n== closures ==")
    fns = [lambda: i for i in range(3)]
    print(f"  late binding bites: {[f() for f in fns]}")

    fixed_default = [lambda i=i: i for i in range(3)]
    fixed_partial = [functools.partial(lambda i: i, i) for i in range(3)]
    print(f"  bound via default: {[f() for f in fixed_default]}")
    print(f"  bound via partial: {[f() for f in fixed_partial]}")

    def make_counter(start: int = 0):
        count = start

        def increment(step: int = 1) -> int:
            nonlocal count  # without this, `count = ...` would create a LOCAL
            count += step
            return count

        return increment

    counter = make_counter(10)
    print(f"  closure state: {counter()=} {counter(5)=}")
    print(f"  free variables: {counter.__code__.co_freevars}")
    print(f"  cell contents:  {counter.__closure__[0].cell_contents}")


def functools_tour() -> None:
    print("\n== functools ==")

    @functools.cache
    def fib(n: int) -> int:
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    t0 = time.perf_counter()
    value = fib(300)
    print(f"  fib(300) = {str(value)[:20]}... in {(time.perf_counter() - t0) * 1e6:.0f} us")
    print(f"  {fib.cache_info()}")

    add = functools.partial(lambda a, b: a + b, 10)
    print(f"  partial: {add(5)=}")

    class Report:
        def __init__(self, rows: list[int]) -> None:
            self.rows = rows

        @functools.cached_property
        def total(self) -> int:
            print("    (computing total — you'll see this once)")
            return sum(self.rows)

    r = Report([1, 2, 3])
    print(f"  cached_property: {r.total=} {r.total=}")
    print(f"  it lives in the instance dict now: {'total' in r.__dict__}")

    @functools.total_ordering
    class Version:
        def __init__(self, parts: tuple[int, ...]) -> None:
            self.parts = parts

        def __eq__(self, other: object) -> bool:
            return isinstance(other, Version) and self.parts == other.parts

        def __lt__(self, other: Version) -> bool:
            return self.parts < other.parts

        def __repr__(self) -> str:
            return f"v{'.'.join(map(str, self.parts))}"

    print(f"  total_ordering gives >= for free: {Version((1, 2)) >= Version((1, 1))}")


def decorators() -> None:
    print("\n== decorators ==")

    def logged(func):
        @functools.wraps(func)  # keeps __name__, __doc__, __wrapped__
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            print(f"    {func.__name__}{args} -> {result!r}")
            return result

        return wrapper

    @logged
    def double(n: int) -> int:
        """Double a number."""
        return n * 2

    double(21)
    print(f"  metadata preserved: {double.__name__=} {double.__doc__=}")
    print(f"  original reachable: {double.__wrapped__.__name__=}")

    def repeat(times: int):  # decorator factory: three nested levels
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return [func(*args, **kwargs) for _ in range(times)]

            return wrapper

        return decorator

    @repeat(3)
    def roll() -> str:
        return "x"

    print(f"  parameterised decorator: {roll()}")

    # Stacking is bottom-up: shout(exclaim(f))
    def shout(f):
        return lambda: f().upper()

    def exclaim(f):
        return lambda: f() + "!"

    @shout
    @exclaim
    def greet() -> str:
        return "hi"

    print(f"  @shout over @exclaim -> {greet()}")


if __name__ == "__main__":
    print(INTRO)
    parameter_grammar()
    mutable_defaults()
    closures_and_late_binding()
    functools_tour()
    decorators()
