"""One base exception per library, so callers can catch everything you raise (module 05)."""

from __future__ import annotations

from typing import Any


class AgentError(Exception):
    """Base for every error agentkit raises."""


class ToolValidationError(AgentError):
    """Arguments didn't match a tool's schema. Carries `.tool_name` and `.errors`."""

    def __init__(self, tool_name: str, errors: list[str]) -> None:
        super().__init__(f"{tool_name}: {'; '.join(errors)}")
        self.tool_name = tool_name
        self.errors = errors


class StepLimitExceeded(AgentError):
    """The loop hit `max_steps`. Carries the partial `.transcript` so nothing is lost."""

    def __init__(self, steps: int, transcript: list[Any]) -> None:
        super().__init__(f"step limit of {steps} exceeded")
        self.steps = steps
        self.transcript = transcript


class BudgetExceeded(AgentError):
    """A budget limit was hit. Carries `.limit_name`, `.limit` and `.used`."""

    def __init__(self, limit_name: str, limit: float, used: float) -> None:
        super().__init__(f"{limit_name} budget exceeded: used {used} of {limit}")
        self.limit_name = limit_name
        self.limit = limit
        self.used = used


class ModelError(AgentError):
    """The underlying model failed. `.retryable` tells the retry loop what to do."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable
