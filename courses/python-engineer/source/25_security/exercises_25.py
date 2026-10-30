"""Module 25 exercises.  pytest 25_security

All defensive. Each function is a control you'd actually put between untrusted input and
a dangerous operation.

Two habits the tests enforce throughout:
- compare secrets with `secrets.compare_digest`, never `==`
- fail CLOSED — when in doubt, reject
"""

from __future__ import annotations

from typing import Any


def hash_password(password: str, *, n: int = 2**14) -> str:
    """Hash a password for storage, self-describing so the cost can be raised later.

    Return a single string in this exact format (the fields joined by "$"):

        scrypt$<n>$<r>$<p>$<salt-hex>$<key-hex>

    - Use `hashlib.scrypt` with `r=8`, `p=1`, `dklen=32`, and a FRESH
      `secrets.token_bytes(16)` salt on every call.
    - Two calls with the same password must produce different strings (different salts).
    - An empty password raises ValueError.

    Storing the parameters alongside the hash is what lets you migrate to a higher cost
    later without locking every user out.
    """
    raise NotImplementedError


def verify_password(stored: str, password: str) -> bool:
    """Check a password against a `hash_password` string. Never raises on bad input.

    - Recompute with the parameters parsed OUT of `stored` — that's the whole reason
      they're in there.
    - Compare with `secrets.compare_digest`, not `==`.
    - A malformed, empty or unknown-algorithm `stored` value returns False rather than
      raising. Fail closed: an exception here becomes a 500, and a 500 on the login path
      is a much more interesting signal to an attacker than "no".
    """
    raise NotImplementedError


def generate_token(n_bytes: int = 32) -> str:
    """Return a URL-safe random token from a CSPRNG.

    - Use `secrets.token_urlsafe` — NOT `random`, which is a predictable PRNG.
    - `n_bytes < 16` raises ValueError (anything shorter is brute-forceable).
    - Tokens must be unique across calls; the tests generate 10,000 and check.
    """
    raise NotImplementedError


def sign_payload(secret: bytes, body: bytes, timestamp: int) -> str:
    """Return the hex HMAC-SHA256 of `f"{timestamp}.".encode() + body`.

    Signing the timestamp TOGETHER WITH the body is what makes replay detection possible;
    signing the body alone lets a captured request be resent forever.
    """
    raise NotImplementedError


def verify_payload(
    secret: bytes, body: bytes, timestamp: int, signature: str, *, max_age: int = 300, now: float | None = None
) -> bool:
    """Verify a webhook signature. Returns a bool; never raises.

    - Recompute and compare with `hmac.compare_digest`.
    - Reject when `abs(now - timestamp) > max_age` (replay protection), where `now`
      defaults to `time.time()` — injected so the tests are deterministic (module 09).
    - Reject a tampered body, a wrong secret, a malformed signature, and a future
      timestamp beyond the window.
    - Do the cheap timestamp check first, but do NOT skip the signature check because of
      it — both must pass.
    """
    raise NotImplementedError


def sanitize_filename(name: str, *, max_length: int = 255) -> str:
    """Reduce a user-supplied filename to something safe to write to disk.

    - Keep only the BASENAME: "../../etc/passwd" -> "passwd", "C:\\\\windows\\\\x" -> "x"
      (handle both separators; the client OS is not your OS).
    - Allow only `[A-Za-z0-9._-]`; replace every other character with "_".
    - Collapse runs of "." so ".." can't survive, and strip leading dots (no hidden files,
      no traversal).
    - Truncate to `max_length`, preserving the extension if there is one.
    - If nothing usable remains, return "unnamed".
    - Reject Windows reserved device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9,
      case-insensitively, with or without an extension) by prefixing with "_".

    This is a defence in DEPTH, not the primary one: you still write into a directory you
    control and check with `safe_join` (module 19). Two independent controls.
    """
    raise NotImplementedError


def is_safe_url(url: str, allowed_hosts: frozenset[str] | None = None) -> bool:
    """Decide whether a user-supplied URL is safe to fetch or redirect to.

    Reject (return False) when:
    - the scheme is not http or https (blocks `javascript:`, `data:`, `file:`)
    - there is no hostname
    - the host is a literal IP that is loopback, private, link-local, reserved or
      unspecified — 127.0.0.1, 10.x, 192.168.x, 172.16-31.x, and especially
      169.254.169.254, the cloud metadata endpoint
    - the hostname is "localhost" or ends in ".localhost" / ".internal" / ".local"
    - `allowed_hosts` is given and the hostname is not in it (exact match, lowercased)
    - the URL contains credentials (`user:pass@host`) or a newline (header injection)

    Accept otherwise. This one function is both the SSRF guard and the open-redirect
    guard; they're the same check with a different allow-list.
    """
    raise NotImplementedError


def redact(data: Any, *, extra_keys: frozenset[str] = frozenset()) -> Any:
    """Recursively redact secrets in a nested structure, for safe logging.

    - A dict key is sensitive when its lowercased name CONTAINS any of: password, passwd,
      secret, token, api_key, apikey, authorization, auth, credential, private_key,
      session, cookie — plus anything in `extra_keys`.
    - A sensitive value becomes the string "[REDACTED]", whatever its type.
    - Recurse into nested dicts, lists and tuples (preserving the container type).
    - Non-sensitive scalars pass through untouched.
    - The INPUT MUST NOT BE MODIFIED — return a new structure.
    - Handle self-referencing structures without infinite recursion (track ids seen).

    Redacting centrally, in one function used by your log formatter, is what stops the
    one call site you forgot from leaking a token.
    """
    raise NotImplementedError


def parse_json_safely(text: str, *, max_bytes: int = 1_000_000, max_depth: int = 20) -> Any:
    """Parse untrusted JSON with hard limits, so a hostile document can't take you down.

    - Reject input longer than `max_bytes` (measured in UTF-8 bytes) -> ValueError.
    - Reject nesting deeper than `max_depth` -> ValueError. A 10,000-deep document will
      otherwise blow the recursion limit inside the parser, and `RecursionError` is not
      something your request handler is ready for.
    - Invalid JSON -> ValueError (not `json.JSONDecodeError` leaking out; wrap it).
    - Never use `eval` or `pickle` for this. Ever.

    Check the depth on the PARSED object rather than by counting brackets in the text —
    escaped brackets inside strings would fool a textual count.
    """
    raise NotImplementedError
