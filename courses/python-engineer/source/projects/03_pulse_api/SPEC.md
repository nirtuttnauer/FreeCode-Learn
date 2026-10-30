# Project 03 — `pulse`: a production-grade FastAPI service

Not a tutorial CRUD app. A service you could hand to an on-call rotation: layered,
typed, migrated, authenticated, rate-limited, templated, instrumented, and deployable.

The domain: a **link shortener with analytics**. Small enough to finish, real enough to
have every hard problem — uniqueness under concurrency, hot-path caching, time-series
aggregation, abuse prevention, and a public redirect endpoint that must never be slow.

**Modules it draws on**: 05 (errors), 07 (typing), 09 (testing), 11 (async), 14
(architecture), 15 (FastAPI), 16 (Jinja2), 17 (observability).

---

## Milestone 1 — the domain, with no framework in sight

`src/pulse/domain/` must not import FastAPI, SQLAlchemy, or anything I/O.

- `ShortLink` (frozen dataclass): `code`, `target: Url`, `owner_id`, `created_at`,
  `expires_at`, `is_active`.
- Value objects: `Url` (validates scheme and host, rejects `javascript:` and private
  IP ranges — this is an SSRF guard, not decoration), `ShortCode` (6–12 chars,
  base58 alphabet, no `0/O/l/I`).
- `generate_code(rng)` — deterministic under an injected RNG, so tests aren't flaky.
- Domain errors: `PulseError` base, `LinkNotFound`, `LinkExpired`, `CodeTaken`,
  `QuotaExceeded`.
- 100% unit-tested with no fixtures, no database, no client.

## Milestone 2 — ports and adapters

- `LinkRepository` and `ClickRepository` Protocols, declared beside the services.
- Two implementations of each: in-memory (tests) and SQLite/Postgres via SQLAlchemy 2.0
  async (production).
- Alembic migrations, with an `upgrade`/`downgrade` round-trip test.
- `UnitOfWork` as an async context manager: commit on success, roll back on exception.
- The **same** service test suite runs against both implementations, via a parametrised
  fixture (module 09). If it passes in memory but fails on SQLite, your Protocol is lying.

## Milestone 3 — services

- `ShortenerService.create(target, owner, custom_code=None, ttl=None)` — retries on
  `CodeTaken` up to N times with a fresh random code, honours a per-owner quota, and
  emits a `LinkCreated` event.
- `.resolve(code)` — returns the target or raises `LinkNotFound`/`LinkExpired`, and
  records a click **without blocking the redirect** (a background task / queue).
- `AnalyticsService.stats(code, window)` — clicks bucketed by hour, plus unique
  referrers and top countries.
- Every service takes its dependencies (repos, clock, RNG, bus) as constructor
  arguments. Not one module-level singleton.

## Milestone 4 — the HTTP layer

| Method | Path | Notes |
|---|---|---|
| POST | `/api/links` | 201, body validated by pydantic, `Location` header |
| GET | `/api/links/{code}` | 200 / 404 |
| GET | `/api/links` | cursor pagination, not offset |
| DELETE | `/api/links/{code}` | 204, owner-only |
| GET | `/api/links/{code}/stats` | 200, query-param window |
| GET | `/{code}` | **307 redirect**, the hot path |
| GET | `/health` `/ready` | liveness vs readiness — they are different |

- Domain exceptions mapped to status codes with `@app.exception_handler`. No handler
  raises `HTTPException` for a domain condition.
- Auth: API key in a header, resolved to an owner by a dependency; 401 vs 403 used
  correctly.
- Per-owner rate limiting with the token bucket you wrote in module 09.
- Cursor pagination (opaque, base64-encoded), because offset pagination breaks under
  concurrent inserts.
- `ETag` + `Cache-Control` on the redirect, and a small in-process LRU in front of the
  repository for hot codes.

## Milestone 5 — the HTML side (module 16)

- Jinja2 templates with inheritance: a landing page, a create form, and a stats
  dashboard with a chart rendered as inline SVG (no JS build step).
- `StrictUndefined`, autoescaping on, macros for form fields and flash messages.
- A CSRF token on the form, verified server-side.
- The same handler serves JSON or HTML by `Accept` header — content negotiation, one
  service call, two renderers.

## Milestone 6 — operations (module 17)

- OTel tracing on every request and DB call, with `service.name` and version from
  `importlib.metadata`.
- RED metrics per route, plus domain counters (`links.created`, `links.resolved`,
  `links.expired`).
- Structured JSON logs with the trace id, and API keys redacted at the formatter.
- Settings via `pydantic-settings`, validated at startup: a missing DSN must kill the
  process at boot, never at 3am.
- Graceful shutdown: drain in-flight requests, close the pool in the lifespan handler.
- A Dockerfile (multi-stage, non-root, < 200 MB) and a `docker-compose.yml` with Postgres.
- CI: ruff, mypy --strict, pytest with coverage, and a build.

## Going further

- Load-test the redirect with `locust` or `k6`; find and fix the first bottleneck.
- Replace the in-process cache with Redis and measure the difference honestly.
- Idempotency keys on POST, so a retried create doesn't make two links.
- OpenAPI schema pinned in CI to catch breaking changes.
- Blue/green migration of a column with zero downtime — write the runbook.

## What "done" means

`docker compose up`, then a fresh clone can create a link, follow the redirect, and see
the click in the dashboard — and `mypy --strict` and the acceptance suite are both green.
