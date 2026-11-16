"""On-call responder (§11). Receives Grafana's alert webhook, saves the alert and an
evidence packet to incidents/<id>/ and starts the on-call agent headless.

The endpoint has no auth: it binds to localhost unless RESPONDER_HOST says otherwise
(the Docker bridge address on Linux, e.g. 172.17.0.1)."""

import json
import os
import subprocess
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).parent
INCIDENTS = HERE / "incidents"
LOKI_URL = os.environ.get("LOKI_URL", "http://localhost:3100")
TEMPO_URL = os.environ.get("TEMPO_URL", "http://localhost:3200")

# Matches the "Practice sessions failing" rule in observability/grafana/alerting.yaml.
WINDOW = timedelta(minutes=5)
TRACEQL = (
    '{ span.http.route =~ "/api/sessions.*" && span.http.response.status_code >= 500 }'
)
LOGQL = '{service_name="woodshed"} | severity_text="ERROR"'

# The agent may diagnose, test, commit, push its own branch and open a PR: nothing else.
TOOLS = [
    "Read",
    "Glob",
    "Grep",
    "Edit",
    "Write",
    "mcp__grafana",
    "Bash(make test)",
    "Bash(make lint)",
    "Bash(uv run --directory backend pytest *)",
    "Bash(uv run --directory backend ruff *)",
    "Bash(git branch --show-current)",
    "Bash(git switch -c incident-*)",
    "Bash(git add *)",
    "Bash(git commit *)",
    "Bash(git push -u origin incident-*)",
    "Bash(gh pr create *)",
]
# Deny wins over allow, so these hold even if a rule above matches.
DENIED = [
    "Bash(gh pr merge*)",
    "Bash(gh workflow*)",
    "Bash(gh api*)",
    "Bash(gh release*)",
    "Bash(git push* -f*)",
    "Bash(git push* --force*)",
    "Bash(git push* +*)",
    "Bash(git push* main*)",
    "Bash(git push*:main*)",
]


def _get(base: str, path: str, **params: str | int) -> dict:
    url = f"{base}{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def evidence(start: datetime, end: datetime) -> dict:
    packet: dict = {"window": {"start": start.isoformat(), "end": end.isoformat()}}
    s, e = int(start.timestamp()), int(end.timestamp())
    # A telemetry outage shouldn't stop the agent: it can still query Grafana.
    try:
        logs = _get(LOKI_URL, "/loki/api/v1/query_range", query=LOGQL, start=s, end=e)
        packet["loki"] = {"query": LOGQL, "streams": logs["data"]["result"]}
    except OSError as error:
        packet["loki"] = {"query": LOGQL, "error": str(error)}
    try:
        traces = _get(TEMPO_URL, "/api/search", q=TRACEQL, start=s, end=e, limit=20)
        packet["tempo"] = {"query": TRACEQL, "traces": traces.get("traces", [])}
    except OSError as error:
        packet["tempo"] = {"query": TRACEQL, "error": str(error)}
    return packet


def command(id: str) -> list[str]:
    prompt = (HERE / "task.md").read_text().format(id=id)
    return [
        "claude",
        "-p",
        prompt,
        "--agent",
        "on-call",
        # Anything outside TOOLS is denied rather than prompted for.
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        ",".join(TOOLS),
        "--disallowedTools",
        ",".join(DENIED),
    ]


def _open_incident(fingerprint: str) -> Path | None:
    # Grafana stamps a resolved notification with a new startsAt, so match on the
    # alert's fingerprint, which stays the same while its labels do.
    return next(
        (
            alert.parent
            for alert in INCIDENTS.glob("*/alert.json")
            if not (alert.parent / "resolved.json").exists()
            and json.loads(alert.read_text())["alerts"][0]["fingerprint"] == fingerprint
        ),
        None,
    )


def handle(payload: dict, now: datetime) -> None:
    alert = payload["alerts"][0]
    start = datetime.fromisoformat(alert["startsAt"])
    id = f"{start:%Y%m%d-%H%M%S}"
    open_incident = _open_incident(alert["fingerprint"])
    if payload["status"] == "resolved":
        incident = open_incident or INCIDENTS / id
        incident.mkdir(parents=True, exist_ok=True)
        (incident / "resolved.json").write_text(json.dumps(payload, indent=2))
        return
    # Grafana repeats the notification while the alert fires; one agent per incident.
    if open_incident:
        return
    incident = INCIDENTS / id
    incident.mkdir(parents=True)
    (incident / "alert.json").write_text(json.dumps(payload, indent=2))
    packet = evidence(start - WINDOW, now)
    (incident / "evidence.json").write_text(json.dumps(packet, indent=2))
    subprocess.Popen(command(id), cwd=HERE.parent)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/alerts":
            return self.send_error(404)
        body = self.rfile.read(int(self.headers["Content-Length"]))
        handle(json.loads(body), datetime.now(UTC))
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    host = os.environ.get("RESPONDER_HOST", "127.0.0.1")
    HTTPServer((host, 8090), Handler).serve_forever()
