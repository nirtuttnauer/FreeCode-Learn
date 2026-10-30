"""Acceptance tests for agentkit, milestones 1-3.

Run: pytest projects/01_agentkit -o addopts=""

Everything here runs offline against ScriptedModel. If a change you make requires a
network call to test, the design has drifted.
"""

import asyncio
import sys
from pathlib import Path
from typing import Literal

import pytest

sys.path.insert(0, str(Path(__file__).parent / "src"))

agentkit = pytest.importorskip("agentkit")
from agentkit import Agent, tool  # noqa: E402
from agentkit.errors import BudgetExceeded, StepLimitExceeded, ToolValidationError  # noqa: E402
from agentkit.models import Completion, ScriptedModel, ToolCall, Usage  # noqa: E402


def run(coro):
    return asyncio.run(coro)


@tool
def search(query: str, limit: int = 10) -> list[str]:
    """Search the knowledge base.

    Args:
        query: what to look for
        limit: maximum number of results
    """
    return [f"{query}-{i}" for i in range(limit)]


@tool
def failing_tool(x: int) -> int:
    """Always blows up.

    Args:
        x: ignored
    """
    raise RuntimeError("tool exploded")


class TestToolSchema:
    def test_name_and_description(self):
        assert search.name == "search"
        assert search.description == "Search the knowledge base."

    def test_parameter_types(self):
        props = search.parameters["properties"]
        assert props["query"]["type"] == "string"
        assert props["limit"]["type"] == "integer"

    def test_required_is_only_defaultless_params(self):
        assert search.parameters["required"] == ["query"]

    def test_parameter_descriptions_from_the_docstring(self):
        assert search.parameters["properties"]["query"]["description"] == "what to look for"

    def test_schema_shape(self):
        assert search.parameters["type"] == "object"

    def test_openai_schema(self):
        schema = search.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "search"

    def test_literal_becomes_an_enum(self):
        @tool
        def pick(mode: Literal["fast", "slow"]) -> str:
            """Pick a mode.

            Args:
                mode: which mode
            """
            return mode

        assert pick.parameters["properties"]["mode"]["enum"] == ["fast", "slow"]

    def test_list_and_optional(self):
        @tool
        def complex_args(names: list[str], note: str | None = None) -> int:
            """Count names.

            Args:
                names: the names
                note: an optional note
            """
            return len(names)

        props = complex_args.parameters["properties"]
        assert props["names"] == {"type": "array", "items": {"type": "string"}, "description": "the names"}
        assert complex_args.parameters["required"] == ["names"]

    def test_custom_name(self):
        @tool(name="search_docs")
        def s(q: str) -> str:
            """Search.

            Args:
                q: query
            """
            return q

        assert s.name == "search_docs"


class TestToolInvocation:
    def test_invoke(self):
        result = run(search.invoke(query="retries", limit=2))
        assert result.ok
        assert result.content == ["retries-0", "retries-1"]

    def test_defaults_apply(self):
        assert len(run(search.invoke(query="x")).content) == 10

    def test_missing_required_argument(self):
        with pytest.raises(ToolValidationError):
            run(search.invoke(limit=1))

    def test_unknown_argument(self):
        with pytest.raises(ToolValidationError):
            run(search.invoke(query="x", nonsense=1))

    def test_wrong_type(self):
        with pytest.raises(ToolValidationError):
            run(search.invoke(query="x", limit="many"))

    def test_tool_exceptions_become_failed_results(self):
        result = run(failing_tool.invoke(x=1))
        assert result.ok is False
        assert "tool exploded" in result.error

    def test_async_tools(self):
        @tool
        async def fetch(url: str) -> str:
            """Fetch a url.

            Args:
                url: the url
            """
            await asyncio.sleep(0)
            return f"body of {url}"

        assert run(fetch.invoke(url="/a")).content == "body of /a"


