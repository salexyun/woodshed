# Incident 20261116-133510: practice sessions fail to start

> **Drill.** The running branch is `drill-session-clock`. Its bug was introduced on purpose.

## Summary

Commit `47194f7` ("Read the request clock from the server") changed `get_now()` in `backend/woodshed/api.py` from `datetime.now(UTC)` to `datetime.now()`. A naive `now` can't be compared with the timezone-aware `timestamptz` values loaded from Postgres. The planner compares the two when it picks due items, so every `POST /api/sessions` raised `TypeError` and returned 500. The fix restores the aware UTC clock and adds a regression test that runs the journey on the real clock.

## User impact

- **Broken step:** starting a practice session (`POST /api/sessions`), the first step of the key journey. Nobody could start a session, so nobody could rate or finish one.
- **Error rate:** 100% of `POST /api/sessions` requests failed (13 of 13). The alert's value, 0.54, is lower only because it mixes in successful `GET /api/sessions` history reads (13 × 200).
- **Duration:** 13:33:58Z to 13:35:26Z, when the last request arrived. The bad build is still running, so the failure continues until the fix or a rollback is deployed.
- **Also affected, from the code path:** `GET /api/home` calls the same `scheduler.due` with `now`, so it fails too. The rating and finish endpoints also mix `now` with stored timestamps (`finish` computes `now - session.started_at`). They got no traffic during the window because no session could be started.
- **Who:** the requests came from `curl` (drill traffic). No player data was lost; failed requests roll back before commit.

## Timeline (UTC, 2026-11-16)

| Time | Event |
| --- | --- |
| 13:32:20 | `47194f7` committed on `drill-session-clock` and run |
| 13:33:58 | First failing `POST /api/sessions` (trace `8588a33db2da4aebc257972a874eca70`) |
| 13:34:52 to 13:35:26 | 12 more failures, one every ~3 s |
| 13:35:10 | "Practice sessions failing" fires (A = 0.538 > 0.05) |
| ~13:37 | On-call reproduces it with a failing test, fixes it on `incident-20261116-133510` and runs `make lint` and `make test` (green) |

## Root cause

`get_now()` returned a naive local datetime. `Item.due_at` is read from a `timestamptz` column, so it's aware. `scheduler.due` evaluates `i.due_at <= now`, and Python raises `TypeError: can't compare offset-naive and offset-aware datetimes`.

Code path, from the span's stack trace: `api.start_session` (api.py:226) → `planner.plan` (planner.py:47) → `scheduler.due` (scheduler.py:55).

### Evidence

**Rate (Prometheus):**

```promql
sum by (http_route, http_request_method, http_response_status_code) (
  increase(http_server_request_duration_seconds_count{http_route=~"/api/.*"}[10m]))
```

At 13:36: `POST /api/sessions` 500 ≈ 13.5 and `GET /api/sessions` 200 ≈ 13. No 2xx for `POST /api/sessions`. The alert ratio over time:

```promql
(sum(increase(http_server_request_duration_seconds_count{http_route=~"/api/sessions.*", http_response_status_code=~"5.."}[5m])) or vector(0))
  / sum(increase(http_server_request_duration_seconds_count{http_route=~"/api/sessions.*"}[5m]))
```

Result: 1.0 at 13:34, then 0.54 at 13:35.

**Errors (Loki):**

```logql
{service_name="woodshed"} | severity_text="ERROR"
sum(count_over_time({service_name="woodshed"} | severity_text="ERROR" [1h]))   # = 13
```

All 13 have `exception_type="TypeError"`, the same message, and the same stack trace ending in `scheduler.py:55`.

**Traces (Tempo):**

```traceql
{ span.http.route =~ "/api/sessions.*" && span.http.response.status_code >= 500 }
```

This returns 13 traces, all `POST /api/sessions`. In the one I inspected in full, `8588a33db2da4aebc257972a874eca70`, the `planner.plan` child span has status error and an `exception` event with the TypeError. The root span ends in 500 after 12 ms. The trace IDs are:

`8588a33db2da4aebc257972a874eca70`, `a39d4fbda3dcafab7bda19eb2d931706`, `35881d7784c2ce6e9906341299637447`, `6476ac76c9ebfab35909db929f296fc3`, `4feecd91acc58aa9464ab07fa65f0ae2`, `3c7777cc88dd4d36140443cf6bdc9051`, `9468a4782891d29e35b0ea5f7ea5c13d`, `bee4bd3011d8ca2038624beb512a4c26`, `c00f47e68dcaa3ec917d70ea4db9444e`, `99bfcdddfedf13ffeecb2c838180ff01`, `9239203fcd2161d06423dc224446d78d`, `1bac1c0d8e4484f2dac660224ed7939f` and `f3f76d5dc950e29e03fe29065bbd4b93`.

The error log lines carry no `trace_id` (see follow-ups). I matched logs to traces by timestamp: each log line falls inside one failing trace's span. For example, the log at 13:33:58.3316 falls inside trace `8588a33d…`, which runs from 13:33:58.319 to 13:33:58.331.

### Why tests didn't catch it

Every test in `test_sessions.py`, `test_profile.py` and `test_home_progress.py` overrides `get_now` with a fixed aware datetime, so they never run the real clock. `test_telemetry.py` does use the real clock, and 11 of its tests fail on `drill-session-clock`. So `make test` was red for `47194f7`, but the change ran without passing it.

## Fix

- `backend/woodshed/api.py`: `get_now()` returns `datetime.now(UTC)` again, with a comment on why it must be aware.
- `backend/tests/integration/test_sessions.py`: `test_journey_runs_on_the_server_clock` removes the clock override, then starts, rates and finishes a session and loads home. It failed with the production TypeError before the fix and passes after it.
- `make lint` passes. `make test` passes: 555 backend tests and 163 frontend tests.

**Deploying:** merge this PR, or roll back to `8667152`, the parent of `47194f7`. Either restores the aware clock. A rollback is safe because `47194f7` has no migration. The human decides.

## Follow-ups

1. **Error logs lack `trace_id` and `span_id`.** §11 says logs carry both, but uvicorn's "Exception in ASGI application" line is logged outside the request span. Logs had to be joined to traces by timestamp.
2. **Make the red build block the run.** `47194f7` ran with `make test` failing. Check that CI is a required check on the branches that get deployed.
3. **Exercise the real clock more widely.** Consider having one shared clock fixture that keeps the timezone (for example, a frozen clock that asserts `tzinfo` is set), so a naive clock fails every suite, not just telemetry.
4. **Alert ratio hides a total outage.** Fast `GET /api/sessions` reads dilute the ratio: a 100% failure to start sessions showed as 54%. A per-route or `POST`-only ratio would show the real impact. (Not changed here: Grafana is read-only for on-call.)

**PR not opened:** the base branch `drill-session-clock` exists only locally, not on `origin`, so `gh pr create --base drill-session-clock` failed ("Base ref must be a branch"). The fix branch `incident-20261116-133510` is pushed. Opening the PR needs a human to push `drill-session-clock`, or to choose another base.

No tools were denied that the diagnosis needed. Targeted `pytest` runs and ad-hoc Python weren't on the allowlist, so I checked the failing test with `make test`.
