# 05 — Exceptions, context managers, resource management

## In plain English

Two ideas here, both about "what happens when things go wrong".

**Exceptions** are an emergency exit. When something breaks, Python stops running the rest of
your code and goes looking, upward through your program, for someone who said "I know how to
handle this". If nobody does, the program stops and prints the trail of how it got there.

The skill isn't catching errors — it's catching *only* the ones you can actually do something
about, and letting the rest fly. Code that swallows every error is code that fails silently,
which is much worse than failing loudly.

**Context managers** are the `with` statement: a promise that something gets cleaned up no
matter what happens. Think of a door that always closes behind you — even if you leave the
room by jumping out the window. You've used it: `with open(...)` always closes the file, even
if your code crashes halfway through.

**Watch out for:** the file-writing example near the end. Saving a file the obvious way means
that if the power dies mid-write, you're left with half a file and the old version is gone.
The fix (write to a temporary file, then swap it in) is three lines and it's how every serious
program does it.

## 1. The exception hierarchy

```
BaseException
├── SystemExit, KeyboardInterrupt, GeneratorExit   <- do NOT catch with `except Exception`
└── Exception
    ├── ArithmeticError, LookupError (KeyError, IndexError), OSError, ValueError, TypeError...
    └── your code goes here
```

- `except Exception:` deliberately misses `KeyboardInterrupt`/`SystemExit`. That's the
  point. Never write bare `except:`.
- Catch the **narrowest** exception that you can actually handle. If you can't handle it,
  don't catch it.
- `OSError` subsumes the old `IOError`, and has useful subclasses:
  `FileNotFoundError`, `PermissionError`, `TimeoutError`, `ConnectionResetError`.

## 2. Design your own hierarchy

One base per library/package, so callers can catch everything from you in one line:

```python
class AppError(Exception): ...
class ConfigError(AppError): ...
class ValidationError(AppError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")   # keeps str(e) useful
        self.field, self.message = field, message
```

Attach structured data as attributes; keep `str(exc)` human-readable.

## 3. Chaining: `raise ... from ...`

```python
try:
    value = data["port"]
except KeyError as exc:
    raise ConfigError("port is required") from exc   # __cause__  -> "The above ... direct cause"
```

- `raise X from exc` sets `__cause__` — explicit.
- Raising inside an `except` block without `from` sets `__context__` — implicit
  ("During handling of the above exception, another occurred").
- `raise X from None` **suppresses** the context. Use when the inner error is noise.
- A bare `raise` inside `except` re-raises with the **original traceback** — always prefer
  it over `raise exc`.

## 4. `try/except/else/finally`

```python
try:
    resource = acquire()
except Timeout:
    ...              # runs on error
else:
    use(resource)    # runs only if NO exception — keeps the try block minimal
finally:
    release()        # ALWAYS runs, even on return/break/raise
```

A `return` in `finally` swallows in-flight exceptions. Don't.

## 5. Exception groups (3.11+)

For "several things failed at once" — concurrent tasks, batch validation:

```python
raise ExceptionGroup("validation failed", [ValueError("a"), TypeError("b")])

try:
    run_batch()
except* ValueError as eg:      # note the star; eg is itself an ExceptionGroup
    handle(eg.exceptions)
except* TypeError as eg:
    ...
```

`except*` can match **multiple** clauses for one group. `asyncio.TaskGroup` (module 11)
raises these natively.

Also 3.11+: `exc.add_note("extra context")` shows up in the traceback.

## 6. Context managers

Two ways to write one:

```python
class Timer:
    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self                      # this is what `as x` binds
    def __exit__(self, exc_type, exc, tb) -> bool | None:
        self.elapsed = time.perf_counter() - self.start
        return False                     # falsy => exception propagates; True SWALLOWS it
```

```python
from contextlib import contextmanager

@contextmanager
def timer():
    start = time.perf_counter()
    try:
        yield (result := {})             # everything before yield == __enter__
    finally:
        result["elapsed"] = time.perf_counter() - start   # finally == __exit__
```

The `try/finally` in a generator-based CM is mandatory — without it, cleanup is skipped
when the body raises.

`contextlib` extras worth knowing:

| Tool | Use |
|---|---|
| `suppress(FileNotFoundError)` | replaces `try/except/pass` |
| `closing(thing)` | calls `.close()` on exit |
| `ExitStack()` | a *dynamic* number of context managers |
| `nullcontext(x)` | optional-CM placeholder |
| `redirect_stdout(buf)` | capture prints |
| `ContextDecorator` | a CM that also works as `@decorator` |
| `asynccontextmanager` | the async twin (module 11) |

Multiple managers in one `with`:

```python
with open(a) as fa, open(b) as fb: ...
with (open(a) as fa, open(b) as fb): ...     # parenthesised, 3.10+
with ExitStack() as stack:
    files = [stack.enter_context(open(p)) for p in paths]   # N files, unknown at compile time
```

## 7. Safe file writing

Half-written files are a real production failure mode. The pattern: write to a temp file
in the same directory, `fsync`, then `os.replace` — which is atomic on POSIX and Windows.
You'll implement it in the exercises.

## 8. Cleanup that isn't `with`

- `try/finally` — always available.
- `weakref.finalize(obj, cleanup)` — better than `__del__`.
- `atexit.register` — process exit only, skipped on `os._exit` and hard crashes.
- `__del__` — timing is not guaranteed, exceptions in it are ignored. Avoid.

## Exercises

`exercises_05.py`, then `pytest 05_errors_context`.

## Further reading

- [`contextlib`](https://docs.python.org/3/library/contextlib.html)
- [PEP 654 — exception groups](https://peps.python.org/pep-0654/)
