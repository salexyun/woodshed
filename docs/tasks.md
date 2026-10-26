# Woodshed — Tasks

The backlog for v1, drafted here for review. Once approved, each task becomes a GitHub Issue and this file is deleted. Section numbers (§) refer to `docs/plans.md`.

Each task is one pull request. A task is done when all of its acceptance criteria pass and `make test` is green.

---

## Foundation

### 1. Agent team and docs
**Goal:** the agent team, its tools and its rules exist before any code is written.
- [ ] `AGENTS.md` covers the layout, the commands (`make up`, `make test`, `make lint`), code style (short, pythonic, typed, no speculative abstractions) and workflow (issue → branch `<n>-slug` → PR "Closes #n"). It links to `docs/plans.md` and `docs/team.md`.
- [ ] `docs/team.md` defines each role (planner, tester, implementer, reviewer, on-call): its inputs, outputs, tools, the skills it uses and its handoffs.
- [ ] `.claude/agents/` has one subagent per role, each with a least-privilege tool list. The reviewer has no write access. The on-call agent can't merge or deploy.
- [ ] `.mcp.json` configures Grafana MCP (on-call), Playwright MCP (implementer, reviewer) and Context7 (implementer, tester). GitHub access goes through the `gh` CLI.
- [ ] `AGENTS.md` and `team.md` are each under 100 lines.

### 2. Project scaffold
**Goal:** an empty full-stack project where one command runs the tests.
- [ ] `backend/` is a `uv` project with FastAPI. `GET /healthz` returns 200.
- [ ] `frontend/` is a Vite + React + TypeScript project with React Router.
- [ ] `make test` runs pytest and Vitest, with one passing test each.
- [ ] `make lint` runs `ruff check`, `ruff format --check` and `tsc --noEmit`.

### 3. CI on pull requests
**Goal:** every PR is tested automatically.
- [ ] A GitHub Actions workflow runs `make lint` and `make test` on every PR.
- [ ] The workflow fails if any check fails.
- [ ] Branch protection on `main` requires the workflow to pass.

### 4. Database and migrations
**Goal:** the player's state persists in Postgres (§8).
- [ ] SQLAlchemy models for `profile`, `item`, `session` and `rating`, matching §8.
- [ ] The initial Alembic migration creates all 4 tables. `alembic upgrade head` followed by `alembic downgrade base` works on an empty database.
- [ ] `compose.yaml` runs Postgres 16. Integration tests run against a separate test database.
- [ ] `/healthz` returns 503 when the database is unreachable.

## Domain (pure functions, unit tested)

### 5. Music theory
**Goal:** triad shapes are computed rather than hand-entered (§4).
- [ ] `triad(root, quality)` supports major, minor, diminished and augmented, with sharps and flats. For example, `triad("D", "major")` returns `("D", "F♯", "A")` and `triad("C", "diminished")` returns `("C", "E♭", "G♭")`.
- [ ] `shape(root, quality, inversion)` returns frets on G-B-E at the lowest position with a span of 4 frets or fewer.
- [ ] Expected shapes:
  - C major: 5-5-3, 9-8-8, 0-1-0
  - C minor: 5-4-3, 8-8-8, 12-13-11
  - C augmented: 5-5-4, 9-9-8, 1-1-0
- [ ] `parse_chord("F♯m")` returns `("F♯", "minor")`. The symbols `°` and `+` parse as diminished and augmented.
- [ ] Every chord used in any passage produces valid shapes.

### 6. Content
**Goal:** lessons, passages and challenge cards are defined as code (§4).
- [ ] 4 lessons (major, minor, diminished, augmented), in that order. Each has an explanation of 120 words or fewer and at least one passage.
- [ ] 7 passages (5 songs, 2 exercises) with title, kind, chords and lesson, as listed in §4. There are no lyrics or tabs.
- [ ] A pool of at least 6 challenge cards.
- [ ] Integrity tests: IDs are unique, every lesson has a passage, every chord parses, and item IDs follow `shape:<quality>:<inversion>` and `passage:<id>`.

