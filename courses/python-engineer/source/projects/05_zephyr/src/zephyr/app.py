"""Milestones 1-5: the ASGI application object.

ASGI in full:

    async def app(scope, receive, send) -> None

`scope` is a dict describing the connection ("type" is "http", "websocket" or "lifespan").
`receive` is an async callable yielding event dicts. `send` is an async callable taking
them. That is the entire protocol — everything else is your framework.

An HTTP response is exactly two sends:

    await send({"type": "http.response.start", "status": 200, "headers": [(b"k", b"v")]})
    await send({"type": "http.response.body", "body": b"...", "more_body": False})
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


class Zephyr:
    """The application.

        app = Zephyr(title="Demo", version="1.0.0", lifespan=lifespan)

        @app.get("/users/{user_id}")
        async def get_user(user_id: int, verbose: bool = False) -> dict: ...

    Required behaviour:
    - `__call__(scope, receive, send)` dispatches on `scope["type"]`:
      "lifespan" -> run the startup/shutdown protocol, "http" -> route and respond,
      "websocket" -> milestone 6.
    - Route decorators: `.get/.post/.put/.patch/.delete/.head/.options`, all delegating to
      `.route(path, methods=...)`.
    - `.include_router(router, prefix="", tags=(), dependencies=())`.
    - `.middleware("http")` and `.add_middleware(cls, **options)`.
    - `.exception_handler(ExcType)` — resolved along the MRO, so a handler for
      `LookupError` also catches `KeyError`.
    - `.dependency_overrides: dict[Callable, Callable]` for tests.
    - Unknown path -> 404. Known path, wrong method -> 405 with an `Allow` header.
    - An unhandled exception -> 500, logged with a traceback, and NOTHING about the
      traceback in the response body.

    Analyse each handler's signature at REGISTRATION time and store the plan. Doing it
    per request is the classic slow-framework mistake.
    """

    def __init__(
        self,
        *,
        title: str = "zephyr",
        version: str = "0.1.0",
        lifespan: Any = None,
    ) -> None:
        raise NotImplementedError

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        raise NotImplementedError

    def route(self, path: str, methods: list[str] | None = None) -> Callable[..., Any]:
        raise NotImplementedError

    def get(self, path: str, **kwargs: Any) -> Callable[..., Any]:
        raise NotImplementedError

    def post(self, path: str, **kwargs: Any) -> Callable[..., Any]:
        raise NotImplementedError

    def openapi(self) -> dict[str, Any]:
        """Milestone 6: build the OpenAPI 3.1 document from the stored handler plans."""
        raise NotImplementedError


class Router:
    """A mountable group of routes, with its own prefix, tags and dependencies."""

    def __init__(self, prefix: str = "", tags: tuple[str, ...] = ()) -> None:
        raise NotImplementedError


class TestClient:
    """Drive the app in-process — no sockets, no server, no ports.

        client = TestClient(app)
        response = client.get("/users/1", params={"verbose": "true"})
        response.status_code, response.json(), response.headers

    Build the ASGI `scope` yourself, feed the body through `receive`, and collect what the
    app sends. Support `with TestClient(app) as client:` to run the lifespan events.

    Writing this is the best possible way to prove you understand ASGI: if you can fake
    the server, you know the protocol.
    """

    def __init__(self, app: Zephyr) -> None:
        raise NotImplementedError
