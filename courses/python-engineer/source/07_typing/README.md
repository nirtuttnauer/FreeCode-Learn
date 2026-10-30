# 07 — Typing and static analysis

Type hints are not enforced at runtime. They exist for **mypy**, your **editor**, and the
next person reading the code. On a codebase of any size they pay for themselves within a
week.

From here on, run `make typecheck` as often as `make test`.

## In plain English

Python doesn't care what type things are. You can pass a string where the author obviously
meant a number, and Python will cheerfully try it and blow up somewhere else entirely, ten
minutes later, in a completely different file.

**Type hints** are notes you write in the code — `def add(a: int, b: int) -> int` — saying
what you actually meant. Python itself still ignores them completely at runtime. But a tool
called **mypy** reads them and tells you, before you ever run the program, "line 84 passes a
string here, and that's going to break."

It's a spell-checker for your code's plumbing. On a small script it's mild convenience. On a
big codebase it's the difference between refactoring confidently and refactoring by prayer.

The most valuable idea in here is **`Protocol`**: instead of saying "I need a Postgres
database", you say "I need something that has a `save` method and a `get` method". Anything
with the right shape fits — including a simple fake you write for your tests. That one idea
reappears in modules 14, 15, and every project.

**Watch out for:** hints are checked by mypy, not by Python. If you need actual runtime
enforcement on untrusted data, that's pydantic (module 15) — a different tool for a
different job.

## 1. Modern syntax (3.10+/3.12+)

```python
def f(a: int, b: str | None = None) -> list[dict[str, int]]: ...
```

- Builtin generics: `list[int]`, `dict[str, int]`, `tuple[int, ...]`, `set[str]`.
  `typing.List` etc. are deprecated.
- `X | None` instead of `Optional[X]`; `A | B` instead of `Union[A, B]`.
- `from __future__ import annotations` makes all annotations lazy strings — avoids most
  forward-reference and circular-import pain.
- Prefer **abstract** parameter types and **concrete** return types:
  `def f(items: Iterable[int]) -> list[int]` — accept anything, promise something specific.

## 2. Generics

3.12 syntax (clean, no `TypeVar` import):

```python
def first[T](items: Sequence[T]) -> T: ...

class Stack[T]:
    def push(self, item: T) -> None: ...
    def pop(self) -> T: ...
```

Pre-3.12 / library-compatible syntax:

```python
T = TypeVar("T")
class Stack(Generic[T]): ...
```

Bounded and constrained:

```python
NumT = TypeVar("NumT", bound=float)          # anything float-compatible
StrOrBytes = TypeVar("StrOrBytes", str, bytes)   # exactly one of these
```

**Variance** in one line: a `list[Dog]` is *not* a `list[Animal]` (you could append a Cat),
but a `Sequence[Dog]` *is* a `Sequence[Animal]` (read-only). This is why your parameters
should be `Sequence`/`Iterable`/`Mapping`, not `list`/`dict`.

## 3. `Protocol` — structural typing

Nominal typing asks "does it inherit from X?". Structural asks "does it have the right
shape?". Protocols give you Go-style interfaces with zero coupling:

```python
class SupportsClose(Protocol):
    def close(self) -> None: ...

def cleanup(items: Iterable[SupportsClose]) -> None:
    for item in items:
        item.close()
```

Any object with `close()` satisfies this — no registration, no base class, and it works on
third-party types you don't control. Add `@runtime_checkable` for `isinstance` support
(it only checks *method names*, not signatures).

This is the backbone of dependency inversion in Python (module 14).

## 4. The vocabulary you'll actually use

| Feature | Use |
|---|---|
| `TypedDict` | dict with a fixed key schema — JSON payloads, config |
| `NamedTuple` | typed immutable record |
| `Literal["a", "b"]` | an enum-ish set of allowed values |
| `Final` | this name is never reassigned |
| `ClassVar[T]` | class attribute, not an instance field |
| `Annotated[int, Ge(0)]` | attach metadata (FastAPI/pydantic build on this) |
| `TypeAlias` / `type X = ...` | name a complex type (3.12: `type Json = ...`) |
| `Self` | methods returning their own type — fluent APIs, `__enter__` |
| `Never` / `NoReturn` | functions that always raise or never return |
| `Any` | the escape hatch; every `Any` is a hole in your type coverage |
| `cast(T, x)` | "trust me" — no runtime effect |
| `TYPE_CHECKING` | import only for type checking, avoids circular imports |
| `ParamSpec` + `Concatenate` | decorators that preserve the wrapped signature |
| `TypeGuard` / `TypeIs` | narrowing functions (`def is_str_list(v) -> TypeIs[list[str]]`) |
| `overload` | different return types for different argument shapes |

## 5. Decorators that don't destroy types

```python
P = ParamSpec("P")
R = TypeVar("R")

def timed(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        ...
        return func(*args, **kwargs)
    return wrapper
```

Without `ParamSpec` the decorated function collapses to `(*args: Any) -> Any` and you lose
checking at every call site.

## 6. mypy in practice

```bash
mypy .                       # uses [tool.mypy] in pyproject.toml
mypy --strict path/          # the setting you actually want on new code
```

Useful settings: `disallow_untyped_defs`, `warn_return_any`, `no_implicit_optional`,
`warn_unused_ignores`, `strict_equality`. Silence a specific line with
`# type: ignore[error-code]` — always with the code, never bare.

Adopting types in an existing codebase: enable `--strict` per-module via
`[[tool.mypy.overrides]]`, starting with new files and the core domain model.

**Alternatives**: `pyright`/Pylance (faster, better inference, what VS Code uses),
`ty` and `pyrefly` (newer Rust-based checkers). mypy is still the reference.

## 7. Runtime validation is a *different* problem

Type hints don't validate anything at runtime. For untrusted input (HTTP bodies, config
files) use **pydantic**, which reads the same annotations and enforces them — module 15
builds a FastAPI service on exactly that.

## Exercises

`exercises_07.py`, then `pytest 07_typing` **and** `make typecheck` — the tests check
behaviour, mypy checks the annotations. Both must pass.

## Further reading

- [typing docs](https://docs.python.org/3/library/typing.html)
- [mypy cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [PEP 544 — Protocols](https://peps.python.org/pep-0544/)
