"""Milestone 4: dependency injection.

The rules that make DI feel effortless in FastAPI, and which you now have to implement:

  1. Dependencies are just callables. Their OWN parameters are resolved the same way a
     handler's are — recursively.
  2. Within one request, a dependency resolves ONCE. Two handlers asking for `get_db`
     share the session.
  3. A `yield` dependency's teardown runs after the response, in reverse order, even if
     the handler raised. `contextlib.AsyncExitStack` is the tool (module 05).
  4. Sync dependencies go through `asyncio.to_thread` so they can't block the loop.
  5. `app.dependency_overrides` is consulted FIRST, which is what makes tests painless.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Depends:
    """Marker placed in `Annotated[T, Depends(fn)]`.

    `use_cache=False` opts out of per-request caching for the rare dependency that must
    run every time it's asked for.
    """

    dependency: Callable[..., Any] | None = None
    use_cache: bool = True


class DependencyResolver:
    """Builds a resolution PLAN at registration and executes it per request.

    - `build_plan(callable)` -> a tree of dependencies, with cycles detected here and
      reported with the cycle path (`RouteConfigurationError`).
    - `async resolve(plan, request, exit_stack, overrides)` -> the kwargs for the call.
    - Caches by the dependency callable within a single request.
    """

    def build_plan(self, call: Callable[..., Any]) -> Any:
        raise NotImplementedError

    async def resolve(self, plan: Any, request: Any, exit_stack: Any, overrides: dict) -> dict:
        raise NotImplementedError
