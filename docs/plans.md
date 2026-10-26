# Woodshed — Plan

Woodshed tells experienced guitarists what to practice today and helps them practice consistently. v1 teaches the four triad qualities through song passages and schedules reviews with spaced repetition.

## 1. Problem

Players who have played for years often plateau:

1. **They don't know what to practice.** Without a plan they default to the songs and shapes they already know, so nothing new gets learned.
2. **They don't practice consistently.** Sessions are irregular, motivation fades, and what was learned is forgotten before it is reinforced.

Woodshed removes the daily decision (the app builds the session) and makes regular practice easy to keep up (short default sessions, a forgiving streak, reviews timed to memory).

## 2. Principles

This section draws on general research in learning, skill acquisition and habit formation. None of the studies tested guitar directly. Each row anchors on the most influential work in its area and maps it to a design decision.

### Learning and memory

| Principle | Evidence | Design decision |
| --- | --- | --- |
| **Recalling strengthens memory** (the testing effect) | Repeated testing beat restudying for retention after 2 days and after 1 week ([Roediger & Karpicke 2006](https://www.gwern.net/docs/spaced-repetition/2006-roediger.pdf)). Practice testing was one of only 2 of 10 techniques rated "high utility" ([Dunlosky et al. 2013](https://www.psychologicalscience.org/news/releases/which-study-strategies-make-the-grade.html)). | Sessions open with due reviews. Reviews ask the player to recall before revealing the answer. "Test me" mode. |
| **Spacing beats cramming** | Meta-analysis of 317 experiments ([Cepeda et al. 2006](https://pubmed.ncbi.nlm.nih.gov/16719566/)). Distributed practice was the other "high utility" technique ([Dunlosky et al. 2013](https://www.psychologicalscience.org/news/releases/which-study-strategies-make-the-grade.html)). | Frequent short sessions. Reviews are scheduled, not crammed. |
| **Review gaps should expand** | 13 sessions spaced 56 days apart matched 26 sessions spaced 14 days apart for long-term retention ([Bahrick et al. 1993](https://www.psychologicalscience.org/journals/psychological-science/j.1467-9280.1993.tb00571.x/)). The best gap grows with how long material must be remembered ([Cepeda et al. 2006](https://pubmed.ncbi.nlm.nih.gov/16719566/)). | Leitner scheduler: 1 → 3 → 7 → 14 → 30 days. |

### Skill practice

| Principle | Evidence | Design decision |
| --- | --- | --- |
| **Deliberate practice:** focused work on weaknesses, in limited daily doses | Expertise tracks accumulated deliberate practice, and its daily duration is limited by effort ([Ericsson et al. 1993](https://stafforini.com/works/ericsson-1993-role-deliberate-practice/)). Typing training: 1 h/day was the most efficient schedule tested, 2 × 2 h/day the least ([Baddeley & Longman 1978](https://www.gwern.net/doc/psychology/spaced-repetition/1978-baddeley.pdf)). Across 63 studies, spaced practice outperformed massed practice (d = 0.46) ([Donovan & Radosevich 1999](https://www.gwern.net/docs/spaced-repetition/1999-donovan.pdf)). | The planner targets the weakest items. 25-minute default. Open-ended sessions nudge the player to stop at 60 minutes. |
| **Mixed practice beats blocked practice** (contextual interference) | Random-order practice gave worse performance during training but better retention and transfer than blocked practice ([Shea & Morgan 1979](https://www.gwern.net/doc/psychology/spaced-repetition/1979-shea.pdf)). | Reviews interleave triad qualities, inversions and roots. Challenge cards vary the context (rhythm, register). |
| **Skills consolidate between sessions** | Motor-sequence speed improved about 20% after a night of sleep, with no gain over equal waking time ([Walker et al. 2002](https://walkerlab.berkeley.edu/reprints/Walker%20et%20al._Neuron_2002.pdf)). The effect varies by task. | Daily practice instead of long weekly blocks. |

### Habit and motivation

| Principle | Evidence | Design decision |
| --- | --- | --- |
| **Habits are cued by context** | Habits form as responses become tied to recurring contexts; once formed, the context triggers the behavior without deliberation ([Wood & Neal 2007](https://dornsife.usc.edu/wendy-wood/wp-content/uploads/sites/183/2023/10/wood.neal_.2007psychrev_a_new_look_at_habits_and_the_interface_between_habits_and_goals.pdf)). Automaticity took a median of about 66 days (range 18–254), and missing a single day did not derail it ([Lally et al. 2010](https://www.ucl.ac.uk/news/2009/aug/how-long-does-it-take-form-habit)). | Practice in the same context each day. Missing one day doesn't break the streak. |
| **Plans of the form "When X, I will Y" increase follow-through** (implementation intentions) | Meta-analysis of 94 tests: d ≈ 0.65 on goal attainment ([Gollwitzer & Sheeran 2006](https://www.socmot.uni-konstanz.de/publications/implementation-intentions-and-goal-achievement-meta-analysis-effects-and-processes)). | At onboarding, the player completes the sentence "After ___, I'll practice." The home screen shows it. |
| **Broken streaks cause people to drop off; repairable streaks don't** | Across 7 studies, an intact streak increased later engagement compared with a broken one. Being able to repair a streak weakened the drop-off ([Silverman & Barasch 2023](https://udspace.udel.edu/items/42ce576b-8e1f-429a-8541-e29e48dbcfbb)). | Forgiving streak. No failure messages. The weekly goal resets every Monday. |
| **Autonomy and competence sustain motivation** | Self-determination theory ([Ryan & Deci 2000](https://doi.org/10.1037/0003-066X.55.1.68)). | "Pick a song" and challenge cards give choice. A visible fretboard map shows growing competence. |

## 3. Scope

**v1 (this project):** single player, no accounts. 4 lessons (one per triad quality), 12 movable shapes, 7 passages, Leitner scheduling.

**Out of scope for v1:** authentication, other string sets, seventh chords, audio (metronome, backing tracks, microphone), notifications.

**Roadmap**

- v2: replace the Leitner scheduler with [FSRS](https://github.com/open-spaced-repetition/py-fsrs) using default parameters.
- v3: FSRS parameters fitted to the player's review history; the D-G-B and A-D-G string sets; more passages.

## 4. Content

Content is code: versioned, reviewed and tested with the app. The database stores only the player's state.

### Shapes

A triad is a root, a 3rd and a 5th. v1 covers 4 qualities, each in 3 inversions on the top string set (G-B-E):

| Quality | Formula | Relation to major |
| --- | --- | --- |
| Major | 1 3 5 | The base shapes |
| Minor | 1 ♭3 5 | Lower the 3rd by one fret |
| Diminished | 1 ♭3 ♭5 | Minor with the 5th lowered |
| Augmented | 1 3 ♯5 | Major with the 5th raised. It's symmetric, so every inversion is the same shape moved 4 frets. |

- **Shapes are movable.** The same 3 shapes play every key by sliding along the neck. That makes 12 shapes in total (4 qualities × 3 inversions).
- **Fret positions are computed from note theory**, not entered by hand. For example:
  - C major: 5-5-3, 9-8-8, 0-1-0
  - C minor: 5-4-3, 8-8-8, 12-13-11

### Lessons

There are 4 lessons, ordered from most common to least common: **major → minor → diminished → augmented**.

Each lesson teaches one quality and contains:

- a short explanation (≤ 120 words) of how the quality relates to major
- its 3 shapes, shown in C
- its passages
- a challenge card

### Passages

There are two kinds of passage:

- **Song:** a real song. Only the title, artist and chord progression are stored. No lyrics or tablature, to avoid copyright issues.
- **Exercise:** a short progression that shows the quality's typical use. Used where songs rarely feature it.

| Passage | Kind | Chords | Lesson |
| --- | --- | --- | --- |
| La Bamba | song | C F G | Major |
| Twist and Shout | song | D G A | Major |
| Sweet Home Alabama | song | D C G | Major |
| Let It Be | song | C G Am F | Minor |
| Stand By Me | song | A F♯m D E | Minor |
| Passing diminished | exercise | C C♯° Dm G | Diminished |
| Augmented lead-in | exercise | C C+ F | Augmented |

A passage unlocks when its lesson is completed. Diagrams are shown for every chord in the passage.

### Challenge cards

A fixed pool of variations, one shown per lesson or passage. Examples:

- "Use only the nearest shape: no jumps."
- "Same chords, reggae offbeat strum."
- "Play it up an octave."
- "Improvise a 4-bar riff using only these shapes."

## 5. Behavior

### 5.1 Learning items

The scheduler tracks two kinds of item:

- **shape**: one quality in one inversion, e.g. `shape:minor:1` (12 total)
- **passage**: one song or exercise, e.g. `passage:let-it-be` (7 total)

An item is created when its lesson is completed, or when its quality is placed as known at onboarding. Items that have not been created yet are never scheduled.

A shape review names a root, e.g. "Play F♯ minor, 1st inversion." Roots rotate through the cycle of fourths (C F B♭ E♭ A♭ D♭ G♭ B E A D G), advancing one step per review of that item. Over time each shape is practiced in every key, and the choice stays deterministic, so it can be tested.

### 5.2 Scheduler (Leitner)

- Boxes 1–5 have intervals of 1, 3, 7, 14 and 30 days.
- Every rating updates the item's box:
  - **easy**: move up one box (box 5 is the maximum)
  - **challenging**: stay in the same box
  - **unfamiliar**: go back to box 1
- A new item starts in box 1, and its first rating applies the same rule.
- `due_at = rated_at + interval(box)`. An item is due when `due_at ≤ now`.
- Due items are ordered by how overdue they are, most overdue first. Where possible, consecutive reviews don't repeat the same quality (interleaving).

### 5.3 Onboarding (first visit, ~3 minutes)

1. **Questions:**
   - years playing
   - which triad qualities the player already knows on the top strings (multi-select)
   - what feels stuck (one of: repeating the same material / not knowing what to practice / technique / theory)
2. **Check:** for each quality the player claims to know:
   - a playing prompt (root position, root from the rotation): the player plays it, reveals the diagram, then self-grades *got it / close / no idea*
   - a multiple-choice theory question: "Which notes make up A minor?"
3. **Placement:** a quality counts as known only if both checks pass (*got it* + correct answer). Its 3 shape items are created in box 2. The starting lesson is the first quality in lesson order that isn't known.
4. **Habit setup:**
   - a cue that completes "After ___, I'll practice." (free text, e.g. "after dinner")
   - a weekly goal in days (1–7, default 4)
   - the browser's timezone is stored

### 5.4 Home

The home screen shows:

- the current streak
- days practiced this week against the goal
- the number of reviews due
- the next lesson
- the cue

Actions:

| Action | Session content |
| --- | --- |
| **Today's plan** (primary) | Up to 3 due reviews → next lesson. If all lessons are done, the least recently practiced passage instead. |
| **Continue** | Next lesson, with no reviews |
| **Test me** | Up to 10 items: due items first, then items from the last session, then the lowest boxes. One theory question per distinct quality. |
| **Pick a song** | Any unlocked passage, plus a challenge card |

Every session starts with a length choice:

- **25 min**: the timer counts down. At 0 it offers *wrap up* or *keep going*, which switches to open-ended.
- **Open-ended**: the timer counts up. At 60 minutes it suggests stopping: "diminishing returns; let it consolidate."

The timer advises; it never ends a session by itself.

### 5.5 Session flow

1. **Review cards:** each card shows the prompt ("Play F♯ minor, 1st inversion, on G-B-E"), then *reveal*, then a rating.
2. **Lesson:** the explanation and the 3 diagrams, then one passage, then a challenge card. Each shape and the passage is rated.
3. **Summary:** duration, items rated, changes in the next due dates, and the updated streak.

Ratings are saved as they happen, so an abandoned session keeps them. A lesson is completed once all 3 of its shapes are rated.

### 5.6 Consistency

- **Practice day:** a local date (in the profile's timezone) with at least one finished session that has at least one rating.
- **Streak:** the number of practice days in the current run. A run allows gaps of one missed day and ends after two consecutive missed days. The streak counts as current if the last practice day was today, yesterday or the day before.
- **Weekly progress:** practice days in the current ISO week (Mon–Sun) against the weekly goal.

### 5.7 Progress

- A map of the 12 shapes (4 qualities × 3 inversions), colored by box.
- A history of sessions: date, duration, action and number of items.
- Settings: edit the cue and the weekly goal.

## 6. Architecture

```
Browser (React SPA) ──HTTP/JSON──▶ FastAPI ──SQLAlchemy──▶ Postgres
                                     │
                                     └─OTLP─▶ OTel Collector ─▶ Prometheus · Loki · Tempo ─▶ Grafana ─alert─▶ Responder agent
```

There is one container per environment. FastAPI serves the API under `/api` and the built SPA from `/`.

## 7. Backend

**Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, Postgres 16, `uv`, `ruff`.

**Layout**

```
backend/woodshed/
  main.py        # app factory, static SPA mount, telemetry setup
  db.py          # engine, session dependency
  models.py      # ORM models
  schemas.py     # request/response models
  api.py         # routes (split into a package only when it grows)
  domain/        # pure functions, no I/O
    theory.py    # notes, triads, fret positions
    scheduler.py # Leitner rules
    streak.py    # practice days, streak, weekly progress
    planner.py   # builds a session plan from items and progress
  content.py     # lessons, passages, challenge cards
```

**Rules**

- Domain functions take plain values and return plain values.
- Routes only load data, call the domain and save the result.
- Time is passed into the domain explicitly as `now`, never read inside it, so it can be tested.

**API**

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/healthz` | Liveness and database check |
| GET | `/api/profile` | Profile, or 404 before onboarding |
| POST | `/api/onboarding` | Submit answers and check results; creates the profile and the placed items |
| PATCH | `/api/profile` | Update the cue and the weekly goal |
| GET | `/api/home` | Streak, weekly progress, due count, next lesson, cue |
| GET | `/api/lessons` · `/api/lessons/{quality}` | Lesson content with computed shapes |
| GET | `/api/passages` · `/api/passages/{id}` | Passage content (song or exercise) and unlock state |
| POST | `/api/sessions` | Start a session `{action, length}`; returns the plan |
| POST | `/api/sessions/{id}/ratings` | Rate one item `{item_id, rating}`; returns its new box and `due_at` |
| POST | `/api/sessions/{id}/finish` | Finish a session; returns the summary |
| GET | `/api/sessions` | Session history |
| GET | `/api/progress` | All items with box and `due_at` |

**Key user journey:** `POST /api/sessions` → `POST …/ratings` (one or more) → `POST …/finish`.

**Errors:**

- 422 for invalid input
- 404 for unknown resources
- 409 for rating an item in a finished session

## 8. Database

The database stores the player's state only. Content IDs reference `content.py`.

| Table | Columns |
| --- | --- |
| `profile` | `id` (always 1), `years_playing`, `stuck_on`, `cue`, `weekly_goal_days`, `timezone`, `created_at` |
| `item` | `id` (e.g. `shape:minor:1`, `passage:let-it-be`), `kind`, `box`, `due_at`, `reviews`, `last_rated_at`, `created_at` |
| `session` | `id`, `action`, `length`, `started_at`, `finished_at` |
| `rating` | `id`, `session_id` → session, `item_id` → item, `value`, `box_before`, `box_after`, `rated_at` |

Notes:

- `reviews` counts ratings and drives the root rotation.
- Timestamps are UTC (`timestamptz`).
- A lesson is completed when its 3 shape items exist, so no separate completion table is needed.
- Migrations are managed with Alembic and run on container start.

## 9. Frontend

**Stack:** React 18, TypeScript, Vite, React Router. There's no state library: the server is the source of truth.

**API contract:** TypeScript types are generated from FastAPI's OpenAPI schema (`openapi-typescript`) and used through a thin `fetch` wrapper. CI fails if the generated types are out of date.

**Screens:**

- Onboarding
- Home
- Session (review cards → lesson → passage → challenge → summary)
- Pick a song
- Progress (including settings)

**Components:**

- `Fretboard`: SVG; takes string/fret positions and renders the diagram. It knows nothing about lessons.
- `RatingButtons`: easy / challenging / unfamiliar
- `ReviewCard`: prompt, reveal, rating
- `Timer`: countdown or count-up
- `ChallengeCard`

**Layout:** mobile-first, because the player holds a guitar and the phone sits on a music stand.

## 10. Testing

One command, `make test`, runs every suite.

| Suite | Tool | Covers |
| --- | --- | --- |
| Unit | pytest | `domain/`: triad positions, Leitner transitions and due dates, root rotation, streak and week rules, plan building, onboarding placement |
| Integration | pytest + httpx against a real Postgres (Docker) | API flows end to end: onboarding → home → the key journey → progress; error cases; migrations |
| Frontend | Vitest + Testing Library | Components (`Fretboard`, `RatingButtons`, `ReviewCard`, `Timer`) and the session screen against a mocked API |

Each task's acceptance criteria define the cases its tests must cover.

## 11. Operations

### Local

`make up` runs `docker compose up`. That starts the app, Postgres, and the telemetry stack (Collector, Prometheus, Loki, Tempo and Grafana, with provisioned dashboards and alerts).

### Deployment

- **Hosting:** Render, with two web services: `woodshed-dev` and `woodshed-prod`. Each runs the same image from GHCR.
- **Database:** Neon Postgres with one branch per environment.
- **Config:** environment variables only. Secrets are stored in GitHub and Render, never in the repo.

### CI/CD (GitHub Actions)

| Trigger | Steps |
| --- | --- |
| Pull request | `ruff`, OpenAPI types check, `make test` |
| Merge to `main` | Tests → build the image tagged with the git SHA → push to GHCR → deploy to dev → smoke-test `/healthz` |
| Manual (`workflow_dispatch`, with environment approval) | Deploy a chosen SHA (default: the current dev SHA) to prod → smoke test |

**Rollback:** run the prod workflow again with the previous SHA. Migrations must be backward-compatible with the previous release (expand, then contract).

### Observability (OpenTelemetry)

- **Traces:** automatic for FastAPI and SQLAlchemy, plus spans for planning and scheduling.
- **Metrics:**
  - HTTP request count and duration by route and status
  - `woodshed_sessions_started_total{action}`
  - `woodshed_sessions_finished_total`
  - `woodshed_ratings_total{rating}`
- **Logs:** JSON lines that carry `trace_id` and `span_id`.
- **Privacy:** no free text (the cue) and no request bodies are sent to telemetry.
- **Dashboard:** in Grafana, "Woodshed: practice journey", covering sessions started and finished, rating mix, error rate and p95 latency of the journey routes. It links logs to traces by `trace_id`.

### Alert (user impact)

**"Practice sessions failing":** the 5xx ratio on `/api/sessions*` routes is above 5% over 5 minutes, with at least 3 requests. This means players can't start, rate or finish a session.

### On-call agent

1. The Grafana alert sends a webhook to `incident-response/responder.py`.
2. The responder saves the alert and an evidence packet (matching Loki logs and Tempo traces) to `incident-response/incidents/<id>/`.
3. It runs Claude Code headless with `incident-response/task.md` and a fixed tool allowlist. During diagnosis it can query Grafana MCP.
4. The agent reproduces the failure, fixes it on a branch, runs `make test` and opens a PR that links the incident. It cannot merge or deploy. Merging the PR deploys through CI/CD.

It is demonstrated with an incident drill: a deliberately introduced bug in the journey triggers the alert and the agent's fix.
