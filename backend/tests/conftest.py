"""Installs in-memory OpenTelemetry providers before any test imports the app,
so the app's telemetry reports to them. OTel lets a global provider be set once."""

import pytest

try:
    from opentelemetry import metrics, trace
    from opentelemetry.sdk.metrics import Counter, Histogram, MeterProvider
    from opentelemetry.sdk.metrics.export import (
        AggregationTemporality,
        InMemoryMetricReader,
    )
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )
except ImportError:  # Until opentelemetry-sdk is a dependency (#25).
    SPANS = METRICS = None
else:
    SPANS = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(SPANS))
    trace.set_tracer_provider(tracer_provider)

    # Delta temporality: each collection returns only what happened since the last.
    delta = AggregationTemporality.DELTA
    METRICS = InMemoryMetricReader(
        preferred_temporality={Counter: delta, Histogram: delta}
    )
    metrics.set_meter_provider(MeterProvider(metric_readers=[METRICS]))


@pytest.fixture
def spans():
    """The span exporter, emptied for this test."""
    if SPANS is None:
        pytest.fail("opentelemetry-sdk is not installed")
    SPANS.clear()
    return SPANS


@pytest.fixture
def metric_reader(spans):
    """The metric reader, holding only what this test records."""
    METRICS.get_metrics_data()
    return METRICS
