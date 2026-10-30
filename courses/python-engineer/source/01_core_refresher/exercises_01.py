"""Module 01 exercises. Implement each function, then run:  pytest 01_core_refresher

Remove the `raise NotImplementedError` lines as you go.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def chunked(seq: Sequence[T], size: int) -> list[Sequence[T]]:
    """Split `seq` into consecutive chunks of length `size` (last one may be shorter).

    >>> chunked([1, 2, 3, 4, 5], 2)
    [[1, 2], [3, 4], [5]]
    >>> chunked([], 3)
    []

    Raise ValueError if size < 1. Works on any sequence, so slice — don't loop-and-append
    element by element.
    """
    raise NotImplementedError


def normalize_whitespace(text: str) -> str:
    """Collapse every run of whitespace (spaces, tabs, newlines) into one space, and strip.

    >>> normalize_whitespace("  hello\\t\\n world  ")
    'hello world'
    >>> normalize_whitespace("   ")
    ''

    One line. Think about what no-argument `str.split()` does.
    """
    raise NotImplementedError


def parse_kv(text: str, item_sep: str = ",", kv_sep: str = "=") -> dict[str, str]:
    """Parse "a=1, b = 2 ,c=x=y" into {"a": "1", "b": "2", "c": "x=y"}.

    - Keys and values are stripped of surrounding whitespace.
    - Only the FIRST kv_sep splits a pair (so values may contain it).
    - Empty items (e.g. from a trailing comma) are skipped.
    - An item with no kv_sep at all raises ValueError.
    """
    raise NotImplementedError


def clamp(value: float, lo: float, hi: float) -> float:
    """Constrain value to [lo, hi]. Raise ValueError if lo > hi.

    >>> clamp(5, 0, 3)
    3
    >>> clamp(-1, 0, 3)
    0
    """
    raise NotImplementedError


def snake_to_camel(name: str, *, upper_first: bool = False) -> str:
    """Convert snake_case to camelCase (or PascalCase when upper_first).

    >>> snake_to_camel("http_response_code")
    'httpResponseCode'
    >>> snake_to_camel("http_response_code", upper_first=True)
    'HttpResponseCode'
    >>> snake_to_camel("_leading__and_trailing_")
    'leadingAndTrailing'

    Only the first letter of each word changes case: "HTTP_code" -> "HTTPCode" is NOT
    required; use `.capitalize()`-like behaviour only on the first character so
    "http_OK" -> "httpOK".
    """
    raise NotImplementedError


def format_row(name: str, qty: int, price: float) -> str:
    """Format one table row using the f-string mini-language, exactly:

        name  left-aligned  in 12 columns
        '|'
        qty   right-aligned in 5 columns
        '|'
        price right-aligned in 12 columns, thousands separators, 2 decimals

    >>> format_row("apple", 3, 1234.5)
    'apple       |    3|    1,234.50'
    """
    raise NotImplementedError
