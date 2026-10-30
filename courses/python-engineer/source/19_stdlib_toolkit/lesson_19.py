"""Module 19 — runnable lesson. `python 19_stdlib_toolkit/lesson_19.py`"""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import io
import json
import secrets
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

INTRO = """The tools already in the box. The one that deserves real attention is time: a timestamp
without a timezone is meaningless, and a wall clock can jump BACKWARDS when the machine
syncs, which is why measuring durations needs a monotonic clock."""


def paths() -> None:
    print("\n== pathlib ==")
    p = Path("/var/log/app/service.tar.gz")
    print(f"  {p.name=} {p.stem=} {p.suffix=} {p.suffixes=}")
    print(f"  {p.parent=}")
    print(f"  {p.with_suffix('.bak')=}")
    print(f"  joined with /: {Path('/var') / 'log' / 'app.log'}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a" / "b").mkdir(parents=True, exist_ok=True)
        (root / "a" / "one.py").write_text("print(1)", encoding="utf-8")
        (root / "a" / "b" / "two.py").write_text("print(2)", encoding="utf-8")
        (root / "a" / "notes.txt").write_text("hi", encoding="utf-8")

        print(f"  glob('a/*.py'):  {[q.name for q in sorted(root.glob('a/*.py'))]}")
        print(f"  rglob('*.py'):   {[q.name for q in sorted(root.rglob('*.py'))]}")

        print("\n  path traversal guard:")
        for user_input in ("reports/q1.csv", "../../etc/passwd"):
            candidate = (root / user_input).resolve()
            safe = candidate.is_relative_to(root.resolve())
            print(f"    {user_input:<20} safe={safe}")


def dates() -> None:
    print("\n== datetime ==")
    naive = datetime(2026, 8, 2, 14, 30)
    aware = datetime(2026, 8, 2, 14, 30, tzinfo=UTC)
    print(f"  naive: {naive}  <- no timezone: a bug in waiting")
    print(f"  aware: {aware}")
    try:
        naive < aware
    except TypeError as exc:
        print(f"  comparing them: TypeError: {exc}")

    berlin = aware.astimezone(ZoneInfo("Europe/Berlin"))
    print(f"\n  UTC -> Berlin: {berlin} (offset {berlin.utcoffset()})")

    winter = datetime(2026, 1, 15, 12, tzinfo=UTC).astimezone(ZoneInfo("Europe/Berlin"))
    print(f"  the same code in January: offset {winter.utcoffset()}  <- DST is real")

    fixed = datetime(2026, 1, 15, 12, tzinfo=timezone(timedelta(hours=2)))
    print(f"  a fixed offset never changes: {fixed.utcoffset()}  <- which is why it's wrong")

    print(f"\n  fromisoformat with Z: {datetime.fromisoformat('2026-08-02T14:31:07Z')}")
    print(f"  isoformat:            {aware.isoformat()}")
    print(f"  strftime:             {aware.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"  arithmetic:           {aware + timedelta(days=30, hours=6)}")
    print(f"  difference in hours:  {(aware - datetime(2026, 8, 1, tzinfo=UTC)) / timedelta(hours=1)}")


def serialisation() -> None:
    print("\n== json ==")
    payload = {"id": uuid.UUID(int=7), "when": datetime(2026, 1, 1, tzinfo=UTC), "n": 1}
    print(f"  default=str handles unknown types: {json.dumps(payload, default=str)}")
    print(f"  canonical form: {json.dumps({'b': 1, 'a': 2}, sort_keys=True, separators=(',', ':'))}")

    print("\n== csv ==")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["name", "amount"])
    writer.writeheader()
    writer.writerows([{"name": "ada", "amount": 10}, {"name": 'b,"quoted"', "amount": 2}])
    print(f"  written (quoting handled for you): {buffer.getvalue().splitlines()}")

    rows = list(csv.DictReader(io.StringIO(buffer.getvalue())))
    print(f"  read back: {rows}")
    print("  everything comes back as STRINGS — coerce types yourself")


def cli() -> None:
    print("\n== argparse ==")
    parser = argparse.ArgumentParser(prog="tool", description="demo")
    parser.add_argument("path", type=Path)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--retries", type=int, default=3)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--dry-run", action="store_true")
    sub.add_parser("check")

    args = parser.parse_args(["/tmp/x", "--retries", "5", "-v", "run", "--dry-run"])
    print(f"  parsed: {vars(args)}")
    print("  parse_args(argv) with an explicit list => main() is a testable function")


def subprocesses() -> None:
    print("\n== subprocess ==")
    result = subprocess.run(
        ["python3", "-c", "print('hello from a child')"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    print(f"  stdout: {result.stdout.strip()!r} returncode={result.returncode}")

    try:
        subprocess.run(["python3", "-c", "raise SystemExit(3)"], check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        print(f"  check=True raises: returncode={exc.returncode}")

    print("  args as a LIST => no shell => no command injection")
    print("  always pass timeout=; a hung child otherwise hangs you")


def identity_and_secrets() -> None:
    print("\n== uuid / hashlib / secrets ==")
    print(f"  uuid4:  {uuid.uuid4()}")
    print(f"  sha256: {hashlib.sha256(b'content').hexdigest()[:32]}...")
    print(f"  blake2b:{hashlib.blake2b(b'content', digest_size=16).hexdigest()}")

    token = secrets.token_urlsafe(24)
    print(f"\n  secrets.token_urlsafe: {token}")
    print("  random.random() is a PRNG — predictable. NEVER use it for tokens.")

    signature = hmac.new(b"shared-key", b"payload", "sha256").hexdigest()
    print(f"  hmac signature: {signature[:32]}...")
    print(f"  constant-time compare: {secrets.compare_digest(signature, signature)}")
    print("  == leaks timing information; compare_digest doesn't")

    print("\n  password hashing is a DIFFERENT problem:")
    derived = hashlib.scrypt(b"hunter2", salt=b"per-user-salt", n=2**14, r=8, p=1)
    print(f"    scrypt (slow on purpose): {derived.hex()[:32]}...")


if __name__ == "__main__":
    print(INTRO)
    paths()
    dates()
    serialisation()
    cli()
    subprocesses()
    identity_and_secrets()
