"""Module 15 — runnable lesson. `python 15_fastapi/lesson_15.py`

Runs the whole demo in-process with TestClient — no server, no port, no network.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

INTRO = """FastAPI reads your type hints and does the boring bits: checking incoming JSON, returning
helpful errors, generating docs. You write the SHAPE of your data; the framework writes the
plumbing. Everything below runs in-process — no server, no port."""


# --- pydantic ---------------------------------------------------------------------------
class TaskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown keys are an error, not ignored

    title: str = Field(min_length=1, max_length=200)
    priority: int = Field(default=1, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()


class TaskOut(BaseModel):
    id: int
    title: str
    priority: int
    done: bool


def pydantic_basics() -> None:
    print("\n== pydantic v2: hints become RUNTIME validation ==")
    task = TaskIn.model_validate({"title": "  write tests  ", "priority": "3"})
    print(f"  coerced and stripped: {task}")
    print(f"  model_dump(): {task.model_dump()}")

    try:
        TaskIn.model_validate({"title": "", "priority": 99, "nope": 1})
    except ValidationError as exc:
        print(f"  {len(exc.errors())} structured errors:")
        for error in exc.errors():
            print(f"    {error['loc']}: {error['msg']}")


# --- the app ----------------------------------------------------------------------------
class InMemoryTasks:
    def __init__(self) -> None:
        self._rows: dict[int, dict] = {}
        self._next = 1

    def add(self, data: TaskIn) -> dict:
        row = {"id": self._next, "done": False, "secret_note": "never leaves the server",
               **data.model_dump()}
        self._rows[self._next] = row
        self._next += 1
        return row

    def get(self, task_id: int) -> dict | None:
        return self._rows.get(task_id)

    def list(self) -> list[dict]:
        return list(self._rows.values())


class TaskNotFound(LookupError):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"task {task_id} not found")


REPO = InMemoryTasks()


def get_repo() -> InMemoryTasks:
    """The composition root — overridden in tests, never called from a handler directly."""
    return REPO


RepoDep = Annotated[InMemoryTasks, Depends(get_repo)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("  [lifespan] startup: open pools here")
    yield
    print("  [lifespan] shutdown: close them here")


app = FastAPI(title="Tasks", lifespan=lifespan)


@app.exception_handler(TaskNotFound)
async def handle_not_found(request, exc: TaskNotFound) -> JSONResponse:
    # Domain errors are mapped to HTTP at the EDGE; the domain knows no status codes.
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskIn, repo: RepoDep) -> dict:
    return repo.add(payload)


@app.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, repo: RepoDep) -> dict:
    row = repo.get(task_id)
    if row is None:
        raise TaskNotFound(task_id)
    return row


@app.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    repo: RepoDep, min_priority: Annotated[int, Query(ge=1, le=5)] = 1
) -> list[dict]:
    return [t for t in repo.list() if t["priority"] >= min_priority]


@app.get("/boom")
async def boom() -> dict:
    raise HTTPException(status.HTTP_418_IM_A_TEAPOT, "framework-level error")


def api_demo() -> None:
    print("\n== the API, driven in-process ==")
    with TestClient(app) as client:  # `with` runs the lifespan events
        created = client.post("/tasks", json={"title": "ship it", "priority": 4})
        print(f"  POST /tasks -> {created.status_code} {created.json()}")
        print("  note: 'secret_note' was dropped by response_model. That's your leak guard.")

        print(f"  GET /tasks/1 -> {client.get('/tasks/1').json()}")
        print(f"  GET /tasks/99 -> {client.get('/tasks/99').status_code} "
              f"{client.get('/tasks/99').json()}")

        client.post("/tasks", json={"title": "low", "priority": 1})
        print(f"  GET /tasks?min_priority=4 -> {len(client.get('/tasks?min_priority=4').json())} row(s)")

        bad = client.post("/tasks", json={"title": "", "priority": 9})
        print(f"  invalid body -> {bad.status_code} with {len(bad.json()['detail'])} field errors")

        print(f"  GET /boom -> {client.get('/boom').status_code}")

        schema = client.get("/openapi.json").json()
        print(f"  OpenAPI generated from the type hints: {sorted(schema['paths'])}")


def dependency_overrides() -> None:
    print("\n== overriding dependencies in tests ==")
    isolated = InMemoryTasks()
    app.dependency_overrides[get_repo] = lambda: isolated
    with TestClient(app) as client:
        client.post("/tasks", json={"title": "only in the fake repo"})
        print(f"  fake repo has {len(isolated.list())} row(s); the real one is untouched")
    app.dependency_overrides.clear()
    print("  this is why handlers must never build their own dependencies")


if __name__ == "__main__":
    print(INTRO)
    pydantic_basics()
    api_demo()
    dependency_overrides()
