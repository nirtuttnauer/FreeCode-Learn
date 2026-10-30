# 21 — HTTP clients, APIs, and scraping

Calling other people's services well is most of backend work. The hard part isn't the
request — it's what happens when the other side is slow, flaky, rate-limited, or lying.

We use **httpx**: the same API sync and async, HTTP/2, connection pooling, and a
`MockTransport` that makes every test in this module run with no network at all.

## In plain English

Calling someone else's web API is easy. Calling it *well* is the job, because the other
side will eventually be slow, broken, rate-limiting you, or lying.

Two things matter more than everything else:

**Always set a timeout.** If you don't, and the other server hangs, your program waits
*forever*. Do that on a web server and every worker gradually gets stuck on a dead
connection until your site stops responding — not because your code broke, but because you
never said how long you were willing to wait. Neither `requests` nor `httpx` sets one for
you by default.

**Know what's safe to retry.** If the server said "I'm overloaded, try later" (503), retry.
If it said "your request is malformed" (400), retrying identical junk a hundred times helps
nobody. And be very careful retrying anything that *changes* something — retrying "charge
this card" after a timeout is how a customer gets billed twice.

There's also a testing idea here worth stealing: every test in this module runs with **no
network at all**. httpx lets you swap in a fake transport, so your real code — headers,
retries, timeouts and all — runs against a pretend server defined in ten lines. Fast, and it
can't fail because someone else's API is down.

**Watch out for:** an HTTP error status is *not* an exception. A 500 response arrives as a
perfectly normal response object. Check it, or call `raise_for_status()` — otherwise a
`None` shows up three layers away and you spend an hour finding it.

## 1. The client, not the module-level function

```python
import httpx

httpx.get(url)                      # opens and closes a connection every time — don't
```

```python
with httpx.Client(
    base_url="https://api.example.com",
    timeout=httpx.Timeout(10.0, connect=5.0),
    headers={"user-agent": "myapp/1.0", "accept": "application/json"},
    follow_redirects=True,
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
) as client:
    response = client.get("/users", params={"page": 1})
```

A `Client` gives you connection pooling, shared headers, cookies and a base URL. Reusing
one is often a 3–5× throughput difference on repeated calls. Create it once, at your
composition root (module 14), and inject it.

## 2. Timeouts are not optional

**Every** request needs a timeout. Without one, a hung upstream holds your worker forever
and your service dies of thread exhaustion, not of an error.

```python
httpx.Timeout(10.0, connect=5.0, read=10.0, write=10.0, pool=5.0)
```

`requests` has no default timeout either. This is the single most common production bug in
Python HTTP code.

## 3. Responses and errors

```python
response.status_code, response.text, response.json(), response.content
response.headers["content-type"], response.elapsed, response.url

response.raise_for_status()      # -> HTTPStatusError for 4xx/5xx
```

`httpx` raises for **transport** problems (`ConnectError`, `ReadTimeout`) but **not** for
HTTP error statuses — a 500 is a perfectly valid response object. Call `raise_for_status()`
or check explicitly; forgetting is how a `None` ends up three layers deep.

Exception tree: `httpx.HTTPError` → `TransportError` (`ConnectError`, `ReadTimeout`,
`ConnectTimeout`) and `HTTPStatusError`. Catch the narrow one you can handle, and translate
it into a **domain** error at your boundary (module 14) — nothing above your client layer
should import httpx.

## 4. Retries — what's safe to retry

| Condition | Retry? |
|---|---|
| Connection error, timeout | Yes |
| 502, 503, 504 | Yes |
| 429 Too Many Requests | Yes — and **honour `Retry-After`** |
| 500 | Careful: only if the operation is idempotent |
| 4xx (400, 401, 403, 404, 422) | **No.** Retrying won't fix your request |

Only retry **idempotent** operations (GET, PUT, DELETE) unless you send an idempotency
key. Retrying a POST that already succeeded is how a customer gets charged twice.

Always: exponential backoff **with jitter** (module 09), a cap on attempts, and a cap on
total time.

## 5. Pagination, streaming, uploads

```python
# Follow Link headers or a next cursor — lazily (module 06)
async def paginate(client, url):
    while url:
        response = await client.get(url)
        payload = response.json()
        yield from payload["items"]
        url = payload.get("next")

# Never load a large body into memory
with client.stream("GET", url) as response:
    for chunk in response.iter_bytes(chunk_size=65536):
        sink.write(chunk)
```

`files={"upload": ("name.csv", handle, "text/csv")}` for multipart, `content=` for raw
bytes, `json=` for JSON, `data=` for form encoding.

## 6. Async and concurrency

```python
async with httpx.AsyncClient() as client:
    semaphore = asyncio.Semaphore(10)              # bound it (module 11)

    async def fetch(url):
        async with semaphore:
            return await client.get(url)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(u)) for u in urls]
```

One `AsyncClient` shared across tasks — creating one per request throws away the pool.

## 7. Auth and secrets

- `auth=("user", "pass")`, `auth=httpx.BasicAuth(...)`, or a custom `httpx.Auth` subclass
  for token refresh.
- Bearer tokens in the `Authorization` header, read from the environment or a secret
  manager — never in the URL, never in the repo, never in a log line (module 17's
  redaction).
- Verify TLS. `verify=False` is a decision to be MITM'd; if you need a private CA, pass it.

## 8. Testing without a network

```python
def handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/users"
    return httpx.Response(200, json={"items": []})

client = httpx.Client(transport=httpx.MockTransport(handler))
```

`MockTransport` replaces the network at the transport layer, so your code, headers, retries
and timeouts are all exercised for real. Use `respx` for a richer matcher API. Recorded
fixtures (VCR-style) are the fallback for complex APIs.

**Never let a unit test hit a real network.** It will be slow, flaky, and one day it will
fail during an incident for reasons unrelated to your change.

## 9. Scraping, briefly and responsibly

`httpx` + `selectolax` (fast) or `BeautifulSoup` (friendly) for parsing;
`scrapy` for a real crawler; `playwright` when the content is JS-rendered.

Check `robots.txt` and the site's terms, identify yourself in the user-agent, rate-limit
yourself, cache aggressively, and prefer an API if one exists. And **never** parse HTML
with a regex (module 18).

## Exercises

`exercises_21.py`, then `pytest 21_http_clients`. Every test uses `MockTransport` — the
suite runs offline in under a second.

## Further reading

- [httpx docs](https://www.python-httpx.org/)
- [Google API design guide](https://cloud.google.com/apis/design) — for the other side of the wire
