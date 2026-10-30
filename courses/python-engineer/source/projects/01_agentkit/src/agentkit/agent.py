"""Milestones 3–4: the agent loop and multi-agent delegation."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agentkit.models import ChatModel, Message, Usage
from agentkit.tools import Tool, ToolResult


@dataclass(frozen=True, slots=True)
class Budget:
    """Hard limits, checked BETWEEN steps. None means unlimited."""

    max_tokens: int | None = None
    max_tool_calls: int | None = None
    max_cost_usd: float | None = None


@dataclass
class RunResult:
    output: str
    steps: int
    usage: Usage
    transcript: list[Message] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)


class Agent:
    """The loop: prompt -> model -> tools -> model -> ... -> answer.

    Construction:
        Agent(model, tools=[...], system=None, name="agent", max_steps=8,
              budget=Budget(), timeout=None, sleeper=asyncio.sleep, clock=time.monotonic)

    `run(prompt)` must:
      1. Build the message list: system (if any), then the user prompt.
      2. Call the model with the tool schemas.
      3. If the completion has tool calls: run them CONCURRENTLY with `asyncio.TaskGroup`,
         append one role="tool" message per result (including failures), and loop.
      4. If it has text: return a `RunResult`.
      5. Enforce `max_steps` (`StepLimitExceeded` carrying the transcript), the `Budget`
         (`BudgetExceeded`), and `timeout` with `asyncio.timeout`.
      6. Retry retryable `ModelError`s with exponential backoff via the injected
         `sleeper` — so tests never actually wait (module 09).

    Cancellation must propagate: cancelling `run()` cancels in-flight tool calls, and
    `CancelledError` is never swallowed (module 11).
    """

    def __init__(
        self,
        model: ChatModel,
        tools: list[Tool] | None = None,
        *,
        system: str | None = None,
        name: str = "agent",
        max_steps: int = 8,
        budget: Budget | None = None,
        timeout: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        raise NotImplementedError

    async def run(self, prompt: str) -> RunResult:
        raise NotImplementedError

    def as_tool(self, name: str | None = None, description: str | None = None) -> Tool:
        """Expose this agent as a Tool another agent can call.

        This single method is what turns one agent into a hierarchy: the parent sees a
        normal tool taking `{"prompt": str}` and returning the child's output. Guard
        against unbounded recursion with a depth counter.
        """
        raise NotImplementedError


@dataclass
class Team:
    """Milestone 4: several agents behind a routing strategy.

    `router` is a callable `(prompt, agents) -> Agent`. Ship `round_robin`,
    `by_capability` (each agent declares `skills: set[str]`), and `llm_router`
    (ask a model to choose). A dict of strategies beats an if/elif chain (module 14).
    """

    agents: list[Agent]
    router: Callable[[str, list[Agent]], Agent]

    async def run(self, prompt: str) -> RunResult:
        raise NotImplementedError


@dataclass
class Step:
    """One node of a Workflow DAG."""

    name: str
    agent: Agent
    prompt: str | Callable[[dict[str, Any]], str]
    depends_on: tuple[str, ...] = ()


class Workflow:
    """A DAG of steps: independent branches run concurrently, results feed downstream.

    - Topologically sort the steps; a cycle raises ValueError at construction.
    - Run each "layer" concurrently with a TaskGroup.
    - A failing step fails the workflow with an `ExceptionGroup` (module 05), after the
      steps already running have settled.
    - `results[name]` holds each step's RunResult.
    """

    def __init__(self, steps: list[Step]) -> None:
        raise NotImplementedError

    async def run(self, initial: dict[str, Any] | None = None) -> dict[str, RunResult]:
        raise NotImplementedError
