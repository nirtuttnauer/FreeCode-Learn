# Project 01 — `agentkit`: a multi-agent orchestration library

Build the framework that runs LLM agents: tool calling, a planner loop, multi-agent
delegation, budgets, retries, and full tracing. **No LLM provider is required** — the
model is an injected `Protocol`, and the acceptance tests drive it with a scripted fake.
That's the design lesson: a framework whose core can't be tested offline is a bad
framework.

**Modules it draws on**: 03 (decorators), 04b (dunders), 07 (Protocol, generics, ParamSpec,
TypedDict), 11 (asyncio, TaskGroup, timeouts), 12 (introspection → JSON schema),
14 (dependency inversion, event bus), 17 (spans and metrics).

---

## Milestone 1 — tools from type hints

```python
@tool
def search(query: str, limit: int = 10) -> list[str]:
    """Search the knowledge base.

    Args:
        query: what to look for
        limit: maximum results
    """
```

Required:
- `@tool` reads the signature and docstring and produces a JSON Schema:
  `{"name", "description", "parameters": {"type": "object", "properties": {...}, "required": [...]}}`.
- Support `str, int, float, bool, list[T], dict[str, T]`, `Literal[...]` → `enum`,
  optional (`X | None`), and pydantic models / dataclasses as nested objects.
- Parameter descriptions come from a Google-style `Args:` block in the docstring.
- Use `typing.get_type_hints`, **not** raw `__annotations__` — under
  `from __future__ import annotations` those are strings (module 12).
- `tool.invoke(**kwargs)` validates arguments against the schema before calling, raising
  `ToolValidationError` on a mismatch, and returns a `ToolResult`.
- Async tools work too; `invoke` is `async` and awaits or offloads with `to_thread`.
- A `ToolRegistry` with `.register()`, `.get()`, `.schemas()`, and duplicate detection.

## Milestone 2 — the model boundary

```python
class ChatModel(Protocol):
    async def complete(self, messages: list[Message], tools: list[dict]) -> Completion: ...
```

- `Message` (role, content, tool_calls, tool_call_id) and `Completion`
  (content, tool_calls, usage) as frozen dataclasses or pydantic models.
- `ScriptedModel(responses)` — the test double: returns queued completions in order and
  records what it was asked.
- One real adapter of your choice (`OpenAIModel` / `AnthropicModel`), which the acceptance
  tests **skip** unless an API key is present. The core must never import it.

## Milestone 3 — the agent loop

```python
agent = Agent(model=model, tools=[search], system="You are terse.", max_steps=8)
result = await agent.run("What is in the docs about retries?")
result.output, result.steps, result.usage
```

- Loop: send messages → if the completion has tool calls, execute them (**concurrently**,
  with `TaskGroup`) → append results → repeat until a text answer or `max_steps`.
- Tool errors are fed back to the model as tool results, not raised — an agent must be
  able to recover from a bad call.
- `max_steps` exceeded raises `StepLimitExceeded` carrying the partial transcript.
- Per-run `timeout` via `asyncio.timeout`, and cancellation that actually cancels
  in-flight tools.
- `Budget(max_tokens, max_tool_calls, max_cost_usd)` enforced between steps, raising
  `BudgetExceeded`.
- Retries with exponential backoff on transient model errors (module 09's injectable
  sleeper — no real waiting in tests).

## Milestone 4 — multiple agents

- `Agent.as_tool(name, description)` — an agent becomes a tool another agent can call.
  This one primitive gives you hierarchical delegation for free.
- `Team(agents, router)` with routing strategies: `round_robin`, `by_capability`
  (match a declared skill set), and `llm_router` (the model picks).
- A `MessageBus` with topic subscriptions and an `asyncio.Queue` per subscriber, with
  **bounded** queues (backpressure, module 11).
- `Workflow`: a DAG of steps with dependencies, running independent branches
  concurrently and failing fast with an `ExceptionGroup`.
- Loop detection: refuse to recurse past `max_depth`, and detect A→B→A delegation cycles.

## Milestone 5 — memory and state

- `ConversationMemory` with pluggable trimming: `last_n`, `token_window`,
  `summarise` (calls the model).
- A `Checkpoint` protocol, plus a JSON file implementation, so a run can be resumed
  after a crash.
- `Session` tying together memory, budget and transcript, usable as an async context
  manager.

## Milestone 6 — observability (module 17)

- A span per run, per step, and per tool call, with attributes
  `agent.name`, `tool.name`, `llm.model`, `llm.usage.input_tokens`, `llm.usage.output_tokens`.
- Metrics: `agent.runs`, `agent.steps`, `agent.tool_calls`, `agent.errors`,
  `agent.duration` (histogram), `llm.tokens` — all with low-cardinality attributes.
- Structured JSON logs carrying `trace_id`, with prompts redactable via a policy hook.
- `agentkit.instrument()` wires it all up; the library must work with telemetry off.

## Going further

- Streaming: `async for chunk in agent.stream(prompt)`, with tool calls surfaced as events.
- An MCP client, so any MCP server's tools appear in your registry.
- A sandboxed code-execution tool (subprocess + timeout + no network).
- Structured output: force the model to fill a pydantic model, with repair-on-invalid.
- A cost model per provider, and a `--dry-run` that prices a run without calling out.
- A replay harness: record real model responses to a fixture file and re-run offline.

## What "done" means

`pytest projects/01_agentkit` is green with only the scripted model, a real provider works
when a key is present, and a two-agent delegation produces a trace you can read top to
bottom.
