import pytest

from courselib import impl

m = impl("07")


class TestStack:
    def test_push_returns_self_for_chaining(self):
        s = m.Stack()
        assert s.push(1) is s
        assert len(m.Stack().push(1).push(2)) == 2

    def test_lifo(self):
        s = m.Stack()
        s.push(1).push(2)
        assert s.pop() == 2
        assert s.pop() == 1

    def test_peek_does_not_remove(self):
        s = m.Stack().push(1)
        assert s.peek() == 1
        assert len(s) == 1

    def test_pop_empty_raises(self):
        with pytest.raises(IndexError, match="empty"):
            m.Stack().pop()

    def test_peek_empty_raises(self):
        with pytest.raises(IndexError):
            m.Stack().peek()

    def test_truthiness(self):
        assert not m.Stack()
        assert m.Stack().push(1)

    def test_iterates_top_first(self):
        s = m.Stack()
        s.push(1).push(2).push(3)
        assert list(s) == [3, 2, 1]

    def test_clear(self):
        s = m.Stack().push(1)
        s.clear()
        assert len(s) == 0

    def test_repr(self):
        s = m.Stack()
        s.push(1).push(2)
        assert repr(s) == "Stack([1, 2])"

    def test_subscripting_the_class_works(self):
        assert m.Stack[int]().push(1).pop() == 1

    def test_instances_are_independent(self):
        a, b = m.Stack(), m.Stack()
        a.push(1)
        assert len(b) == 0


class TestCloseAll:
    def test_closes_everything(self):
        closed = []

        class Thing:
            def __init__(self, name):
                self.name = name

            def close(self):
                closed.append(self.name)

        assert m.close_all([Thing("a"), Thing("b")]) == []
        assert closed == ["a", "b"]

    def test_keeps_going_after_a_failure(self):
        closed = []

        class Bad:
            def close(self):
                raise OSError("cannot close")

        class Good:
            def close(self):
                closed.append("good")

        errors = m.close_all([Bad(), Good(), Bad()])
        assert closed == ["good"]
        assert len(errors) == 2
        assert all(isinstance(e, OSError) for e in errors)

    def test_empty_input(self):
        assert m.close_all([]) == []

    def test_protocol_is_runtime_checkable(self):
        class Thing:
            def close(self):
                pass

        assert isinstance(Thing(), m.SupportsClose)
        assert not isinstance(object(), m.SupportsClose)


class TestParseUser:
    def test_valid(self):
        assert m.parse_user({"id": 1, "name": "ada", "email": "a@b.c"}) == {
            "id": 1,
            "name": "ada",
            "email": "a@b.c",
        }

    def test_coerces_string_id(self):
        assert m.parse_user({"id": "42", "name": "n", "email": "a@b"})["id"] == 42

    def test_strips_name(self):
        assert m.parse_user({"id": 1, "name": "  ada  ", "email": "a@b"})["name"] == "ada"

    def test_drops_extra_keys(self):
        got = m.parse_user({"id": 1, "name": "n", "email": "a@b", "admin": True})
        assert set(got) == {"id", "name", "email"}

    @pytest.mark.parametrize(
        ("raw", "field"),
        [
            ({"name": "n", "email": "a@b"}, "id"),
            ({"id": "abc", "name": "n", "email": "a@b"}, "id"),
            ({"id": True, "name": "n", "email": "a@b"}, "id"),
            ({"id": 1, "email": "a@b"}, "name"),
            ({"id": 1, "name": "   ", "email": "a@b"}, "name"),
            ({"id": 1, "name": 5, "email": "a@b"}, "name"),
            ({"id": 1, "name": "n"}, "email"),
            ({"id": 1, "name": "n", "email": "nope"}, "email"),
            ({"id": 1, "name": "n", "email": None}, "email"),
        ],
    )
    def test_rejects_bad_input(self, raw, field):
        with pytest.raises(ValueError, match=field):
            m.parse_user(raw)

    def test_result_is_a_plain_dict(self):
        assert type(m.parse_user({"id": 1, "name": "n", "email": "a@b"})) is dict


class TestCounted:
    def test_counts(self):
        @m.counted
        def f(n):
            return n

        assert f.calls == 0
        f(1)
        f(2)
        assert f.calls == 2

    def test_reset(self):
        @m.counted
        def f():
            pass

        f()
        f.reset()
        assert f.calls == 0

    def test_return_value_passes_through(self):
        @m.counted
        def add(a, b=0):
            return a + b

        assert add(1, b=2) == 3

    def test_exceptions_propagate_and_still_count(self):
        @m.counted
        def boom():
            raise ValueError

        with pytest.raises(ValueError):
            boom()
        assert boom.calls == 1

    def test_preserves_metadata(self):
        @m.counted
        def documented():
            """Docs."""

        assert documented.__name__ == "documented"
        assert documented.__doc__ == "Docs."

    def test_separate_counters_per_function(self):
        @m.counted
        def a():
            pass

        @m.counted
        def b():
            pass

        a()
        assert b.calls == 0


class TestResult:
    def test_ok_and_err_construction(self):
        assert m.Ok(1).value == 1
        assert m.Err("bad").error == "bad"

    def test_is_ok(self):
        assert m.is_ok(m.Ok(1))
        assert not m.is_ok(m.Err("bad"))

    def test_unwrap_or(self):
        assert m.unwrap_or(m.Ok(5), 0) == 5
        assert m.unwrap_or(m.Err("bad"), 0) == 0

    def test_unwrap_or_with_falsy_value(self):
        assert m.unwrap_or(m.Ok(0), 99) == 0
        assert m.unwrap_or(m.Ok(None), 99) is None

    def test_map_ok(self):
        assert m.map_ok(m.Ok(2), lambda n: n * 3) == m.Ok(6)

    def test_map_passes_err_through(self):
        err = m.Err("bad")
        assert m.map_ok(err, lambda n: n * 3) is err

    def test_map_catches_exceptions(self):
        result = m.map_ok(m.Ok(0), lambda n: 1 / n)
        assert not m.is_ok(result)
        assert isinstance(result.error, ZeroDivisionError)

    def test_chaining(self):
        result = m.map_ok(m.map_ok(m.Ok(2), lambda n: n + 1), str)
        assert m.unwrap_or(result, "") == "3"

    def test_frozen_and_equal_by_value(self):
        assert m.Ok(1) == m.Ok(1)
        with pytest.raises(Exception):
            m.Ok(1).value = 2