class TestAgentLoop:
    def test_plain_answer(self):
        model = ScriptedModel([Completion(content="42", usage=Usage(10, 5))])
        result = run(Agent(model).run("what is the answer?"))
        assert result.output == "42"
        assert result.steps == 1

    def test_system_prompt_is_first(self):
        model = ScriptedModel([Completion(content="ok")])
        run(Agent(model, system="Be terse.").run("hi"))
        first = model.calls[0][0][0]
        assert first.role == "system"
        assert first.content == "Be terse."

    def test_tool_call_round_trip(self):
        model = ScriptedModel(
            [
                Completion(tool_calls=(ToolCall("1", "search", {"query": "retries", "limit": 1}),)),
                Completion(content="found it"),
            ]
        )
        result = run(Agent(model, tools=[search]).run("look it up"))
        assert result.output == "found it"
        assert result.steps == 2
        assert result.tool_results[0].content == ["retries-0"]

    def test_tool_results_are_sent_back_to_the_model(self):
        model = ScriptedModel(
            [
                Completion(tool_calls=(ToolCall("1", "search", {"query": "x", "limit": 1}),)),
                Completion(content="done"),
            ]
        )
        run(Agent(model, tools=[search]).run("go"))
        second_call_messages = model.calls[1][0]
        assert any(msg.role == "tool" and msg.tool_call_id == "1" for msg in second_call_messages)

    def test_failed_tools_are_reported_not_raised(self):
        model = ScriptedModel(
            [
                Completion(tool_calls=(ToolCall("1", "failing_tool", {"x": 1}),)),
                Completion(content="recovered"),
            ]
        )
        result = run(Agent(model, tools=[failing_tool]).run("go"))
        assert result.output == "recovered"
        assert result.tool_results[0].ok is False

    def test_parallel_tool_calls(self):
        calls = []

        @tool
        async def slow(n: int) -> int:
            """Sleep then return n.

            Args:
                n: the number
            """
            await asyncio.sleep(0.05)
            calls.append(n)
            return n

        model = ScriptedModel(
            [
                Completion(
                    tool_calls=tuple(ToolCall(str(i), "slow", {"n": i}) for i in range(4))
                ),
                Completion(content="all done"),
            ]
        )

        async def main():
            loop = asyncio.get_running_loop()
            start = loop.time()
            await Agent(model, tools=[slow]).run("go")
            return loop.time() - start

        # Four 50ms tools run concurrently: well under 200ms.
        assert run(main()) < 0.15
        assert sorted(calls) == [0, 1, 2, 3]

    def test_step_limit(self):
        looping = [
            Completion(tool_calls=(ToolCall(str(i), "search", {"query": "x"}),)) for i in range(10)
        ]
        model = ScriptedModel(looping)
        with pytest.raises(StepLimitExceeded) as info:
            run(Agent(model, tools=[search], max_steps=3).run("go"))
        assert info.value.steps == 3
        assert info.value.transcript

    def test_usage_accumulates(self):
        model = ScriptedModel(
            [
                Completion(
                    tool_calls=(ToolCall("1", "search", {"query": "x"}),), usage=Usage(10, 2)
                ),
                Completion(content="done", usage=Usage(20, 3)),
            ]
        )
        result = run(Agent(model, tools=[search]).run("go"))
        assert result.usage.input_tokens == 30
        assert result.usage.output_tokens == 5

    def test_token_budget(self):
        from agentkit.agent import Budget

        model = ScriptedModel(
            [
                Completion(
                    tool_calls=(ToolCall("1", "search", {"query": "x"}),), usage=Usage(100, 0)
                ),
                Completion(content="done", usage=Usage(100, 0)),
            ]
        )
        with pytest.raises(BudgetExceeded):
            run(Agent(model, tools=[search], budget=Budget(max_tokens=150)).run("go"))

    def test_timeout_cancels_in_flight_tools(self):
        cancelled = []

        @tool
        async def forever(x: int) -> int:
            """Never returns.

            Args:
                x: ignored
            """
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancelled.append(1)
                raise
            return x

        model = ScriptedModel([Completion(tool_calls=(ToolCall("1", "forever", {"x": 1}),))])
        with pytest.raises(TimeoutError):
            run(Agent(model, tools=[forever], timeout=0.05).run("go"))
        assert cancelled == [1]


class TestAgentAsTool:
    def test_delegation(self):
        child_model = ScriptedModel([Completion(content="child answer")])
        child = Agent(child_model, name="researcher", system="You research.")

        parent_model = ScriptedModel(
            [
                Completion(tool_calls=(ToolCall("1", "researcher", {"prompt": "dig in"}),)),
                Completion(content="parent answer using: child answer"),
            ]
        )
        parent = Agent(parent_model, tools=[child.as_tool()])
        result = run(parent.run("delegate this"))
        assert result.output == "parent answer using: child answer"
        assert result.tool_results[0].content == "child answer"

    def test_as_tool_schema(self):
        child = Agent(ScriptedModel([]), name="researcher")
        as_tool = child.as_tool()
        assert as_tool.name == "researcher"
        assert as_tool.parameters["properties"]["prompt"]["type"] == "string"
