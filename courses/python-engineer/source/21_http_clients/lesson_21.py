"""Module 21 — runnable lesson. `python 21_http_clients/lesson_21.py`

Every request here goes through httpx.MockTransport, so nothing touches the network.
"""

from __future__ import annotations

import asyncio
import time

import httpx

INTRO = """Calling someone else's API is easy; calling it well is the job, because they will be slow,
broken or rate-limiting you. Always set a timeout — without one, a hung server freezes your
program forever. Every request here goes through a fake transport, so nothing touches the
network."""

USERS = [{"id": i, "name": f"user{i}"} for i in range(1, 8)]


def fake_api(request: httpx.Request) -> httpx.Response:
    """A tiny fake server, implemented as one function."""
    path = request.url.path

    if path == "/users":
        page = int(request.url.params.get("page", 1))
        start = (page - 1) * 3
        items = USERS[start : start + 3]
        next_url = f"/users?page={page + 1}" if start + 3 < len(USERS) else None
        return httpx.Response(200, json={"items": items, "next": next_url})

    if path == "/slow":
        time.sleep(0.3)
        return httpx.Response(200, json={"ok": True})

    if path == "/flaky":
        fake_api.calls = getattr(fake_api, "calls", 0) + 1
        if fake_api.calls < 3:
            return httpx.Response(503, json={"error": "unavailable"})
        return httpx.Response(200, json={"attempt": fake_api.calls})

    if path == "/rate-limited":
        return httpx.Response(429, headers={"Retry-After": "2"}, json={"error": "slow down"})

    if path == "/boom":
        return httpx.Response(500, json={"error": "internal"})

    if path == "/big":
        return httpx.Response(200, content=b"x" * 100_000)

    return httpx.Response(404, json={"error": "not found"})


def client_basics() -> None:
    print("\n== a Client, not module-level get() ==")
    with httpx.Client(
        base_url="https://api.example.com",
        transport=httpx.MockTransport(fake_api),
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={"user-agent": "course/1.0"},
    ) as client:
        response = client.get("/users", params={"page": 1})
        payload = response.json()  # reads the body; .elapsed only exists after that
        print(f"  status={response.status_code} items={len(payload['items'])}")
        print(f"  request headers carried through: {response.request.headers['user-agent']}")
        print(f"  base_url + relative path resolved to: {response.request.url}")
        print("  one Client => connection pooling, shared headers, one base_url")


def errors() -> None:
    print("\n== an error status is still a valid response ==")
    with httpx.Client(
        base_url="https://api.example.com", transport=httpx.MockTransport(fake_api)
    ) as client:
        response = client.get("/boom")
        print(f"  no exception raised for {response.status_code}")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"  raise_for_status(): {type(exc).__name__}: {exc.response.status_code}")

        print("  transport failures are different — those raise on their own:")

        def broken(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        with httpx.Client(transport=httpx.MockTransport(broken)) as bad:
            try:
                bad.get("https://down.example.com/")
            except httpx.ConnectError as exc:
                print(f"    {type(exc).__name__}: {exc}")


def retries() -> None:
    print("\n== retrying only what is safe to retry ==")
    RETRYABLE = {429, 502, 503, 504}

    def get_with_retry(client: httpx.Client, url: str, attempts: int = 5) -> httpx.Response:
        for attempt in range(attempts):
            response = client.get(url)
            if response.status_code not in RETRYABLE:
                return response
            if attempt == attempts - 1:
                return response
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 0.05 * 2**attempt
            print(f"    got {response.status_code}, waiting {delay}s (attempt {attempt + 1})")
        raise AssertionError("unreachable")

    with httpx.Client(
        base_url="https://api.example.com", transport=httpx.MockTransport(fake_api)
    ) as client:
        response = get_with_retry(client, "/flaky")
        print(f"  recovered after {response.json()['attempt']} attempts")

        limited = client.get("/rate-limited")
        print(f"  429 tells you how long to wait: Retry-After={limited.headers['Retry-After']}s")
        print("  never retry a 4xx (except 429) — and never retry a non-idempotent POST")


def pagination_and_streaming() -> None:
    print("\n== pagination ==")
    with httpx.Client(
        base_url="https://api.example.com", transport=httpx.MockTransport(fake_api)
    ) as client:

        def all_users():
            url = "/users"
            while url:
                payload = client.get(url).json()
                yield from payload["items"]
                url = payload["next"]

        print(f"  followed next links lazily: {[u['id'] for u in all_users()]}")

        print("\n== streaming ==")
        total = 0
        with client.stream("GET", "/big") as response:
            for chunk in response.iter_bytes(chunk_size=16_384):
                total += len(chunk)
        print(f"  read {total:,} bytes in chunks — never all in memory at once")


def async_concurrency() -> None:
    print("\n== async, bounded ==")

    async def main() -> tuple[int, float]:
        async def handler(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(0.05)
            return httpx.Response(200, json={"path": request.url.path})

        semaphore = asyncio.Semaphore(5)

        async with httpx.AsyncClient(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ) as client:

            async def fetch(n: int) -> httpx.Response:
                async with semaphore:  # bound the concurrency, always
                    return await client.get(f"/item/{n}")

            start = time.perf_counter()
            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(fetch(n)) for n in range(20)]
            return len(tasks), time.perf_counter() - start

    count, elapsed = asyncio.run(main())
    print(f"  {count} requests, limit 5, in {elapsed:.2f}s (serial would be 1.0s)")
    print("  ONE AsyncClient shared by every task — per-request clients throw away the pool")


def testing_without_a_network() -> None:
    print("\n== MockTransport is the whole testing story ==")

    def assert_and_respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["authorization"] == "Bearer secret"
        assert request.url.path == "/orders"
        return httpx.Response(201, json={"id": 1}, headers={"location": "/orders/1"})

    with httpx.Client(
        base_url="https://api.example.com",
        transport=httpx.MockTransport(assert_and_respond),
        headers={"authorization": "Bearer secret"},
    ) as client:
        response = client.post("/orders", json={"sku": "abc"})
        print(f"  {response.status_code} {response.headers['location']}")
    print("  your real code ran: headers, serialisation, status handling — just no socket")


if __name__ == "__main__":
    print(INTRO)
    client_basics()
    errors()
    retries()
    pagination_and_streaming()
    async_concurrency()
    testing_without_a_network()
