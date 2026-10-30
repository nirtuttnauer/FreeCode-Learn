"""Milestone 1: the domain. No I/O, no framework, no imports from the outer layers.

Everything here should be testable with plain function calls and zero fixtures. If a test
of this package needs a database or a client, something belongs in `services/` instead.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime

__all__ = [
    "CodeTaken",
    "LinkExpired",
    "LinkNotFound",
    "PulseError",
    "QuotaExceeded",
    "ShortCode",
    "ShortLink",
    "Url",
    "generate_code",
]

BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"  # no 0 O l I


class PulseError(Exception):
    """Base for every domain error."""


class LinkNotFound(PulseError):
    def __init__(self, code: str) -> None:
        super().__init__(f"link {code!r} not found")
        self.code = code


class LinkExpired(PulseError):
    def __init__(self, code: str) -> None:
        super().__init__(f"link {code!r} has expired")
        self.code = code


class CodeTaken(PulseError):
    def __init__(self, code: str) -> None:
        super().__init__(f"code {code!r} is already taken")
        self.code = code


class QuotaExceeded(PulseError):
    def __init__(self, owner_id: str, limit: int) -> None:
        super().__init__(f"owner {owner_id!r} exceeded the quota of {limit}")
        self.owner_id = owner_id
        self.limit = limit


@dataclass(frozen=True, slots=True)
class Url:
    """A validated destination.

    Rules (all enforced in `__post_init__`, raising ValueError):
    - scheme must be http or https — `javascript:` and `data:` are how you become an
      open redirect used in phishing
    - a host is required
    - reject localhost, 127.0.0.0/8, 10/8, 172.16/12, 192.168/16, 169.254/16 and ::1
      (an SSRF guard: without it your server becomes a proxy into your own VPC)
    - normalise: lowercase the scheme and host, strip the default port, keep the path
    - max length 2048
    """

    value: str

    def __post_init__(self) -> None:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ShortCode:
    """6-12 characters from the base58 alphabet. Anything else is a ValueError."""

    value: str

    def __post_init__(self) -> None:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.value


def generate_code(rng: random.Random, length: int = 7) -> ShortCode:
    """Random code from an INJECTED rng, so tests are deterministic (module 09)."""
    raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ShortLink:
    code: ShortCode
    target: Url
    owner_id: str
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool = True

    def is_expired(self, now: datetime) -> bool:
        """True when `expires_at` is set and has passed. Timezone-aware datetimes only —
        raise ValueError on a naive one (a naive datetime in a link shortener is a
        production incident waiting for daylight saving)."""
        raise NotImplementedError

    def deactivate(self) -> "ShortLink":
        """Immutable update, like module 14's Task.complete()."""
        raise NotImplementedError
