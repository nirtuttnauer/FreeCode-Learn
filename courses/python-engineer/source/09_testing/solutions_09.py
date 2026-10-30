"""Module 09 — reference solutions."""

from __future__ import annotations

import random
import re
import time
from collections.abc import Callable
from typing import Any

UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}
_TOKEN = re.compile(r"(\d+)([dhms]?)")
_ROMAN = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]  # fmt: skip


def parse_duration(text: str) -> int:
    compact = "".join(text.split()).lower()
    if not compact:
        raise ValueError("empty duration")
    if compact.startswith("-"):
        raise ValueError(f"negative duration: {text!r}")

    if compact.isdigit():  # a bare number is seconds, but only on its own
        return int(compact)

    total = 0
    position = 0
    for match in _TOKEN.finditer(compact):
        if match.start() != position:  # something unparsable in between
            raise ValueError(f"invalid duration: {text!r}")
        amount, unit = match.groups()
        if not unit:  # "1h30" — ambiguous, so rejected
            raise ValueError(f"missing unit in {text!r}")
        total += int(amount) * UNITS[unit]
        position = match.end()
    if position != len(compact):
        raise ValueError(f"invalid duration: {text!r}")
    return total


def format_duration(seconds: int) -> str:
    if seconds < 0:
        raise ValueError(f"negative duration: {seconds}")
    if seconds == 0:
        return "0s"
    parts = []
    for unit, size in UNITS.items():
        count, seconds = divmod(seconds, size)
        if count:
            parts.append(f"{count}{unit}")
    return "".join(parts)


def roman_encode(number: int) -> str:
    if isinstance(number, bool) or not isinstance(number, int):
        raise TypeError(f"expected int, got {type(number).__name__}")
    if not 1 <= number <= 3999:
        raise ValueError(f"out of range: {number}")
    out = []
    for value, symbol in _ROMAN:
        count, number = divmod(number, value)
        out.append(symbol * count)
    return "".join(out)


def roman_decode(numeral: str) -> int:
    if not isinstance(numeral, str) or not numeral:
        raise ValueError("empty numeral")
    text = numeral.upper()
    values = {s: v for v, s in _ROMAN if len(s) == 1}
    if any(ch not in values for ch in text):
        raise ValueError(f"invalid numeral: {numeral!r}")

    total = 0
    previous = 0
    for char in reversed(text):  # right-to-left makes subtractive pairs trivial
        value = values[char]
        total += -value if value < previous else value
        previous = max(previous, value)

    # Canonical-form check: only one spelling of each number is legal.
    if not 1 <= total <= 3999 or roman_encode(total) != text:
        raise ValueError(f"non-canonical numeral: {numeral!r}")
    return total


class TokenBucket:
    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be > 0, got {capacity}")
        if refill_per_second < 0:
            raise ValueError(f"refill_per_second must be >= 0, got {refill_per_second}")
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.clock = clock
        self._tokens = float(capacity)  # starts full
        self._last = clock()

    def _refill(self) -> None:
        now = self.clock()
        elapsed = max(0.0, now - self._last)  # a non-monotonic clock can't make us lose tokens
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_second)
        self._last = now

    @property
    def tokens(self) -> float:
        self._refill()
        return self._tokens

    def allow(self, cost: float = 1) -> bool:
        if cost <= 0:
            raise ValueError(f"cost must be > 0, got {cost}")
        self._refill()
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False


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
    if attempts < 1:
        raise ValueError(f"attempts must be >= 1, got {attempts}")

    for attempt in range(attempts):
        try:
            return func()
        except exceptions:
            if attempt == attempts - 1:
                raise
            delay = min(base_delay * 2**attempt, max_delay) * jitter()
            sleeper(delay)
    raise AssertionError("unreachable")
