"""Outgoing responses. Each one knows how to write itself to an ASGI `send`."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any


class Response:
    """Base response: content, status_code, headers, media_type.

    `render(content) -> bytes` is the hook subclasses override. `__call__(send)` emits
    `http.response.start` then `http.response.body`, and must set Content-Length.
    """

    media_type = "text/plain"

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        raise NotImplementedError


class JSONResponse(Response):
    """media_type application/json; `render` is `json.dumps(...).encode()`.

    Serialise dataclasses, pydantic models, datetimes and UUIDs too — a `default=` hook
    on json.dumps is the tidy way (module 04b's serialisation section).
    """

    media_type = "application/json"


class HTMLResponse(Response):
    media_type = "text/html"


class RedirectResponse(Response):
    """307 by default — it preserves the request method, unlike 302."""


class StreamingResponse(Response):
    """Wraps an async generator, sending chunks with `more_body: True` until it ends.

    This is where module 06 (generators) and module 11 (asyncio) finally meet: the
    response body is a lazy async stream, so a 2 GB export never lands in memory.
    """

    def __init__(self, content: AsyncIterator[bytes], **kwargs: Any) -> None:
        raise NotImplementedError
