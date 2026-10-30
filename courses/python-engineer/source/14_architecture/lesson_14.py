"""Module 14 — runnable lesson. `python 14_architecture/lesson_14.py`"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

INTRO = """Depend on SHAPES, not brands. Don't say "I need Postgres"; say "I need something that can
save and fetch a user". In production you hand it a database; in tests you hand it a
dictionary. Same code, no mocks, instant tests."""


# --- domain: pure, no I/O, no framework imports ----------------------------------------
@dataclass(frozen=True, slots=True)
class User:
    id: int
    email: str
    active: bool = True


class UserRepository(Protocol):
    """Declared next to its CONSUMER, so the dependency points inwards."""

    def get(self, user_id: int) -> User | None: ...
    def save(self, user: User) -> None: ...
    def all(self) -> list[User]: ...


class UserService:
    def __init__(self, repo: UserRepository, clock: Callable[[], float] = time.time) -> None:
        self.repo = repo  # a shape, not a class
        self.clock = clock

    def deactivate(self, user_id: int) -> User:
        user = self.repo.get(user_id)
        if user is None:
            raise LookupError(f"no user {user_id}")
        updated = User(id=user.id, email=user.email, active=False)
        self.repo.save(updated)
        return updated


# --- adapters: two real implementations, neither inheriting anything -------------------
class InMemoryUsers:
    def __init__(self, users: list[User] | None = None) -> None:
        self._rows = {u.id: u for u in (users or [])}

    def get(self, user_id: int) -> User | None:
        return self._rows.get(user_id)

    def save(self, user: User) -> None:
        self._rows[user.id] = user

    def all(self) -> list[User]:
        return list(self._rows.values())


class LoggingUsers:
    """An adapter that decorates another repository — composition, not inheritance."""

    def __init__(self, inner: UserRepository, log: list[str]) -> None:
        self.inner = inner
        self.log = log

    def get(self, user_id: int) -> User | None:
        self.log.append(f"get({user_id})")
        return self.inner.get(user_id)

    def save(self, user: User) -> None:
        self.log.append(f"save({user.id})")
        self.inner.save(user)

    def all(self) -> list[User]:
        return self.inner.all()


def dependency_inversion() -> None:
    print("\n== dependency inversion ==")
    repo = InMemoryUsers([User(1, "a@b.c")])
    service = UserService(repo)
    print(f"  {service.deactivate(1)}")
    print("  the test above used NO mock library and NO patching")

    log: list[str] = []
    decorated = UserService(LoggingUsers(repo, log))
    decorated.deactivate(1)
    print(f"  a decorating adapter satisfies the same Protocol: {log}")

    try:
        service.deactivate(999)
    except LookupError as exc:
        print(f"  domain error: {exc}")


def dispatch_tables() -> None:
    print("\n== dispatch table instead of if/elif ==")

    def on_created(event: dict) -> str:
        return f"created {event['id']}"

    def on_deleted(event: dict) -> str:
        return f"deleted {event['id']}"

    HANDLERS: dict[str, Callable[[dict], str]] = {
        "created": on_created,
        "deleted": on_deleted,
    }

    for event in ({"type": "created", "id": 1}, {"type": "deleted", "id": 2}):
        handler = HANDLERS.get(event["type"])
        print(f"  {handler(event) if handler else 'unhandled'}")
    print("  open for extension: register a new key, touch no existing code")


def single_dispatch() -> None:
    print("\n== functools.singledispatch (the Visitor pattern, built in) ==")

    @dataclass
    class Text:
        value: str

    @dataclass
    class Bold:
        child: object

    @dataclass
    class Document:
        children: list

    @functools.singledispatch
    def render(node: object) -> str:
        raise TypeError(f"no renderer for {type(node).__name__}")

    # NOTE: `@render.register` normally reads the annotation — but these classes are
    # defined inside a function, and `from __future__ import annotations` makes that
    # annotation a mere string that singledispatch cannot resolve. Pass the class instead.
    @render.register(Text)
    def _(node) -> str:
        return node.value

    @render.register(Bold)
    def _(node) -> str:
        return f"**{render(node.child)}**"

    @render.register(Document)
    def _(node) -> str:
        return " ".join(render(c) for c in node.children)

    doc = Document([Text("hello"), Bold(Text("world"))])
    print(f"  {render(doc)}")
    print(f"  registered types: {[t.__name__ for t in render.registry if t is not object]}")
    try:
        render(42)
    except TypeError as exc:
        print(f"  unregistered: {exc}")


def event_bus() -> None:
    print("\n== event bus (observer) ==")

    @dataclass
    class UserCreated:
        user_id: int

    @dataclass
    class UserDeleted:
        user_id: int

    @dataclass
    class Bus:
        handlers: dict[type, list[Callable]] = field(default_factory=dict)

        def subscribe(self, event_type: type, handler: Callable) -> None:
            self.handlers.setdefault(event_type, []).append(handler)

        def publish(self, event: object) -> None:
            for handler in self.handlers.get(type(event), []):
                handler(event)

    bus = Bus()
    bus.subscribe(UserCreated, lambda e: print(f"    email welcome to {e.user_id}"))
    bus.subscribe(UserCreated, lambda e: print(f"    audit log: created {e.user_id}"))
    bus.subscribe(UserDeleted, lambda e: print(f"    audit log: deleted {e.user_id}"))
    bus.publish(UserCreated(1))
    bus.publish(UserDeleted(2))
    print("  publishers know nothing about subscribers — that's the decoupling")


def composition_root() -> None:
    print("\n== composition root ==")

    @dataclass(frozen=True, slots=True)
    class Settings:
        dsn: str
        retries: int = 3

        @classmethod
        def from_env(cls, env: dict[str, str]) -> Settings:
            try:
                return cls(dsn=env["DSN"], retries=int(env.get("RETRIES", 3)))
            except KeyError as exc:
                raise SystemExit(f"missing required setting: {exc}") from exc

    settings = Settings.from_env({"DSN": "postgres://localhost", "RETRIES": "5"})
    repo = InMemoryUsers([User(1, "a@b.c")])
    service = UserService(repo)
    print(f"  built once, at the edge: {settings}")
    print(f"  everything below takes its dependencies as arguments: {type(service.repo).__name__}")
    print("  validate config at STARTUP, not on the first request at 3am")


if __name__ == "__main__":
    print(INTRO)
    dependency_inversion()
    dispatch_tables()
    single_dispatch()
    event_bus()
    composition_root()
