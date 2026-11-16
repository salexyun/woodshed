import json
import threading
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from http.server import HTTPServer

import pytest
import responder

STARTS_AT = datetime(2026, 11, 16, 12, 3, tzinfo=UTC)
NOW = STARTS_AT + timedelta(minutes=1)
ID = "20261116-120300"
LOGS = [{"stream": {"service_name": "woodshed"}, "values": [["1", "boom"]]}]
TRACES = [{"traceID": "abc", "rootTraceName": "POST /api/sessions"}]


def payload(status: str) -> dict:
    alert = {"status": status, "startsAt": "2026-11-16T12:03:00Z", "fingerprint": "f"}
    return {"status": status, "alerts": [alert]}


@pytest.fixture
def calls(monkeypatch, tmp_path):
    """Isolates the responder: incidents go to tmp_path, Loki, Tempo and the agent are fakes."""
    calls = {"get": [], "popen": []}

    def get(base, path, **params):
        calls["get"].append((base, path, params))
        if path == "/api/search":
            return {"traces": TRACES}
        return {"data": {"result": LOGS}}

    monkeypatch.setattr(responder, "INCIDENTS", tmp_path)
    monkeypatch.setattr(responder, "_get", get)
    monkeypatch.setattr(
        responder.subprocess,
        "Popen",
        lambda cmd, cwd: calls["popen"].append((cmd, cwd)),
    )
    return calls


def test_firing_saves_the_alert_and_evidence(calls, tmp_path):
    responder.handle(payload("firing"), NOW)
    incident = tmp_path / ID
    assert json.loads((incident / "alert.json").read_text()) == payload("firing")
    evidence = json.loads((incident / "evidence.json").read_text())
    assert evidence == {
        "window": {
            "start": (STARTS_AT - timedelta(minutes=5)).isoformat(),
            "end": NOW.isoformat(),
        },
        "loki": {"query": responder.LOGQL, "streams": LOGS},
        "tempo": {"query": responder.TRACEQL, "traces": TRACES},
    }


def test_evidence_covers_the_alert_window_on_the_failing_routes(calls):
    responder.handle(payload("firing"), NOW)
    start, end = (
        int((STARTS_AT - timedelta(minutes=5)).timestamp()),
        int(NOW.timestamp()),
    )
    assert calls["get"] == [
        (
            responder.LOKI_URL,
            "/loki/api/v1/query_range",
            {"query": responder.LOGQL, "start": start, "end": end},
        ),
        (
            responder.TEMPO_URL,
            "/api/search",
            {"q": responder.TRACEQL, "start": start, "end": end, "limit": 20},
        ),
    ]
    assert '"/api/sessions.*"' in responder.TRACEQL
    assert "status_code >= 500" in responder.TRACEQL


def test_firing_starts_the_on_call_agent_headless_once(calls):
    responder.handle(payload("firing"), NOW)
    assert calls["popen"] == [(responder.command(ID), responder.HERE.parent)]


def test_command_runs_the_task_as_the_on_call_agent_with_the_allowlist():
    task = (responder.HERE / "task.md").read_text().format(id=ID)
    assert responder.command(ID) == [
        "claude",
        "-p",
        task,
        "--agent",
        "on-call",
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        ",".join(responder.TOOLS),
        "--disallowedTools",
        ",".join(responder.DENIED),
    ]
    assert f"incident-response/incidents/{ID}/" in task
    assert f"incident-{ID}" in task


def test_allowlist_cannot_merge_deploy_force_push_or_dispatch():
    assert not any(
        word in rule
        for rule in responder.TOOLS
        for word in ("merge", "workflow", "api", "release", "force", "deploy")
    )
    assert not any(
        rule in ("Bash", "Bash(*)", "Bash(git *)", "Bash(gh *)")
        for rule in responder.TOOLS
    )
    assert {
        "Bash(gh pr merge*)",
        "Bash(gh workflow*)",
        "Bash(gh api*)",
        "Bash(git push* -f*)",
        "Bash(git push* --force*)",
        "Bash(git push* +*)",
        "Bash(git push* main*)",
        "Bash(git push*:main*)",
    } <= set(responder.DENIED)


def test_a_repeated_firing_doesnt_start_a_second_agent(calls):
    responder.handle(payload("firing"), NOW)
    responder.handle(payload("firing"), NOW + timedelta(hours=4))
    assert len(calls["popen"]) == 1


def test_resolved_is_recorded_without_an_agent(calls, tmp_path):
    responder.handle(payload("firing"), NOW)
    responder.handle(payload("resolved"), NOW + timedelta(minutes=10))
    incident = tmp_path / ID
    assert json.loads((incident / "resolved.json").read_text()) == payload("resolved")
    assert len(calls["popen"]) == 1


def test_resolved_alone_starts_nothing(calls, tmp_path):
    responder.handle(payload("resolved"), NOW)
    assert [p.name for p in (tmp_path / ID).iterdir()] == ["resolved.json"]
    assert calls == {"get": [], "popen": []}


def test_unreachable_telemetry_is_noted_and_the_agent_still_starts(
    calls, monkeypatch, tmp_path
):
    def down(base, path, **params):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(responder, "_get", down)
    responder.handle(payload("firing"), NOW)
    evidence = json.loads((tmp_path / ID / "evidence.json").read_text())
    assert "connection refused" in evidence["loki"]["error"]
    assert "connection refused" in evidence["tempo"]["error"]
    assert len(calls["popen"]) == 1


@pytest.fixture
def url():
    server = HTTPServer(("127.0.0.1", 0), responder.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def post(url: str, body: dict) -> int:
    request = urllib.request.Request(url, json.dumps(body).encode(), method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def test_webhook_posts_to_alerts_are_handled(calls, tmp_path, url):
    assert post(f"{url}/alerts", payload("firing")) == 204
    assert (tmp_path / ID / "alert.json").exists()


def test_other_paths_are_404(calls, tmp_path, url):
    assert post(f"{url}/other", payload("firing")) == 404
    assert list(tmp_path.iterdir()) == []
