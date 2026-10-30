"""Acceptance tests for forge, milestone 1 (jobs, states, registry).

Run: pytest projects/04_forge -o addopts=""

Milestone 2's broker contract suite is the one that matters most — write it as a single
parametrised suite that every broker implementation must pass, including the concurrent
reservation test sketched at the bottom of this file.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "src"))

forge = pytest.importorskip("forge")
from forge.jobs import REGISTRY, InvalidTransition, Job, JobState, NotSerialisable  # noqa: E402


@pytest.fixture(autouse=True)
def clean_registry():
    saved = dict(REGISTRY)
    REGISTRY.clear()
    yield
    REGISTRY.clear()
    REGISTRY.update(saved)


def make_job(**overrides) -> Job:
    defaults = {"id": "job-1", "task_name": "noop"}
    return Job(**{**defaults, **overrides})


class TestStateMachine:
    def test_starts_pending(self):
        assert make_job().state is JobState.PENDING

    @pytest.mark.parametrize(
        ("start", "target"),
        [
            (JobState.PENDING, JobState.RUNNING),
            (JobState.PENDING, JobState.CANCELLED),
            (JobState.RUNNING, JobState.SUCCEEDED),
            (JobState.RUNNING, JobState.FAILED),
            (JobState.RUNNING, JobState.RETRYING),
            (JobState.RETRYING, JobState.RUNNING),
            (JobState.RETRYING, JobState.DEAD),
            (JobState.FAILED, JobState.RETRYING),
            (JobState.FAILED, JobState.DEAD),
        ],
    )
    def test_legal_transitions(self, start, target):
        job = make_job(state=start)
        job.transition_to(target)
        assert job.state is target

    @pytest.mark.parametrize(
        ("start", "target"),
        [
            (JobState.PENDING, JobState.SUCCEEDED),
            (JobState.SUCCEEDED, JobState.RUNNING),
            (JobState.DEAD, JobState.PENDING),
            (JobState.CANCELLED, JobState.RUNNING),
            (JobState.RUNNING, JobState.PENDING),
        ],
    )
    def test_illegal_transitions_raise(self, start, target):
        with pytest.raises(InvalidTransition):
            make_job(state=start).transition_to(target)

    @pytest.mark.parametrize(
        "state", [JobState.SUCCEEDED, JobState.DEAD, JobState.CANCELLED]
    )
    def test_terminal_states(self, state):
        assert make_job(state=state).is_terminal

    @pytest.mark.parametrize("state", [JobState.PENDING, JobState.RUNNING, JobState.RETRYING])
    def test_non_terminal_states(self, state):
        assert not make_job(state=state).is_terminal


class TestRetryPolicy:
    def test_can_retry_within_limit(self):
        assert make_job(attempt=1, max_retries=3).can_retry()

    def test_cannot_retry_at_the_limit(self):
        assert not make_job(attempt=3, max_retries=3).can_retry()

    def test_zero_retries(self):
        assert not make_job(attempt=0, max_retries=0).can_retry()

    def test_exponential_backoff(self):
        delays = [
            make_job(attempt=n).next_retry_delay(base=1.0, cap=300.0, jitter=1.0)
            for n in range(5)
        ]
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]

    def test_backoff_is_capped(self):
        assert make_job(attempt=20).next_retry_delay(base=1.0, cap=300.0, jitter=1.0) == 300.0

    def test_jitter_is_applied(self):
        assert make_job(attempt=2).next_retry_delay(base=1.0, cap=300.0, jitter=0.5) == 2.0


class TestSerialisation:
    def test_round_trip(self):
        job = make_job(args=(1, "two"), kwargs={"k": [1, 2]}, priority=5, attempt=2)
        restored = Job.from_json(job.to_json())
        assert restored.id == job.id
        assert restored.task_name == job.task_name
        assert tuple(restored.args) == (1, "two")
        assert restored.kwargs == {"k": [1, 2]}
        assert restored.priority == 5
        assert restored.attempt == 2

    def test_state_survives(self):
        job = make_job(state=JobState.RETRYING)
        assert Job.from_json(job.to_json()).state is JobState.RETRYING

    def test_output_is_valid_json(self):
        json.loads(make_job().to_json())


class TestTaskDecorator:
    def test_registers_by_function_name(self):
        @forge.task
        def send_email(to: str) -> None:
            pass

        assert "send_email" in REGISTRY

    def test_custom_name(self):
        @forge.task(name="mail.send")
        def send(to: str) -> None:
            pass

        assert "mail.send" in REGISTRY

    def test_duplicate_name_raises(self):
        @forge.task(name="dup")
        def a() -> None:
            pass

        with pytest.raises(ValueError):

            @forge.task(name="dup")
            def b() -> None:
                pass

    def test_options_are_stored(self):
        @forge.task(max_retries=7, timeout=30, rate_limit="10/s", cpu_bound=True)
        def crunch(n: int) -> int:
            return n

        definition = REGISTRY["crunch"]
        assert definition.max_retries == 7
        assert definition.timeout == 30
        assert definition.rate_limit == "10/s"
        assert definition.cpu_bound is True

    def test_async_tasks_are_detected(self):
        @forge.task
        async def fetch(url: str) -> str:
            return url

        assert REGISTRY["fetch"].is_async is True

    def test_original_function_is_still_callable(self):
        @forge.task
        def double(n: int) -> int:
            return n * 2

        assert double(21) == 42

    def test_has_delay_and_apply_async(self):
        @forge.task
        def noop() -> None:
            pass

        assert callable(noop.delay)
        assert callable(noop.apply_async)

    def test_unserialisable_arguments_are_rejected_at_enqueue(self):
        @forge.task
        def handle(payload: object) -> None:
            pass

        with pytest.raises(NotSerialisable):
            handle.delay(payload=object())


# ---------------------------------------------------------------------------------------
# Milestone 2 sketch — write this one yourself, and run it against EVERY broker.
#
# @pytest.mark.parametrize("broker_factory", [MemoryBroker, SQLiteBroker])
# def test_no_job_is_reserved_twice(broker_factory):
#     broker = broker_factory()
#     for i in range(50):
#         await broker.enqueue(make_job(id=f"job-{i}"))
#
#     async def claim_all():
#         claimed = []
#         while (job := await broker.reserve(timeout=0.01)) is not None:
#             claimed.append(job.id)
#         return claimed
#
#     results = await asyncio.gather(*(claim_all() for _ in range(10)))
#     everything = [job_id for batch in results for job_id in batch]
#     assert sorted(everything) == sorted(f"job-{i}" for i in range(50))   # no duplicates
#
# If that test is flaky, your reservation isn't atomic — and a flaky queue loses money.
# ---------------------------------------------------------------------------------------
