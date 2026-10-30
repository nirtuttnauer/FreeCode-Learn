import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from courselib import impl

m = impl("15")


@pytest.fixture
def repo():
    return m.InMemoryTaskRepo()


@pytest.fixture
def client(repo):
    with TestClient(m.create_app(repo)) as c:
        yield c


class TestModels:
    def test_valid_task_in(self):
        task = m.TaskIn.model_validate({"title": "write tests"})
        assert (task.title, task.priority, task.tags) == ("write tests", 1, [])

    def test_title_is_stripped(self):
        assert m.TaskIn.model_validate({"title": "  x  "}).title == "x"

    def test_whitespace_only_title_rejected(self):
        with pytest.raises(ValidationError):
            m.TaskIn.model_validate({"title": "   "})

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            m.TaskIn.model_validate({"title": ""})

    def test_long_title_rejected(self):
        with pytest.raises(ValidationError):
            m.TaskIn.model_validate({"title": "x" * 201})

    @pytest.mark.parametrize("priority", [0, 6, -1])
    def test_priority_range(self, priority):
        with pytest.raises(ValidationError):
            m.TaskIn.model_validate({"title": "x", "priority": priority})

    def test_priority_is_coerced_from_a_string(self):
        assert m.TaskIn.model_validate({"title": "x", "priority": "3"}).priority == 3

    def test_extra_keys_forbidden(self):
        with pytest.raises(ValidationError):
            m.TaskIn.model_validate({"title": "x", "admin": True})

    def test_tags_default_is_not_shared(self):
        a = m.TaskIn(title="a")
        b = m.TaskIn(title="b")
        a.tags.append("x")
        assert b.tags == []

    def test_task_out_fields(self):
        assert set(m.TaskOut.model_fields) == {"id", "title", "priority", "done"}


class TestRepo:
    def test_add_assigns_sequential_ids(self, repo):
        assert repo.add(m.TaskIn(title="a"))["id"] == 1
        assert repo.add(m.TaskIn(title="b"))["id"] == 2

    def test_new_tasks_are_not_done(self, repo):
        assert repo.add(m.TaskIn(title="a"))["done"] is False

    def test_get(self, repo):
        repo.add(m.TaskIn(title="a"))
        assert repo.get(1)["title"] == "a"
        assert repo.get(99) is None

    def test_list_is_a_copy(self, repo):
        repo.add(m.TaskIn(title="a"))
        repo.list().clear()
        assert len(repo.list()) == 1

    def test_complete(self, repo):
        repo.add(m.TaskIn(title="a"))
        assert repo.complete(1)["done"] is True
        assert repo.complete(1)["done"] is True  # idempotent

    def test_complete_unknown(self, repo):
        with pytest.raises(m.TaskNotFound):
            repo.complete(99)

    def test_delete(self, repo):
        repo.add(m.TaskIn(title="a"))
        repo.delete(1)
        assert repo.get(1) is None

    def test_delete_unknown(self, repo):
        with pytest.raises(m.TaskNotFound):
            repo.delete(99)

    def test_not_found_message(self):
        exc = m.TaskNotFound(42)
        assert str(exc) == "task 42 not found"
        assert exc.task_id == 42


class TestApi:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_create_returns_201(self, client):
        response = client.post("/tasks", json={"title": "ship it", "priority": 4})
        assert response.status_code == 201
        assert response.json() == {"id": 1, "title": "ship it", "priority": 4, "done": False}

    def test_response_model_hides_internal_fields(self, client):
        body = client.post("/tasks", json={"title": "a"}).json()
        assert "internal_note" not in body
        assert "tags" not in body

    def test_get_one(self, client):
        client.post("/tasks", json={"title": "a"})
        assert client.get("/tasks/1").json()["title"] == "a"

    def test_get_missing_is_404_with_domain_message(self, client):
        response = client.get("/tasks/42")
        assert response.status_code == 404
        assert response.json() == {"detail": "task 42 not found"}

    def test_list_all(self, client):
        client.post("/tasks", json={"title": "a"})
        client.post("/tasks", json={"title": "b"})
        assert len(client.get("/tasks").json()) == 2

    def test_list_filtered_by_priority(self, client):
        client.post("/tasks", json={"title": "low", "priority": 1})
        client.post("/tasks", json={"title": "high", "priority": 5})
        rows = client.get("/tasks", params={"min_priority": 5}).json()
        assert [r["title"] for r in rows] == ["high"]

    def test_list_filtered_by_done(self, client):
        client.post("/tasks", json={"title": "a"})
        client.post("/tasks", json={"title": "b"})
        client.post("/tasks/2/complete")
        assert [r["id"] for r in client.get("/tasks", params={"done": True}).json()] == [2]
        assert [r["id"] for r in client.get("/tasks", params={"done": False}).json()] == [1]

    def test_complete(self, client):
        client.post("/tasks", json={"title": "a"})
        response = client.post("/tasks/1/complete")
        assert response.status_code == 200
        assert response.json()["done"] is True

    def test_complete_missing_is_404(self, client):
        assert client.post("/tasks/42/complete").status_code == 404

    def test_delete(self, client):
        client.post("/tasks", json={"title": "a"})
        response = client.delete("/tasks/1")
        assert response.status_code == 204
        assert response.content == b""
        assert client.get("/tasks/1").status_code == 404

    def test_delete_missing_is_404(self, client):
        assert client.delete("/tasks/42").status_code == 404

    def test_invalid_body_is_422(self, client):
        response = client.post("/tasks", json={"title": "", "priority": 9})
        assert response.status_code == 422
        assert len(response.json()["detail"]) == 2

    def test_extra_field_is_422(self, client):
        assert client.post("/tasks", json={"title": "a", "hacker": 1}).status_code == 422

    def test_invalid_query_param_is_422(self, client):
        assert client.get("/tasks", params={"min_priority": 99}).status_code == 422

    def test_non_integer_path_param_is_422(self, client):
        assert client.get("/tasks/abc").status_code == 422

    def test_apps_are_isolated(self):
        a, b = m.InMemoryTaskRepo(), m.InMemoryTaskRepo()
        with TestClient(m.create_app(a)) as ca, TestClient(m.create_app(b)) as cb:
            ca.post("/tasks", json={"title": "only in a"})
            assert len(cb.get("/tasks").json()) == 0

    def test_openapi_schema(self, client):
        schema = client.get("/openapi.json").json()
        assert schema["info"]["title"] == "Tasks API"
        assert schema["info"]["version"] == "1.0.0"
        assert set(schema["paths"]) == {
            "/health",
            "/tasks",
            "/tasks/{task_id}",
            "/tasks/{task_id}/complete",
        }


class TestSummariseErrors:
    def test_formats_errors(self):
        try:
            m.TaskIn.model_validate({"title": "", "priority": 9})
        except ValidationError as exc:
            summary = m.summarise_errors(exc)
        assert len(summary) == 2
        assert summary[0].startswith("title: ")
        assert summary[1].startswith("priority: ")

    def test_joins_nested_locations(self):
        from pydantic import BaseModel

        class Wrapper(BaseModel):
            task: m.TaskIn

        try:
            Wrapper.model_validate({"task": {"title": ""}})
        except ValidationError as exc:
            assert m.summarise_errors(exc)[0].startswith("task.title: ")
