"""Module 09 exercises.  pytest 09_testing

Theme: make the untestable testable. Time, sleeping and randomness all arrive as
parameters with production-sane defaults.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any

UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    """Parse a human duration into whole seconds.

    >>> parse_duration("1h30m")
    5400
    >>> parse_duration("2d")
    172800
    >>> parse_duration("1h 30m 10s")
    5410
    >>> parse_duration("90")
    90

    Rules:
    - Units: d, h, m, s (case-insensitive). Whitespace anywhere is ignored.
    - A bare number means seconds — but ONLY when it is the entire input. Once any unit
      appears, every number needs one, so "1h30" is a ValueError, not 1h30m. (Ambiguous
      input formats are how you end up with a bug report about a 30-second timeout.)
    - Units may appear in any order and repeat; the values add up ("1m1m" == 120).
    - Empty/blank input, unknown units, a unit with no number, or any leftover junk
      raise ValueError.
    - Negative numbers raise ValueError.

    A good candidate for a hypothesis round-trip property — see the README challenge.
    """
    raise NotImplementedError


def format_duration(seconds: int) -> str:
    """The inverse of `parse_duration`, using the largest units first.

    >>> format_duration(5410)
    '1h30m10s'
    >>> format_duration(0)
    '0s'
    >>> format_duration(86400)
    '1d'

    Skip zero components (172800 -> "2d", not "2d0h0m0s"). Negative input raises ValueError.
    `parse_duration(format_duration(n)) == n` must hold for every n >= 0.
    """
    raise NotImplementedError


def roman_encode(number: int) -> str:
    """Convert 1..3999 to a Roman numeral, subtractive form.

    >>> roman_encode(1994)
    'MCMXCIV'

    Outside 1..3999 raises ValueError. Non-int raises TypeError.
    """
    raise NotImplementedError


def roman_decode(numeral: str) -> int:
    """Convert a Roman numeral back to an int (case-insensitive).

    >>> roman_decode("MCMXCIV")
    1994

    Invalid characters, an empty string, or a numeral that doesn't round-trip
    (e.g. "IIII", "IC") raise ValueError. The easy way to enforce canonical form:
    decode it, then check `roman_encode(value)` equals the input.
    """
    raise NotImplementedError


class TokenBucket:
    """A rate limiter you can test without waiting.

    - `TokenBucket(capacity=10, refill_per_second=1, clock=time.monotonic)`
    - Starts full.
    - `.allow(cost=1) -> bool`: refill first based on elapsed time, then spend if enough
      tokens are available. Never refill above capacity.
    - `.tokens` reports the current balance (after refilling — a property, not a stale field).
    - capacity <= 0 or refill_per_second < 0 raise ValueError.
    - `.allow(cost)` with cost <= 0 raises ValueError.

    The `clock` parameter is the whole exercise: the tests drive it by hand, so a
    "one hour later" case runs instantly. Use a MONOTONIC clock in production —
    `time.time()` can jump backwards when NTP corrects the system clock.
    """

    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        raise NotImplementedError


def retry_with_backoff(
    func: Callable[[], Any],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleeper: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
) -> Any:
    """Call `func()`, retrying with exponential backoff and full jitter.

    - Attempt n (0-based) sleeps `min(base_delay * 2**n, max_delay) * jitter()`.
    - No sleep after the final attempt; the last exception is re-raised.
    - Only `exceptions` are retried; anything else propagates immediately.
    - `attempts < 1` raises ValueError.

    Jitter matters in production: without it, every client that failed at the same
    moment retries at the same moment (the "thundering herd"). Injecting it means the
    tests still see exact, predictable delays.
    """
    raise NotImplementedError
