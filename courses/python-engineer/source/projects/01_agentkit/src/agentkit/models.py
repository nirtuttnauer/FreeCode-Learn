"""Milestone 2: the model boundary.

`ChatModel` is a Protocol (module 07/14). The core NEVER imports a provider SDK — that's
what makes the whole test suite run offline in milliseconds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None  # set on role="tool" replies

    def to_wire(self) -> dict[str, Any]:
        """The provider-shaped dict. TODO."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Completion:
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = field(default_factory=Usage)

    @property
    def wants_tools(self) -> bool:
        raise NotImplementedError


class ChatModel(Protocol):
    """The only thing the agent core knows about an LLM."""

    async def complete(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> Completion: ...


class ScriptedModel:
    """The test double: hands back queued completions and records what it was asked.

    - `ScriptedModel([Completion(...), Completion(...)])`
    - Running out of scripted responses raises AssertionError with a clear message —
      an over-running agent loop should fail loudly in tests.
    - `.calls` records every (messages, tools) pair it received.
    - Optional `failures={0: ModelError("rate limited")}` maps a call index to an
      exception, so you can test the retry path deterministically.
    """

    def __init__(
        self,
        responses: list[Completion],
        failures: dict[int, Exception] | None = None,
    ) -> None:
        raise NotImplementedError

    async def complete(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> Completion:
        raise NotImplementedError
