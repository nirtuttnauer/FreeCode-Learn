# Project 05 — `zephyr`: write your own FastAPI

Build an ASGI web framework from scratch: routing, dependency injection, validation from
type hints, middleware, background tasks, WebSockets, and OpenAPI generation. Run it under
uvicorn. No Starlette, no FastAPI — the standard library and your own code.

After module 15 you can *use* FastAPI. After this project you know exactly what it's doing,
and framework bugs stop being magic.

**Modules it draws on**: 04b (dunders), 06 (generators), 07 (typing — the whole module),
11 (asyncio), 12 (introspection and metaprogramming), 14 (architecture).

---

## Milestone 1 — speak ASGI

The entire protocol is one callable:

```python
async def app(scope: Scope, receive: Receive, send: Send) -> None: ...
```

- Handle `scope["type"] == "lifespan"` (`startup`/`shutdown` messages) and `"http"`.
- `Request`: method, path, headers (case-insensitive — reuse module 04b's
  `CaseInsensitiveDict`), query params (multi-value), cookies, and lazy `await .body()`
  / `.json()` / `.form()`.
- `Response`, `JSONResponse`, `HTMLResponse`, `PlainTextResponse`, `RedirectResponse`,
  `StreamingResponse` (an async generator — module 06 meets module 11).
- Run it: `uvicorn myapp:app`. It has to work with a real server, not just your tests.
- A `TestClient` of your own, calling the app in-process — no sockets. This is the tool
  every later milestone is tested with.

## Milestone 2 — routing

- `@app.get("/users/{user_id}")` and friends, plus `app.route(path, methods=[...])`.
- Path parameters with converters: `{id:int}`, `{slug:str}`, `{rest:path}`, and
  conversion failures giving 422, not 500.
- A **trie or compiled-regex** router, not a linear scan of every route. Benchmark it at
  500 routes and show the difference.
- 404 for unknown paths and **405 with an `Allow` header** for a known path with the wrong
  method — the detail almost every hand-rolled framework gets wrong.
- `Router` objects mountable under a prefix (`app.include_router(users, prefix="/api")`),
  with tags and per-router dependencies.

## Milestone 3 — handler signatures from type hints

The core trick, and the reason FastAPI feels like magic:

```python
@app.post("/users/{user_id}")
async def update(user_id: int, body: UserIn, verbose: bool = False) -> UserOut: ...
```

For each parameter, work out where the value comes from:
1. name matches a path parameter → path
2. annotated with a pydantic model / dataclass → request body
3. `Annotated[T, Depends(f)]` → dependency
4. otherwise → query parameter (required when it has no default)

Then coerce with the annotation and return 422 with a per-field error list when it fails.
Use `typing.get_type_hints` and `inspect.signature`, and resolve each handler's plan
**once at registration**, not per request — that's the difference between a toy and
something you'd serve traffic with.

## Milestone 4 — dependency injection

- `Depends(callable)` with **recursive** resolution of a dependency's own parameters.
- Per-request caching: the same dependency requested twice resolves once.
- `yield`-based dependencies with teardown after the response, running in reverse order,
  and still running when the handler raised (module 05's `ExitStack`).
- Sync dependencies offloaded with `to_thread` so they never block the loop.
- Router- and app-level dependencies that run for every matching request.
- `app.dependency_overrides` for tests — the feature that makes module 15's tests trivial.
- Cycle detection at registration time, with an error naming the cycle.

## Milestone 5 — middleware, errors, lifespan

- Pure-ASGI middleware (wrapping the app) *and* a friendlier
  `@app.middleware("http")` decorator; establish the ordering rules and document them.
- Ship: CORS, GZip (only above a size threshold), request-id injection, and access logs.
- Exception handlers by exception type, resolved along the MRO, plus a default 500 that
  never leaks a traceback in production but always logs one.
- `HTTPException(status, detail, headers)`.
- Lifespan as an async context manager, with startup failures preventing the server from
  accepting traffic at all.
- `BackgroundTasks` running after the response is sent.

## Milestone 6 — the extras that prove it's real

- OpenAPI 3.1 generated from the same signature analysis, plus a `/docs` page rendering
  Swagger UI (Jinja2 — module 16).
- WebSocket support: `@app.websocket("/ws")`, with accept/receive/send/close and a
  connection manager for broadcast.
- Static files with `ETag`, `Last-Modified`, and range requests.
- Benchmarks against FastAPI on a hello-world and a 10-field validated body. Be honest
  about where you're slower and why.

## Going further

- Server-sent events, an `HTTP/2` push story, or trailers.
- A form/multipart parser with streaming file uploads to disk (never into memory).
- Signed session cookies and CSRF, done correctly.
- Plugin system via entry points (module 08), so third parties can add response classes.
- An `@app.get(..., response_model=)` filter that strips extra fields, like module 15's.

## What "done" means

`uvicorn demo:app` serves a documented API with DI, validation and middleware; your own
`TestClient` drives the full acceptance suite in-process; and you can explain, from
memory, exactly what happens between a socket byte arriving and your handler being called.
