"""The incoming request.

Everything here is LAZY: the body is only read when someone awaits it, because most
handlers never touch it and reading costs a round trip through `receive`.
"""

from __future__ import annotations

from typing import Any


class Request:
    """Wraps an ASGI http scope.

    Required:
    - `.method`, `.path`, `.url`, `.client`
    - `.headers` — case-insensitive (module 04b built you one)
    - `.query_params` — multi-value: `?tag=a&tag=b` must not lose `a`
    - `.cookies` — parsed lazily from the Cookie header
    - `.path_params` — filled in by the router
    - `await .body()` -> bytes, cached so a second call doesn't hang on an exhausted
      `receive`
    - `await .json()` -> parsed body, raising ValidationError on malformed JSON
    - `await .form()` -> urlencoded and multipart
    - `.state` — a per-request namespace for middleware to hang things on
    """

    def __init__(self, scope: dict[str, Any], receive: Any) -> None:
        raise NotImplementedError
