"""Module 01 — reference solutions. Read only after your own attempt passes (or truly stalls)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def chunked(seq: Sequence[T], size: int) -> list[Sequence[T]]:
    if size < 1:
        raise ValueError(f"size must be >= 1, got {size}")
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def normalize_whitespace(text: str) -> str:
    # No-arg split() splits on runs of any whitespace and drops leading/trailing empties.
    return " ".join(text.split())


def parse_kv(text: str, item_sep: str = ",", kv_sep: str = "=") -> dict[str, str]:
    result: dict[str, str] = {}
    for item in text.split(item_sep):
        if not item.strip():
            continue
        key, sep, value = item.partition(kv_sep)  # partition splits on the FIRST occurrence
        if not sep:
            raise ValueError(f"missing {kv_sep!r} in item {item!r}")
        result[key.strip()] = value.strip()
    return result


def clamp(value: float, lo: float, hi: float) -> float:
    if lo > hi:
        raise ValueError(f"lo ({lo}) must be <= hi ({hi})")
    return max(lo, min(value, hi))


def snake_to_camel(name: str, *, upper_first: bool = False) -> str:
    words = [w for w in name.split("_") if w]
    if not words:
        return ""
    head, *tail = words
    if upper_first:
        head = head[0].upper() + head[1:]
    # Only touch the first character so acronyms like "OK" survive intact.
    return head + "".join(w[0].upper() + w[1:] for w in tail)


def format_row(name: str, qty: int, price: float) -> str:
    return f"{name:<12}|{qty:>5}|{price:>12,.2f}"
