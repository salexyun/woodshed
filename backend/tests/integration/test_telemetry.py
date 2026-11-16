"""Telemetry (§11): traces, metrics and JSON logs, and no free text in any of them."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from woodshed import db as woodshed_db
from woodshed.main import app

CUE = "zebra-marmalade-7731 after the kettle"
PASS = {"playing": "got_it", "theory_correct": True}
ANSWERS = {
    "years_playing": 3,
    "stuck_on": "what_to_practice",
    "claimed_qualities": ["major"],
    "checks": {"major": PASS},
    "cue": "quokka-onboarding-cue",
    "weekly_goal_days": 5,
    "timezone": "Europe/Berlin",
}
HTTP_DURATIONS = {"http.server.duration", "http.server.request.duration"}
JOURNEY = ["/api/sessions", "/api/sessions/{id}/ratings", "/api/sessions/{id}/finish"]


@pytest.fixture
def client(database_url, db, monkeypatch, metric_reader):
    """A client on the app's own engine, so its instrumentation is what's tested."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    woodshed_db.engine.cache_clear()
    yield TestClient(app)
    woodshed_db.engine().dispose()
    woodshed_db.engine.cache_clear()


@pytest.fixture
def journey(client) -> None:
    """Onboarding, a cue update, then the key journey: start, rate, finish."""
    assert client.post("/api/onboarding", json=ANSWERS).status_code == 201
    assert client.patch("/api/profile", json={"cue": CUE}).status_code == 200
    assert client.get("/api/home").json()["cue"] == CUE
    response = client.post("/api/sessions", json={"action": "today", "length": "25"})
    assert response.status_code == 201
    plan = response.json()
    item_id = next(s["id"] for s in plan["steps"] if s["kind"] == "review")
    rating = client.post(
        f"/api/sessions/{plan['id']}/ratings",
        json={"item_id": item_id, "rating": "easy"},
    )
    assert rating.status_code == 200
    assert client.post(f"/api/sessions/{plan['id']}/finish").status_code == 200


def data_points(reader, keep=lambda name: True) -> list:
    data = reader.get_metrics_data()
    return [
        point
        for rm in (data.resource_metrics if data else [])
        for sm in rm.scope_metrics
        for metric in sm.metrics
        if keep(metric.name)
        for point in metric.data.data_points
    ]


def counted(reader, name: str) -> list[tuple[dict, int]]:
    """(labels, value) of the counter exported to Prometheus as `<name>_total`."""
    points = data_points(
        reader, lambda n: n.replace(".", "_").removesuffix("_total") == name
    )
    return [(dict(p.attributes), p.value) for p in points]


def server_span(spans, route: str):
    return next(
        s
        for s in spans.get_finished_spans()
        if s.kind.name == "SERVER" and s.attributes.get("http.route") == route
    )


def app_formatters() -> list[logging.Formatter]:
    """Formatters of the handlers the app installed on the root logger (not pytest's)."""
    return [
        h.formatter
        for h in logging.getLogger().handlers
        if h.formatter and not type(h).__module__.startswith("_pytest")
    ]


@pytest.mark.parametrize("route", JOURNEY)
def test_journey_requests_are_traced(journey, spans, route):
    assert server_span(spans, route)


def test_database_queries_are_traced_within_the_request(journey, spans):
    trace_id = server_span(spans, "/api/sessions").context.trace_id
    assert any(
        s.attributes.get("db.system") == "postgresql" and s.context.trace_id == trace_id
        for s in spans.get_finished_spans()
    )


@pytest.mark.parametrize(
    ("route", "word"),
    [("/api/sessions", "plan"), ("/api/sessions/{id}/ratings", "schedul")],
)
def test_planning_and_scheduling_have_their_own_spans(journey, spans, route, word):
    trace_id = server_span(spans, route).context.trace_id
    assert any(
        word in s.name.lower()
        and s.kind.name == "INTERNAL"
        and s.context.trace_id == trace_id
        for s in spans.get_finished_spans()
    )


def test_sessions_started_are_counted_by_action(journey, metric_reader):
    started = counted(metric_reader, "woodshed_sessions_started")
    assert started == [({"action": "today"}, 1)]


def test_sessions_finished_are_counted(journey, metric_reader):
    assert counted(metric_reader, "woodshed_sessions_finished") == [({}, 1)]


def test_ratings_are_counted_by_rating(journey, metric_reader):
    assert counted(metric_reader, "woodshed_ratings") == [({"rating": "easy"}, 1)]


def test_http_requests_are_measured_by_route_and_status(journey, metric_reader):
    points = data_points(metric_reader, HTTP_DURATIONS.__contains__)
    measured = {
        (
            p.attributes.get("http.route"),
            p.attributes.get("http.response.status_code")
            or p.attributes.get("http.status_code"),
        ): p.count
        for p in points
    }
    assert measured[("/api/sessions", 201)] == 1
    assert measured[("/api/sessions/{id}/finish", 200)] == 1


def test_json_logs_carry_trace_and_span_ids(client, caplog):
    from opentelemetry import trace

    with trace.get_tracer(__name__).start_as_current_span("probe") as span:
        logging.getLogger("woodshed").warning("probe")
        record = next(r for r in caplog.records if r.getMessage() == "probe")
        lines = [json.loads(f.format(record)) for f in app_formatters()]
    ctx = span.get_span_context()
    assert lines
    assert lines[0]["trace_id"] == format(ctx.trace_id, "032x")
    assert lines[0]["span_id"] == format(ctx.span_id, "016x")


def test_no_free_text_reaches_telemetry(journey, spans, metric_reader, caplog):
    traced = [
        (s.name, dict(s.attributes), [dict(e.attributes) for e in s.events])
        for s in spans.get_finished_spans()
    ]
    labels = [dict(p.attributes) for p in data_points(metric_reader)]
    logs = [f.format(r) for r in caplog.records for f in app_formatters()]
    assert traced and labels and app_formatters()
    for telemetry in map(str, (traced, labels, logs)):
        assert "zebra-marmalade" not in telemetry
        assert "quokka-onboarding" not in telemetry
