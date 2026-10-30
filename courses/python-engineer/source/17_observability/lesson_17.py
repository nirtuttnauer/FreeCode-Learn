"""Module 17 — runnable lesson. `python 17_observability/lesson_17.py`

Everything runs against in-memory exporters, so there's no collector and no network.
"""

from __future__ import annotations

import json
import logging
import sys
import time

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode

INTRO = """Your code is on a server you can't see and someone says "it's slow". Logs are diary
entries, metrics are the dashboard gauges, traces are a GPS trail for ONE request.
Metrics say something's wrong, traces say where, logs say why."""

EXPORTER = InMemorySpanExporter()
READER = InMemoryMetricReader()


def configure() -> None:
    """The composition root for telemetry: done ONCE, at the application entry point."""
    resource = Resource.create({"service.name": "course-demo", "service.version": "1.0.0"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(EXPORTER))  # Batch* in production
    trace.set_tracer_provider(provider)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[READER]))


class JsonFormatter(logging.Formatter):
    """Structured logs: one JSON object per line, with the trace id attached."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        context = trace.get_current_span().get_span_context()
        if context.is_valid:
            payload["trace_id"] = format(context.trace_id, "032x")
            payload["span_id"] = format(context.span_id, "016x")
        for key, value in getattr(record, "fields", {}).items():
            payload[key] = value
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info).splitlines()[-1]
        return json.dumps(payload)


def structured_logging() -> None:
    print("\n== structured logging ==")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("demo")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    logger.info("order_placed", extra={"fields": {"order_id": 42, "amount_cents": 1999}})

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("checkout"):
        logger.info("inside_a_span", extra={"fields": {"step": "payment"}})
    print("  ^ the trace_id on that line is how you jump from a log to its trace")


def tracing() -> None:
    print("\n== tracing ==")
    EXPORTER.clear()  # drop the spans the logging demo produced
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("handle_request") as parent:
        # Low-cardinality NAME, high-cardinality ATTRIBUTES. Never the other way round.
        parent.set_attribute("http.request.method", "POST")
        parent.set_attribute("http.route", "/orders/{id}")
        parent.set_attribute("order.id", 12345)

        with tracer.start_as_current_span("db.query") as child:
            child.set_attribute("db.system", "postgresql")
            child.set_attribute("db.statement", "SELECT * FROM orders WHERE id = $1")
            time.sleep(0.01)

        with tracer.start_as_current_span("charge_card") as child:
            child.add_event("provider_call_started", {"provider": "stripe"})
            try:
                raise RuntimeError("card declined")
            except RuntimeError as exc:
                child.record_exception(exc)
                child.set_status(Status(StatusCode.ERROR, str(exc)))

    spans = EXPORTER.get_finished_spans()
    print(f"  {len(spans)} spans exported (children finish first):")
    for span in spans:
        duration_ms = (span.end_time - span.start_time) / 1e6
        print(f"    {span.name:<16} {duration_ms:>6.2f} ms  status={span.status.status_code.name}")

    root = spans[-1]
    print(f"  root attributes: {dict(root.attributes)}")
    print(f"  all share one trace id: {len({s.context.trace_id for s in spans}) == 1}")
    failed = next(s for s in spans if s.name == "charge_card")
    print(f"  recorded exception event: {[e.name for e in failed.events]}")


def metrics_demo() -> None:
    print("\n== metrics ==")
    meter = metrics.get_meter(__name__)
    orders = meter.create_counter("orders.placed", unit="1", description="orders placed")
    latency = meter.create_histogram("checkout.duration", unit="s")

    orders.add(1, {"currency": "usd"})
    orders.add(2, {"currency": "eur"})
    latency.record(0.12, {"route": "/checkout"})
    latency.record(0.34, {"route": "/checkout"})

    data = READER.get_metrics_data()
    for resource_metric in data.resource_metrics:
        for scope in resource_metric.scope_metrics:
            for metric in scope.metrics:
                print(f"  {metric.name} ({metric.unit}):")
                for point in metric.data.data_points:
                    value = getattr(point, "value", None)
                    if value is None:
                        print(f"    {dict(point.attributes)} count={point.count} sum={point.sum:.2f}")
                    else:
                        print(f"    {dict(point.attributes)} value={value}")
    print("  attributes are DIMENSIONS — keep them low-cardinality (no user ids!)")


def what_to_measure() -> None:
    print("\n== what to actually measure ==")
    print("  RED  (per endpoint):  Rate, Errors, Duration")
    print("  USE  (per resource):  Utilisation, Saturation, Errors")
    print("  alert on user-visible symptoms (latency, error rate), not on CPU")
    print("  read p95/p99 from histograms — the mean hides every problem you care about")


if __name__ == "__main__":
    print(INTRO)
    configure()
    structured_logging()
    tracing()
    metrics_demo()
    what_to_measure()
