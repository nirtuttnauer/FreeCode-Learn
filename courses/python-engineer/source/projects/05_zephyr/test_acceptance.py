"""Acceptance tests for zephyr, milestones 1-4.

Run: pytest projects/05_zephyr -o addopts=""

Note that these use YOUR TestClient, not one from a library. If the client works, you
understand ASGI.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import pytest

sys.path.insert(0, str(Path(__file__).parent / "src"))

zephyr = pytest.importorskip("zephyr")
from zephyr import Depends, HTTPException, Zephyr  # noqa: E402
from zephyr.app import TestClient  # noqa: E402


@dataclass
class UserIn:
    name: str
    age: int = 0


@pytest.fixture
def app():
    return Zephyr(title="Test", version="1.0.0")


class TestBasics:
    def test_hello_world(self, app):
        @app.get("/")
        async def index() -> dict:
            return {"hello": "world"}

        response = TestClient(app).get("/")
        assert response.status_code == 200
        assert response.json() == {"hello": "world"}

    def test_content_type_and_length(self, app):
        @app.get("/")
        async def index() -> dict:
            return {"a": 1}

        response = TestClient(app).get("/")
        assert response.headers["content-type"].startswith("application/json")
        assert int(response.headers["content-length"]) == len(response.content)

    def test_unknown_path_is_404(self, app):
        assert TestClient(app).get("/nope").status_code == 404

    def test_wrong_method_is_405_with_allow(self, app):
        @app.get("/only-get")
        async def handler() -> dict:
            return {}

        response = TestClient(app).post("/only-get")
        assert response.status_code == 405
        assert "GET" in response.headers["allow"]

    def test_sync_handlers_work(self, app):
        @app.get("/sync")
        def handler() -> dict:
            return {"sync": True}

        assert TestClient(app).get("/sync").json() == {"sync": True}

    def test_unhandled_exception_is_500_without_a_traceback(self, app):
        @app.get("/boom")
        async def handler() -> dict:
            raise RuntimeError("internal detail nobody should see")

        response = TestClient(app).get("/boom")
        assert response.status_code == 500
        assert "internal detail" not in response.text

    def test_lifespan_runs(self):
        events = []

        async def lifespan(app):
            events.append("startup")
            yield
            events.append("shutdown")

        app = Zephyr(lifespan=lifespan)

        @app.get("/")
        async def index() -> dict:
            return {}

        with TestClient(app) as client:
            client.get("/")
            assert events == ["startup"]
        assert events == ["startup", "shutdown"]


class TestRouting:
    def test_path_parameters(self, app):
        @app.get("/users/{user_id}")
        async def handler(user_id: int) -> dict:
            return {"user_id": user_id, "type": type(user_id).__name__}

        assert TestClient(app).get("/users/42").json() == {"user_id": 42, "type": "int"}

    def test_typed_converter_rejects_bad_input(self, app):
        @app.get("/users/{user_id:int}")
        async def handler(user_id: int) -> dict:
            return {}

        assert TestClient(app).get("/users/abc").status_code == 422

    def test_path_converter_matches_slashes(self, app):
        @app.get("/files/{rest:path}")
        async def handler(rest: str) -> dict:
            return {"rest": rest}

        assert TestClient(app).get("/files/a/b/c.txt").json() == {"rest": "a/b/c.txt"}

    def test_multiple_path_parameters(self, app):
        @app.get("/users/{user_id}/posts/{slug}")
        async def handler(user_id: int, slug: str) -> dict:
            return {"user_id": user_id, "slug": slug}

        assert TestClient(app).get("/users/1/posts/hello").json() == {"user_id": 1, "slug": "hello"}

    def test_static_route_beats_a_parameterised_one(self, app):
        @app.get("/users/{user_id}")
        async def by_id(user_id: str) -> dict:
            return {"which": "dynamic"}

        @app.get("/users/me")
        async def me() -> dict:
            return {"which": "static"}

        assert TestClient(app).get("/users/me").json() == {"which": "static"}


class TestParameterBinding:
    def test_query_parameters(self, app):
        @app.get("/search")
        async def handler(q: str, limit: int = 10) -> dict:
            return {"q": q, "limit": limit}

        client = TestClient(app)
        assert client.get("/search", params={"q": "x"}).json() == {"q": "x", "limit": 10}
        assert client.get("/search", params={"q": "x", "limit": "5"}).json()["limit"] == 5

    def test_missing_required_query_is_422(self, app):
        @app.get("/search")
        async def handler(q: str) -> dict:
            return {}

        assert TestClient(app).get("/search").status_code == 422

    def test_bad_query_type_is_422_with_field_errors(self, app):
        @app.get("/search")
        async def handler(limit: int = 1) -> dict:
            return {}

        response = TestClient(app).get("/search", params={"limit": "many"})
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["query", "limit"]

    def test_bool_query_coercion(self, app):
        @app.get("/flag")
        async def handler(verbose: bool = False) -> dict:
            return {"verbose": verbose}

        client = TestClient(app)
        assert client.get("/flag", params={"verbose": "true"}).json()["verbose"] is True
        assert client.get("/flag", params={"verbose": "false"}).json()["verbose"] is False

    def test_body_binding(self, app):
        @app.post("/users")
        async def handler(body: UserIn) -> dict:
            return {"name": body.name, "age": body.age}

        response = TestClient(app).post("/users", json={"name": "ada", "age": 36})
        assert response.json() == {"name": "ada", "age": 36}

    def test_invalid_body_is_422(self, app):
        @app.post("/users")
        async def handler(body: UserIn) -> dict:
            return {}

        assert TestClient(app).post("/users", json={"age": "old"}).status_code == 422

    def test_request_object_injection(self, app):
        from zephyr import Request

        @app.get("/raw")
        async def handler(request: Request) -> dict:
            return {"path": request.path, "method": request.method}

        assert TestClient(app).get("/raw").json() == {"path": "/raw", "method": "GET"}

    def test_headers_are_case_insensitive(self, app):
        from zephyr import Request

        @app.get("/h")
        async def handler(request: Request) -> dict:
            return {"value": request.headers["X-CUSTOM"]}

        response = TestClient(app).get("/h", headers={"x-custom": "hello"})
        assert response.json() == {"value": "hello"}


class TestDependencies:
    def test_simple_dependency(self, app):
        def get_config() -> dict:
            return {"env": "test"}

        @app.get("/")
        async def handler(config: Annotated[dict, Depends(get_config)]) -> dict:
            return config

        assert TestClient(app).get("/").json() == {"env": "test"}

    def test_nested_dependencies(self, app):
        def get_a() -> str:
            return "a"

        def get_b(a: Annotated[str, Depends(get_a)]) -> str:
            return a + "b"

        @app.get("/")
        async def handler(b: Annotated[str, Depends(get_b)]) -> dict:
            return {"value": b}

        assert TestClient(app).get("/").json() == {"value": "ab"}

    def test_cached_within_one_request(self, app):
        calls = []

        def get_session() -> int:
            calls.append(1)
            return len(calls)

        def use_a(s: Annotated[int, Depends(get_session)]) -> int:
            return s

        def use_b(s: Annotated[int, Depends(get_session)]) -> int:
            return s

        @app.get("/")
        async def handler(
            a: Annotated[int, Depends(use_a)], b: Annotated[int, Depends(use_b)]
        ) -> dict:
            return {"a": a, "b": b}

        assert TestClient(app).get("/").json() == {"a": 1, "b": 1}
        assert len(calls) == 1

    def test_yield_dependency_teardown(self, app):
        events = []

        def get_db():
            events.append("open")
            yield "session"
            events.append("close")

        @app.get("/")
        async def handler(db: Annotated[str, Depends(get_db)]) -> dict:
            events.append("handler")
            return {"db": db}

        TestClient(app).get("/")
        assert events == ["open", "handler", "close"]

    def test_teardown_runs_even_when_the_handler_raises(self, app):
        events = []

        def get_db():
            yield "session"
            events.append("closed")

        @app.get("/")
        async def handler(db: Annotated[str, Depends(get_db)]) -> dict:
            raise RuntimeError("boom")

        TestClient(app).get("/")
        assert events == ["closed"]

    def test_dependency_overrides(self, app):
        def get_config() -> dict:
            return {"env": "production"}

        @app.get("/")
        async def handler(config: Annotated[dict, Depends(get_config)]) -> dict:
            return config

        app.dependency_overrides[get_config] = lambda: {"env": "test"}
        assert TestClient(app).get("/").json() == {"env": "test"}

    def test_dependency_can_raise_http_exception(self, app):
        def require_auth() -> str:
            raise HTTPException(401, "unauthorised", headers={"WWW-Authenticate": "Bearer"})

        @app.get("/private")
        async def handler(user: Annotated[str, Depends(require_auth)]) -> dict:
            return {}

        response = TestClient(app).get("/private")
        assert response.status_code == 401
        assert response.json()["detail"] == "unauthorised"
        assert response.headers["www-authenticate"] == "Bearer"


class TestExceptionHandling:
    def test_http_exception(self, app):
        @app.get("/missing")
        async def handler() -> dict:
            raise HTTPException(404, "no such thing")

        response = TestClient(app).get("/missing")
        assert response.status_code == 404
        assert response.json() == {"detail": "no such thing"}

    def test_custom_exception_handler(self, app):
        class DomainError(Exception):
            pass

        @app.exception_handler(DomainError)
        async def handle(request, exc):
            from zephyr import JSONResponse

            return JSONResponse({"detail": "domain"}, status_code=418)

        @app.get("/domain")
        async def handler() -> dict:
            raise DomainError()

        assert TestClient(app).get("/domain").status_code == 418

    def test_handler_resolution_follows_the_mro(self, app):
        @app.exception_handler(LookupError)
        async def handle(request, exc):
            from zephyr import JSONResponse

            return JSONResponse({"detail": "lookup"}, status_code=404)

        @app.get("/key")
        async def handler() -> dict:
            raise KeyError("missing")  # a subclass of LookupError

        assert TestClient(app).get("/key").status_code == 404
