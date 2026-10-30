"""Module 19 — reference solutions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_TRUE = {"true", "1", "yes", "y", "on"}
_FALSE = {"false", "0", "no", "n", "off"}


def safe_join(root: Path, *parts: str) -> Path:
    root = Path(root).resolve()
    candidate = root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("path escapes root")
    return candidate


def iter_source_files(
    root: Path, suffix: str = ".py", exclude_dirs: frozenset[str] = frozenset()
) -> Iterator[Path]:
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"no such directory: {root}")

    def walk(directory: Path) -> Iterator[Path]:
        for entry in sorted(directory.iterdir()):
            if entry.is_dir():
                if entry.name in exclude_dirs:  # prune here, not after descending
                    continue
                yield from walk(entry)
            elif entry.suffix == suffix:
                yield entry

    yield from walk(root)


def parse_timestamp(text: str) -> datetime:
    text = text.strip()
    if not text:
        raise ValueError("empty timestamp")

    if text.isdigit():
        return datetime.fromtimestamp(int(text), UTC)

    try:
        parsed = datetime.fromisoformat(text)  # 3.11+ understands the trailing Z
    except ValueError as exc:
        raise ValueError(f"unparsable timestamp: {text!r}") from exc

    if parsed.tzinfo is None:
        raise ValueError("timestamp is naive")
    return parsed.astimezone(UTC)


def _coerce(value: str, target: type, row_number: int, column: str) -> Any:
    if value == "":
        return None
    try:
        if target is bool:
            lowered = value.strip().lower()
            if lowered in _TRUE:
                return True
            if lowered in _FALSE:
                return False
            raise ValueError(value)
        return target(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"row {row_number}, column {column!r}: cannot read {value!r}") from exc


def load_records(path: Path, schema: dict[str, type]) -> list[dict[str, Any]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = set(reader.fieldnames or ())
        missing = [name for name in schema if name not in header]
        if missing:
            raise ValueError(f"missing columns: {', '.join(missing)}")

        return [
            {
                column: _coerce(row[column], target, number, column)
                for column, target in schema.items()
            }
            for number, row in enumerate(reader, start=1)
        ]


def canonical_hash(obj: Any) -> str:
    # sort_keys makes key order irrelevant; the compact separators remove whitespace.
    # Never use hash() here: it's salted per process by PYTHONHASHSEED.
    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="datatool", description="import and export data")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--config", type=Path, default=None)

    sub = parser.add_subparsers(dest="command", required=True)

    importer = sub.add_parser("import")
    importer.add_argument("source")
    importer.add_argument("--format", choices=["csv", "json"], default="csv")
    importer.add_argument("--dry-run", action="store_true")

    exporter = sub.add_parser("export")
    exporter.add_argument("dest")
    exporter.add_argument("--format", choices=["csv", "json"], default="csv")
    exporter.add_argument("--limit", type=int, default=0)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "export" and args.limit < 0:
        print("--limit must be >= 0", file=__import__("sys").stderr)
        return 2

    try:
        if args.command == "import":
            return 0
        return 0
    except Exception:  # noqa: BLE001 — the entry point is the one place to catch broadly
        return 1
