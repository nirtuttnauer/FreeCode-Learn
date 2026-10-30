"""Module 20 — reference solutions."""

from __future__ import annotations

import contextlib
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

# sqlite3.Connection has no __dict__, so nesting depth is tracked out of band.
_DEPTHS: dict[int, int] = {}


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # off by default in SQLite
    conn.executescript(SCHEMA)
    return conn


def add_user(conn: sqlite3.Connection, email: str, name: str) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO users (email, name) VALUES (?, ?)", (email, name)
        )
    return int(cursor.lastrowid)


def add_orders(conn: sqlite3.Connection, rows: Iterable[tuple[int, int, str]]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    with conn:  # one transaction for the whole batch
        cursor = conn.executemany(
            "INSERT INTO orders (user_id, amount_cents, placed_at) VALUES (?, ?, ?)", rows
        )
    return cursor.rowcount


def find_users(conn: sqlite3.Connection, name_fragment: str) -> list[dict[str, Any]]:
    # The wildcards go in the VALUE, so the whole fragment stays data.
    pattern = f"%{name_fragment}%"
    rows = conn.execute(
        "SELECT id, email, name FROM users WHERE name LIKE ? ORDER BY id", (pattern,)
    ).fetchall()
    return [dict(row) for row in rows]


def user_totals(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT u.id, u.name,
               COUNT(o.id) AS order_count,
               COALESCE(SUM(o.amount_cents), 0) AS total_cents
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.id
        GROUP BY u.id, u.name
        ORDER BY total_cents DESC, u.name ASC
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "order_count": row["order_count"],
            "total": cents_to_decimal(row["total_cents"]),
        }
        for row in rows
    ]


@contextlib.contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    key = id(conn)
    depth = _DEPTHS.get(key, 0)
    _DEPTHS[key] = depth + 1
    name = f"sp_{depth}"

    if depth == 0:
        conn.execute("BEGIN")
    else:
        conn.execute(f"SAVEPOINT {name}")  # nested: a partial rollback point

    try:
        yield conn
    except BaseException:
        if depth == 0:
            conn.execute("ROLLBACK")
        else:
            conn.execute(f"ROLLBACK TO {name}")
            conn.execute(f"RELEASE {name}")
        raise
    else:
        if depth == 0:
            conn.execute("COMMIT")
        else:
            conn.execute(f"RELEASE {name}")
    finally:
        if depth:
            _DEPTHS[key] = depth
        else:
            _DEPTHS.pop(key, None)  # don't hold a reference to a closed connection


def page_orders(
    conn: sqlite3.Connection, limit: int = 20, cursor: tuple[str, int] | None = None
) -> tuple[list[dict[str, Any]], tuple[str, int] | None]:
    if limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")

    # Fetch one extra row: its presence is the "is there a next page" answer.
    if cursor is None:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY placed_at DESC, id DESC LIMIT ?", (limit + 1,)
        ).fetchall()
    else:
        placed_at, last_id = cursor
        rows = conn.execute(
            """SELECT * FROM orders
               WHERE (placed_at < ?) OR (placed_at = ? AND id < ?)
               ORDER BY placed_at DESC, id DESC LIMIT ?""",
            (placed_at, placed_at, last_id, limit + 1),
        ).fetchall()

    has_more = len(rows) > limit
    page = [dict(row) for row in rows[:limit]]
    next_cursor = (page[-1]["placed_at"], page[-1]["id"]) if (has_more and page) else None
    return page, next_cursor


def stream_orders(conn: sqlite3.Connection, batch_size: int = 100) -> Iterator[dict[str, Any]]:
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}")
    cursor = conn.execute("SELECT * FROM orders ORDER BY id")
    while batch := cursor.fetchmany(batch_size):
        for row in batch:
            yield dict(row)


def cents_to_decimal(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))
