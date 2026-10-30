# 20 — Databases: SQL, `sqlite3`, and ORMs

Most Python jobs are, underneath, a program that talks to a database. This module is the
part that transfers between every driver and every ORM.

We use stdlib **`sqlite3`** so there's nothing to install and nothing to run — but every
technique here (parameters, transactions, indexes, keyset pagination, connection scope)
is identical against Postgres.

## In plain English

Most real programs are, underneath, something that talks to a database. The good news is
that the important ideas transfer everywhere — learn them on SQLite (which needs no setup at
all) and they work identically against Postgres.

The most important one is **SQL injection**, and it's easiest to understand through the
famous cartoon: a school asks for a student's name, and the parents have named their child
`Robert'); DROP TABLE Students;--`. The school's software glues that name straight into a
database command, the database reads it as *instructions* rather than a *name*, and the
entire student table is deleted.

The fix takes one character. Instead of building the command by gluing text together, you
leave a hole (`?`) and hand the value separately. The database then treats it as data, full
stop — it could be Shakespeare or a virus, it's still just a name.

The other big idea is **indexes**. A database without an index reads every row to answer a
question, like reading a whole book to find one word. An index is the book's index: it goes
straight there. The lesson measures a query getting ~15× faster from adding one line.

**Watch out for:** the "N+1" problem — fetching a list of 100 things, then making 100 more
queries to get each one's details. It's invisible with 10 rows of test data and catastrophic
in production.

## 1. Parameters, always

```python
cur.execute("SELECT * FROM users WHERE email = ?", (email,))          # sqlite3
cur.execute("SELECT * FROM users WHERE email = %s", (email,))         # psycopg
cur.execute("SELECT * FROM users WHERE email = :email", {"email": e}) # named
```

```python
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")           # NEVER
```

That f-string is SQL injection. Not "a risk" — the vulnerability itself. Parameters are
also *faster*, because the driver and server can reuse the prepared plan.

Note the trailing comma in `(email,)`: a bare `(email)` is not a tuple, and the error
message won't tell you that.

Identifiers (table and column names) **can't** be parameterised. If one must be dynamic,
validate it against an allow-list you control — never interpolate user input.

## 2. Connections, cursors, transactions

```python
conn = sqlite3.connect("app.db", isolation_level=None)   # autocommit off at the driver
conn.row_factory = sqlite3.Row                           # rows behave like dicts
conn.execute("PRAGMA foreign_keys = ON")                 # sqlite: OFF by default!
conn.execute("PRAGMA journal_mode = WAL")                # concurrent readers
```

```python
with conn:                      # commits on success, ROLLS BACK on exception
    conn.execute("INSERT INTO ...", params)
    conn.execute("UPDATE ...", params)
```

`with conn:` manages the **transaction**, not the connection — the connection stays open.
Close it yourself, or wrap it in `contextlib.closing`.

Rules:
- One transaction per unit of work. Not per statement, not per request-with-five-writes.
- Keep transactions **short**: never do HTTP calls or user interaction inside one.
- A connection is not thread-safe; use one per thread, or a pool.

`executemany` for bulk writes — one round trip instead of N:

```python
conn.executemany("INSERT INTO users (name, email) VALUES (?, ?)", rows)
```

## 3. Schema and constraints

```sql
CREATE TABLE users (
    id         INTEGER PRIMARY KEY,
    email      TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE orders (
    id       INTEGER PRIMARY KEY,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount   REAL    NOT NULL CHECK (amount >= 0)
);
CREATE INDEX idx_orders_user_id ON orders(user_id);
```

Put invariants in the schema. `NOT NULL`, `UNIQUE`, `CHECK` and foreign keys are enforced
for *every* writer, including the migration script someone runs at 2am. Application-level
validation is a nicer error message, not a guarantee.

## 4. Indexes — the 90% of query performance

- An index makes reads fast and writes slower. Index what you filter, join and sort on.
- **Every foreign key needs an index.** Most databases don't create one for you.
- Composite indexes are ordered: `(a, b)` serves `WHERE a = ?` and `WHERE a = ? AND b = ?`,
  but not `WHERE b = ?` alone.
- A function on the column defeats the index: `WHERE lower(email) = ?` needs an index on
  `lower(email)`.
- `EXPLAIN QUERY PLAN` (sqlite) / `EXPLAIN ANALYZE` (Postgres) tells you what actually
  happened. `SCAN TABLE` on a big table is your bug.

## 5. The N+1 problem

```python
for user in fetch_users():                       # 1 query
    orders = fetch_orders(user.id)               # ...and N more
```

Fix with a join, or one `WHERE user_id IN (...)` followed by grouping in Python. In an ORM
this is `select_related`/`joinedload`/`selectinload`. It is the single most common
performance bug in database-backed apps, and it never shows up on a dev machine with 10
rows.

## 6. Pagination

`LIMIT 20 OFFSET 10000` makes the database walk 10,020 rows, and rows shift under a
concurrent insert so users see duplicates. Use **keyset (cursor) pagination**:

```sql
SELECT * FROM orders WHERE (created_at, id) < (?, ?) ORDER BY created_at DESC, id DESC LIMIT 20
```

Constant time at any depth, and stable under concurrent writes.

## 7. ORMs

**SQLAlchemy 2.0** is the default choice; Django's ORM if you're in Django; `SQLModel`
(pydantic + SQLAlchemy) pairs well with FastAPI. `asyncpg` when you want raw async speed.

```python
stmt = select(User).where(User.email == email).options(selectinload(User.orders))
user = session.scalars(stmt).one_or_none()
```

What an ORM buys: mapping, identity, unit of work, migrations, portability.
What it costs: hidden queries, lazy-loading surprises, and a leaky abstraction the day you
need a window function. Know the SQL your ORM emits — turn on `echo=True` once and read it.

**Migrations** (`alembic`, Django migrations) are not optional. Every schema change is a
reviewed, versioned, reversible script — and for a live system, an expand/contract dance:
add the column, backfill, switch reads, then drop the old one.

## 8. Money and time

Never store money as a float. `NUMERIC`/`DECIMAL` in the database, `decimal.Decimal` in
Python (module 01). Store timestamps as UTC (`TIMESTAMPTZ` in Postgres), and convert only
for display (module 19).

## Exercises

`exercises_20.py`, then `pytest 20_databases`. Everything runs against an in-memory
SQLite database, so the suite is instant.

## Further reading

- [`sqlite3` docs](https://docs.python.org/3/library/sqlite3.html)
- [Use The Index, Luke](https://use-the-index-luke.com/) — the best free SQL-performance resource
- [SQLAlchemy 2.0 ORM tutorial](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
