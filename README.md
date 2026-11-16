# Woodshed

A guitar practice planner. See [`docs/plans.md`](docs/plans.md) for the spec.

## Run it

You need only Docker (with Compose).

```sh
git clone https://github.com/salexyun/woodshed.git
cd woodshed
make up    # or, without make: docker compose up --build --wait
```

This builds the image, starts Postgres and the app, runs migrations and waits until both are healthy. Open <http://localhost:8000>. Data lives in the `pgdata` volume, so it survives `docker compose restart` and `docker compose down`. Stop with `docker compose down`; add `-v` to delete the data too.

The app reads `DATABASE_URL` and, optionally, `PORT` (default 8000) from the environment.

`make up` also starts the telemetry stack: the OpenTelemetry Collector, Prometheus, Loki, Tempo and Grafana. Open <http://localhost:3000> for the "Woodshed: practice journey" dashboard. Grafana also provisions the "Practice sessions failing" alert, which posts a webhook to the on-call responder at `RESPONDER_URL` (default `http://host.docker.internal:8090/alerts`). The app exports traces, metrics and logs over OTLP when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (the standard `OTEL_*` variables apply); without it, it logs JSON lines to stderr only.

## On-call responder

When "Practice sessions failing" fires, the responder saves the alert and an evidence packet (Loki error logs and Tempo traces of failing `/api/sessions*` requests) to `incident-response/incidents/<id>/`. It then starts the on-call agent headless (`claude -p` with [`incident-response/task.md`](incident-response/task.md)). The agent fixes the bug on `incident-<id>` and opens a PR against the branch the responder's checkout is on, so that branch must be on `origin`. The run uses only the repo's settings (`--setting-sources project`), with auto-memory off. Its allowlist has no rule for merging, deploying, force-pushing or dispatching workflows, and deny rules block those commands. It pushes only its own branch and can't edit agent config, `CLAUDE.md`, `AGENTS.md`, `.mcp.json` or `.github/`. These rules match command text, and `make test` runs whatever code the agent writes, so they narrow the agent rather than sandbox it. The hard stops are on GitHub: branch protection on `main` and approval for prod deploys (see [`docs/team.md`](docs/team.md)). A resolved alert is recorded as `resolved.json` and starts nothing.

Run it from a checkout of the deployed branch, with Python 3.12+, Claude Code and `gh` signed in:

```sh
export GRAFANA_URL=http://localhost:3000 GRAFANA_SERVICE_ACCOUNT_TOKEN=<viewer token>  # the agent's Grafana MCP
python3 incident-response/responder.py
```

It listens on port 8090 at `/alerts`, bound to `127.0.0.1` (that works with Docker Desktop's `host.docker.internal`). On Linux, set `RESPONDER_HOST` to the Docker bridge address, e.g. `172.17.0.1`; the endpoint has no auth, so never bind it to all interfaces. It reads Loki from `LOKI_URL` (default `http://localhost:3100`) and Tempo from `TEMPO_URL` (default `http://localhost:3200`). The agent runs `make test`, so it also needs `TEST_DATABASE_URL` if Postgres isn't on 5432.

## Deploy

Every merge to `main` builds an image tagged with the commit SHA, pushes it to GHCR and deploys it to dev. Production is manual:

1. Pick the SHA to ship: usually dev's, the `version` at dev's `/healthz`.
2. Actions → **Deploy prod** → **Run workflow**, paste the full SHA and run.
3. Approve the `prod` deployment when the run asks for review.

The run deploys that SHA's existing image (it never rebuilds) and waits until prod's `/healthz` reports it.

**Rollback:** run **Deploy prod** again with the previous SHA, the one from the last good run in the **Deploy prod** runs list. This works only if no migration landed in between: the image runs `alembic upgrade head` on start, and an older image doesn't know a newer database revision, so it never comes up.
