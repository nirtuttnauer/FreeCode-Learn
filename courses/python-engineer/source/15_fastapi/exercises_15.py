"""Module 15 exercises.  pytest 15_fastapi

Build a small task API. The tests drive it with `TestClient`, so nothing listens on a
port and the whole suite runs in well under a second.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel


class TaskIn(BaseModel):
    """The request body for creating a task.

    - `title: str` — required, 1..200 characters AFTER stripping whitespace. A title of
      only spaces must be rejected (strip in a `field_validator`, then let the length
      constraint do the work — order matters; use `mode="before"` if needed).
    - `priority: int = 1` — between 1 and 5 inclusive.
    - `tags: list[str] = []` — use `Field(default_factory=list)`, never a bare `[]`.
    - Unknown keys are REJECTED (`model_config = ConfigDict(extra="forbid")`).
    """


class TaskOut(BaseModel):
    """The response body: `id: int`, `title: str`, `priority: int`, `done: bool`.

    Deliberately does NOT include the repository's internal fields — the point of a
    separate output model is that internal data cannot leak by accident.
    """


class TaskNotFound(LookupError):
    """Domain error. `str(exc)` == "task 42 not found"; carries `.task_id`."""

    def __init__(self, task_id: int) -> None:
        raise NotImplementedError


class InMemoryTaskRepo:
    """Storage. Rows are plain dicts with keys: id, title, priority, tags, done, internal_note.

    - `.add(data: TaskIn) -> dict` assigns sequential ids starting at 1, sets
      `done=False` and `internal_note="internal"`, stores and returns the row.
    - `.get(task_id) -> dict | None`.
    - `.list() -> list[dict]` in insertion order (a copy).
    - `.complete(task_id) -> dict` sets done=True and returns the row; unknown id raises
      TaskNotFound. Completing twice is fine.
    - `.delete(task_id) -> None`; unknown id raises TaskNotFound.
    """

    def __init__(self) -> None:
        raise NotImplementedError


def get_repo() -> InMemoryTaskRepo:
    """The dependency the handlers ask for. Tests override it — so no handler may ever
    construct a repository itself."""
    raise NotImplementedError


def create_app(repo: InMemoryTaskRepo | None = None) -> FastAPI:
    """App factory. Returns a FastAPI app with these routes:

    | Method | Path                  | Behaviour |
    |--------|-----------------------|-----------|
    | GET    | /health               | 200 `{"status": "ok"}` |
    | POST   | /tasks                | 201, body TaskIn -> TaskOut |
    | GET    | /tasks                | 200 list[TaskOut]; query params `done: bool \\| None = None` and `min_priority: int = 1` (1..5, validated) |
    | GET    | /tasks/{task_id}      | 200 TaskOut, 404 when missing |
    | POST   | /tasks/{task_id}/complete | 200 TaskOut, 404 when missing |
    | DELETE | /tasks/{task_id}      | 204 with no body, 404 when missing |

    Requirements:
    - Every handler takes the repository via `Annotated[InMemoryTaskRepo, Depends(get_repo)]`.
    - When `repo` is passed to the factory, wire it in with
      `app.dependency_overrides[get_repo] = lambda: repo` — that is how the tests inject
      an isolated repository per test.
    - Register an exception handler mapping `TaskNotFound` to
      `404 {"detail": "task 42 not found"}`. Handlers must raise the DOMAIN error, not
      `HTTPException` — the HTTP status lives at the edge, nowhere else (module 14).
    - Use `response_model=` so `internal_note` never reaches a client.
    - Invalid bodies and query params return 422 automatically. Don't write that code.
    - Set `title="Tasks API"` and `version="1.0.0"` on the app.
    """
    raise NotImplementedError


def summarise_errors(exc: Any) -> list[str]:
    """Turn a pydantic `ValidationError` into readable "field: message" strings.

    >>> summarise_errors(err)      # doctest: +SKIP
    ['title: String should have at least 1 character', 'priority: Input should be ...']

    - Use `exc.errors()`; each entry has `loc` (a tuple) and `msg`.
    - Join a nested `loc` with "." — `("body", "title")` becomes "body.title".
    - Keep the order pydantic gives you.
    """
    raise NotImplementedError
