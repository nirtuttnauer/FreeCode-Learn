"""Module 25 — runnable lesson. `python 25_security/lesson_25.py`

Everything here is defensive and runs locally: no network, no real targets. The "attacks"
are demonstrated against toy code in this file so you can see the mechanism.
"""

from __future__ import annotations

import ast
import hashlib
import hmac
import random
import secrets
import sqlite3
import subprocess
import time

INTRO = """Almost every security bug you'll write has the same shape: something a STRANGER typed
reached something DANGEROUS. A name reached a database command; a filename reached the
filesystem. Find those pairs, put a guard between them. That's the whole job."""


def injection() -> None:
    print("\n== SQL injection ==")
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (id INTEGER, email TEXT, is_admin INTEGER)")
    conn.executemany(
        "INSERT INTO users VALUES (?, ?, ?)",
        [(1, "ada@example.com", 0), (2, "root@example.com", 1)],
    )

    hostile = "x' OR '1'='1"
    unsafe = f"SELECT COUNT(*) FROM users WHERE email = '{hostile}'"  # noqa: S608
    print(f"  f-string query returned {conn.execute(unsafe).fetchone()[0]} of 2 rows")
    safe = conn.execute("SELECT COUNT(*) FROM users WHERE email = ?", (hostile,))
    print(f"  parameterised returned  {safe.fetchone()[0]}  <- the input stayed DATA")

    print("\n== command injection ==")
    filename = "notes.txt; echo PWNED"
    result = subprocess.run(f"echo {filename}", shell=True, capture_output=True, text=True)  # noqa: S602
    print(f"  shell=True ran: {result.stdout.strip()!r}")
    result = subprocess.run(["echo", filename], capture_output=True, text=True)
    print(f"  a list of args: {result.stdout.strip()!r}  <- one argument, no shell")

    print("\n== eval vs ast.literal_eval ==")
    print(f"  literal_eval('{{\"a\": 1}}') = {ast.literal_eval('{\"a\": 1}')}")
    try:
        ast.literal_eval("__import__('os').system('echo pwned')")
    except ValueError as exc:
        print(f"  literal_eval refuses a call: {type(exc).__name__}: {exc}")
    print("  eval() would have run it. There is no safe way to eval untrusted input.")


def pickle_is_code_execution() -> None:
    print("\n== pickle.loads IS code execution ==")

    class Harmless:
        """A payload class. On unpickling, __reduce__ decides what gets called."""

        def __reduce__(self):
            # A real payload would call os.system. This one just proves the mechanism.
            return (print, ("    >>> arbitrary code ran during pickle.loads <<<",))

    import pickle

    payload = pickle.dumps(Harmless())
    print("  unpickling a 'data' blob:")
    pickle.loads(payload)  # noqa: S301 — demonstrating the vulnerability on our own payload
    print("  no eval, no exec — just loading data. Use JSON, or sign the blob.")


def password_storage() -> None:
    print("\n== password hashing ==")
    password = "correct horse battery staple"

    start = time.perf_counter()
    fast = hashlib.sha256(password.encode()).hexdigest()
    fast_ms = (time.perf_counter() - start) * 1000

    salt = secrets.token_bytes(16)
    start = time.perf_counter()
    slow = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    slow_ms = (time.perf_counter() - start) * 1000

    print(f"  sha256:  {fast_ms:>8.4f} ms  -> {fast[:24]}...")
    print(f"  scrypt:  {slow_ms:>8.4f} ms  -> {slow.hex()[:24]}...")
    print(f"  scrypt is ~{slow_ms / fast_ms:.0f}x slower ON PURPOSE.")
    print("  at sha256 speed a GPU tries billions of guesses/second; that's the attack.")

    other_salt = secrets.token_bytes(16)
    other = hashlib.scrypt(password.encode(), salt=other_salt, n=2**14, r=8, p=1, dklen=32)
    print(f"  same password, different salt -> different hash: {slow != other}")
    print("  which is what stops one rainbow table cracking every user at once")


def randomness() -> None:
    print("\n== random is not secrets ==")
    predictable = random.Random(12345)
    replay = random.Random(12345)
    print(f"  random.Random(seed) token: {''.join(predictable.choices('abcdef0123456789', k=16))}")
    print(f"  reproduced from the seed:  {''.join(replay.choices('abcdef0123456789', k=16))}")
    print("  a Mersenne Twister is fully reconstructible from ~624 observed outputs")
    print(f"\n  secrets.token_urlsafe(24): {secrets.token_urlsafe(24)}")
    print("  use secrets for anything an attacker would like to guess")


