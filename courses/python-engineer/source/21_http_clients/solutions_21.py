"""Module 21 — reference solutions."""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import httpx

RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})


class ApiError(Exception):
    """Base for this client's errors — httpx types never escape this module."""


class ApiUnavailable(ApiError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiClientError(ApiError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def build_client(
    base_url: str, token: str | None = None, transport: httpx.BaseTransport | None = None
) -> httpx.Client:
    headers = {"accept": "application/json", "user-agent": "mypycourse/1.0"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    return httpx.Client(
        base_url=base_url,
        timeout=httpx.Timeout(10.0, connect=5.0),  # never unbounded
        headers=headers,
        follow_redirects=True,
        transport=transport,
    )


def _translate(response: httpx.Response) -> Any:
    status = response.status_code
    if status in RETRYABLE_STATUSES or status >= 500:
        raise ApiUnavailable(f"upstream returned {status}", status)
    if status >= 400:
        raise ApiClientError(f"request rejected with {status}", status)
    try:
        return response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise ApiError(f"invalid JSON in response: {exc}") from exc


def fetch_json(client: httpx.Client, path: str, **params: Any) -> Any:
    try:
        response = client.get(path, params=params or None)
    except httpx.TransportError as exc:
        raise ApiUnavailable(f"transport failure: {exc}") from exc
    return _translate(response)


def request_with_retry(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    sleeper: Callable[[float], None] = time.sleep,
    **kwargs: Any,
) -> httpx.Response:
    if attempts < 1:
        raise ValueError(f"attempts must be >= 1, got {attempts}")

    last_error: Exception | None = None
    for attempt in range(attempts):
        response = None
        try:
            response = client.request(method, path, **kwargs)
            if response.status_code not in RETRYABLE_STATUSES:
                return response  # includes 4xx and 500: not safe or not worth retrying
        except httpx.TransportError as exc:
            last_error = exc

        if attempt == attempts - 1:
            break

        delay = base_delay * 2**attempt
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                # A date-form Retry-After isn't a float; fall back to the backoff.
                with contextlib.suppress(ValueError):
                    delay = float(retry_after)
        sleeper(delay)

    if response is not None:
        return response
    raise last_error  # type: ignore[misc]


def paginate(client: httpx.Client, path: str) -> Iterator[dict[str, Any]]:
    url: str | None = path
    while url:
        payload = fetch_json(client, url)
        yield from payload.get("items", [])
        url = payload.get("next")


async def fetch_all(
    client: httpx.AsyncClient, paths: list[str], *, limit: int = 10
) -> list[Any]:
    if limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")
    if not paths:
        return []

    semaphore = asyncio.Semaphore(limit)

    async def one(path: str) -> Any:
        async with semaphore:
            try:
                response = await client.get(path)
            except httpx.TransportError as exc:
                raise ApiUnavailable(f"transport failure: {exc}") from exc
            return _translate(response)

    return await asyncio.gather(*(one(path) for path in paths))


async def stream_lines(client: httpx.AsyncClient, path: str) -> AsyncIterator[str]:
    try:
        async with client.stream("GET", path) as response:
            if response.status_code >= 400:
                await response.aread()  # needed before touching the body on an error
                _translate(response)
            async for line in response.aiter_lines():
                if line.strip():
                    yield line
    except httpx.TransportError as exc:
        raise ApiUnavailable(f"transport failure: {exc}") from exc
