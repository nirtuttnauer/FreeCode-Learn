import sqlite3
from decimal import Decimal

import pytest

from courselib import impl

m = impl("20")


@pytest.fixture
def conn():
    connection = m.connect()
    yield connection
    connection.close()


@pytest.fixture
def seeded(conn):
    ada = m.add_user(conn, "ada@example.com", "Ada Lovelace")
    bob = m.add_user(conn, "bob@example.com", "Bob Barker")
    m.add_user(conn, "cy@example.com", "Cy Nolan")  # no orders
    m.add_orders(
        conn,
        [
            (ada, 1000, "2026-01-01"),
            (ada, 250, "2026-01-03"),
            (bob, 500, "2026-01-02"),
        ],
    )
    return conn


class TestConnect:
    def test_row_factory(self, conn):
        conn.execute("INSERT INTO users (email, name) VALUES ('a@b.c', 'a')")
        row = conn.execute("SELECT name FROM users").fetchone()
        assert row["name"] == "a"

    def test_foreign_keys_are_on(self, conn):
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_schema_applied(self, conn):
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"users", "orders"} <= tables

    def test_foreign_key_is_enforced(self, conn):
        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                conn.execute(
                    "INSERT INTO orders (user_id, amount_cents, placed_at) VALUES (999, 1, 'x')"
                )


class TestAddUser:
    def test_returns_the_new_id(self, conn):
        assert m.add_user(conn, "a@b.c", "a") == 1
        assert m.add_user(conn, "b@b.c", "b") == 2

    def test_persists(self, conn):
        user_id = m.add_user(conn, "a@b.c", "Ada")
        assert conn.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()[0] == "Ada"

    def test_duplicate_email_raises(self, conn):
        m.add_user(conn, "a@b.c", "a")
        with pytest.raises(sqlite3.IntegrityError):
            m.add_user(conn, "a@b.c", "different name")

    def test_failed_insert_leaves_no_row(self, conn):
        m.add_user(conn, "a@b.c", "a")
        with pytest.raises(sqlite3.IntegrityError):
            m.add_user(conn, "a@b.c", "b")
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


class TestAddOrders:
    def test_returns_the_count(self, conn):
        uid = m.add_user(conn, "a@b.c", "a")
        assert m.add_orders(conn, [(uid, 100, "2026-01-01"), (uid, 200, "2026-01-02")]) == 2

    def test_empty_input(self, conn):
        assert m.add_orders(conn, []) == 0

    def test_whole_batch_rolls_back_on_a_bad_row(self, conn):
        uid = m.add_user(conn, "a@b.c", "a")
        with pytest.raises(sqlite3.IntegrityError):
            m.add_orders(conn, [(uid, 100, "ok"), (uid, -5, "negative")])
        assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


class TestFindUsers:
    def test_substring_match(self, seeded):
        assert [u["name"] for u in m.find_users(seeded, "Lovelace")] == ["Ada Lovelace"]

    def test_case_insensitive(self, seeded):
        assert len(m.find_users(seeded, "ada")) == 1

    def test_multiple_matches_ordered_by_id(self, seeded):
        results = m.find_users(seeded, "a")
        assert [u["id"] for u in results] == sorted(u["id"] for u in results)

    def test_no_match(self, seeded):
        assert m.find_users(seeded, "zzzz") == []

    def test_returns_plain_dicts(self, seeded):
        assert type(m.find_users(seeded, "Ada")[0]) is dict

    def test_sql_injection_is_treated_as_data(self, seeded):
        assert m.find_users(seeded, "' OR '1'='1") == []

    def test_wildcards_in_input_are_not_special_to_the_caller(self, seeded):
        # A literal % from a user shouldn't match everything by accident... but LIKE does
        # treat it as a wildcard. Knowing that is the lesson; escaping it is optional.
        assert isinstance(m.find_users(seeded, "%"), list)


class TestUserTotals:
    def test_totals(self, seeded):
        totals = {row["name"]: row["total"] for row in m.user_totals(seeded)}
        assert totals["Ada Lovelace"] == Decimal("12.50")
        assert totals["Bob Barker"] == Decimal("5.00")

    def test_users_without_orders_appear(self, seeded):
        row = next(r for r in m.user_totals(seeded) if r["name"] == "Cy Nolan")
        assert row["order_count"] == 0
        assert row["total"] == Decimal("0.00")

    def test_order_counts(self, seeded):
        counts = {r["name"]: r["order_count"] for r in m.user_totals(seeded)}
        assert counts["Ada Lovelace"] == 2

    def test_sorted_by_total_desc(self, seeded):
        names = [r["name"] for r in m.user_totals(seeded)]
        assert names == ["Ada Lovelace", "Bob Barker", "Cy Nolan"]

    def test_totals_are_decimals(self, seeded):
        assert all(isinstance(r["total"], Decimal) for r in m.user_totals(seeded))

    def test_uses_a_single_query(self, seeded):
        queries = []
        seeded.set_trace_callback(queries.append)
        m.user_totals(seeded)
        seeded.set_trace_callback(None)
        assert len(queries) == 1, f"expected 1 query, got {len(queries)}: {queries}"


