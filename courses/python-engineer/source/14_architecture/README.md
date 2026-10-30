# 14 — Architecture: dependency inversion, patterns, plugin systems

Design patterns in Python are mostly *smaller* than in Java, because first-class functions
and duck typing dissolve half of them. Strategy is a function. Command is a callable.
Iterator is built into the language. What's left is worth knowing properly.

## In plain English

This module answers: how do you organise a program so that it's still changeable in a year?

The single most useful idea: **depend on shapes, not brands.**

Bad version: your order-processing code imports Postgres directly. Now it *is* a
Postgres program. Want to test it? Install Postgres. Want to switch database? Rewrite
everything.

Good version: your order code says "I need something that can `save` an order and `get` an
order". It doesn't know or care what that something is. In production you hand it Postgres;
in tests you hand it a dictionary. Same code, no changes, and your tests run instantly with
no database at all.

That's it. That's dependency inversion, and it's most of what "good architecture" means in
practice.

The other half of the module is the design patterns that survive the trip into Python.
Many of them collapse into something much smaller here — the Strategy pattern is "pass a
function", and a dictionary of functions replaces most long `if/elif` chains.

**Watch out for:** building the object graph in one place (`main()`), at the edge of your
program. Everything below that should be *handed* what it needs, not go fetch it. That's
the rule that makes the whole thing work.

## 1. Dependency inversion with `Protocol`

The single most valuable architectural idea in this course:

```python
class UserRepository(Protocol):
    def get(self, user_id: int) -> User | None: ...
    def save(self, user: User) -> None: ...

class PostgresUsers:       # production
    def get(self, user_id): ...
class InMemoryUsers:       # tests — a real implementation, not a mock
    def __init__(self): self._rows: dict[int, User] = {}

class UserService:
    def __init__(self, repo: UserRepository) -> None:   # depends on the SHAPE
        self.repo = repo
```

- The high-level policy (`UserService`) doesn't import the low-level detail.
- The Protocol lives with the **consumer**, not the implementation — that's what makes
  the dependency point inwards.
- Neither implementation inherits anything. No registration, no ABC, no coupling.
- Tests construct `UserService(InMemoryUsers())` — no patching, no mock library.

`ABC` is the alternative when you *want* nominal typing: shared implementation in the base,
`@abstractmethod` to force overrides, and `isinstance` that means something. Use `ABC` for
your own hierarchies, `Protocol` for boundaries you don't own.

## 2. Wiring: composition root

Build the object graph **once**, at the edge of the application (`main()`, a FastAPI
dependency, a CLI entry point). Everything below that takes its dependencies as
constructor arguments.

```python
def main() -> int:
    settings = Settings.from_env()
    repo = PostgresUsers(connect(settings.dsn))
    service = UserService(repo, clock=time.monotonic)
    return run_cli(service)
```

You almost never need a DI *framework* in Python. Constructor arguments plus one
composition root covers it. Globals and module-level singletons are the thing you're
avoiding — they make every test order-dependent.

## 3. The patterns that survive translation

| Pattern | Pythonic form |
|---|---|
| Strategy | pass a function, or a dict of functions |
| Command | a callable, or a small frozen dataclass + a handler |
| Template method | a base class with hooks — or just a function taking callbacks |
| Observer / pub-sub | an event bus: `dict[type, list[handler]]` |
| Adapter | a thin wrapper class satisfying your Protocol |
| Facade | a module with a small public `__all__` |
| Factory | a `@classmethod` alternative constructor, or a registry dict |
| Visitor | `functools.singledispatch` |
| Singleton | a module-level object (modules are already singletons) |
| Repository | a Protocol + one implementation per backing store |
| Unit of work | a context manager wrapping a transaction |

**Dispatch tables beat `if/elif` chains.** A dict from key to handler is open for
extension, testable per-entry, and doesn't grow a 40-branch function.

```python
HANDLERS: dict[str, Callable[[Event], None]] = {"created": on_created, ...}
HANDLERS[event.type](event)
```

## 4. `singledispatch` — real polymorphism on functions

```python
@functools.singledispatch
def render(node) -> str:
    raise TypeError(f"no renderer for {type(node).__name__}")

@render.register
def _(node: Text) -> str: return node.value

@render.register
def _(node: Bold) -> str: return f"**{render(node.child)}**"
```

The dispatch is on the **first argument's type**, resolved via the MRO, and third parties
can register handlers for their own types without touching your code. `singledispatchmethod`
does the same inside a class.

## 5. Errors as values vs exceptions

Exceptions for *exceptional* things. For expected, recoverable outcomes — validation
failures, a lookup miss, a business rule rejection — returning a `Result` (module 07) or a
domain object often reads better and can't be accidentally swallowed by a broad `except`.
Don't dogmatise: use exceptions at boundaries, values inside a pipeline.

## 6. Layering that actually holds

```
cli / http (framework code)      <- thin: parse input, call a use case, format output
    ↓
services / use cases             <- orchestration, transactions, no framework imports
    ↓
domain (entities, value objects) <- pure logic, no I/O, trivially testable
    ↑
adapters (db, http clients, fs)  <- implement the Protocols the layers above declare
```

The rule that enforces it: **domain code imports nothing from the outer layers.** If your
`User` entity imports SQLAlchemy or FastAPI, the layering is already gone.

## 7. Configuration

- Read the environment **once**, at the composition root, into a frozen settings object.
- Validate at startup and fail loudly — not on the first request at 3am.
- `pydantic-settings` for typed env parsing; `os.environ` + a dataclass is fine too.
- Never reach into `os.environ` from deep inside the domain.

## 8. Plugin systems

Three tiers, in increasing order of openness:
1. A **registry dict** in your package (module 12's `__init_subclass__`).
2. **Entry points** in `pyproject.toml` — third parties install a package and it appears
   (module 08).
3. Explicit **import paths** in config, resolved with `load_object("pkg.mod:Class")`.

## Exercises

`exercises_14.py`, then `pytest 14_architecture`. You'll build a repository + service pair
against a Protocol, an event bus, a `singledispatch` renderer, and a small pipeline —
i.e. the skeleton of every application you'll write after this course.

## Further reading

- *Architecture Patterns with Python* (Percival & Gregory) — free online, Python-native DDD
- [PEP 544 — Protocols](https://peps.python.org/pep-0544/)
