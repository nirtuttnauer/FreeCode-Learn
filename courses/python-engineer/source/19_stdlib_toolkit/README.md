# 19 — The standard library toolkit

"Batteries included" only helps if you know which batteries are in the box. This module is
the working set: paths, dates, serialisation, CLIs, subprocesses, and the security-adjacent
bits people reliably get wrong.

## In plain English

Python comes with an enormous amount of stuff already built in — "batteries included". The
catch is that this only helps if you know what's in the box, so people cheerfully install a
library to do something the standard library already did.

This module is the working set: the parts you'll actually reach for most weeks.

The one that deserves special attention is **dates and times**, because it is *genuinely
harder than it looks* and gets real software badly wrong every year.

The rule: a time without a timezone is meaningless. "3pm" — where? If you store "3pm" and
your server moves country, or the clocks change, your data is now wrong and you can't tell
which entries are affected. So: always attach a timezone, always store UTC, and convert to
local time only at the last moment when you show it to a human.

And for measuring how long something took, use a *monotonic* clock — one that only ever
counts forwards. The normal wall clock can jump backwards when the machine syncs with a
time server, and then your "elapsed time" comes out negative.

**Watch out for:** `open(path)` without `encoding="utf-8"`. The default differs between
operating systems, which is exactly how "it works on my machine" bugs are born.

## 1. `pathlib` — stop using `os.path`

```python
from pathlib import Path

root = Path(__file__).resolve().parent
config = root / "conf" / "app.toml"        # / is the join operator

config.exists(), config.is_file(), config.stat().st_size
config.name, config.stem, config.suffix, config.suffixes, config.parent, config.parents[1]
config.with_suffix(".bak"), config.with_stem("app.old"), config.relative_to(root)

config.read_text(encoding="utf-8"), config.write_text(data, encoding="utf-8")
config.read_bytes(), config.write_bytes(blob)

root.iterdir(), root.glob("*.py"), root.rglob("**/*.py")
target.mkdir(parents=True, exist_ok=True)
target.unlink(missing_ok=True)
```

**Always pass `encoding=`.** The platform default differs between Linux and Windows, and
a missing encoding is the most common "works on my machine" bug in file handling.

`Path.resolve()` + `Path.is_relative_to(root)` is the path-traversal guard — without it,
`user_input = "../../etc/passwd"` walks straight out of your directory.

## 2. `datetime` — and the rules that keep you out of trouble

```python
from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

datetime.now(UTC)                      # aware. ALWAYS aware.
datetime.now()                         # naive — a bug waiting for a DST boundary
datetime.now(ZoneInfo("Asia/Jerusalem"))
```

The four rules:
1. **Store and compute in UTC.** Convert to local time only at the edge, for display.
2. **Never create a naive datetime.** `datetime.now()` without a tz is almost always wrong.
3. **Use `zoneinfo`, not fixed offsets.** `timezone(timedelta(hours=2))` doesn't know
   about DST; `ZoneInfo("Europe/Berlin")` does.
4. **Use `time.monotonic()` for durations.** Wall clocks jump when NTP corrects them.

```python
datetime.fromisoformat("2026-08-02T14:31:07+00:00")   # 3.11+ parses Z too
dt.isoformat(), dt.strftime("%Y-%m-%d"), datetime.strptime(s, "%Y-%m-%d")
dt.astimezone(ZoneInfo("America/New_York"))
dt.timestamp(), datetime.fromtimestamp(ts, UTC)
```

`timedelta` arithmetic is exact for days/seconds. Calendar arithmetic ("one month later")
is *not* a timedelta — use `dateutil.relativedelta` or handle it explicitly, because
"one month after 31 January" has no obvious answer.

## 3. Serialisation

| Format | Module | Note |
|---|---|---|
| JSON | `json` | `default=` hook for non-serialisable types; `object_hook` on load |
| TOML | `tomllib` | read-only, stdlib since 3.11, **binary mode** |
| CSV | `csv` | `DictReader`/`DictWriter`, `newline=""` on open |
| pickle | `pickle` | **never** unpickle untrusted data — it executes code |
| Binary | `struct` | fixed-width records, network protocols |

```python
json.dumps(obj, default=str, sort_keys=True, separators=(",", ":"))
json.dumps(obj, indent=2)             # human-facing only
```

`sort_keys=True` + compact separators gives you a **canonical** form, which is what you
hash for a content address or an ETag.

## 4. CLIs with `argparse`

```python
parser = argparse.ArgumentParser(prog="tool", description="...")
parser.add_argument("path", type=Path)
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("--retries", type=int, default=3, choices=range(1, 6))
parser.add_argument("--format", choices=["json", "text"], default="text")

sub = parser.add_subparsers(dest="command", required=True)
run = sub.add_parser("run"); run.add_argument("--dry-run", action="store_true")

args = parser.parse_args(argv)        # pass argv explicitly => testable
```

Make `main(argv: list[str] | None = None) -> int` your entry point: it takes arguments,
returns an exit code, and is therefore a plain function you can unit-test. Reserve
`sys.exit(main())` for the `if __name__ == "__main__"` block.

Alternatives: `typer` (type-hint driven, lovely), `click` (mature), `argparse` (zero deps).

## 5. Subprocesses

```python
result = subprocess.run(
    ["git", "rev-parse", "HEAD"],       # a LIST, never a string
    capture_output=True, text=True, timeout=30, check=True, cwd=repo,
)
result.stdout.strip()
```

- **Never `shell=True` with untrusted input.** That's command injection. With a list
  argument there's no shell to inject into.
- Always set a `timeout`; a hung subprocess hangs your service.
- `check=True` raises `CalledProcessError` (which carries `.returncode`, `.stdout`,
  `.stderr`) instead of silently continuing.
- For streaming output use `subprocess.Popen` and iterate `proc.stdout`.

## 6. Identifiers, hashing, secrets

```python
uuid.uuid4()                                    # random id
hashlib.sha256(data).hexdigest()                # checksums, content addresses
hashlib.blake2b(data).hexdigest()               # faster, modern

secrets.token_urlsafe(32)                       # tokens, API keys, reset links
secrets.compare_digest(a, b)                    # constant-time comparison
hmac.new(key, msg, "sha256").hexdigest()        # webhook signatures
```

**`random` is not `secrets`.** `random` is a deterministic PRNG — fine for simulations and
test data, catastrophic for tokens. And never hash passwords with sha256: use
`hashlib.scrypt`, `argon2`, or `bcrypt`.

## 7. The rest of the working set

`os` (environ, cpu_count, replace), `shutil` (copytree, rmtree, disk_usage, which),
`tempfile` (`TemporaryDirectory`, `NamedTemporaryFile`), `glob`, `fnmatch`,
`textwrap` (dedent, shorten), `string` (Template), `enum` (`StrEnum`, `IntFlag`, `auto`),
`decimal`, `fractions`, `statistics`, `math`, `zoneinfo`, `urllib.parse`, `base64`,
`gzip`/`zipfile`/`tarfile`, `sqlite3` (module 20), `logging` (module 17), `dataclasses`,
`typing`, `abc`, `copy`, `pprint`, `difflib`, `heapq`/`bisect` (module 02),
`argparse`, `shlex.quote`.

## Exercises

`exercises_19.py`, then `pytest 19_stdlib_toolkit`.

## Further reading

- [The Python Standard Library](https://docs.python.org/3/library/) — skim the index once
  a year; it pays for itself
- [`pathlib`](https://docs.python.org/3/library/pathlib.html),
  [`zoneinfo`](https://docs.python.org/3/library/zoneinfo.html)
