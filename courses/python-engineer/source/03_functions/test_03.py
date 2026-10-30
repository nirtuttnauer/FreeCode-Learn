import pytest

from courselib import impl

m = impl("03")


class TestCompose:
    def test_right_to_left(self):
        assert m.compose(str, lambda n: n + 1)(41) == "42"

    def test_identity_when_empty(self):
        assert m.compose()(7) == 7

    def test_single_function(self):
        assert m.compose(abs)(-3) == 3

    def test_three_deep(self):
        f = m.compose(lambda s: s + "!", str.upper, str.strip)
        assert f("  hi  ") == "HI!"

    def test_reusable(self):
        f = m.compose(lambda n: n * 2)
        assert (f(1), f(2)) == (2, 4)


class TestMemoize:
    def test_caches_by_args(self):
        calls = []

        @m.memoize
        def slow(n):
            calls.append(n)
            return n * 2

        assert (slow(2), slow(2), slow(3)) == (4, 4, 6)
        assert calls == [2, 3]

    def test_kwargs_are_part_of_the_key(self):
        @m.memoize
        def f(a, b=0):
            return a + b

        assert f(1, b=2) == 3
        assert f(1, b=5) == 6

    def test_kwarg_order_does_not_matter(self):
        calls = []

        @m.memoize
        def f(**kw):
            calls.append(kw)
            return sum(kw.values())

        f(a=1, b=2)
        f(b=2, a=1)
        assert len(calls) == 1

    def test_caches_none_results(self):
        calls = []

        @m.memoize
        def f(n):
            calls.append(n)
            return

        f(1)
        f(1)
        assert len(calls) == 1

    def test_exposes_cache_and_clear(self):
        @m.memoize
        def f(n):
            return n

        f(1)
        assert len(f.cache) == 1
        f.cache_clear()
        assert len(f.cache) == 0

    def test_preserves_metadata(self):
        @m.memoize
        def documented(n):
            """Doc string."""
            return n

        assert documented.__name__ == "documented"
        assert documented.__doc__ == "Doc string."
        assert hasattr(documented, "__wrapped__")

    def test_recursion_works(self):
        @m.memoize
        def fib(n):
            return n if n < 2 else fib(n - 1) + fib(n - 2)

        assert fib(60) == 1548008755920


class TestMakeAccumulator:
    def test_accumulates(self):
        acc = m.make_accumulator(10)
        assert (acc(5), acc(5)) == (15, 20)

    def test_default_start_is_zero(self):
        assert m.make_accumulator()(3) == 3

    def test_independent_instances(self):
        a, b = m.make_accumulator(), m.make_accumulator()
        a(100)
        assert b(1) == 1

    def test_reset(self):
        acc = m.make_accumulator(5)
        acc(10)
        acc.reset()
        assert acc(1) == 6


class TestAppendTo:
    def test_creates_a_fresh_list_each_call(self):
        assert (m.append_to(1), m.append_to(2)) == ([1], [2])

    def test_uses_the_given_list(self):
        target = [0]
        assert m.append_to(1, target) is target
        assert target == [0, 1]

    def test_still_fresh_after_many_calls(self):
        for _ in range(5):
            assert len(m.append_to("x")) == 1


class TestRetry:
    def test_succeeds_first_try(self):
        calls = []

        @m.retry(3, sleeper=lambda _: None)
        def ok():
            calls.append(1)
            return "fine"

        assert ok() == "fine"
        assert len(calls) == 1

    def test_retries_until_success(self):
        attempts = []

        @m.retry(3, sleeper=lambda _: None)
        def flaky():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("not yet")
            return "recovered"

        assert flaky() == "recovered"
        assert len(attempts) == 3

    def test_reraises_after_exhausting(self):
        attempts = []

        @m.retry(2, sleeper=lambda _: None)
        def always():
            attempts.append(1)
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            always()
        assert len(attempts) == 2

    def test_unlisted_exception_is_not_retried(self):
        attempts = []

        @m.retry(5, exceptions=(ValueError,), sleeper=lambda _: None)
        def wrong_error():
            attempts.append(1)
            raise KeyError("different")

        with pytest.raises(KeyError):
            wrong_error()
        assert len(attempts) == 1

    def test_sleeps_between_attempts_but_not_after_the_last(self):
        slept = []

        @m.retry(3, delay=0.25, sleeper=slept.append)
        def always():
            raise ValueError

        with pytest.raises(ValueError):
            always()
        assert slept == [0.25, 0.25]

    def test_rejects_bad_times(self):
        with pytest.raises(ValueError):
            m.retry(0)

    def test_passes_through_arguments(self):
        @m.retry(2, sleeper=lambda _: None)
        def add(a, b=0):
            return a + b

        assert add(1, b=2) == 3

    def test_preserves_metadata(self):
        @m.retry(1)
        def named():
            """Docs."""

        assert named.__name__ == "named"
        assert named.__doc__ == "Docs."


class TestCurry:
    def test_all_arities(self):
        add3 = m.curry(lambda a, b, c: a + b + c)
        assert add3(1)(2)(3) == 6
        assert add3(1, 2)(3) == 6
        assert add3(1)(2, 3) == 6
        assert add3(1, 2, 3) == 6

    def test_partial_is_reusable_and_stateless(self):
        add3 = m.curry(lambda a, b, c: a + b + c)
        f = add3(1)
        assert f(2)(3) == 6
        assert f(10)(10) == 21

    def test_single_argument_function(self):
        assert m.curry(abs)(-4) == 4

    def test_works_on_real_functions(self):
        def volume(w, h, d):
            return w * h * d

        assert m.curry(volume)(2)(3)(4) == 24
