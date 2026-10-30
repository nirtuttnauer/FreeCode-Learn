"""Module 25 — reference solutions."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import re
import secrets
import time
from typing import Any
from urllib.parse import urlparse

SENSITIVE_KEYS = frozenset(
    {
        "password", "passwd", "secret", "token", "api_key", "apikey",
        "authorization", "auth", "credential", "private_key", "session", "cookie",
    }
)  # fmt: skip

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]")
_WINDOWS_RESERVED = frozenset(
    {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
)
_BLOCKED_SUFFIXES = (".localhost", ".internal", ".local")


# --- passwords --------------------------------------------------------------------------
def hash_password(password: str, *, n: int = 2**14) -> str:
    if not password:
        raise ValueError("password must not be empty")
    r, p, dklen = 8, 1, 32
    salt = secrets.token_bytes(16)  # fresh per call, so identical passwords differ
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen)
    return f"scrypt${n}${r}${p}${salt.hex()}${key.hex()}"


def verify_password(stored: str, password: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, key_hex = stored.split("$")
        if algorithm != "scrypt":
            return False
        expected = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(key_hex) // 2,
        )
    except Exception:  # noqa: BLE001 — fail closed: any malformed record is just "no"
        return False
    return hmac.compare_digest(expected.hex(), key_hex)


def generate_token(n_bytes: int = 32) -> str:
    if n_bytes < 16:
        raise ValueError(f"n_bytes must be >= 16, got {n_bytes}")
    return secrets.token_urlsafe(n_bytes)  # CSPRNG, not random.*


# --- webhook signatures -----------------------------------------------------------------
def sign_payload(secret: bytes, body: bytes, timestamp: int) -> str:
    message = f"{timestamp}.".encode() + body  # timestamp INSIDE the signature
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_payload(
    secret: bytes,
    body: bytes,
    timestamp: int,
    signature: str,
    *,
    max_age: int = 300,
    now: float | None = None,
) -> bool:
    try:
        current = time.time() if now is None else now
        if abs(current - timestamp) > max_age:
            return False
        expected = sign_payload(secret, body, timestamp)
        return hmac.compare_digest(expected, signature)
    except Exception:  # noqa: BLE001 — fail closed
        return False


# --- filenames --------------------------------------------------------------------------
def sanitize_filename(name: str, *, max_length: int = 255) -> str:
    if not isinstance(name, str):
        return "unnamed"

    # Strip any directory component, for BOTH separator conventions.
    basename = name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _SAFE_FILENAME.sub("_", basename)
    cleaned = re.sub(r"\.{2,}", ".", cleaned).lstrip(".")  # no "..", no hidden files

    if not cleaned or cleaned.strip("._-") == "":
        return "unnamed"

    if len(cleaned) > max_length:
        stem, dot, suffix = cleaned.rpartition(".")
        if dot and len(suffix) < max_length - 1:
            cleaned = stem[: max_length - len(suffix) - 1] + "." + suffix
        else:
            cleaned = cleaned[:max_length]

    if cleaned.split(".")[0].lower() in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned


# --- URLs -------------------------------------------------------------------------------
def is_safe_url(url: str, allowed_hosts: frozenset[str] | None = None) -> bool:
    if not isinstance(url, str) or any(c in url for c in "\r\n"):
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:  # user:pass@host is a phishing classic
        return False

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False
    if hostname == "localhost" or hostname.endswith(_BLOCKED_SUFFIXES):
        return False

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass  # a name, not a literal IP — a full guard would also resolve it
    else:
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local  # 169.254.169.254 lives here
            or address.is_reserved
            or address.is_unspecified
            or address.is_multicast
        ):
            return False

    return not (allowed_hosts is not None and hostname not in allowed_hosts)


# --- logging ----------------------------------------------------------------------------
def redact(data: Any, *, extra_keys: frozenset[str] = frozenset()) -> Any:
    sensitive = SENSITIVE_KEYS | {k.lower() for k in extra_keys}

    def is_sensitive(key: Any) -> bool:
        return isinstance(key, str) and any(marker in key.lower() for marker in sensitive)

    def walk(value: Any, seen: frozenset[int]) -> Any:
        if id(value) in seen:  # self-referencing structure
            return "[CIRCULAR]"
        if isinstance(value, dict):
            inner = seen | {id(value)}
            return {
                key: ("[REDACTED]" if is_sensitive(key) else walk(item, inner))
                for key, item in value.items()
            }
        if isinstance(value, list | tuple):
            inner = seen | {id(value)}
            rebuilt = [walk(item, inner) for item in value]
            return type(value)(rebuilt) if isinstance(value, tuple) else rebuilt
        return value

    return walk(data, frozenset())


# --- JSON -------------------------------------------------------------------------------
def parse_json_safely(text: str, *, max_bytes: int = 1_000_000, max_depth: int = 20) -> Any:
    if not isinstance(text, str):
        raise ValueError("expected a string")
    if len(text.encode("utf-8")) > max_bytes:
        raise ValueError(f"payload exceeds {max_bytes} bytes")

    try:
        parsed = json.loads(text)  # never eval, never pickle
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    # Depth is measured on the PARSED object: counting brackets in the text would be
    # fooled by escaped brackets inside strings.
    def depth_of(value: Any, level: int = 1) -> int:
        if level > max_depth:
            raise ValueError(f"nesting deeper than {max_depth}")
        if isinstance(value, dict):
            return max((depth_of(v, level + 1) for v in value.values()), default=level)
        if isinstance(value, list):
            return max((depth_of(v, level + 1) for v in value), default=level)
        return level

    depth_of(parsed)
    return parsed
