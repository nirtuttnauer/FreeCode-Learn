"""Module 21 exercises.  pytest 21_http_clients

Every test drives your code through `httpx.MockTransport`, so the suite is offline and
instant. If an exercise seems to need a real network to test, the design is wrong.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import httpx


class ApiError(Exception):
    """Base for this client's errors — nothing above this module should import httpx."""


class ApiUnavailable(ApiError):
    """A transport failure or a retryable status. Carries `.status_code` (may be None)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        raise NotImplementedError


class ApiClientError(ApiError):
    """A 4xx: the request itself is wrong, so retrying won't help. Carries `.status_code`."""

    def __init__(self, message: str, status_code: int) -> None:
        raise NotImplementedError


def build_client(
    base_url: str, token: str | None = None, transport: httpx.BaseTransport | None = None
) -> httpx.Client:
    """Construct the one Client the application will share.

    - `base_url` as given.
    - A `httpx.Timeout` of 10s overall with a 5s connect timeout. Never no timeout.
    - Headers: `accept: application/json`, `user-agent: mypycourse/1.0`, and
      `authorization: Bearer <token>` when a token is supplied.
    - `follow_redirects=True`.
    - Pass `transport` straight through — that parameter is what makes this testable.
    """
    raise NotImplementedError


def fetch_json(client: httpx.Client, path: str, **params: Any) -> Any:
    """GET `path`, returning the decoded JSON, and translating failures into domain errors.

    - 2xx -> the parsed body.
    - 4xx -> `ApiClientError` (not retryable).
    - 5xx and 429 -> `ApiUnavailable` (retryable).
    - `httpx.TransportError` (connect errors, timeouts) -> `ApiUnavailable`.
    - A 2xx with an undecodable body -> `ApiError`.

    The point: httpx types stop here. Callers above see only `ApiError` and friends
    (module 14's boundary rule).
    """
    raise NotImplementedError


def request_with_retry(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    sleeper: Callable[[float], None] = __import__("time").sleep,
    **kwargs: Any,
) -> httpx.Response:
    """Send a request, retrying only what is safe to retry.

    Retry on: `httpx.TransportError`, and statuses 429, 502, 503, 504.
    Do NOT retry: any other 4xx, or a 500 (it may not be idempotent).

    - Delay before retry n is `base_delay * 2**n`, EXCEPT when the response carries a
      `Retry-After` header — then honour it (seconds form only).
    - No sleep after the final attempt.
    - After the last attempt: return the response if there was one, else re-raise the
      transport error.
    - `attempts < 1` raises ValueError.
    - `sleeper` is injected so the tests assert on exact delays without waiting
      (module 09).
    """
    raise NotImplementedError


def paginate(client: httpx.Client, path: str) -> Iterator[dict[str, Any]]:
    """Follow a `{"items": [...], "next": "<url or null>"}` pagination chain lazily.

    - Yield each item from each page, in order.
    - Stop when `next` is null or missing.
    - Must be a generator: the tests assert that only ONE request has been made after
      pulling the first item (module 06).
    - A page that fails goes through `fetch_json`, so it raises a domain error.
    """
    raise NotImplementedError


async def fetch_all(
    client: httpx.AsyncClient, paths: list[str], *, limit: int = 10
) -> list[Any]:
    """Fetch every path concurrently, at most `limit` at a time, results in input order.

    - Bound with an `asyncio.Semaphore` (module 11).
    - Each response is `.json()`-decoded.
    - A failure fails the whole call — translate it with the same rules as `fetch_json`.
    - `limit < 1` raises ValueError; an empty list returns [].
    """
    raise NotImplementedError


async def stream_lines(client: httpx.AsyncClient, path: str) -> AsyncIterator[str]:
    """Stream a text response line by line, without buffering the whole body.

    Use `client.stream(...)` and `response.aiter_lines()`. Skip blank lines. A non-2xx
    status raises the same domain errors as `fetch_json`, before any streaming starts.

    This is the shape of an SSE/NDJSON consumer, and the reason is memory: a 2 GB export
    must never become a 2 GB string.
    """
    raise NotImplementedError
