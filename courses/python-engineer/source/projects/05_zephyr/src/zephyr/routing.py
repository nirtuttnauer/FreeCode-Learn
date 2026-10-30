"""Milestones 2-3: the router and signature analysis.

Two jobs, both done ONCE at registration:

  1. Compile `/users/{user_id:int}/posts/{slug}` into something matchable in better than
     O(routes) — a trie of path segments, or one alternation regex.
  2. Analyse the handler's signature and decide, per parameter, where its value comes
     from. Store that as a plan; never re-inspect at request time.
"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class Source(enum.StrEnum):
    """Where a handler parameter's value comes from."""

    PATH = "path"
    QUERY = "query"
    BODY = "body"
    HEADER = "header"
    COOKIE = "cookie"
    DEPENDENCY = "dependency"
    REQUEST = "request"  # the raw Request object


@dataclass(frozen=True, slots=True)
class ParamPlan:
    name: str
    source: Source
    annotation: Any
    required: bool
    default: Any = None


CONVERTERS: dict[str, Callable[[str], Any]] = {
    # "int": int, "float": float, "str": str, "path": str, "uuid": UUID
}


def analyse_signature(handler: Callable[..., Any], path: str) -> list[ParamPlan]:
    """Work out where each parameter comes from.

    Resolution order (first match wins):
      1. the annotation is `Request`                      -> Source.REQUEST
      2. `Annotated[T, Depends(...)]`                      -> Source.DEPENDENCY
      3. the name appears as a `{placeholder}` in the path -> Source.PATH
      4. the annotation is a pydantic model / dataclass    -> Source.BODY
      5. anything else                                     -> Source.QUERY

    `required` is "has no default". Use `typing.get_type_hints`, not `__annotations__`
    (module 12) — with postponed evaluation the latter gives you strings.
    """
    raise NotImplementedError


class Route:
    """One compiled path + methods + handler + its parameter plans."""

    def __init__(self, path: str, methods: set[str], handler: Callable[..., Any]) -> None:
        raise NotImplementedError

    def match(self, path: str) -> dict[str, Any] | None:
        """Return converted path params, or None. A converter failure is a 422, not a
        no-match — `/users/abc` against `{user_id:int}` should say why."""
        raise NotImplementedError
