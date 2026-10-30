"""Module 05 — runnable lesson. `python 05_errors_context/lesson_05.py`"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import time
import traceback
from pathlib import Path

INTRO = """Exceptions are an emergency exit: everything stops and Python looks upward for someone who
said "I can handle this". A `with` block is a door that always closes behind you, even if
you leave by jumping out the window."""


class AppError(Exception):
    """One base class per package lets callers catch everything you raise."""


class ConfigError(AppError):
    pass


class ValidationError(AppError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


def hierarchy_and_chaining() -> None:
    print("\n== custom hierarchy ==")
    err = ValidationError("port", "must be an integer")
    print(f"  str(err) = {err}")
    print(f"  structured: {err.field=} {err.message=}")
    print(f"  {isinstance(err, AppError)=}")

    print("\n== chaining ==")

    def load(data: dict) -> int:
        try:
            return int(data["port"])
        except KeyError as exc:
            raise ConfigError("port is required") from exc  # __cause__

    try:
        load({})
    except ConfigError as exc:
        print(f"  raised: {exc}")
        print(f"  __cause__: {exc.__cause__!r}")
        print(f"  __suppress_context__: {exc.__suppress_context__}")

    # `from None` hides an implementation detail you don't want in the traceback.
    def load_quiet(data: dict) -> int:
        try:
            return int(data["port"])
        except KeyError:
            raise ConfigError("port is required") from None

    try:
        load_quiet({})
    except ConfigError as exc:
        print(f"  from None -> __cause__={exc.__cause__} __context__={exc.__context__!r}")

    print("\n== add_note (3.11+) ==")
    try:
        try:
            raise ValueError("bad row")
        except ValueError as exc:
            exc.add_note("while parsing line 42 of users.csv")
            raise
    except ValueError as exc:
        print("  " + "  ".join(traceback.format_exception_only(exc)))


def else_and_finally() -> None:
    print("\n== try/except/else/finally ==")
    order = []

    def run(fail: bool) -> str:
        try:
            order.append("try")
            if fail:
                raise ValueError("boom")
            return "returned-from-try"
        except ValueError:
            order.append("except")
            return "returned-from-except"
        else:
            order.append("else")  # only when no exception AND no early return
            return "returned-from-else"
        finally:
            order.append("finally")  # runs even after `return`

    print(f"  happy path: {run(False)}  order={order}")
    order.clear()
    print(f"  error path: {run(True)}  order={order}")


def exception_groups() -> None:
    print("\n== ExceptionGroup + except* (3.11+) ==")

    def validate(record: dict) -> None:
        errors = []
        if "name" not in record:
            errors.append(ValidationError("name", "required"))
        if not isinstance(record.get("age", 0), int):
            errors.append(ValidationError("age", "must be an int"))
        if not str(record.get("email", "")).count("@"):
            errors.append(ValidationError("email", "invalid"))
        if errors:
            raise ExceptionGroup("record is invalid", errors)

    try:
        validate({"age": "old"})
    except* ValidationError as group:
        print(f"  caught {len(group.exceptions)} problems at once:")
        for exc in group.exceptions:
            print(f"    - {exc}")


def context_managers() -> None:
    print("\n== class-based context manager ==")

    class Timer:
        def __enter__(self) -> Timer:
            self.start = time.perf_counter()
            return self  # bound by `as`

        def __exit__(self, exc_type, exc, tb) -> bool:
            self.elapsed = time.perf_counter() - self.start
            print(f"    exit sees exc_type={exc_type.__name__ if exc_type else None}")
            return False  # falsy: let any exception propagate

    with Timer() as t:
        sum(range(100_000))
    print(f"  elapsed {t.elapsed * 1000:.2f} ms")

    print("\n== generator-based ==")

    @contextlib.contextmanager
    def tag(name: str):
        print(f"    <{name}>")
        try:
            yield name  # the try/finally is what makes cleanup exception-safe
        finally:
            print(f"    </{name}>")

    with tag("div"):
        print("    content")

    with contextlib.suppress(ZeroDivisionError):
        1 / 0
    print("  contextlib.suppress swallowed a ZeroDivisionError")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print("captured, not printed")
    print(f"  redirect_stdout captured: {buf.getvalue().strip()!r}")

    print("\n== ExitStack: a dynamic number of managers ==")
    with tempfile.TemporaryDirectory() as tmp:
        paths = [Path(tmp) / f"f{i}.txt" for i in range(3)]
        for p in paths:
            p.write_text(p.name)
        with contextlib.ExitStack() as stack:
            handles = [stack.enter_context(p.open()) for p in paths]
            print(f"  opened {len(handles)} files; all close on exit")


def atomic_write_demo() -> None:
    print("\n== atomic writes ==")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "config.json"
        target.write_text("original")

        # Write to a sibling temp file, flush+fsync, then atomically rename over the target.
        fd, tmp_name = tempfile.mkstemp(dir=target.parent)
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write("new content")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, target)  # atomic on POSIX and Windows
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_name)
            raise

        print(f"  content is now {target.read_text()!r}")
        print("  a crash mid-write leaves the ORIGINAL file intact — never a half file")


if __name__ == "__main__":
    print(INTRO)
    hierarchy_and_chaining()
    else_and_finally()
    exception_groups()
    context_managers()
    atomic_write_demo()
