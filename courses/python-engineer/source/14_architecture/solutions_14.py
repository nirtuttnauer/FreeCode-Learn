"""Module 14 — reference solutions."""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any, Protocol


# --- domain -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Task:
    id: int
    title: str
    done: bool = False
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title is required")

    def complete(self) -> Task:
        return replace(self, done=True)  # immutable update

    def with_tag(self, tag: str) -> Task:
        if tag in self.tags:
            return self
        return replace(self, tags=(*self.tags, tag))


class TaskNotFound(LookupError):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"task {task_id} not found")
        self.task_id = task_id


@dataclass(frozen=True, slots=True)
class TaskCreated:
    task_id: int


@dataclass(frozen=True, slots=True)
class TaskCompleted:
    task_id: int


# --- port -------------------------------------------------------------------------------
class TaskRepository(Protocol):
    def get(self, task_id: int) -> Task | None: ...
    def save(self, task: Task) -> None: ...
    def delete(self, task_id: int) -> None: ...
    def list_all(self) -> list[Task]: ...


# --- adapter ----------------------------------------------------------------------------
class InMemoryTasks:  # deliberately NOT inheriting TaskRepository
    def __init__(self, tasks: list[Task] | None = None) -> None:
        self._rows: dict[int, Task] = {t.id: t for t in (tasks or [])}

    def get(self, task_id: int) -> Task | None:
        return self._rows.get(task_id)

    def save(self, task: Task) -> None:
        self._rows[task.id] = task

    def delete(self, task_id: int) -> None:
        del self._rows[task_id]  # KeyError for unknown ids, as documented

    def list_all(self) -> list[Task]:
        return list(self._rows.values())  # a copy: callers can't mutate our state


# --- event bus --------------------------------------------------------------------------
class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: type, handler: Callable[[Any], None]) -> None:
        try:
            self._handlers[event_type].remove(handler)
        except (KeyError, ValueError):
            raise ValueError(f"{handler!r} is not subscribed to {event_type.__name__}") from None

    def publish(self, event: Any) -> None:
        errors: list[BaseException] = []
        for handler in list(self._handlers.get(type(event), [])):
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 — one bad subscriber must not block others
                errors.append(exc)
        if errors:
            raise ExceptionGroup("handler failures", errors)


# --- service ----------------------------------------------------------------------------
class TaskService:
    def __init__(
        self,
        repo: TaskRepository,
        clock: Callable[[], float] | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self.repo = repo
        self.clock = clock or time.time
        self.bus = bus

    def _publish(self, event: Any) -> None:
        if self.bus is not None:
            self.bus.publish(event)

    def create(self, title: str, tags: tuple[str, ...] = ()) -> Task:
        existing = self.repo.list_all()
        next_id = max((t.id for t in existing), default=0) + 1
        task = Task(id=next_id, title=title, tags=tags)
        self.repo.save(task)
        self._publish(TaskCreated(task.id))
        return task

    def complete(self, task_id: int) -> Task:
        task = self.repo.get(task_id)
        if task is None:
            raise TaskNotFound(task_id)
        if task.done:
            return task  # idempotent, and no event
        updated = task.complete()
        self.repo.save(updated)
        self._publish(TaskCompleted(task_id))
        return updated

    def stats(self) -> dict[str, int]:
        tasks = self.repo.list_all()
        done = sum(1 for t in tasks if t.done)
        return {"total": len(tasks), "done": done, "open": len(tasks) - done}


# --- rendering --------------------------------------------------------------------------
@dataclass(frozen=True)
class Text:
    value: str


@dataclass(frozen=True)
class Bold:
    child: Any


@dataclass(frozen=True)
class Italic:
    child: Any


@dataclass
class Paragraph:
    children: list[Any] = field(default_factory=list)


@dataclass
class Document:
    children: list[Any] = field(default_factory=list)


@functools.singledispatch
def render(node: Any) -> str:
    raise TypeError(f"no renderer for {type(node).__name__}")


@render.register
def _(node: str) -> str:
    return node


@render.register
def _(node: Text) -> str:
    return node.value


@render.register
def _(node: Bold) -> str:
    return f"**{render(node.child)}**"


@render.register
def _(node: Italic) -> str:
    return f"_{render(node.child)}_"


@render.register
def _(node: Paragraph) -> str:
    return " ".join(render(c) for c in node.children)


@render.register
def _(node: Document) -> str:
    return "\n\n".join(render(c) for c in node.children)
