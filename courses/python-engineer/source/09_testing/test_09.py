"""Graded tests for module 09 — and a demonstration of the techniques themselves.

Read this file as a worked example: parametrize, fixtures, injected clocks, recording
doubles, and hypothesis properties, all in one place.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from courselib import impl

m = impl("09")


class TestParseDuration:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("1h30m", 5400),
            ("2d", 172800),
            ("90s", 90),
            ("90", 90),
            ("1h 30m 10s", 5410),
            ("  1h  ", 3600),
            ("1H30M", 5400),
            ("30m1h", 5400),
            ("1m1m", 120),
            ("0s", 0),
        ],
    )
    def test_valid(self, raw, expected):
        assert m.parse_duration(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", "abc", "1x", "h", "1h30", "-5s", "1..5h", "s1"])
    def test_invalid(self, raw):
        with pytest.raises(ValueError):
            m.parse_duration(raw)

    def test_bare_number_is_seconds(self):
        assert m.parse_duration("3600") == 3600


class TestFormatDuration:
    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [(5410, "1h30m10s"), (0, "0s"), (86400, "1d"), (172800, "2d"), (59, "59s"), (60, "1m")],
    )
    def test_valid(self, seconds, expected):
        assert m.format_duration(seconds) == expected

    def test_skips_zero_components(self):
        assert m.format_duration(86460) == "1d1m"

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            m.format_duration(-1)

    @given(st.integers(min_value=0, max_value=10**7))
    def test_roundtrip_property(self, seconds):
        # The property that matters: formatting then parsing is the identity.
        assert m.parse_duration(m.format_duration(seconds)) == seconds


class TestRoman:
    @pytest.mark.parametrize(
        ("number", "numeral"),
        [(1, "I"), (4, "IV"), (9, "IX"), (14, "XIV"), (40, "XL"), (1994, "MCMXCIV"),
         (3999, "MMMCMXCIX"), (2024, "MMXXIV")],
    )
    def test_encode(self, number, numeral):
        assert m.roman_encode(number) == numeral

    @pytest.mark.parametrize(
        ("number", "numeral"), [(1, "I"), (1994, "MCMXCIV"), (3999, "MMMCMXCIX")]
    )
    def test_decode(self, number, numeral):
        assert m.roman_decode(numeral) == number

    def test_decode_is_case_insensitive(self):
        assert m.roman_decode("mcmxciv") == 1994

    @pytest.mark.parametrize("number", [0, -1, 4000, 10**6])
    def test_encode_out_of_range(self, number):
        with pytest.raises(ValueError):
            m.roman_encode(number)

    def test_encode_rejects_non_int(self):
        with pytest.raises(TypeError):
            m.roman_encode("5")

    @pytest.mark.parametrize("numeral", ["", "ABC", "IIII", "IC", "VV", "XM", "I I"])
    def test_decode_rejects_invalid(self, numeral):
        with pytest.raises(ValueError):
            m.roman_decode(numeral)

    @given(st.integers(min_value=1, max_value=3999))
    def test_roundtrip_property(self, number):
        assert m.roman_decode(m.roman_encode(number)) == number

    @given(st.integers(min_value=1, max_value=3998))
    def test_monotonic_length_property(self, number):
        # An oracle-style invariant: encoding never produces an empty string.
        assert len(m.roman_encode(number)) >= 1


class FakeClock:
    """A clock the test drives by hand. No sleeping, no flakiness."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestTokenBucket:
    @pytest.fixture
    def clock(self) -> FakeClock:
        return FakeClock()

    @pytest.fixture
    def bucket(self, clock):
        return m.TokenBucket(capacity=10, refill_per_second=1, clock=clock)

    def test_starts_full(self, bucket):
        assert bucket.tokens == 10

    def test_spends_tokens(self, bucket):
        assert bucket.allow()
        assert bucket.tokens == 9

    def test_denies_when_empty(self, bucket):
        for _ in range(10):
            assert bucket.allow()
        assert not bucket.allow()

    def test_refills_over_time(self, bucket, clock):
        for _ in range(10):
            bucket.allow()
        assert not bucket.allow()
        clock.advance(3)
        assert bucket.tokens == pytest.approx(3)
        assert bucket.allow()

    def test_never_refills_above_capacity(self, bucket, clock):
        bucket.allow()
        clock.advance(3600)  # an hour later — instantly
        assert bucket.tokens == 10

    def test_variable_cost(self, bucket):
        assert bucket.allow(cost=10)
        assert not bucket.allow(cost=1)

    def test_cost_larger_than_capacity_is_never_allowed(self, bucket):
        assert not bucket.allow(cost=11)

    def test_rejects_bad_cost(self, bucket):
        with pytest.raises(ValueError):
            bucket.allow(cost=0)

    @pytest.mark.parametrize(("capacity", "rate"), [(0, 1), (-1, 1), (10, -1)])
    def test_rejects_bad_config(self, capacity, rate):
        with pytest.raises(ValueError):
            m.TokenBucket(capacity=capacity, refill_per_second=rate)

    def test_zero_refill_rate_never_recovers(self, clock):
        bucket = m.TokenBucket(capacity=1, refill_per_second=0, clock=clock)
        assert bucket.allow()
        clock.advance(10_000)
        assert not bucket.allow()

    def test_fractional_refill(self, clock):
        bucket = m.TokenBucket(capacity=10, refill_per_second=0.5, clock=clock)
        bucket.allow(cost=10)
        clock.advance(4)
        assert bucket.tokens == pytest.approx(2)