### 7. Leitner scheduler
**Goal:** reviews expand as the player succeeds (§5.2).
- [ ] `rate(box, rating, now)` returns `(new_box, due_at)`, using intervals of 1, 3, 7, 14 and 30 days.
- [ ] easy → box + 1 (capped at 5); challenging → the same box; unfamiliar → box 1.
- [ ] `due(items, now, limit)` returns the most overdue items first. Where possible, consecutive items don't share a quality.
- [ ] `review_root(reviews)` steps through the cycle of fourths, starting at C.
- [ ] Tests cover every transition, the cap at box 5, the ordering, the interleaving and the root rotation.

### 8. Streak and weekly progress
**Goal:** consistency is measured as defined in §5.6.
- [ ] `practice_days(sessions, tz)` returns local dates that have at least one finished session with a rating.
- [ ] `streak(days, today)` allows single missed days and breaks after two consecutive missed days. The streak is current if the last practice day is within 2 days of today.
- [ ] `week_progress(days, today)` counts practice days in the current ISO week.
- [ ] Tests cover a timezone boundary (23:30 local vs. UTC), a 1-day gap, a 2-day gap and a week rollover.

### 9. Session planner
**Goal:** the app decides what to practice (§5.4).
- [ ] `plan(action, items, completed_lessons, last_session, now)` returns an ordered list of steps.
- [ ] Today's plan: up to 3 due reviews, then the next lesson. If every lesson is done, the least recently practiced passage instead.
- [ ] Continue: the next lesson only. Test me: up to 10 items, in the order defined in §5.4. Pick a song: the chosen passage plus a challenge card.
- [ ] Tests cover each action, an empty review queue and the all-lessons-done case.

### 10. Onboarding placement
**Goal:** the player starts at the right lesson (§5.3).
- [ ] `place(claimed_qualities, checks)` returns the known qualities and the starting lesson.
- [ ] A quality counts as known only when its playing check is "got it" **and** its theory answer is correct.
- [ ] Each known quality produces its 3 shape items in box 2.
- [ ] Tests cover no qualities claimed, all checks passed, mixed results, and every quality known (no lesson remains).

## API (integration tested against Postgres)

### 11. Profile and onboarding API
- [ ] `POST /api/onboarding` creates the profile and the placed items in one transaction. A second call returns 409.
- [ ] `GET /api/profile` returns 404 before onboarding.
- [ ] `PATCH /api/profile` updates the cue and the goal. A goal outside 1–7 returns 422.

### 12. Content API
- [ ] `GET /api/lessons` and `/api/lessons/{quality}` return lesson content with computed shapes.
- [ ] `GET /api/passages` returns the unlock state for each passage. An unknown ID returns 404.

### 13. Sessions API: the key journey
**Goal:** start, rate and finish a session (§7, key user journey).
- [ ] `POST /api/sessions` stores the session and returns the plan from task 9.
- [ ] `POST /api/sessions/{id}/ratings` updates the item using task 7 and stores a rating with `box_before` and `box_after`. Rating all 3 shapes of a lesson completes the lesson and creates its passage item.
- [ ] Rating in a finished session returns 409.
- [ ] `POST /api/sessions/{id}/finish` returns the duration, the items rated, the next due dates and the streak.
- [ ] `GET /api/sessions` lists sessions newest first.
- [ ] An integration test runs onboarding → session → ratings → finish → home, and checks the streak and due counts.

### 14. Home and progress API
- [ ] `GET /api/home` returns the streak, weekly progress, due count, next lesson and cue.
- [ ] `GET /api/progress` returns every item with its box and `due_at`.

## Frontend (Vitest + Testing Library)

### 15. Typed API client
- [ ] `make types` generates TypeScript types from FastAPI's OpenAPI schema.
- [ ] A thin `fetch` wrapper uses those types, and API errors surface as typed results.
- [ ] CI fails when the generated types are out of date.

