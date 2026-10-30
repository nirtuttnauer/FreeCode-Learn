import asyncio
from datetime import datetime,timezone
import pytest


class TestMilestone2:
    @pytest.mark.parametrize('durable',[False,True])
    def test_atomic_claims_and_visibility(self,durable,tmp_path):
        from forge import Job
        from forge.brokers import MemoryBroker,SQLiteBroker
        now=[0.]
        broker=SQLiteBroker(tmp_path/'queue.db',clock=lambda:now[0],lease_seconds=5) if durable else MemoryBroker(clock=lambda:now[0],lease_seconds=5)
        async def scenario():
            for i in range(50): await broker.enqueue(Job(id=str(i),task_name='noop'))
            jobs=await asyncio.gather(*(broker.reserve(timeout=0) for _ in range(50)))
            assert len({j.id for j in jobs})==50
            assert await broker.reserve(timeout=0) is None
            now[0]=6
            retried=await broker.reserve(timeout=0)
            assert retried is not None
            await broker.ack(retried.id,result='ok')
        asyncio.run(scenario())


class TestMilestone3:
    def test_worker_executes_retries_and_shuts_down(self):
        from forge import Job
        from forge.jobs import TaskDefinition
        from forge.brokers import MemoryBroker
        from forge.worker import Worker
        calls=[]
        async def compute(value):
            calls.append(value)
            if calls.count(value)==1: raise RuntimeError('transient')
            return value*2
        async def scenario():
            broker=MemoryBroker()
            registry={'double':TaskDefinition(name='double',func=compute,is_async=True,max_retries=2)}
            await broker.enqueue(Job(id='a',task_name='double',args=(3,)))
            worker=Worker(broker,registry,concurrency=2,poll_interval=0.001)
            running=asyncio.create_task(worker.run())
            try:
                for _ in range(200):
                    job=await broker.get('a')
                    if job.state.value=='succeeded':break
                    await asyncio.sleep(0.01)
                assert job.state.value=='succeeded' and job.result==6
                assert calls==[3,3]
            finally:
                await worker.stop();await asyncio.wait_for(running,2)
        asyncio.run(scenario())


class TestMilestone4:
    @pytest.mark.parametrize('cron,minutes',[('*/5 * * * *',5),('1,6 * * * *',1),('0 * * * *',60)])
    def test_next_run_is_strictly_future(self,cron,minutes):
        from forge.scheduler import next_run_at
        after=datetime(2026,1,1,tzinfo=timezone.utc)
        assert (next_run_at(cron,after)-after).total_seconds()==minutes*60

    def test_shared_scheduler_tick_has_one_job(self):
        from forge.brokers import MemoryBroker
        from forge.scheduler import Scheduler
        async def scenario():
            now=[0.];broker=MemoryBroker(clock=lambda:now[0])
            a=Scheduler(broker,clock=lambda:now[0]);b=Scheduler(broker,clock=lambda:now[0])
            for scheduler in [a,b]:scheduler.add_interval('tick',task_name='noop',seconds=60)
            now[0]=60
            await asyncio.gather(a.tick(),b.tick())
            assert await broker.reserve(timeout=0) is not None
            assert await broker.reserve(timeout=0) is None
        asyncio.run(scenario())


class TestMilestone5:
    def test_chain_group_and_chord(self):
        from forge.flows import chain,group,chord
        async def scenario():
            def double(x):return x*2
            def plus_one(x):return x+1
            assert await chain(plus_one,double).run(2)==6
            assert await group(double,plus_one).run(2)==[4,3]
            assert await chord(group(double,plus_one),sum).run(2)==7
        asyncio.run(scenario())

    def test_circuit_breaker_and_rate_limit(self):
        from forge.control import CircuitBreaker,TokenBucket
        now=[0.];clock=lambda:now[0]
        circuit=CircuitBreaker(threshold=2,cooldown=5,clock=clock)
        circuit.record(False);circuit.record(False)
        assert circuit.allow() is False
        now[0]=6;assert circuit.allow() is True
        circuit.record(True);assert circuit.allow() is True
        bucket=TokenBucket(rate=1,capacity=1,clock=clock)
        assert bucket.allow() is True and bucket.allow() is False
        now[0]+=1;assert bucket.allow() is True


class TestMilestone6:
    @pytest.mark.parametrize('args', [['worker'],['scheduler'],['inspect'],['dlq','list'],['purge']])
    def test_cli_has_operations(self,args):
        from forge.operations import create_parser
        assert create_parser().parse_args(args) is not None

    def test_local_job_span_preserves_parent_trace(self):
        from forge.operations import job_span
        from forge import Job
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        exporter=InMemorySpanExporter();provider=TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter));trace.set_tracer_provider(provider)
        with trace.get_tracer('producer').start_as_current_span('request') as parent:
            expected=parent.get_span_context().trace_id
            from opentelemetry.propagate import inject
            headers={};inject(headers)
        with job_span(Job(id='a',task_name='noop'),trace_context=headers):pass
        spans=exporter.get_finished_spans()
        assert spans[-1].context.trace_id==expected
        assert spans[-1].attributes['job_id']=='a'
