"""Module 05 — reference solutions."""

from __future__ import annotations

import contextlib
import os
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import IO, Any


class PipelineError(Exception):
    """Base for everything this module raises."""


class RetryableError(PipelineError):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class FatalError(PipelineError):
    pass


class ValidationError(FatalError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")  # keeps str(exc) readable
        self.field = field
        self.message = message


def parse_port(config: dict[str, Any]) -> int:
    try:
        raw = config["port"]
    except KeyError as exc:
        raise FatalError("port is required") from exc
    try:
        port = int(raw)
    except (TypeError, ValueError) as exc:
        raise FatalError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise FatalError("port out of range")  # nothing to chain from
    return port


def validate_record(record: dict[str, Any]) -> None:
    errors: list[Exception] = []

    name = record.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(ValidationError("name", "required"))

    age = record.get("age")
    # bool is a subclass of int, so exclude it explicitly.
    if not isinstance(age, int) or isinstance(age, bool) or age < 0:
        errors.append(ValidationError("age", "must be a non-negative int"))

    email = record.get("email")
    if not isinstance(email, str) or "@" not in email:
        errors.append(ValidationError("email", "invalid"))

    if errors:
        raise ExceptionGroup("invalid record", errors)


class Timer:
    def __init__(self, label: str = "") -> None:
        self.label = label

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.elapsed = time.perf_counter() - self._start
        return False  # never swallow

    def __repr__(self) -> str:
        return f"Timer({self.label!r})"


@contextlib.contextmanager
def suppress_and_collect(
    sink: list[BaseException], *exc_types: type[BaseException]
) -> Iterator[list[BaseException]]:
    try:
        yield sink
    except exc_types as exc:  # an empty tuple matches nothing — exactly what we want
        sink.append(exc)


@contextlib.contextmanager
def atomic_write(path: Path, encoding: str = "utf-8") -> Iterator[IO[str]]:
    path = Path(path)
    # Same directory => os.replace is a true atomic rename, not a copy.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            yield handle
            handle.flush()
            os.fsync(handle.fileno())  # durable before we swap it in
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise
