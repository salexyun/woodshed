"""OpenTelemetry setup (§11). Exports over OTLP only when OTEL_EXPORTER_OTLP_ENDPOINT is set,
so the app runs without a Collector. Never put the cue or request bodies in telemetry."""

import json
import logging
import os

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if (ctx := trace.get_current_span().get_span_context()).is_valid:
            line |= {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
            }
        if record.exc_info:
            line["exception"] = self.formatException(record.exc_info)
        return json.dumps(line)


def _export_otlp() -> None:
    # Service name, endpoint and intervals come from the standard OTEL_* variables.
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
    logger_provider = LoggerProvider()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(logger_provider)
    logging.getLogger().addHandler(LoggingHandler(logger_provider=logger_provider))


def setup(app: FastAPI) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # Uvicorn prints plain text through its own handlers; route its logs through ours.
    for logger in map(logging.getLogger, ("uvicorn", "uvicorn.access")):
        logger.handlers.clear()
        logger.propagate = True
    # Docker's healthcheck hits /healthz every 2 s; its access lines are noise.
    logging.getLogger("uvicorn.access").addFilter(lambda r: r.args[2] != "/healthz")
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        _export_otlp()
    # Only the stable HTTP conventions label request metrics with http.route.
    os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http")
    FastAPIInstrumentor.instrument_app(app)
    # Traces SQLAlchemy's queries at the driver: the SQLAlchemy instrumentation
    # doesn't support SQLAlchemy 2.1 yet.
    PsycopgInstrumentor().instrument()
