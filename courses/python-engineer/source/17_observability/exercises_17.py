"""Module 17 exercises.  pytest 17_observability

The tests configure an in-memory span exporter and metric reader and then assert on the
telemetry your code produces — so "did I instrument this correctly?" becomes a unit test.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """A `logging.Formatter` producing one JSON object per line.

    Required keys, in this order: "level", "logger", "event".
    - "event" is the formatted message (`record.getMessage()`).
    - Any dict passed as `extra={"fields": {...}}` is merged in at the top level.
    - When a span is currently active, add "trace_id" (32 lowercase hex chars) and
      "span_id" (16 hex chars) — that correlation is the whole point.
    - When `exc_info` is set, add "error" with the LAST line of the formatted traceback.
    - Redact any field whose name contains "password", "token" or "secret" (case
      insensitive), replacing the value with "[redacted]". Never log a credential.
    """

    def format(self, record: logging.LogRecord) -> str:
        raise NotImplementedError


def traced(name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """A decorator that wraps a function in a span.

    - The span name is `name`, defaulting to the function's `__name__`.
    - On success the span status is left UNSET (OpenTelemetry treats that as "fine").
    - On an exception: call `span.record_exception(exc)`, set the status to
      `Status(StatusCode.ERROR, str(exc))`, and RE-RAISE. Swallowing the error would
      make the telemetry a lie.
    - Add the attribute "code.function" = the wrapped function's name.
    - Preserve metadata with `functools.wraps`.
    """
    raise NotImplementedError


def process_order(
    order_id: int, items: Iterable[dict[str, Any]], charge: Callable[[float], str]
) -> dict[str, Any]:
    """Instrument a small business operation properly.

    Behaviour: total the items (`price * quantity`), call `charge(total)`, and return
    `{"order_id": ..., "total": ..., "receipt": ...}`.

    Required telemetry — a span named "process_order" with:
    - attribute "order.id" (int)
    - attribute "order.item_count" (int)
    - attribute "order.total" (float)
    - a CHILD span named "charge" around the `charge(...)` call only
    - an event "order.validated" added after the totals are computed
    - if `charge` raises: record the exception on the CHILD span, set its status to
      ERROR, set the PARENT status to ERROR too, and re-raise
    - if items is empty: raise ValueError("order has no items") and record that on the
      parent span the same way

    Note the naming rule: the span name is fixed and low-cardinality ("process_order"),
    while the order id lives in an attribute.
    """
    raise NotImplementedError


class RequestMetrics:
    """RED metrics for an HTTP-ish workload.

    Create these instruments from a meter obtained with
    `opentelemetry.metrics.get_meter(__name__)`:

    - counter   "http.server.requests"        unit "1"
    - counter   "http.server.errors"          unit "1"
    - histogram "http.server.duration"        unit "s"

    `.record(route: str, method: str, status_code: int, duration: float)` adds one to
    the request counter and records the duration, both with attributes
    `{"http.route": route, "http.request.method": method, "http.response.status_code":
    status_code}`; when `status_code >= 500` it also increments the error counter.

    `.time(route, method)` is a CONTEXT MANAGER that measures wall time itself and
    records on exit, defaulting to status 200 and using 500 if the block raised (then
    re-raising). Use `time.perf_counter` via an injectable `clock` parameter on
    `__init__` so the tests are deterministic.

    Keep the attribute set exactly as specified: `http.route` is the TEMPLATE
    ("/orders/{id}"), never the filled-in path — one metric series per route, not per id.
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        raise NotImplementedError


def extract_trace_context() -> dict[str, str]:
    """Return the W3C trace-context headers for the CURRENT span, ready to send onward.

    >>> extract_trace_context()          # doctest: +SKIP
    {'traceparent': '00-<32 hex>-<16 hex>-01'}

    - Use `opentelemetry.propagate.inject` into a fresh dict.
    - With no active span, return an empty dict.

    This is what makes a trace *distributed*: the callee continues the same trace because
    these headers travelled with the request.
    """
    raise NotImplementedError
