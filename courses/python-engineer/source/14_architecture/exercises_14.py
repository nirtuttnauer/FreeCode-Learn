"""Module 14 exercises.  pytest 14_architecture

Build the skeleton of a real application: a domain entity, a repository Protocol with two
implementations, a service that depends only on the Protocol, an event bus, and a
singledispatch renderer. Fully annotated — mypy runs strict here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class Task:
    """A domain entity: pure data + behaviour, no I/O, no framework imports.

    Build it as a FROZEN, SLOTTED dataclass with fields
    `id: int`, `title: str`, `done: bool = False`, `tags: tuple[str, ...] = ()`.

    - `__post_init__` rejects a blank title with ValueError("title is required").
    - `.complete()` returns a NEW Task with done=True (immutable update — do not mutate).
    - `.with_tag(tag)` returns a new Task with the tag appended, ignoring duplicates.
    - Frozen + hashable, so tasks can live in sets.
    """

    def __init__(self, id: int, title: str, done: bool = False, tags: tuple[str, ...] = ()) -> None:
        raise NotImplementedError


class TaskRepository(Protocol):
    """The port. Declared next to its CONSUMER (the service), not its implementations.

    Leave every body as `...`. This is a shape, not a base class — implementations must
    NOT inherit from it.
    """

    def get(self, task_id: int) -> Task | None: ...
    def save(self, task: Task) -> None: ...
    def delete(self, task_id: int) -> None: ...
    def list_all(self) -> list[Task]: ...


class InMemoryTasks:
    """A real in-memory implementation — the one your tests use instead of a mock.

    - `InMemoryTasks([Task(...), ...])`, empty by default.
    - `get` returns None for an unknown id.
    - `delete` on an unknown id raises KeyError.
    - `list_all` returns tasks in insertion order, and mutating the returned list must
      not affect the repository.
    - Must NOT subclass TaskRepository — structural typing is the point.
    """

    def __init__(self, tasks: list[Task] | None = None) -> None:
        raise NotImplementedError


class TaskService:
    """The use-case layer. Depends on the Protocol and an injected clock — nothing else.

    - `TaskService(repo, clock=time.time, bus=None)`.
    - `.create(title, tags=())` assigns the next id (max existing + 1, starting at 1),
      saves, publishes a `TaskCreated` event if a bus was given, and returns the Task.
    - `.complete(task_id)` loads, completes, saves, publishes `TaskCompleted`, returns
      the updated task. Unknown id raises `TaskNotFound(task_id)` — a domain exception
      you define, subclassing LookupError, whose str() is "task 42 not found".
    - Completing an already-done task is a no-op that still returns the task and
      publishes NOTHING.
    - `.stats()` returns `{"total": n, "done": n, "open": n}`.
    """

    def __init__(self, repo: TaskRepository, clock: Callable[[], float] | None = None,
                 bus: Any = None) -> None:
        raise NotImplementedError


class EventBus:
    """Synchronous pub/sub, dispatching on the event's exact type.

    - `.subscribe(EventType, handler)` — several handlers per type, called in
      subscription order.
    - `.publish(event)` calls every handler registered for `type(event)`.
    - Publishing an event with no subscribers is a silent no-op.
    - A handler that raises must NOT stop the remaining handlers; collect the failures
      and raise `ExceptionGroup("handler failures", [...])` after all have run.
    - `.unsubscribe(EventType, handler)` removes one handler; unknown pairs raise
      ValueError.
    - Subclass matching is NOT required — dispatch on the exact type.
    """

    def __init__(self) -> None:
        raise NotImplementedError


def render(node: Any) -> str:
    """A `functools.singledispatch` renderer for a tiny document tree.

    Define these node types as dataclasses in this module, then register a renderer
    for each:

        Text(value: str)          -> the value, unchanged
        Bold(child: Any)          -> "**" + render(child) + "**"
        Italic(child: Any)        -> "_" + render(child) + "_"
        Paragraph(children: list) -> children rendered and joined with a single space
        Document(children: list)  -> paragraphs joined with "\\n\\n"

    - The base implementation raises TypeError("no renderer for <TypeName>").
    - `str` must render as itself (register a handler for the builtin type — it makes
      `Bold("hi")` work without wrapping in Text).
    - Third parties must be able to `@render.register` their own types afterwards; the
      tests do exactly that.
    """
    raise NotImplementedError
