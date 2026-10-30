"""Module 17 — reference solutions."""

from __future__ import annotations

import contextlib
import functools
import json
import logging
import time
from collections.abc import Callable, Iterable, Iterator
from typing import Any

from opentelemetry import metrics, propagate, trace
from opentelemetry.trace import Status, StatusCode

_REDACT = ("password", "token", "secret")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }

        context = trace.get_current_span().get_span_context()
        if context.is_valid:
            payload["trace_id"] = format(context.trace_id, "032x")
            payload["span_id"] = format(context.span_id, "016x")

        for key, value in getattr(record, "fields", {}).items():
            lowered = key.lower()
            payload[key] = "[redacted]" if any(s in lowered for s in _REDACT) else value

        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info).splitlines()[-1]
        return json.dumps(payload)


def traced(name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("code.function", func.__name__)
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise  # telemetry must never swallow the error

        return wrapper

    return decorator


def process_order(
    order_id: int, items: Iterable[dict[str, Any]], charge: Callable[[float], str]
) -> dict[str, Any]:
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("process_order") as span:  # low-cardinality NAME
        span.set_attribute("order.id", order_id)
        try:
            rows = list(items)
            if not rows:
                raise ValueError("order has no items")

            total = float(sum(row["price"] * row["quantity"] for row in rows))
            span.set_attribute("order.item_count", len(rows))
            span.set_attribute("order.total", total)
            span.add_event("order.validated")

            with tracer.start_as_current_span("charge") as charge_span:
                try:
                    receipt = charge(total)
                except Exception as exc:
                    charge_span.record_exception(exc)
                    charge_span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise

        return {"order_id": order_id, "total": total, "receipt": receipt}


class RequestMetrics:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        meter = metrics.get_meter(__name__)
        self.clock = clock or time.perf_counter
        self.requests = meter.create_counter("http.server.requests", unit="1")
        self.errors = meter.create_counter("http.server.errors", unit="1")
        self.duration = meter.create_histogram("http.server.duration", unit="s")

    def record(self, route: str, method: str, status_code: int, duration: float) -> None:
        attributes = {
            "http.route": route,  # the TEMPLATE, so cardinality stays bounded
            "http.request.method": method,
            "http.response.status_code": status_code,
        }
        self.requests.add(1, attributes)
        self.duration.record(duration, attributes)
        if status_code >= 500:
            self.errors.add(1, attributes)

    @contextlib.contextmanager
    def time(self, route: str, method: str) -> Iterator[None]:
        start = self.clock()
        status = 200
        try:
            yield
        except Exception:
            status = 500
            raise
        finally:
            self.record(route, method, status, self.clock() - start)


def extract_trace_context() -> dict[str, str]:
    if not trace.get_current_span().get_span_context().is_valid:
        return {}
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier
