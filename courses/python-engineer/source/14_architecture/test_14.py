from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from courselib import impl

m = impl("14")
Task = m.Task


class TestTask:
    def test_is_a_frozen_slotted_dataclass(self):
        assert is_dataclass(Task)
        with pytest.raises(FrozenInstanceError):
            Task(1, "a").title = "b"
        assert not hasattr(Task(1, "a"), "__dict__")

    def test_defaults(self):
        t = Task(1, "write tests")
        assert (t.done, t.tags) == (False, ())

    def test_blank_title_rejected(self):
        for bad in ["", "   "]:
            with pytest.raises(ValueError, match="title is required"):
                Task(1, bad)

    def test_complete_returns_a_new_task(self):
        original = Task(1, "a")
        done = original.complete()
        assert done.done and not original.done
        assert done is not original

    def test_with_tag(self):
        t = Task(1, "a").with_tag("urgent")
        assert t.tags == ("urgent",)

    def test_with_tag_ignores_duplicates(self):
        t = Task(1, "a").with_tag("x").with_tag("x")
        assert t.tags == ("x",)

    def test_hashable(self):
        assert len({Task(1, "a"), Task(1, "a")}) == 1


class TestInMemoryTasks:
    def test_get_and_save(self):
        repo = m.InMemoryTasks()
        repo.save(Task(1, "a"))
        assert repo.get(1).title == "a"

    def test_get_unknown_returns_none(self):
        assert m.InMemoryTasks().get(99) is None

    def test_seeded_construction(self):
        repo = m.InMemoryTasks([Task(1, "a"), Task(2, "b")])
        assert len(repo.list_all()) == 2

    def test_save_overwrites(self):
        repo = m.InMemoryTasks([Task(1, "a")])
        repo.save(Task(1, "a").complete())
        assert repo.get(1).done

    def test_delete(self):
        repo = m.InMemoryTasks([Task(1, "a")])
        repo.delete(1)
        assert repo.get(1) is None

    def test_delete_unknown_raises(self):
        with pytest.raises(KeyError):
            m.InMemoryTasks().delete(99)

    def test_list_all_is_a_copy(self):
        repo = m.InMemoryTasks([Task(1, "a")])
        repo.list_all().clear()
        assert len(repo.list_all()) == 1

    def test_does_not_inherit_the_protocol(self):
        assert m.TaskRepository not in m.InMemoryTasks.__mro__

    def test_satisfies_the_protocol_structurally(self):
        for method in ("get", "save", "delete", "list_all"):
            assert callable(getattr(m.InMemoryTasks(), method))


class TestTaskService:
    @pytest.fixture
    def repo(self):
        return m.InMemoryTasks()

    @pytest.fixture
    def service(self, repo):
        return m.TaskService(repo, clock=lambda: 1000.0)

    def test_create_assigns_ids_from_one(self, service):
        assert service.create("first").id == 1
        assert service.create("second").id == 2

    def test_create_continues_after_existing_ids(self):
        service = m.TaskService(m.InMemoryTasks([Task(7, "old")]))
        assert service.create("new").id == 8

    def test_create_with_tags(self, service):
        assert service.create("a", tags=("x",)).tags == ("x",)

    def test_create_persists(self, service, repo):
        task = service.create("a")
        assert repo.get(task.id) == task

    def test_complete(self, service):
        task = service.create("a")
        assert service.complete(task.id).done

    def test_complete_unknown_raises_domain_error(self, service):
        with pytest.raises(LookupError) as info:
            service.complete(42)
        assert str(info.value) == "task 42 not found"

    def test_complete_is_idempotent(self, service):
        task = service.create("a")
        service.complete(task.id)
        assert service.complete(task.id).done

    def test_stats(self, service):
        service.create("a")
        second = service.create("b")
        service.complete(second.id)
        assert service.stats() == {"total": 2, "done": 1, "open": 1}

    def test_stats_when_empty(self, service):
        assert service.stats() == {"total": 0, "done": 0, "open": 0}

    def test_publishes_events(self, repo):
        bus = m.EventBus()
        seen = []
        bus.subscribe(m.TaskCreated, seen.append)
        bus.subscribe(m.TaskCompleted, seen.append)
        service = m.TaskService(repo, bus=bus)
        task = service.create("a")
        service.complete(task.id)
        assert [type(e).__name__ for e in seen] == ["TaskCreated", "TaskCompleted"]

    def test_no_event_for_a_repeated_completion(self, repo):
        bus = m.EventBus()
        seen = []
        bus.subscribe(m.TaskCompleted, seen.append)
        service = m.TaskService(repo, bus=bus)
        task = service.create("a")
        service.complete(task.id)
        service.complete(task.id)
        assert len(seen) == 1

    def test_works_without_a_bus(self, service):
        assert service.create("a").id == 1

    def test_works_with_any_repository_shape(self):
        class ListBackedTasks:  # a second, unrelated implementation
            def __init__(self):
                self.rows = []

            def get(self, task_id):
                return next((t for t in self.rows if t.id == task_id), None)

            def save(self, task):
                self.rows = [t for t in self.rows if t.id != task.id] + [task]

            def delete(self, task_id):
                self.rows = [t for t in self.rows if t.id != task_id]

            def list_all(self):
                return list(self.rows)

        service = m.TaskService(ListBackedTasks())
        task = service.create("a")
        assert service.complete(task.id).done


