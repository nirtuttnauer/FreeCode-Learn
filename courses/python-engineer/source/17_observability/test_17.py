import json
import logging

import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from courselib import impl

m = impl("17")

EXPORTER = InMemorySpanExporter()
READER = InMemoryMetricReader()

# A provider can only be set once per process, so do it at import time.
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(EXPORTER))
trace.set_tracer_provider(_provider)
metrics.set_meter_provider(MeterProvider(metric_readers=[READER]))

tracer = trace.get_tracer("tests")


@pytest.fixture(autouse=True)
def clean_spans():
    EXPORTER.clear()
    yield
    EXPORTER.clear()


def spans_by_name() -> dict:
    return {s.name: s for s in EXPORTER.get_finished_spans()}


def metric_points(name: str) -> list:
    data = READER.get_metrics_data()
    points = []
    for rm in data.resource_metrics:
        for scope in rm.scope_metrics:
            for metric in scope.metrics:
                if metric.name == name:
                    points.extend(metric.data.data_points)
    return points


class TestJsonLogFormatter:
    def format_record(self, msg="event", fields=None, exc_info=None, level=logging.INFO):
        record = logging.LogRecord("mylogger", level, __file__, 1, msg, (), exc_info)
        if fields is not None:
            record.fields = fields
        return json.loads(m.JsonLogFormatter().format(record))

    def test_basic_shape(self):
        payload = self.format_record("order_placed")
        assert payload["level"] == "INFO"
        assert payload["logger"] == "mylogger"
        assert payload["event"] == "order_placed"

    def test_output_is_one_json_line(self):
        record = logging.LogRecord("l", logging.INFO, __file__, 1, "x", (), None)
        assert "\n" not in m.JsonLogFormatter().format(record)

    def test_extra_fields_are_merged(self):
        payload = self.format_record(fields={"order_id": 42, "amount": 1.5})
        assert payload["order_id"] == 42
        assert payload["amount"] == 1.5

    def test_no_trace_id_outside_a_span(self):
        assert "trace_id" not in self.format_record()

    def test_trace_id_inside_a_span(self):
        with tracer.start_as_current_span("work"):
            payload = self.format_record()
        assert len(payload["trace_id"]) == 32
        assert len(payload["span_id"]) == 16
        int(payload["trace_id"], 16)  # valid hex

    def test_exception_line(self):
        try:
            raise ValueError("kaboom")
        except ValueError:
            import sys

            payload = self.format_record(exc_info=sys.exc_info())
        assert payload["error"].endswith("kaboom")

    @pytest.mark.parametrize(
        "key", ["password", "api_token", "SECRET_KEY", "user_password", "Token"]
    )
    def test_redacts_credentials(self, key):
        payload = self.format_record(fields={key: "hunter2"})
        assert payload[key] == "[redacted]"

    def test_does_not_redact_innocent_fields(self):
        assert self.format_record(fields={"order_id": 1})["order_id"] == 1


class TestTraced:
    def test_creates_a_span(self):
        @m.traced()
        def work():
            return "done"

        assert work() == "done"
        assert "work" in spans_by_name()

    def test_custom_name(self):
        @m.traced("custom.name")
        def work():
            pass

        work()
        assert "custom.name" in spans_by_name()

    def test_code_function_attribute(self):
        @m.traced("outer")
        def inner_function():
            pass

        inner_function()
        assert spans_by_name()["outer"].attributes["code.function"] == "inner_function"

    def test_success_leaves_status_unset(self):
        @m.traced()
        def work():
            pass

        work()
        assert spans_by_name()["work"].status.status_code is StatusCode.UNSET

    def test_exception_is_recorded_and_reraised(self):
        @m.traced()
        def boom():
            raise RuntimeError("failed hard")

        with pytest.raises(RuntimeError, match="failed hard"):
            boom()
        span = spans_by_name()["boom"]
        assert span.status.status_code is StatusCode.ERROR
        # The SDK prefixes the exception type when it sets the status on exit, so the
        # description ends with your message rather than being exactly equal to it.
        assert "failed hard" in span.status.description
        assert [e.name for e in span.events].count("exception") >= 1

    def test_preserves_metadata(self):
        @m.traced()
        def documented():
            """Docs."""

        assert documented.__name__ == "documented"
        assert documented.__doc__ == "Docs."

    def test_arguments_pass_through(self):
        @m.traced()
        def add(a, b=0):
            return a + b

        assert add(1, b=2) == 3

    def test_nests(self):
        @m.traced()
        def child():
            pass

        @m.traced()
        def parent():
            child()

        parent()
        found = spans_by_name()
        assert found["child"].parent.span_id == found["parent"].context.span_id


