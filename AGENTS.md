# Woodshed — agent guide

Woodshed is a guitar practice planner. It decides what to practice (triads, scheduled with spaced repetition) and helps the player stay consistent (streaks, weekly goals). It's built with FastAPI + Postgres and a React SPA.

## Docs

- [`docs/plans.md`](docs/plans.md): the spec (problem, principles, behavior, API, database, testing, operations). Section numbers (§) in issues refer to this file.
- [`docs/team.md`](docs/team.md): the agent team, the workflow and handoffs. Read it before picking up an issue.
- [Issues](https://github.com/salexyun/woodshed/issues): the backlog. Every change starts from an issue with acceptance criteria.

## Layout

```
backend/woodshed/       FastAPI app
  domain/               pure functions: theory, scheduler, streak, planner
  content.py            lessons, passages, challenge cards
backend/tests/          unit/ and integration/
frontend/src/           React + TypeScript (Vite)
incident-response/      on-call responder and incident records
observability/          Collector, Prometheus, Loki, Tempo, Grafana config
.claude/agents/         the agent team
```

Directories appear as the issues that create them land.

## Commands

| Command | Does |
| --- | --- |
| `make up` | Starts the full system (app, Postgres, telemetry) with Docker Compose |
| `make test` | Runs all tests: unit, integration and frontend |
| `make lint` | Runs `ruff check`, `ruff format --check` and `tsc --noEmit` |
| `make types` | Regenerates the frontend API types from OpenAPI |

Backend dependencies go through `uv` (`uv add <pkg>`). Frontend dependencies go through `npm`.

## Code style

- Short, pythonic and typed. Prefer plain functions and dataclasses over classes and frameworks.
- Don't add speculative abstractions, options nobody asked for, or wrappers around a single call.
- `domain/` is pure: no I/O and no clock. `now` is passed in.
- Comments explain *why*, never *what*. Names should make *what* obvious.
- Match the code around you. Add a dependency only when it removes real code.
- Each change does what its issue asks, no more. Note follow-ups as new issues.

## Workflow

1. Pick an open issue whose dependencies are merged. Comment on it to claim it.
2. Branch `<issue>-<slug>`, e.g. `7-leitner-scheduler`.
3. Write tests from the acceptance criteria first, then the code.
4. Run `make lint` and `make test` before pushing.
5. Open a PR titled like the issue, with `Closes #<issue>` in the body. Tick each acceptance criterion in the PR body.
6. The reviewer agent comments its verdict. A human merges. Agents never merge.

Commit messages: imperative mood and ≤ 72 characters, with the issue referenced, e.g. `Add Leitner transitions (#7)`.

## Rules

- Never commit secrets. Configuration comes from environment variables.
- Never send free text (the player's cue) or request bodies to logs, traces or metrics.
- Migrations must work with the previous release (expand, then contract).
- If the spec is wrong or unclear, comment on the issue and ask. Don't guess.
