"""pulse — a link shortener with analytics, built like a service you have to operate.

Layering rule, enforced by review and by your own discipline:

    api/       FastAPI routers, pydantic schemas, templates   -> imports services
    services/  use cases, transactions, events                -> imports domain
    domain/    entities, value objects, errors                -> imports NOTHING
    adapters/  repositories, cache, clock                     -> implements the Protocols

`domain/` importing FastAPI or SQLAlchemy is the moment the architecture died.
"""

from __future__ import annotations

__all__ = ["__version__", "create_app"]

__version__ = "0.1.0"


def create_app(settings: object | None = None):  # noqa: ANN201 — fill in the return type
    """Composition root: build settings, adapters, services, then the app. TODO."""
    raise NotImplementedError
