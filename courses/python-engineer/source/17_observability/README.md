# 17 — Observability: logging, metrics, tracing with OpenTelemetry

Monitoring answers "is it up?". **Observability** answers "why is *this* request slow for
*that* customer?" — a question you can't enumerate in advance. The difference is
high-cardinality, correlated, structured telemetry.

## In plain English

Your code works on your laptop. It's now running on a server you can't see, for users you
can't ask, and someone says "it's slow". What do you actually *do*?

Observability is the answer, and it's three different tools:

- **Logs** are diary entries. "14:32:07 — order 5512 failed: card declined." Great detail,
  one event at a time, enormous volume.
- **Metrics** are the dashboard gauges in a car. "Requests per second: 400. Error rate:
  2%." Cheap, and you can alert on them — but they can't tell you *which* request broke.
- **Traces** are a GPS breadcrumb trail for a *single* request. "This one took 3 seconds:
  40ms in your code, 2.9s waiting for the database, 60ms rendering." That's the one that
  actually answers "why is it slow".

Rule of thumb: **metrics tell you something is wrong, traces tell you where, logs tell you
why.**

OpenTelemetry is the standard way to produce all three, and its selling point is that it's
vendor-neutral: instrument your code once, then point it at whichever monitoring product
your company buys this year.

**Watch out for:** the naming rule. Span names and metric labels must be *low-variety*
(`GET /orders/{id}`, not `GET /orders/12345`). Put the order id in an attribute instead.
Getting this backwards is how people accidentally melt their monitoring bill.

## 1. The three signals

| Signal | Answers | Cost |
|---|---|---|
| **Logs** | what happened, in detail, for one event | high volume |
| **Metrics** | how much/how often, aggregated over time | cheap, low cardinality |
| **Traces** | where the time went across services | sampled |

Rule of thumb: **metrics to alert, traces to localise, logs to explain.**

## 2. Structured logging first

```python
import logging, json

logger = logging.getLogger(__name__)     # module-level, __name__, never the root logger
logger.info("order placed", extra={"order_id": order.id, "amount_cents": 1999})
```

- Log **events with fields**, not prose. `f"order {id} placed"` is unsearchable at scale;
  `{"event": "order_placed", "order_id": id}` is queryable.
- Configure handlers **once**, at the entry point. Libraries add a
  `logging.NullHandler()` and never configure anything.
- Levels that mean something: DEBUG (dev), INFO (business events), WARNING (degraded but
  handled), ERROR (a request failed), CRITICAL (the process is in trouble).
- `logger.exception("failed")` inside `except` includes the traceback.
- Never log secrets, tokens, full request bodies, or PII. Redact at the formatter.

## 3. OpenTelemetry: the vendor-neutral standard

One API, one SDK, any backend (Jaeger, Tempo, Honeycomb, Datadog, Prometheus, Grafana).
That's the point — instrument once, switch vendors with a config change.

```
your code -> OTel API -> OTel SDK -> exporter -> collector -> backend
```

Packages: `opentelemetry-api` (what libraries import), `opentelemetry-sdk` (what apps
configure), `opentelemetry-instrumentation-*` (auto-instrumentation for FastAPI, httpx,
psycopg, redis...), `opentelemetry-exporter-otlp`.

## 4. Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("charge_card") as span:
    span.set_attribute("payment.provider", "stripe")
    span.set_attribute("payment.amount_cents", amount)
    try:
        result = charge(amount)
    except PaymentError as exc:
        span.record_exception(exc)
        span.set_status(Status(StatusCode.ERROR, str(exc)))
        raise
```

Vocabulary:
- **Span** — one timed operation, with attributes, events and a status.
- **Trace** — a tree of spans sharing a trace id.
- **Context propagation** — the trace id travels across services in the `traceparent`
  HTTP header (W3C Trace Context). This is what makes a distributed trace *distributed*.
- **Sampling** — keep a fraction (`TraceIdRatioBased(0.1)`), or all errors and a sample of
  the rest (tail sampling in the collector).

`@tracer.start_as_current_span("name")` also works as a decorator.

**Naming**: low-cardinality span names (`GET /orders/{id}`, not `GET /orders/12345`) and
high-cardinality **attributes** (`order.id = 12345`). Getting this backwards is the classic
mistake — it explodes your backend's index.

Follow the [semantic conventions](https://opentelemetry.io/docs/specs/semconv/) for
attribute names (`http.request.method`, `db.system`, `server.address`) so backends can
build dashboards automatically.

## 5. Metrics

```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
orders = meter.create_counter("orders.placed", unit="1")
latency = meter.create_histogram("checkout.duration", unit="s")

orders.add(1, {"currency": "usd"})           # attributes = dimensions
latency.record(elapsed, {"route": "/checkout"})
```

Instruments: `Counter` (monotonic), `UpDownCounter` (goes both ways), `Histogram`
(distributions — use it for latency, then read p95/p99, never the mean), and
observable/async gauges for sampled values.

**Keep metric attributes low-cardinality.** A `user_id` label on a metric is how you take
down your metrics backend; that belongs on a span.

## 6. Logs correlated with traces

```python
span = trace.get_current_span()
ctx = span.get_span_context()
logger.info("charged", extra={"trace_id": format(ctx.trace_id, "032x")})
```

With the trace id on every log line you can jump from a slow trace straight to its logs.
`opentelemetry-instrumentation-logging` wires this in automatically.

## 7. Wiring an app

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

provider = TracerProvider(resource=Resource.create({"service.name": "checkout"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

FastAPIInstrumentor.instrument_app(app)      # every request becomes a span, free
HTTPXClientInstrumentor().instrument()       # and propagates context downstream
```

Zero-code option: `opentelemetry-instrument uvicorn app:app`, configured by
`OTEL_*` environment variables.

**Testing**: `InMemorySpanExporter` + `SimpleSpanProcessor` lets you assert on spans in a
unit test — no collector, no network. That's exactly what this module's tests do.

## 8. What to actually instrument

- Every inbound request and outbound call (auto-instrumentation covers most of it).
- Every unit of business work: a job, a batch, a payment, a retry.
- Errors: `record_exception` + `Status(ERROR)`, always.
- The **RED** metrics per endpoint: Rate, Errors, Duration.
  For resources, **USE**: Utilisation, Saturation, Errors.
- SLOs on user-visible latency and error rate — alert on those, not on CPU.

## Exercises

`exercises_17.py`, then `pytest 17_observability`. The tests use the in-memory exporter,
so they assert on real spans, attributes, statuses and metric values.

## Further reading

- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Semantic conventions](https://opentelemetry.io/docs/specs/semconv/)
- *Observability Engineering* (Majors, Fong-Jones, Miranda)
