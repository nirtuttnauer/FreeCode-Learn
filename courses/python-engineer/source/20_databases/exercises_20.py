"""Module 20 exercises.  pytest 20_databases

Everything runs against in-memory SQLite. Every technique transfers to Postgres unchanged.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from decimal import Decimal
from typing import Any

SCHEMA = """
CREATE TABLE users (
    id    INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name  TEXT NOT NULL
);
CREATE TABLE orders (
    id       INTEGER PRIMARY KEY,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    placed_at TEXT NOT NULL
);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_placed ON orders(placed_at, id);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Open a connection configured the way every SQLite connection should be.

    - `row_factory = sqlite3.Row`, so rows are indexable by column name.
    - `PRAGMA foreign_keys = ON` — SQLite ignores foreign keys unless you ask.
    - Apply SCHEMA (use `executescript`).
    - Return the connection; the caller closes it.
    """
    raise NotImplementedError


def add_user(conn: sqlite3.Connection, email: str, name: str) -> int:
    """Insert a user and return the new id.

    - A duplicate email raises `sqlite3.IntegrityError` — let it propagate; the database
      is the one enforcing the invariant, and translating it here would be a lie.
    - Wrap the write in `with conn:` so it commits (or rolls back).
    - `cursor.lastrowid` gives you the id.
    """
    raise NotImplementedError


def add_orders(conn: sqlite3.Connection, rows: Iterable[tuple[int, int, str]]) -> int:
    """Bulk-insert (user_id, amount_cents, placed_at) rows; return how many were inserted.

    Use `executemany` — one statement, not a Python loop of `execute`. On a real database
    that's one round trip instead of N.

    The whole batch is one transaction: if any row violates a constraint, none are
    inserted and the IntegrityError propagates.
    """
    raise NotImplementedError


def find_users(conn: sqlite3.Connection, name_fragment: str) -> list[dict[str, Any]]:
    """Case-insensitive substring search on `name`, ordered by id.

    Return a list of plain dicts (not `sqlite3.Row` — don't leak the driver's types out
    of the data-access layer).

    The point of this exercise: build the LIKE pattern as a PARAMETER
    (`"%" + fragment + "%"` passed as a value), never by formatting it into the SQL. The
    tests pass `"' OR '1'='1"` and expect zero rows.
    """
    raise NotImplementedError


def user_totals(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every user with their order count and total, in ONE query — no N+1.

    Returns `[{"id", "name", "order_count", "total"}]` ordered by total descending, then
    name ascending. Users with no orders appear with `order_count=0` and
    `total=Decimal("0.00")` (so it's a LEFT JOIN, not an inner one).

    `total` is a `Decimal` of currency units: 1250 cents -> `Decimal("12.50")`. Integer
    cents in the database, Decimal in Python, float nowhere (module 01).

    The tests count the queries you issue. One is the answer.
    """
    raise NotImplementedError


def transaction(conn: sqlite3.Connection) -> Any:
    """A context manager for an explicit transaction with SAVEPOINT semantics.

    ```
    with transaction(conn):
        ...            # commits at the end, rolls back on any exception
    ```

    Requirements:
    - Commit on clean exit, roll back on exception, and re-raise (never swallow).
    - NESTABLE: an inner `transaction()` inside an outer one uses a SAVEPOINT, so the
      inner block can fail and be rolled back while the outer one continues. `with conn:`
      alone cannot do this — that's why you're writing it.
    - Yield the connection so `with transaction(conn) as c:` works.

    Use `@contextlib.contextmanager` (module 05) and track nesting depth. Note that
    `sqlite3.Connection` has no `__dict__`, so you cannot stash the depth on the
    connection object — keep it in a module-level dict keyed by `id(conn)`.
    """
    raise NotImplementedError


def page_orders(
    conn: sqlite3.Connection, limit: int = 20, cursor: tuple[str, int] | None = None
) -> tuple[list[dict[str, Any]], tuple[str, int] | None]:
    """Keyset pagination over orders, newest first.

    Returns `(rows, next_cursor)`. `next_cursor` is `(placed_at, id)` of the LAST row
    returned, or None when there are no more rows.

    - Order by `placed_at DESC, id DESC` — the id breaks ties, without which pagination
      is non-deterministic.
    - With a cursor, continue strictly after it: `(placed_at, id) < (?, ?)`.
    - `limit < 1` raises ValueError.
    - Fetch `limit + 1` rows to discover whether a next page exists without a COUNT.

    No OFFSET anywhere. At page 500, OFFSET makes the database walk 10,000 rows it will
    throw away — and a concurrent insert shifts every subsequent page.
    """
    raise NotImplementedError


def stream_orders(conn: sqlite3.Connection, batch_size: int = 100) -> Iterator[dict[str, Any]]:
    """Yield every order lazily, fetching in batches — constant memory over a huge table.

    Use `cursor.fetchmany(batch_size)` in a loop (module 06). `fetchall()` on ten million
    rows is how a report script gets OOM-killed.

    `batch_size < 1` raises ValueError.
    """
    raise NotImplementedError


def cents_to_decimal(cents: int) -> Decimal:
    """1250 -> Decimal('12.50'). Exact, quantised to 2 places, never via float."""
    raise NotImplementedError