class TestRetryWithBackoff:
    def test_returns_on_first_success(self):
        assert m.retry_with_backoff(lambda: "ok", sleeper=lambda _: None) == "ok"

    def test_retries_until_success(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise TimeoutError
            return "recovered"

        assert m.retry_with_backoff(flaky, sleeper=lambda _: None, jitter=lambda: 1.0) == "recovered"
        assert len(calls) == 3

    def test_exponential_delays_with_jitter(self):
        slept = []

        def always():
            raise ValueError

        with pytest.raises(ValueError):
            m.retry_with_backoff(
                always, attempts=4, base_delay=1, sleeper=slept.append, jitter=lambda: 0.5
            )
        assert slept == [0.5, 1.0, 2.0]  # 1*0.5, 2*0.5, 4*0.5 — and no sleep after the last

    def test_max_delay_caps_growth(self):
        slept = []
        with pytest.raises(ValueError):
            m.retry_with_backoff(
                lambda: (_ for _ in ()).throw(ValueError()),
                attempts=6,
                base_delay=1,
                max_delay=3,
                sleeper=slept.append,
                jitter=lambda: 1.0,
            )
        assert slept == [1, 2, 3, 3, 3]

    def test_unlisted_exception_is_not_retried(self):
        calls = []

        def boom():
            calls.append(1)
            raise KeyError

        with pytest.raises(KeyError):
            m.retry_with_backoff(boom, exceptions=(ValueError,), sleeper=lambda _: None)
        assert len(calls) == 1

    def test_single_attempt_never_sleeps(self):
        slept = []
        with pytest.raises(ValueError):
            m.retry_with_backoff(
                lambda: (_ for _ in ()).throw(ValueError()), attempts=1, sleeper=slept.append
            )
        assert slept == []

    def test_rejects_bad_attempts(self):
        with pytest.raises(ValueError):
            m.retry_with_backoff(lambda: 1, attempts=0)

    def test_does_not_sleep_for_real(self):
        import time as real_time

        start = real_time.perf_counter()
        with pytest.raises(ValueError):
            m.retry_with_backoff(
                lambda: (_ for _ in ()).throw(ValueError()),
                attempts=5,
                base_delay=100,
                sleeper=lambda _: None,
            )
        assert real_time.perf_counter() - start < 0.5