class TestEventBus:
    def test_publish_calls_subscribers(self):
        bus = m.EventBus()
        seen = []
        bus.subscribe(m.TaskCreated, seen.append)
        bus.publish(m.TaskCreated(1))
        assert len(seen) == 1

    def test_several_handlers_in_order(self):
        bus = m.EventBus()
        order = []
        bus.subscribe(m.TaskCreated, lambda e: order.append("first"))
        bus.subscribe(m.TaskCreated, lambda e: order.append("second"))
        bus.publish(m.TaskCreated(1))
        assert order == ["first", "second"]

    def test_dispatch_is_per_type(self):
        bus = m.EventBus()
        created, completed = [], []
        bus.subscribe(m.TaskCreated, created.append)
        bus.subscribe(m.TaskCompleted, completed.append)
        bus.publish(m.TaskCreated(1))
        assert len(created) == 1 and len(completed) == 0

    def test_no_subscribers_is_a_noop(self):
        m.EventBus().publish(m.TaskCreated(1))

    def test_failing_handler_does_not_stop_the_others(self):
        bus = m.EventBus()
        seen = []

        def bad(event):
            raise RuntimeError("handler exploded")

        bus.subscribe(m.TaskCreated, bad)
        bus.subscribe(m.TaskCreated, seen.append)
        with pytest.raises(ExceptionGroup) as info:
            bus.publish(m.TaskCreated(1))
        assert len(seen) == 1
        assert len(info.value.exceptions) == 1

    def test_unsubscribe(self):
        bus = m.EventBus()
        seen = []
        handler = seen.append
        bus.subscribe(m.TaskCompleted, handler)
        bus.unsubscribe(m.TaskCompleted, handler)
        bus.publish(m.TaskCompleted(1))
        assert seen == []

    def test_unsubscribe_unknown_raises(self):
        with pytest.raises(ValueError):
            m.EventBus().unsubscribe(m.TaskCreated, print)


class TestRender:
    def test_text(self):
        assert m.render(m.Text("hello")) == "hello"

    def test_plain_strings(self):
        assert m.render("hello") == "hello"

    def test_bold_and_italic(self):
        assert m.render(m.Bold(m.Text("hi"))) == "**hi**"
        assert m.render(m.Italic("hi")) == "_hi_"

    def test_nesting(self):
        assert m.render(m.Bold(m.Italic("hi"))) == "**_hi_**"

    def test_paragraph(self):
        assert m.render(m.Paragraph([m.Text("a"), m.Bold("b")])) == "a **b**"

    def test_document(self):
        doc = m.Document([m.Paragraph(["one"]), m.Paragraph(["two"])])
        assert m.render(doc) == "one\n\ntwo"

    def test_unknown_type(self):
        with pytest.raises(TypeError, match="no renderer for int"):
            m.render(42)

    def test_third_parties_can_extend_it(self):
        class Strikethrough:
            def __init__(self, child):
                self.child = child

        @m.render.register
        def _(node: Strikethrough) -> str:
            return f"~~{m.render(node.child)}~~"

        assert m.render(Strikethrough("gone")) == "~~gone~~"
        assert m.render(m.Bold(Strikethrough("x"))) == "**~~x~~**"
