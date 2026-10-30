"""Module 09 — runnable lesson. `python 09_testing/lesson_09.py`

This one demonstrates the *design* side of testing without needing a test runner:
the same logic written untestably, then written testably.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from unittest.mock import Mock, create_autospec

INTRO = """The secret of testable code: don't let it reach out and grab things. If a function needs
the time, HAND it a clock. Then in a test you hand it a fake one and say "it is now three
hours later" — and the test finishes in a millisecond instead of three hours."""


class ApiClient:
    def fetch(self, path: str) -> dict:
        raise RuntimeError("would hit the network")


# ---------------------------------------------------------------------------------------
# The same function, twice.
# ---------------------------------------------------------------------------------------


def untestable_retry(client: ApiClient, path: str) -> dict:
    """Hard-codes time, sleep and randomness: a test of this is slow AND flaky."""
    for attempt in range(3):
        try:
            return client.fetch(path)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2**attempt + random.random())  # real seconds, real dice


def testable_retry(
    client: ApiClient,
    path: str,
    *,
    attempts: int = 3,
    sleeper: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
) -> dict:
    """Same behaviour; every source of nondeterminism is a parameter with a sane default.

    Production calls it with no extra arguments. Tests pass a recording sleeper and a
    fixed jitter — no mock library, no patching, and the test runs in microseconds.
    """
    for attempt in range(attempts):
        try:
            return client.fetch(path)
        except Exception:
            if attempt == attempts - 1:
                raise
            sleeper(2**attempt + jitter())


def dependency_injection_demo() -> None:
    print("\n== injection beats patching ==")

    class FlakyClient(ApiClient):
        def __init__(self) -> None:
            self.calls = 0

        def fetch(self, path: str) -> dict:
            self.calls += 1
            if self.calls < 3:
                raise TimeoutError("flaky")
            return {"path": path, "ok": True}

    slept: list[float] = []
    result = testable_retry(
        FlakyClient(), "/users", sleeper=slept.append, jitter=lambda: 0.5
    )
    print(f"  result: {result}")
    print(f"  delays requested: {slept}  (exponential + fixed jitter — deterministic)")
    print("  elapsed: ~0 seconds, because nothing actually slept")


def fakes_vs_mocks() -> None:
    print("\n== fakes vs mocks ==")

    class FakeClient(ApiClient):
        """A real implementation with in-memory behaviour. Refactor-proof."""

        def __init__(self, data: dict[str, dict]) -> None:
            self.data = data

        def fetch(self, path: str) -> dict:
            return self.data[path]

    fake = FakeClient({"/users": {"count": 2}})
    print(f"  fake:  {fake.fetch('/users')}")

    mock = create_autospec(ApiClient, instance=True)  # signature-checked
    mock.fetch.return_value = {"count": 2}
    print(f"  mock:  {mock.fetch('/users')}")
    mock.fetch.assert_called_once_with("/users")
    print("  autospec caught nothing here, but it WOULD catch a renamed method")

    loose = Mock()  # no spec — accepts anything, including typos
    loose.fetchh("/users")
    print(f"  a spec-less Mock happily accepted .fetchh(): {loose.fetchh.called}")
    print("  ^ this is how mocked tests stay green after you delete the real method")


def time_injection() -> None:
    print("\n== injecting the clock ==")

    class Cache:
        def __init__(self, ttl: float, clock: Callable[[], float] = time.monotonic) -> None:
            self.ttl = ttl
            self.clock = clock  # monotonic, not time.time — wall clocks jump
            self._store: dict[str, tuple[float, object]] = {}

        def set(self, key: str, value: object) -> None:
            self._store[key] = (self.clock(), value)

        def get(self, key: str) -> object | None:
            stamped = self._store.get(key)
            if stamped is None:
                return None
            written, value = stamped
            if self.clock() - written > self.ttl:
                del self._store[key]
                return None
            return value

    now = [1000.0]  # a clock we control
    cache = Cache(ttl=60, clock=lambda: now[0])
    cache.set("k", "v")
    print(f"  immediately:      {cache.get('k')!r}")
    now[0] += 59
    print(f"  after 59s:        {cache.get('k')!r}")
    now[0] += 2
    print(f"  after 61s:        {cache.get('k')!r}  (expired — tested in 0 real seconds)")


def property_thinking() -> None:
    print("\n== properties worth testing ==")
    print("  round-trip:  decode(encode(x)) == x")
    print("  invariant:   len(sorted(xs)) == len(xs)")
    print("  oracle:      fast_impl(x) == obvious_slow_impl(x)")
    print("  idempotence: normalise(normalise(x)) == normalise(x)")
    print("  hypothesis generates thousands of cases and SHRINKS failures to a minimal one")


if __name__ == "__main__":
    print(INTRO)
    dependency_injection_demo()
    fakes_vs_mocks()
    time_injection()
    property_thinking()
