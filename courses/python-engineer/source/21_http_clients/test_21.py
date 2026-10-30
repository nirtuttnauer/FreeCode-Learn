import asyncio

import httpx
import pytest

from courselib import impl

m = impl("21")

BASE = "https://api.example.com"


def transport(handler):
    return httpx.MockTransport(handler)


def json_ok(payload, status=200, headers=None):
    return lambda request: httpx.Response(status, json=payload, headers=headers or {})


def run(coro):
    return asyncio.run(coro)


class TestBuildClient:
    def test_base_url_and_headers(self):
        with m.build_client(BASE, transport=transport(json_ok({}))) as client:
            assert str(client.base_url).rstrip("/") == BASE
            assert client.headers["accept"] == "application/json"
            assert "mypycourse" in client.headers["user-agent"]

    def test_token_becomes_a_bearer_header(self):
        with m.build_client(BASE, token="secret", transport=transport(json_ok({}))) as client:
            assert client.headers["authorization"] == "Bearer secret"

    def test_no_token_no_header(self):
        with m.build_client(BASE, transport=transport(json_ok({}))) as client:
            assert "authorization" not in client.headers

    def test_timeout_is_set(self):
        with m.build_client(BASE, transport=transport(json_ok({}))) as client:
            assert client.timeout.read == 10.0
            assert client.timeout.connect == 5.0

    def test_follows_redirects(self):
        with m.build_client(BASE, transport=transport(json_ok({}))) as client:
            assert client.follow_redirects is True


class TestFetchJson:
    def test_success(self):
        with m.build_client(BASE, transport=transport(json_ok({"ok": True}))) as client:
            assert m.fetch_json(client, "/thing") == {"ok": True}

    def test_query_params_are_sent(self):
        seen = {}

        def handler(request):
            seen["params"] = dict(request.url.params)
            return httpx.Response(200, json={})

        with m.build_client(BASE, transport=transport(handler)) as client:
            m.fetch_json(client, "/thing", page=2, q="x")
        assert seen["params"] == {"page": "2", "q": "x"}

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
    def test_4xx_is_a_client_error(self, status):
        with m.build_client(BASE, transport=transport(json_ok({}, status))) as client:
            with pytest.raises(m.ApiClientError) as info:
                m.fetch_json(client, "/thing")
            assert info.value.status_code == status

    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_retryable_statuses_are_unavailable(self, status):
        with m.build_client(BASE, transport=transport(json_ok({}, status))) as client:
            with pytest.raises(m.ApiUnavailable):
                m.fetch_json(client, "/thing")

    def test_transport_error_is_translated(self):
        def broken(request):
            raise httpx.ConnectError("refused", request=request)

        with m.build_client(BASE, transport=transport(broken)) as client:
            with pytest.raises(m.ApiUnavailable):
                m.fetch_json(client, "/thing")

    def test_invalid_json_body(self):
        def handler(request):
            return httpx.Response(200, content=b"not json")

        with m.build_client(BASE, transport=transport(handler)) as client:
            with pytest.raises(m.ApiError):
                m.fetch_json(client, "/thing")

    def test_httpx_errors_do_not_escape(self):
        with m.build_client(BASE, transport=transport(json_ok({}, 500))) as client:
            try:
                m.fetch_json(client, "/thing")
            except Exception as exc:
                assert not isinstance(exc, httpx.HTTPError)

    def test_error_hierarchy(self):
        assert issubclass(m.ApiClientError, m.ApiError)
        assert issubclass(m.ApiUnavailable, m.ApiError)


class TestRequestWithRetry:
    def test_returns_on_success(self):
        with m.build_client(BASE, transport=transport(json_ok({"ok": 1}))) as client:
            response = m.request_with_retry(client, "GET", "/x", sleeper=lambda _: None)
            assert response.status_code == 200

    def test_retries_then_succeeds(self):
        calls = []

        def handler(request):
            calls.append(1)
            if len(calls) < 3:
                return httpx.Response(503)
            return httpx.Response(200, json={"attempt": len(calls)})

        with m.build_client(BASE, transport=transport(handler)) as client:
            response = m.request_with_retry(client, "GET", "/x", attempts=5, sleeper=lambda _: None)
            assert response.json() == {"attempt": 3}

    def test_exponential_delays(self):
        slept = []
        with m.build_client(BASE, transport=transport(json_ok({}, 503))) as client:
            m.request_with_retry(
                client, "GET", "/x", attempts=4, base_delay=1, sleeper=slept.append
            )
        assert slept == [1, 2, 4]  # nothing after the final attempt

    def test_honours_retry_after(self):
        slept = []
        handler = json_ok({}, 429, {"Retry-After": "7"})
        with m.build_client(BASE, transport=transport(handler)) as client:
            m.request_with_retry(
                client, "GET", "/x", attempts=2, base_delay=1, sleeper=slept.append
            )
        assert slept == [7.0]

    @pytest.mark.parametrize("status", [400, 404, 422, 500])
    def test_does_not_retry_client_errors_or_500(self, status):
        calls = []

        def handler(request):
            calls.append(1)
            return httpx.Response(status)

        with m.build_client(BASE, transport=transport(handler)) as client:
            m.request_with_retry(client, "GET", "/x", attempts=5, sleeper=lambda _: None)
        assert len(calls) == 1

    def test_retries_transport_errors(self):
        calls = []

        def handler(request):
            calls.append(1)
            if len(calls) < 2:
                raise httpx.ConnectTimeout("timed out", request=request)
            return httpx.Response(200, json={})

        with m.build_client(BASE, transport=transport(handler)) as client:
            assert m.request_with_retry(
                client, "GET", "/x", attempts=3, sleeper=lambda _: None
            ).status_code == 200

    def test_reraises_transport_error_after_exhausting(self):
        def broken(request):
            raise httpx.ConnectError("refused", request=request)

        with m.build_client(BASE, transport=transport(broken)) as client:
            with pytest.raises(httpx.ConnectError):
                m.request_with_retry(client, "GET", "/x", attempts=2, sleeper=lambda _: None)

    def test_rejects_bad_attempts(self):
        with m.build_client(BASE, transport=transport(json_ok({}))) as client:
            with pytest.raises(ValueError):
                m.request_with_retry(client, "GET", "/x", attempts=0)

    def test_passes_kwargs_through(self):
        seen = {}

        def handler(request):
            seen["body"] = request.content
            return httpx.Response(200, json={})

        with m.build_client(BASE, transport=transport(handler)) as client:
            m.request_with_retry(client, "POST", "/x", json={"a": 1}, sleeper=lambda _: None)
        assert b'"a"' in seen["body"]


