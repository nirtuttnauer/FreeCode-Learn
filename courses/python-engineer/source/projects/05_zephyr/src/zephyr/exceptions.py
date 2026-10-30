"""Framework-level errors."""

from __future__ import annotations

from typing import Any


class ZephyrError(Exception):
    """Base for everything the framework raises."""


class HTTPException(ZephyrError):
    """Raised by a handler to produce a non-200 response.

    `HTTPException(404, "not found")` -> `{"detail": "not found"}` with status 404.
    Optional `headers` are merged into the response (a 401 needs `WWW-Authenticate`).
    """

    def __init__(
        self, status_code: int, detail: str | None = None, headers: dict[str, str] | None = None
    ) -> None:
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail or ""
        self.headers = headers or {}


class ValidationError(ZephyrError):
    """A request didn't match a handler's signature. Becomes a 422.

    `.errors` is a list of `{"loc": [...], "msg": "...", "type": "..."}` — the same
    shape pydantic uses, because clients already know how to read it.
    """

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__(f"{len(errors)} validation error(s)")
        self.errors = errors


class RouteConfigurationError(ZephyrError):
    """A bad route or dependency graph. Raised at REGISTRATION time, never per request."""
