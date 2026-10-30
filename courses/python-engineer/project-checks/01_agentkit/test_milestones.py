import asyncio
import importlib
import pytest


class TestMilestone2:
    def test_model_boundary_and_usage(self):
        from agentkit.models import Message,Usage,Completion,ScriptedModel
        assert Message(role='user',content='hello').to_wire()=={'role':'user','content':'hello'}
        usage=Usage(2,3)+Usage(5,7)
        assert (usage.input_tokens,usage.output_tokens)==(7,10)
        model=ScriptedModel([Completion(content='done')])
        assert asyncio.run(model.complete([Message('user','hello')])).content=='done'
        with pytest.raises(AssertionError): asyncio.run(model.complete([]))


class TestMilestone4:
    def test_workflow_orders_dependencies_and_rejects_cycles(self):
        from agentkit.agent import Step,Workflow
        from types import SimpleNamespace
        order=[]
        class FakeAgent:
            async def run(self,prompt): order.append(prompt);return SimpleNamespace(output=prompt)
        agent=FakeAgent()
        result=asyncio.run(Workflow([Step('a',agent,'first'),Step('b',agent,'second',('a',))]).run())
        assert order==['first','second'] and set(result)=={'a','b'}
        with pytest.raises(ValueError): Workflow([Step('a',agent,'x',('b',)),Step('b',agent,'y',('a',))])

    def test_bounded_message_bus(self):
        from agentkit.messaging import MessageBus
        async def scenario():
            bus=MessageBus(maxsize=1);queue=bus.subscribe('updates')
            await bus.publish('updates','a')
            blocked=asyncio.create_task(bus.publish('updates','b'))
            await asyncio.sleep(0)
            assert not blocked.done()
            assert await queue.get()=='a';await blocked
            assert await queue.get()=='b'
        asyncio.run(scenario())


class TestMilestone5:
    def test_memory_trims_and_checkpoint_roundtrips(self,tmp_path):
        from agentkit.memory import ConversationMemory,JSONCheckpoint
        from agentkit.models import Message
        memory=ConversationMemory(max_messages=2)
        for text in ['a','b','c']: memory.append(Message('user',text))
        assert [m.content for m in memory.messages]==['b','c']
        checkpoint=JSONCheckpoint(tmp_path/'state.json')
        checkpoint.save({'step':2,'transcript':['a','b']})
        assert checkpoint.load()=={'step':2,'transcript':['a','b']}


class TestMilestone6:
    def test_run_emits_local_spans_and_redacts_prompts(self):
        from agentkit import Agent
        from agentkit.models import ScriptedModel,Completion
        from agentkit.telemetry import capture
        with capture(redact_prompts=True) as events:
            asyncio.run(Agent(model=ScriptedModel([Completion(content='done')])).run('private-prompt'))
        assert any(e['name']=='agent.run' for e in events)
        assert 'private-prompt' not in str(events)