### 16. Fretboard component
- [ ] `<Fretboard positions={...} />` renders an SVG with 3 strings and the shown fret window, with the root marked.
- [ ] The component has no knowledge of lessons or sessions.
- [ ] Tests check the rendered dots for C root position and for an open (fret 0) shape.

### 17. Practice components
- [ ] `RatingButtons`, `ReviewCard` (prompt → reveal → rate), `Timer` (25-minute countdown and open count-up, with the prompts at 0 and at 60 minutes) and `ChallengeCard`.
- [ ] Tests cover the reveal, the rating callback and the timer prompts using fake timers.

### 18. Onboarding screen
- [ ] Questions → checks → habit setup → submit. Before onboarding is done, every route redirects to onboarding.
- [ ] The timezone is taken from the browser.
- [ ] A test with a mocked API checks the submitted payload.

### 19. Home screen
- [ ] Shows the streak, weekly progress, due count, next lesson and cue, plus the 4 actions and the length choice.
- [ ] The layout works at 375 px width.

### 20. Session screen
- [ ] Steps through review cards → lesson → passage → challenge → summary, using the plan returned by the API.
- [ ] Each rating is sent as it happens. Reloading resumes the session from the server.
- [ ] A test with a mocked API completes a full session.

### 21. Pick a song and Progress screens
- [ ] Pick a song lists unlocked passages and starts a session.
- [ ] Progress shows the 12-shape map (quality × inversion) colored by box, the session history and settings for the cue and goal.

## Ship

### 22. Containerize
**Goal:** the whole system starts with one command (§11).
- [ ] A multi-stage Dockerfile builds the SPA and serves it from FastAPI.
- [ ] Migrations run on start.
- [ ] `make up` (`docker compose up --build --wait`) starts the app and Postgres. Data survives a restart.
- [ ] README instructions work on a clean machine with only Docker installed.

### 23. Deploy to dev (CD)
- [ ] Render service `woodshed-dev` and a Neon `dev` branch are created. Secrets live in GitHub and Render.
- [ ] On merge to `main`: test → build the image tagged with the SHA → push to GHCR → deploy to dev → smoke-test `/healthz`.
- [ ] The dev URL is public and shows the app.

### 24. Manual prod deploy and rollback
- [ ] Render service `woodshed-prod` and a Neon `prod` branch are created.
- [ ] A `workflow_dispatch` deploys a chosen SHA after environment approval, then runs a smoke test.
- [ ] A rollback is performed once by redeploying the previous SHA, and it is documented in the README.

## Production readiness

### 25. Telemetry
**Goal:** the key journey is observable end to end (§11).
- [ ] OpenTelemetry traces cover FastAPI, SQLAlchemy, and spans for planning and scheduling.
- [ ] The metrics listed in §11 are emitted.
- [ ] JSON logs include `trace_id`.
- [ ] No free text or request bodies reach telemetry, and a test asserts it.
- [ ] Compose runs the Collector, Prometheus, Loki, Tempo and Grafana. The provisioned dashboard "Woodshed: practice journey" links logs to traces.

### 26. User-impact alert
- [ ] The Grafana rule "Practice sessions failing" (§11) is provisioned as code.
- [ ] Its contact point is a webhook to the responder.
- [ ] Forcing errors on `/api/sessions` makes the alert fire within 5 minutes.

### 27. On-call agent
- [ ] `incident-response/responder.py` receives the webhook and saves the alert and evidence (Loki logs and Tempo traces) to `incidents/<id>/`.
- [ ] It runs Claude Code headless with `incident-response/task.md` and a tool allowlist. The agent cannot merge or deploy.
- [ ] Incident drill: a deliberately introduced bug fires the alert, and the agent opens a PR whose fix passes `make test`. The drill's artifacts are committed.

### 28. README
- [ ] Covers the problem, features, screenshots, architecture, how to run and test, live URLs, CI/CD and rollback, observability, and the incident drill.
- [ ] Maps each grading criterion to where it is satisfied.