class TestTransaction:
    def test_commits_on_success(self, conn):
        with m.transaction(conn):
            conn.execute("INSERT INTO users (email, name) VALUES ('a@b.c', 'a')")
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1

    def test_rolls_back_on_exception(self, conn):
        with pytest.raises(RuntimeError), m.transaction(conn):
            conn.execute("INSERT INTO users (email, name) VALUES ('a@b.c', 'a')")
            raise RuntimeError("boom")
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0

    def test_yields_the_connection(self, conn):
        with m.transaction(conn) as c:
            assert c is conn

    def test_nested_inner_failure_does_not_kill_the_outer(self, conn):
        with m.transaction(conn):
            conn.execute("INSERT INTO users (email, name) VALUES ('keep@b.c', 'keep')")
            with pytest.raises(ValueError), m.transaction(conn):
                conn.execute("INSERT INTO users (email, name) VALUES ('drop@b.c', 'drop')")
                raise ValueError("inner failed")
            conn.execute("INSERT INTO users (email, name) VALUES ('also@b.c', 'also')")

        names = {r[0] for r in conn.execute("SELECT name FROM users")}
        assert names == {"keep", "also"}

    def test_nested_success(self, conn):
        with m.transaction(conn):
            conn.execute("INSERT INTO users (email, name) VALUES ('a@b.c', 'a')")
            with m.transaction(conn):
                conn.execute("INSERT INTO users (email, name) VALUES ('b@b.c', 'b')")
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2

    def test_exception_is_reraised(self, conn):
        with pytest.raises(KeyError), m.transaction(conn):
            raise KeyError("propagates")


class TestPageOrders:
    @pytest.fixture
    def many(self, conn):
        uid = m.add_user(conn, "a@b.c", "a")
        m.add_orders(conn, [(uid, i, f"2026-01-{(i % 28) + 1:02d}") for i in range(50)])
        return conn

    def test_first_page(self, many):
        rows, cursor = m.page_orders(many, limit=10)
        assert len(rows) == 10
        assert cursor is not None

    def test_newest_first(self, many):
        rows, _ = m.page_orders(many, limit=5)
        placed = [r["placed_at"] for r in rows]
        assert placed == sorted(placed, reverse=True)

    def test_walks_the_whole_table_without_duplicates(self, many):
        seen, cursor = [], None
        while True:
            rows, cursor = m.page_orders(many, limit=7, cursor=cursor)
            seen.extend(r["id"] for r in rows)
            if cursor is None:
                break
        assert len(seen) == 50
        assert len(set(seen)) == 50

    def test_last_page_has_no_cursor(self, many):
        rows, cursor = m.page_orders(many, limit=100)
        assert len(rows) == 50
        assert cursor is None

    def test_empty_table(self, conn):
        assert m.page_orders(conn) == ([], None)

    def test_rejects_bad_limit(self, conn):
        with pytest.raises(ValueError):
            m.page_orders(conn, limit=0)


class TestStreamOrders:
    def test_yields_everything(self, conn):
        uid = m.add_user(conn, "a@b.c", "a")
        m.add_orders(conn, [(uid, i, "2026-01-01") for i in range(250)])
        assert len(list(m.stream_orders(conn, batch_size=10))) == 250

    def test_is_lazy(self, conn):
        uid = m.add_user(conn, "a@b.c", "a")
        m.add_orders(conn, [(uid, i, "2026-01-01") for i in range(100)])
        stream = m.stream_orders(conn, batch_size=10)
        assert not isinstance(stream, list)
        assert next(stream)["amount_cents"] == 0

    def test_empty_table(self, conn):
        assert list(m.stream_orders(conn)) == []

    def test_rejects_bad_batch_size(self, conn):
        with pytest.raises(ValueError):
            list(m.stream_orders(conn, batch_size=0))


class TestCentsToDecimal:
    @pytest.mark.parametrize(
        ("cents", "expected"),
        [(1250, "12.50"), (0, "0.00"), (5, "0.05"), (100, "1.00"), (999999, "9999.99")],
    )
    def test_conversion(self, cents, expected):
        assert m.cents_to_decimal(cents) == Decimal(expected)

    def test_returns_decimal(self):
        assert isinstance(m.cents_to_decimal(1), Decimal)

    def test_two_decimal_places(self):
        assert str(m.cents_to_decimal(100)) == "1.00"

    def test_exact_arithmetic(self):
        total = sum((m.cents_to_decimal(10) for _ in range(3)), Decimal(0))
        assert total == Decimal("0.30")  # 0.1 * 3 as floats would not be
