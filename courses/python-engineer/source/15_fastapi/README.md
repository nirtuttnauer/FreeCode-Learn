# 15 — FastAPI and pydantic

FastAPI is where modules 07 (typing), 11 (asyncio) and 14 (dependency inversion) cash out:
it reads your **type hints** and turns them into validation, serialisation, dependency
injection and OpenAPI docs.

## In plain English

FastAPI's trick is that it reads your **type hints** and does the boring work for you.

You write a function that says "I take a `TaskIn` and return a `TaskOut`". From that alone,
FastAPI will:

- read the incoming JSON and check every field
- send back a helpful 422 error listing exactly what was wrong, if it wasn't valid
- convert your return value to JSON
- generate live API documentation you can click around in

You wrote none of that. It came from the annotations, which is why modules 07 (typing) and
14 (depend on shapes) pay off here.

The validation engine underneath is **pydantic**, and it's worth understanding as a separate
thing: mypy checks your *code* before it runs; pydantic checks your *data* while it runs.
You need both, for different reasons, and this is the module where that distinction stops
being abstract.

**Watch out for:** define separate models for what comes *in* and what goes *out*. If you
reuse one model for both, the day someone adds an `internal_notes` field is the day it
starts appearing in your public API.

## 1. pydantic v2 first — it's the engine

```python
from pydantic import BaseModel, Field, field_validator, ConfigDict

class TaskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")        # reject unknown keys

    title: str = Field(min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list)
    priority: int = Field(default=1, ge=1, le=5)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()
```

- **Type hints become runtime validation.** This is the difference from module 07: mypy
  checks your code, pydantic checks your *data*.
- `model_validate(raw)`, `model_dump()`, `model_dump_json()`, `model_copy(update=...)`.
- `ValidationError` carries a structured `.errors()` list — field, type, message.
- v2's core is Rust; it's ~5–50× faster than v1. Don't hand-roll validation any more.

Separate models per direction — `TaskIn` (what a client may send), `TaskOut` (what you
return). Sharing one model is how internal fields leak into responses.

## 2. A minimal app

```python
from fastapi import FastAPI, HTTPException, status

app = FastAPI(title="Tasks")

@app.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int) -> Task:
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return task
```

- Path params come from the route, query params from remaining scalars, and the body
  from any pydantic-model parameter. FastAPI works it out from the annotations.
- `response_model` filters the response — extra attributes are dropped, which is your
  safety net against leaking fields.
- `status_code=201`, `response_model_exclude_none=True`, `tags=[...]` on the decorator.

```bash
uvicorn app:app --reload         # docs at /docs and /redoc, schema at /openapi.json
```

## 3. Dependency injection — module 14, with framework support

```python
from typing import Annotated
from fastapi import Depends

def get_repo() -> TaskRepository:            # one composition root
    return PostgresTasks(pool)

RepoDep = Annotated[TaskRepository, Depends(get_repo)]

@app.get("/tasks")
async def list_tasks(repo: RepoDep) -> list[TaskOut]: ...
```

- `Annotated[T, Depends(f)]` is the modern form — reusable as a type alias.
- Dependencies nest, are cached per request, and can be `yield`-based for cleanup
  (a DB session that commits or rolls back).
- **In tests, override them**: `app.dependency_overrides[get_repo] = lambda: InMemoryTasks()`.
  That's why your handlers should never construct their own dependencies.

## 4. async or def?

| Handler | Runs |
|---|---|
| `async def` | on the event loop — **never** call blocking code in it |
| `def` | automatically in a thread pool — safe for blocking DB drivers |

Using `async def` and then calling a synchronous, blocking library inside it is the single
most common FastAPI performance bug. Either use an async driver, or make the handler a
plain `def`.

## 5. Errors

```python
raise HTTPException(404, "not found")                     # framework-level

@app.exception_handler(TaskNotFound)                      # map DOMAIN errors at the edge
async def handle_not_found(request, exc: TaskNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
```

Domain code raises domain exceptions; only the HTTP layer knows about status codes. That's
the layering rule from module 14, applied.

## 6. Lifespan, middleware, background work

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool()     # startup
    yield
    await app.state.pool.close()             # shutdown

app = FastAPI(lifespan=lifespan)
```

`BackgroundTasks` for after-response work in the same process; a real queue (project 04)
for anything that must survive a restart.

## 7. Testing

```python
from fastapi.testclient import TestClient

client = TestClient(app)                # sync, runs the ASGI app in-process — no server
response = client.post("/tasks", json={"title": "x"})
assert response.status_code == 201
```

`httpx.AsyncClient(transport=ASGITransport(app=app))` for async tests. Either way there's
no network and no port — these are fast enough to run on every save.

## 8. Production notes

- `uvicorn app:app --workers 4` behind a proxy; `gunicorn -k uvicorn.workers.UvicornWorker`
  when you want process supervision.
- Settings via `pydantic-settings`, validated at startup.
- Health endpoint, structured JSON logs, and OpenTelemetry (module 17).
- Pin the OpenAPI schema in CI to catch accidental breaking changes.

## Exercises

`exercises_15.py`, then `pytest 15_fastapi`. You'll build a small task API with pydantic
models, injected repositories, domain-error mapping and a real test client.

## Further reading

- [FastAPI docs](https://fastapi.tiangolo.com/) — genuinely excellent
- [pydantic v2 docs](https://docs.pydantic.dev/latest/)
