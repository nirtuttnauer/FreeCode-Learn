"""Milestone 1: turn typed Python functions into LLM-callable tools.

The interesting work is `_schema_for`: mapping Python type hints onto JSON Schema. Use
`typing.get_type_hints` (module 12) — with `from __future__ import annotations` the raw
`__annotations__` are strings, and every framework that forgets this has the same bug.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolResult:
    """What a tool call produced. `ok=False` results are fed BACK to the model."""

    tool_name: str
    ok: bool
    content: Any = None
    error: str | None = None


@dataclass
class Tool:
    """A callable plus the JSON Schema an LLM needs in order to call it."""

    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., Any]
    is_async: bool = False

    async def invoke(self, **kwargs: Any) -> ToolResult:
        """Validate `kwargs` against `self.parameters`, then call.

        - Unknown or missing-required arguments raise `ToolValidationError`.
        - A sync function runs via `asyncio.to_thread` so it can't block the loop
          (module 11).
        - An exception inside the tool becomes `ToolResult(ok=False, error=...)`, not a
          raised exception — the agent has to be able to show the model what went wrong.
        """
        raise NotImplementedError

    def to_openai_schema(self) -> dict[str, Any]:
        """`{"type": "function", "function": {name, description, parameters}}`."""
        raise NotImplementedError


def tool(func: Callable[..., Any] | None = None, *, name: str | None = None) -> Any:
    """Decorator turning a typed function into a `Tool`.

    Usable bare (`@tool`) or with arguments (`@tool(name="search_docs")`) — the two-mode
    decorator from module 03.

    Derives:
    - name: the override, else `func.__name__`
    - description: the docstring's summary line
    - parameters: JSON Schema from the type hints, with per-argument descriptions read
      from a Google-style `Args:` block
    - required: every parameter without a default
    """
    raise NotImplementedError


def _schema_for(annotation: Any) -> dict[str, Any]:
    """Map one type hint to a JSON Schema fragment.

    | Python                | JSON Schema |
    |-----------------------|-------------|
    | `str`                 | `{"type": "string"}` |
    | `int`                 | `{"type": "integer"}` |
    | `float`               | `{"type": "number"}` |
    | `bool`                | `{"type": "boolean"}` |
    | `list[T]`             | `{"type": "array", "items": <T>}` |
    | `dict[str, T]`        | `{"type": "object", "additionalProperties": <T>}` |
    | `Literal["a", "b"]`   | `{"type": "string", "enum": ["a", "b"]}` |
    | `X \\| None`           | schema of X, and the field is not required |
    | dataclass / BaseModel | a nested object schema |

    Unsupported annotations raise TypeError — fail at import time, not at call time.
    """
    raise NotImplementedError


def parse_docstring_args(docstring: str | None) -> dict[str, str]:
    """Extract `{parameter: description}` from a Google-style `Args:` section."""
    raise NotImplementedError


@dataclass
class ToolRegistry:
    """A name → Tool map. Registering a duplicate name raises ValueError."""

    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool_obj: Tool) -> None:
        raise NotImplementedError

    def get(self, name: str) -> Tool:
        """KeyError listing the known names when absent (module 12's Registry)."""
        raise NotImplementedError

    def schemas(self) -> list[dict[str, Any]]:
        raise NotImplementedError