def timing_attacks() -> None:
    print("\n== timing-safe comparison ==")

    def measure(candidate: str, secret: str, compare, repeats: int) -> float:
        best = float("inf")
        for _ in range(5):
            start = time.perf_counter_ns()
            for _ in range(repeats):
                compare(candidate, secret)
            best = min(best, (time.perf_counter_ns() - start) / repeats)
        return best

    print(f"  {'size':>10}  {'== early':>10} {'== late':>10} {'ratio':>8}   {'digest early':>12} {'digest late':>11}")
    for size, repeats in ((32, 20_000), (10_000, 2_000), (1_000_000, 200)):
        secret = "a" * size
        early = "b" + "a" * (size - 1)  # differs at the first byte
        late = "a" * (size - 1) + "b"  # differs at the last byte

        naive_early = measure(early, secret, lambda a, b: a == b, repeats)
        naive_late = measure(late, secret, lambda a, b: a == b, repeats)
        safe_early = measure(early, secret, secrets.compare_digest, repeats)
        safe_late = measure(late, secret, secrets.compare_digest, repeats)
        print(
            f"  {size:>10,}  {naive_early:>10.1f} {naive_late:>10.1f} {naive_late / naive_early:>7.0f}x"
            f"   {safe_early:>12.1f} {safe_late:>11.1f}"
        )

    print("\n  Read that honestly:")
    print("  - `==` short-circuits, so its cost DEPENDS on the matching prefix length.")
    print("    At 1M bytes that's a ~1400x difference. The leak is real and measurable.")
    print("  - At a realistic 32-byte token the difference is nanoseconds, lost in noise —")
    print("    exploiting it over a network needs enormous sampling. It is not the easiest")
    print("    way into your system, and anyone claiming an easy remote exploit is selling.")
    print("  - compare_digest is flat regardless of where the difference is, and costs")
    print("    nothing you will notice. So use it for every secret comparison anyway:")
    print("    the habit is free, and you don't get to choose the attacker's conditions.")


def webhook_signatures() -> None:
    print("\n== signing a webhook ==")
    secret = b"shared-signing-key"
    body = b'{"event": "payment.succeeded", "amount": 4200}'
    timestamp = int(time.time())

    def sign(ts: int, payload: bytes) -> str:
        return hmac.new(secret, f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()

    signature = sign(timestamp, body)
    print(f"  signature: {signature[:32]}...")

    def verify(ts: int, payload: bytes, provided: str, *, max_age: int = 300) -> bool:
        if abs(time.time() - ts) > max_age:
            return False  # replay protection
        return hmac.compare_digest(sign(ts, payload), provided)

    print(f"  valid:                {verify(timestamp, body, signature)}")
    print(f"  body tampered with:   {verify(timestamp, body + b' ', signature)}")
    print(f"  replayed an hour on:  {verify(timestamp - 3600, body, sign(timestamp - 3600, body))}")
    print("  sign the TIMESTAMP + RAW BODY, and verify before you parse anything")


def ssrf_guard() -> None:
    print("\n== SSRF: the URLs you must not fetch ==")
    import ipaddress
    from urllib.parse import urlparse

    def is_safe(url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            return parsed.hostname not in {"localhost"}  # a real guard resolves DNS too
        return not (
            address.is_private or address.is_loopback or address.is_link_local
            or address.is_reserved
        )

    for url in [
        "https://api.example.com/v1/data",
        "http://localhost/admin",
        "http://127.0.0.1:8080/",
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "file:///etc/passwd",
        "http://10.0.0.5/internal",
    ]:
        print(f"  {'ALLOW' if is_safe(url) else 'BLOCK'}  {url}")
    print("  169.254.169.254 is the cloud metadata endpoint — the route to your IAM creds")


def bounded_input() -> None:
    print("\n== unbounded input is a DoS ==")
    import json

    deep = json.dumps({"a": 1})
    for _ in range(200):
        deep = json.dumps({"nested": json.loads(deep)})
    print(f"  a 200-deep JSON document is {len(deep):,} bytes and parses fine")
    print("  at ~1000 deep, a recursive parser hits RecursionError — or worse")
    print("  bound: request size, JSON depth, array length, upload size, regex input")


if __name__ == "__main__":
    print(INTRO)
    injection()
    pickle_is_code_execution()
    password_storage()
    randomness()
    timing_attacks()
    webhook_signatures()
    ssrf_guard()
    bounded_input()