class TestProcessOrder:
    ITEMS = [{"price": 10.0, "quantity": 2}, {"price": 2.5, "quantity": 4}]

    def test_returns_the_result(self):
        got = m.process_order(7, self.ITEMS, lambda total: f"receipt-{total}")
        assert got == {"order_id": 7, "total": 30.0, "receipt": "receipt-30.0"}

    def test_span_attributes(self):
        m.process_order(7, self.ITEMS, lambda t: "ok")
        span = spans_by_name()["process_order"]
        assert span.attributes["order.id"] == 7
        assert span.attributes["order.item_count"] == 2
        assert span.attributes["order.total"] == 30.0

    def test_validated_event(self):
        m.process_order(7, self.ITEMS, lambda t: "ok")
        assert "order.validated" in [e.name for e in spans_by_name()["process_order"].events]

    def test_child_span_around_the_charge(self):
        m.process_order(7, self.ITEMS, lambda t: "ok")
        found = spans_by_name()
        assert found["charge"].parent.span_id == found["process_order"].context.span_id

    def test_span_name_is_low_cardinality(self):
        m.process_order(1, self.ITEMS, lambda t: "ok")
        m.process_order(2, self.ITEMS, lambda t: "ok")
        names = [s.name for s in EXPORTER.get_finished_spans() if s.name != "charge"]
        assert names == ["process_order", "process_order"]  # not "process_order 1"

    def test_charge_failure_marks_both_spans(self):
        def failing(total):
            raise RuntimeError("card declined")

        with pytest.raises(RuntimeError):
            m.process_order(7, self.ITEMS, failing)
        found = spans_by_name()
        assert found["charge"].status.status_code is StatusCode.ERROR
        assert found["process_order"].status.status_code is StatusCode.ERROR
        assert "exception" in [e.name for e in found["charge"].events]

    def test_empty_order_raises_and_is_recorded(self):
        with pytest.raises(ValueError, match="no items"):
            m.process_order(7, [], lambda t: "ok")
        span = spans_by_name()["process_order"]
        assert span.status.status_code is StatusCode.ERROR
        assert "charge" not in spans_by_name()

    def test_accepts_a_generator(self):
        rows = (row for row in self.ITEMS)
        assert m.process_order(1, rows, lambda t: "ok")["total"] == 30.0


class TestRequestMetrics:
    def test_records_requests_and_duration(self):
        rm = m.RequestMetrics()
        rm.record("/orders/{id}", "GET", 200, 0.05)
        counts = metric_points("http.server.requests")
        assert any(p.attributes["http.route"] == "/orders/{id}" for p in counts)
        durations = metric_points("http.server.duration")
        assert any(p.count >= 1 for p in durations)

    def test_error_counter_only_for_5xx(self):
        rm = m.RequestMetrics()
        rm.record("/a", "GET", 404, 0.01)
        before = sum(p.value for p in metric_points("http.server.errors"))
        rm.record("/a", "GET", 500, 0.01)
        after = sum(p.value for p in metric_points("http.server.errors"))
        assert after == before + 1

    def test_attributes_are_the_semconv_names(self):
        rm = m.RequestMetrics()
        rm.record("/unique-route-1", "POST", 201, 0.02)
        point = next(
            p
            for p in metric_points("http.server.requests")
            if p.attributes.get("http.route") == "/unique-route-1"
        )
        assert point.attributes["http.request.method"] == "POST"
        assert point.attributes["http.response.status_code"] == 201

    def test_time_context_manager_measures(self):
        clock = iter([100.0, 100.25]).__next__
        rm = m.RequestMetrics(clock=clock)
        with rm.time("/timed-route", "GET"):
            pass
        point = next(
            p
            for p in metric_points("http.server.duration")
            if p.attributes.get("http.route") == "/timed-route"
        )
        assert point.sum == pytest.approx(0.25)
        assert point.attributes["http.response.status_code"] == 200

    def test_time_records_500_and_reraises(self):
        clock = iter([0.0, 1.0]).__next__
        rm = m.RequestMetrics(clock=clock)
        with pytest.raises(ValueError), rm.time("/failing-route", "GET"):
            raise ValueError("boom")
        point = next(
            p
            for p in metric_points("http.server.requests")
            if p.attributes.get("http.route") == "/failing-route"
        )
        assert point.attributes["http.response.status_code"] == 500


class TestTraceContext:
    def test_empty_without_a_span(self):
        assert m.extract_trace_context() == {}

    def test_injects_traceparent(self):
        with tracer.start_as_current_span("outbound"):
            headers = m.extract_trace_context()
        assert "traceparent" in headers
        version, trace_id, span_id, flags = headers["traceparent"].split("-")
        assert (version, len(trace_id), len(span_id)) == ("00", 32, 16)

    def test_matches_the_current_span(self):
        with tracer.start_as_current_span("outbound") as span:
            headers = m.extract_trace_context()
            expected = format(span.get_span_context().trace_id, "032x")
        assert headers["traceparent"].split("-")[1] == expected
