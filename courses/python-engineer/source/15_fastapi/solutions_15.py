"""Module 15 — reference solutions."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    priority: int = Field(default=1, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: Any) -> Any:
        # mode="before" so stripping happens BEFORE the length constraint is applied.
        return value.strip() if isinstance(value, str) else value


class TaskOut(BaseModel):
    id: int
    title: str
    priority: int
    done: bool


class TaskNotFound(LookupError):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"task {task_id} not found")
        self.task_id = task_id


class InMemoryTaskRepo:
    def __init__(self) -> None:
        self._rows: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def add(self, data: TaskIn) -> dict[str, Any]:
        row = {
            "id": self._next_id,
            "done": False,
            "internal_note": "internal",
            **data.model_dump(),
        }
        self._rows[self._next_id] = row
        self._next_id += 1
        return row

    def get(self, task_id: int) -> dict[str, Any] | None:
        return self._rows.get(task_id)

    def list(self) -> list[dict[str, Any]]:
        return list(self._rows.values())

    def complete(self, task_id: int) -> dict[str, Any]:
        row = self._rows.get(task_id)
        if row is None:
            raise TaskNotFound(task_id)
        row["done"] = True
        return row

    def delete(self, task_id: int) -> None:
        if task_id not in self._rows:
            raise TaskNotFound(task_id)
        del self._rows[task_id]


_DEFAULT_REPO = InMemoryTaskRepo()


def get_repo() -> InMemoryTaskRepo:
    return _DEFAULT_REPO


RepoDep = Annotated[InMemoryTaskRepo, Depends(get_repo)]


def create_app(repo: InMemoryTaskRepo | None = None) -> FastAPI:
    app = FastAPI(title="Tasks API", version="1.0.0")

    if repo is not None:
        # The composition root: swap the dependency, never the handler code.
        app.dependency_overrides[get_repo] = lambda: repo

    @app.exception_handler(TaskNotFound)
    async def _not_found(request: Request, exc: TaskNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
    async def create_task(payload: TaskIn, repo: RepoDep) -> dict[str, Any]:
        return repo.add(payload)

    @app.get("/tasks", response_model=list[TaskOut])
    async def list_tasks(
        repo: RepoDep,
        done: bool | None = None,
        min_priority: Annotated[int, Query(ge=1, le=5)] = 1,
    ) -> list[dict[str, Any]]:
        rows = [r for r in repo.list() if r["priority"] >= min_priority]
        if done is not None:
            rows = [r for r in rows if r["done"] is done]
        return rows

    @app.get("/tasks/{task_id}", response_model=TaskOut)
    async def get_task(task_id: int, repo: RepoDep) -> dict[str, Any]:
        row = repo.get(task_id)
        if row is None:
            raise TaskNotFound(task_id)  # domain error; the handler above maps it to 404
        return row

    @app.post("/tasks/{task_id}/complete", response_model=TaskOut)
    async def complete_task(task_id: int, repo: RepoDep) -> dict[str, Any]:
        return repo.complete(task_id)

    @app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_task(task_id: int, repo: RepoDep) -> Response:
        repo.delete(task_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


def summarise_errors(exc: Any) -> list[str]:
    return [".".join(str(part) for part in e["loc"]) + f": {e['msg']}" for e in exc.errors()]