def paged_handler(request):
    page = int(request.url.params.get("page", 1))
    if request.url.path == "/items" and page < 3:
        return httpx.Response(
            200,
            json={"items": [{"id": page * 10}], "next": f"/items?page={page + 1}"},
        )
    return httpx.Response(200, json={"items": [{"id": 30}], "next": None})


class TestPaginate:
    def test_follows_the_chain(self):
        with m.build_client(BASE, transport=transport(paged_handler)) as client:
            assert [i["id"] for i in m.paginate(client, "/items")] == [10, 20, 30]

    def test_is_lazy(self):
        calls = []

        def handler(request):
            calls.append(1)
            return paged_handler(request)

        with m.build_client(BASE, transport=transport(handler)) as client:
            pages = m.paginate(client, "/items")
            next(pages)
            assert len(calls) == 1  # only the first page was fetched

    def test_single_page(self):
        with m.build_client(BASE, transport=transport(json_ok({"items": [{"id": 1}]}))) as client:
            assert len(list(m.paginate(client, "/items"))) == 1

    def test_empty(self):
        with m.build_client(BASE, transport=transport(json_ok({"items": []}))) as client:
            assert list(m.paginate(client, "/items")) == []

    def test_errors_are_domain_errors(self):
        with m.build_client(BASE, transport=transport(json_ok({}, 500))) as client:
            with pytest.raises(m.ApiUnavailable):
                list(m.paginate(client, "/items"))


class TestFetchAll:
    def make_client(self, handler):
        return httpx.AsyncClient(base_url=BASE, transport=transport(handler))

    def test_results_in_input_order(self):
        async def handler(request):
            await asyncio.sleep(0.02 if request.url.path == "/a" else 0)
            return httpx.Response(200, json={"path": request.url.path})

        async def main():
            async with self.make_client(handler) as client:
                return await m.fetch_all(client, ["/a", "/b", "/c"])

        assert [r["path"] for r in run(main())] == ["/a", "/b", "/c"]

    def test_respects_the_limit(self):
        state = {"now": 0, "peak": 0}

        async def handler(request):
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
            await asyncio.sleep(0.02)
            state["now"] -= 1
            return httpx.Response(200, json={})

        async def main():
            async with self.make_client(handler) as client:
                await m.fetch_all(client, [f"/{n}" for n in range(20)], limit=4)

        run(main())
        assert state["peak"] <= 4

    def test_empty(self):
        async def main():
            async with self.make_client(json_ok({})) as client:
                return await m.fetch_all(client, [])

        assert run(main()) == []

    def test_rejects_bad_limit(self):
        async def main():
            async with self.make_client(json_ok({})) as client:
                return await m.fetch_all(client, ["/a"], limit=0)

        with pytest.raises(ValueError):
            run(main())

    def test_failure_propagates_as_a_domain_error(self):
        async def main():
            async with self.make_client(json_ok({}, 503)) as client:
                return await m.fetch_all(client, ["/a"])

        with pytest.raises(m.ApiUnavailable):
            run(main())


class TestStreamLines:
    def test_yields_lines(self):
        def handler(request):
            return httpx.Response(200, content=b"one\ntwo\nthree\n")

        async def main():
            async with httpx.AsyncClient(base_url=BASE, transport=transport(handler)) as client:
                return [line async for line in m.stream_lines(client, "/stream")]

        assert run(main()) == ["one", "two", "three"]

    def test_skips_blank_lines(self):
        def handler(request):
            return httpx.Response(200, content=b"one\n\n\ntwo\n")

        async def main():
            async with httpx.AsyncClient(base_url=BASE, transport=transport(handler)) as client:
                return [line async for line in m.stream_lines(client, "/stream")]

        assert run(main()) == ["one", "two"]

    def test_error_status_raises_before_streaming(self):
        async def main():
            async with httpx.AsyncClient(
                base_url=BASE, transport=transport(json_ok({}, 404))
            ) as client:
                return [line async for line in m.stream_lines(client, "/stream")]

        with pytest.raises(m.ApiClientError):
            run(main())

    def test_empty_body(self):
        def handler(request):
            return httpx.Response(200, content=b"")

        async def main():
            async with httpx.AsyncClient(base_url=BASE, transport=transport(handler)) as client:
                return [line async for line in m.stream_lines(client, "/stream")]

        assert run(main()) == []
