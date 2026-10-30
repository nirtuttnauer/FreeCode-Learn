"""Module 20 — runnable lesson. `python 20_databases/lesson_20.py`"""

from __future__ import annotations

import sqlite3
import time

INTRO = """The famous cartoon: a school asks for a student's name, and the child is named
`Robert'); DROP TABLE Students;--`. Gluing that into a command lets the database read a
NAME as INSTRUCTIONS. The fix is one character, and it's the first demo below."""

SCHEMA = """
CREATE TABLE users (
    id    INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name  TEXT NOT NULL
);
CREATE TABLE orders (
    id      INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount  REAL NOT NULL CHECK (amount >= 0),
    placed  TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row  # rows you can index by column name
    conn.execute("PRAGMA foreign_keys = ON")  # sqlite defaults this OFF
    conn.executescript(SCHEMA)
    return conn


def seed(conn: sqlite3.Connection, users: int = 200, orders_each: int = 5) -> None:
    with conn:
        conn.executemany(
            "INSERT INTO users (id, email, name) VALUES (?, ?, ?)",
            [(i, f"user{i}@example.com", f"user{i}") for i in range(1, users + 1)],
        )
        conn.executemany(
            "INSERT INTO orders (user_id, amount, placed) VALUES (?, ?, ?)",
            [
                (u, (u * 7 + n) % 100, f"2026-01-{(n % 28) + 1:02d}")
                for u in range(1, users + 1)
                for n in range(orders_each)
            ],
        )


def parameters() -> None:
    print("\n== parameters, not string formatting ==")
    conn = connect()
    seed(conn, users=3, orders_each=1)

    email = "user1@example.com"
    row = conn.execute("SELECT name FROM users WHERE email = ?", (email,)).fetchone()
    print(f"  parameterised: {row['name']}")

    attack = "x' OR '1'='1"
    hostile = f"SELECT COUNT(*) AS n FROM users WHERE email = '{attack}'"  # noqa: S608
    print(f"  f-string query with input {attack!r} returned {conn.execute(hostile).fetchone()['n']}"
          f" of {conn.execute('SELECT COUNT(*) AS n FROM users').fetchone()['n']} rows")
    safe = conn.execute("SELECT COUNT(*) AS n FROM users WHERE email = ?", (attack,)).fetchone()
    print(f"  the same input, parameterised: {safe['n']} rows  <- treated as DATA")


def transactions() -> None:
    print("\n== transactions ==")
    conn = connect()
    seed(conn, users=2, orders_each=0)

    try:
        with conn:  # commits on success, rolls back on exception
            conn.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)", (99, "a@b.c", "a"))
            conn.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)", (98, "a@b.c", "b"))
    except sqlite3.IntegrityError as exc:
        print(f"  second insert violated UNIQUE: {exc}")

    remaining = conn.execute("SELECT COUNT(*) AS n FROM users WHERE id > 90").fetchone()["n"]
    print(f"  rows surviving the failed transaction: {remaining}  <- both rolled back")

    print("\n  constraints are enforced for every writer:")
    for sql, params, label in [
        ("INSERT INTO orders (user_id, amount, placed) VALUES (?, ?, ?)", (999, 5, "x"), "bad FK"),
        ("INSERT INTO orders (user_id, amount, placed) VALUES (?, ?, ?)", (1, -5, "x"), "CHECK"),
    ]:
        try:
            with conn:
                conn.execute(sql, params)
        except sqlite3.IntegrityError as exc:
            print(f"    {label}: {exc}")


def indexes() -> None:
    print("\n== indexes ==")
    conn = connect()
    seed(conn, users=500, orders_each=10)

    query = "SELECT * FROM orders WHERE user_id = ?"
    plan = conn.execute(f"EXPLAIN QUERY PLAN {query}", (5,)).fetchall()
    print(f"  before: {plan[0]['detail']}")

    start = time.perf_counter()
    for uid in range(1, 300):
        conn.execute(query, (uid,)).fetchall()
    before = time.perf_counter() - start

    conn.execute("CREATE INDEX idx_orders_user_id ON orders(user_id)")
    plan = conn.execute(f"EXPLAIN QUERY PLAN {query}", (5,)).fetchall()
    print(f"  after:  {plan[0]['detail']}")

    start = time.perf_counter()
    for uid in range(1, 300):
        conn.execute(query, (uid,)).fetchall()
    after = time.perf_counter() - start
    print(f"  300 lookups: {before * 1000:.1f} ms -> {after * 1000:.1f} ms ({before / after:.1f}x)")
    print("  every foreign key wants an index; the database won't add one for you")


def n_plus_one() -> None:
    print("\n== the N+1 problem ==")
    conn = connect()
    seed(conn, users=300, orders_each=5)
    conn.execute("CREATE INDEX idx_orders_user_id ON orders(user_id)")

    start = time.perf_counter()
    users = conn.execute("SELECT id FROM users").fetchall()
    totals_n1 = {}
    for user in users:  # 1 query...
        row = conn.execute(
            "SELECT SUM(amount) AS total FROM orders WHERE user_id = ?", (user["id"],)
        ).fetchone()  # ...+ N more
        totals_n1[user["id"]] = row["total"]
    n1_time = time.perf_counter() - start

    start = time.perf_counter()
    rows = conn.execute(
        """SELECT u.id, SUM(o.amount) AS total
           FROM users u LEFT JOIN orders o ON o.user_id = u.id
           GROUP BY u.id"""
    ).fetchall()
    totals_join = {r["id"]: r["total"] for r in rows}
    join_time = time.perf_counter() - start

    print(f"  N+1 ({len(users) + 1} queries): {n1_time * 1000:>7.2f} ms")
    print(f"  one join:              {join_time * 1000:>7.2f} ms  ({n1_time / join_time:.0f}x)")
    print(f"  identical results: {totals_n1 == totals_join}")
    print("  in-memory SQLite makes this look mild. Add 1 ms of network latency per query")
    print(f"  and the N+1 version costs {(len(users) + 1) / 1000:.1f}s while the join stays flat.")


def pagination() -> None:
    print("\n== offset vs keyset pagination ==")
    conn = connect()
    seed(conn, users=2000, orders_each=5)
    conn.execute("CREATE INDEX idx_orders_placed ON orders(placed, id)")

    start = time.perf_counter()
    conn.execute("SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 9000").fetchall()
    offset_time = time.perf_counter() - start

    start = time.perf_counter()
    conn.execute("SELECT * FROM orders WHERE id > ? ORDER BY id LIMIT 20", (9000,)).fetchall()
    keyset_time = time.perf_counter() - start

    print(f"  OFFSET 9000: {offset_time * 1000:.3f} ms  (walks 9020 rows)")
    print(f"  keyset:      {keyset_time * 1000:.3f} ms  (seeks straight there)")
    print("  and keyset doesn't skip or duplicate rows when someone inserts mid-scroll")


if __name__ == "__main__":
    print(INTRO)
    parameters()
    transactions()
    indexes()
    n_plus_one()
    pagination()
