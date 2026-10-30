"""agentkit — multi-agent orchestration with a testable core.

The whole library is designed around one rule: the model is a Protocol, injected at the
edge. Nothing in the core imports an HTTP client, so the entire test suite runs offline.
"""

from __future__ import annotations

__all__ = [
    "Agent",
    "AgentError",
    "BudgetExceeded",
    "StepLimitExceeded",
    "ToolValidationError",
    "__version__",
    "tool",
]

__version__ = "0.1.0"

from agentkit.errors import AgentError, BudgetExceeded, StepLimitExceeded, ToolValidationError
from agentkit.tools import tool

# Import Agent last — it depends on everything above.
from agentkit.agent import Agent  # isort: skip
