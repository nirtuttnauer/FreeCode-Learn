"""Milestone 1: jobs, states, and the task registry.

Write the state machine down as DATA (a dict of allowed transitions) rather than as
scattered `if` statements. It's the difference between a bug you can see and one you find
in production at 4am.
"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class ForgeError(Exception):
    """Base for everything forge raises."""


class InvalidTransition(ForgeError):
    def __init__(self, current: "JobState", target: "JobState") -> None:
        super().__init__(f"cannot move a job from {current.value} to {target.value}")
        self.current = current
        self.target = target


class NotSerialisable(ForgeError):
    """An argument couldn't be JSON-encoded. Raised at ENQUEUE time, never at run time."""


class JobState(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD = "dead"
    CANCELLED = "cancelled"


# TODO: fill this in, then make `Job.transition_to` consult it.
# pending   -> running, cancelled
# running   -> succeeded, failed, retrying, cancelled
# retrying  -> running, dead, cancelled
# failed    -> retrying, dead
# terminal  -> nothing
ALLOWED_TRANSITIONS: dict[JobState, frozenset[JobState]] = {}


@dataclass
class Job:
    id: str
    task_name: str
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # higher runs first
    eta: float | None = None  # monotonic-clock timestamp, None = now
    attempt: int = 0
    max_retries: int = 3
    state: JobState = JobState.PENDING
    result: Any = None
    error: str | None = None
    created_at: float = 0.0
    reserved_until: float | None = None  # the visibility timeout

    def transition_to(self, target: JobState) -> None:
        """Move state, raising `InvalidTransition` when the move isn't allowed."""
        raise NotImplementedError

    @property
    def is_terminal(self) -> bool:
        raise NotImplementedError

    def can_retry(self) -> bool:
        raise NotImplementedError

    def next_retry_delay(self, base: float = 1.0, cap: float = 300.0, jitter: float = 1.0) -> float:
        """`min(base * 2**attempt, cap) * jitter` — jitter injected, so tests are exact."""
        raise NotImplementedError

    def to_json(self) -> str:
        """Serialise for a durable broker. Round-trips through `from_json`."""
        raise NotImplementedError

    @classmethod
    def from_json(cls, raw: str) -> "Job":
        raise NotImplementedError


@dataclass
class TaskDefinition:
    name: str
    func: Callable[..., Any]
    max_retries: int = 3
    timeout: float | None = None
    rate_limit: str | None = None  # "10/s", "600/m"
    cpu_bound: bool = False
    is_async: bool = False


REGISTRY: dict[str, TaskDefinition] = {}


def task(
    func: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    max_retries: int = 3,
    timeout: float | None = None,
    rate_limit: str | None = None,
    cpu_bound: bool = False,
) -> Any:
    """Register a function as a task and attach `.delay` / `.apply_async`.

    - Bare (`@task`) and parameterised (`@task(max_retries=5)`) forms both work.
    - Duplicate names raise ValueError at import time.
    - `.delay(*args, **kwargs)` builds a Job and enqueues it on the configured broker.
    - `.apply_async(..., eta=, priority=, countdown=)` for scheduling.
    - Arguments are validated as JSON-serialisable NOW, raising `NotSerialisable` with
      the offending argument named. Discovering that in the worker is far too late.
    - The original function stays callable directly, for tests.
    """
    raise NotImplementedError
