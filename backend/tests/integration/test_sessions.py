import contextlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session

from woodshed.api import get_now
from woodshed.content import CHALLENGE_CARDS, PASSAGES
from woodshed.db import get_session
from woodshed.main import app
from woodshed.models import Item, PracticeSession, Rating

# A Monday. Berlin is UTC+1 here, since DST ended on Sunday 25 October.
NOW = datetime(2026, 10, 26, 18, 30, tzinfo=UTC)
LATER = NOW + timedelta(minutes=25)
PASS = {"playing": "got_it", "theory_correct": True}

# Places major only: minor's playing check is just "close".
ANSWERS = {
    "years_playing": 3,
    "stuck_on": "what_to_practice",
    "claimed_qualities": ["major", "minor"],
    "checks": {"major": PASS, "minor": {"playing": "close", "theory_correct": True}},
    "cue": "after dinner, before dishes",
    "weekly_goal_days": 5,
    "timezone": "Europe/Berlin",
}
# Due items come most overdue first; these are equally due, so by id.
MAJOR_PASSAGES = sorted(f"passage:{p.id}" for p in PASSAGES if p.lesson == "major")
MINOR_PASSAGES = {f"passage:{p.id}" for p in PASSAGES if p.lesson == "minor"}
MINOR_SHAPES = [f"shape:minor:{i}" for i in range(3)]


def freeze(now: datetime) -> None:
    app.dependency_overrides[get_now] = lambda: now


@pytest.fixture(autouse=True)
def frozen_now(client):
    freeze(NOW)


@pytest.fixture
def onboarded(client, db):
    assert client.post("/api/onboarding", json=ANSWERS).status_code == 201


def start(client, action: str = "today", length: str = "25", **body) -> dict:
    response = client.post(
        "/api/sessions", json={"action": action, "length": length} | body
    )
    assert response.status_code == 201
    return response.json()


def rate(client, session_id: int, item_id: str, rating: str = "easy", **body):
    return client.post(
        f"/api/sessions/{session_id}/ratings",
        json={"item_id": item_id, "rating": rating} | body,
    )


def finish(client, session_id: int) -> dict:
    response = client.post(f"/api/sessions/{session_id}/finish")
    assert response.status_code == 200
    return response.json()


def steps(session: dict) -> list[tuple[str, str]]:
    return [(s["kind"], s["id"]) for s in session["steps"]]


def item(db, id: str) -> Item:
    db.expire_all()
    return db.get(Item, id)


def ratings(db) -> list[Rating]:
    db.expire_all()
    return list(db.scalars(select(Rating).order_by(Rating.id)))


# POST /api/sessions


def test_start_is_404_before_onboarding(client, db):
    assert (
        client.post(
            "/api/sessions", json={"action": "today", "length": "25"}
        ).status_code
        == 404
    )


def test_start_stores_the_session(client, db, onboarded):
    session = start(client, length="open")
    stored = db.scalars(select(PracticeSession)).one()
    assert stored.id == session["id"]
    assert (stored.action, stored.length) == ("today", "open")
    assert (stored.started_at, stored.finished_at) == (NOW, None)


def test_todays_plan_is_due_reviews_then_the_next_lesson(client, db, onboarded):
    session = start(client)
    assert steps(session) == [
        *(("review", id) for id in MAJOR_PASSAGES),
        ("lesson", "minor"),
    ]


def test_continue_is_the_next_lesson_only(client, db, onboarded):
    session = start(client, "continue")
    assert steps(session) == [("lesson", "minor")]
    assert session["steps"][0]["card"] in CHALLENGE_CARDS


def test_continue_is_409_and_creates_no_session_when_every_lesson_is_done(client, db):
    qualities = ["major", "minor", "diminished", "augmented"]
    onboarding = ANSWERS | {
        "claimed_qualities": qualities,
        "checks": dict.fromkeys(qualities, PASS),
    }
    assert client.post("/api/onboarding", json=onboarding).status_code == 201
    response = client.post("/api/sessions", json={"action": "continue", "length": "25"})
    assert response.status_code == 409
    assert db.scalars(select(PracticeSession)).all() == []


def test_pick_a_song_plays_the_passage_with_a_challenge_card(client, db, onboarded):
    session = start(client, "pick_a_song", passage="la-bamba")
    assert steps(session) == [
        ("passage", "passage:la-bamba"),
        ("challenge", "passage:la-bamba"),
    ]
    assert session["steps"][1]["card"] in CHALLENGE_CARDS


def test_test_me_draws_from_the_last_session_with_ratings(client, db, onboarded):
    rate(client, start(client)["id"], "shape:major:2")
    start(client, "continue")  # abandoned without ratings
    reviews = [id for kind, id in steps(start(client, "test_me")) if kind == "review"]
    # Due passages first, then the rated shape ahead of its lower-box siblings.
    assert reviews[: len(MAJOR_PASSAGES) + 1] == [*MAJOR_PASSAGES, "shape:major:2"]


def test_shape_reviews_name_a_root_that_advances_per_review(client, db, onboarded):
    rate(client, start(client)["id"], "shape:major:0", "challenging")
    roots = {s["id"]: s["root"] for s in start(client, "test_me")["steps"]}
    # Roots follow the cycle of fourths from C; passages are played as written.
    assert (roots["shape:major:0"], roots["shape:major:1"]) == ("F", "C")
    assert roots["passage:la-bamba"] is None


def test_only_review_steps_have_a_root(client, db, onboarded):
    session = start(client, "pick_a_song", passage="la-bamba")
    assert [s["root"] for s in session["steps"]] == [None, None]
    assert start(client, "continue")["steps"][0]["root"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"action": "practice", "length": "25"},
        {"action": "today", "length": "45"},
        {"action": "pick_a_song", "length": "25"},
        {"action": "pick_a_song", "length": "25", "passage": "let-it-be"},
        {"action": "pick_a_song", "length": "25", "passage": "no-such-song"},
    ],
)
def test_invalid_start_is_422_and_stores_nothing(client, db, onboarded, body):
    assert client.post("/api/sessions", json=body).status_code == 422
    assert db.scalars(select(PracticeSession)).all() == []


# POST /api/sessions/{id}/ratings


@pytest.mark.parametrize(
    ("item_id", "rating", "box_before", "box_after", "days"),
    [
        ("passage:la-bamba", "easy", 1, 2, 3),
        ("passage:la-bamba", "challenging", 1, 1, 1),
        ("passage:la-bamba", "unfamiliar", 1, 1, 1),
        ("shape:major:1", "easy", 2, 3, 7),
        ("shape:major:1", "challenging", 2, 2, 3),
        ("shape:major:1", "unfamiliar", 2, 1, 1),
    ],
)
def test_rating_moves_the_item_and_stores_the_rating(
    client, db, onboarded, item_id, rating, box_before, box_after, days
):
    session = start(client)
    response = rate(client, session["id"], item_id, rating)
    assert response.status_code == 200
    body = response.json()
    due_at = NOW + timedelta(days=days)
    assert (body["box"], datetime.fromisoformat(body["due_at"])) == (box_after, due_at)
    stored = item(db, item_id)
    assert (stored.box, stored.due_at) == (box_after, due_at)
    assert (stored.reviews, stored.last_rated_at) == (1, NOW)
    [row] = ratings(db)
    assert (row.session_id, row.item_id, row.value) == (session["id"], item_id, rating)
    assert (row.box_before, row.box_after, row.rated_at) == (box_before, box_after, NOW)


def test_rating_a_lesson_shape_creates_it_from_box_1(client, db, onboarded):
    session = start(client, "continue")
    assert rate(client, session["id"], "shape:minor:0", "easy").json()["box"] == 2
    stored = item(db, "shape:minor:0")
    assert (stored.kind, stored.box, stored.due_at) == (
        "shape",
        2,
        NOW + timedelta(days=3),
    )
    assert (ratings(db)[0].box_before, ratings(db)[0].box_after) == (1, 2)


LOCK_WAITERS = text(
    "SELECT count(*) FROM pg_stat_activity"
    " WHERE datname = current_database() AND wait_event_type = 'Lock'"
)


def hold_for_the_other_request(engine, arrived: list) -> None:
    """Waits until the other request arrives here too or blocks on a lock.

    A request that serializes on a lock never arrives while this one holds,
    so a lock waiter ends the hold at once instead of after a timeout.
    """
    arrived.append(threading.get_ident())
    deadline = time.monotonic() + 5
    while len(arrived) < 2 and time.monotonic() < deadline:
        with engine.connect() as monitor:
            if monitor.scalar(LOCK_WAITERS):
                return
        time.sleep(0.01)


# The second case completes the lesson, so both requests also try to unlock passages.
@pytest.mark.parametrize("rated_before", [0, 2])
def test_concurrent_first_ratings_of_a_shape_both_succeed(
    client, db, onboarded, database_url, rated_before
):
    session_id = start(client, "continue")["id"]
    for id in MINOR_SHAPES[:rated_before]:
        assert rate(client, session_id, id).status_code == 200
    shape_id = MINOR_SHAPES[rated_before]
    engine = create_engine(database_url)
    arrived = []

    # Holds each request after it finds the item missing, so both race to create it.
    class RacingSession(Session):
        def get(self, entity, ident, **kw):
            found = super().get(entity, ident, **kw)
            if entity is Item and found is None:
                hold_for_the_other_request(engine, arrived)
            return found

    def session():
        with RacingSession(engine) as s:
            yield s

    app.dependency_overrides[get_session] = session
    try:
        with ThreadPoolExecutor(2) as pool:
            responses = list(
                pool.map(lambda _: rate(client, session_id, shape_id), range(2))
            )
    finally:
        engine.dispose()

    assert [r.status_code for r in responses] == [200, 200]
    stored = item(db, shape_id)
    assert (stored.box, stored.reviews) == (3, 2)
    assert [
        (r.box_before, r.box_after) for r in ratings(db) if r.item_id == shape_id
    ] == [(1, 2), (2, 3)]
    unlocked = db.scalars(select(Item.id).where(Item.id.in_(MINOR_PASSAGES)))
    completes_lesson = rated_before == 2
    assert sorted(unlocked) == (sorted(MINOR_PASSAGES) if completes_lesson else [])


def test_concurrent_ratings_of_an_existing_item_both_apply(
    client, db, onboarded, database_url
):
    session_id = start(client, "continue")["id"]
    shape_id = MINOR_SHAPES[0]
    assert rate(client, session_id, shape_id).status_code == 200
    engine = create_engine(database_url)
    # Holds each request after it reads the item, so without a row lock both
    # rate from the same box. With one, the second read waits for the first
    # commit; the first gives up waiting after the timeout and the barrier breaks.
    barrier = threading.Barrier(2, timeout=2)

    class RacingSession(Session):
        def get(self, entity, ident, **kw):
            found = super().get(entity, ident, **kw)
            if entity is Item and found is not None:
                with contextlib.suppress(threading.BrokenBarrierError):
                    barrier.wait()
            return found

    def session():
        with RacingSession(engine) as s:
            yield s

    app.dependency_overrides[get_session] = session
    try:
        with ThreadPoolExecutor(2) as pool:
            responses = list(
                pool.map(lambda _: rate(client, session_id, shape_id), range(2))
            )
    finally:
        engine.dispose()

    assert [r.status_code for r in responses] == [200, 200]
    stored = item(db, shape_id)
    assert (stored.box, stored.reviews) == (4, 3)
    assert [(r.box_before, r.box_after) for r in ratings(db)] == [
        (1, 2),
        (2, 3),
        (3, 4),
    ]


def test_concurrent_first_ratings_of_a_lessons_last_shapes_unlock_it_once(
    client, db, onboarded, database_url
):
    session_id = start(client, "continue")["id"]
    assert rate(client, session_id, MINOR_SHAPES[0]).status_code == 200
    engine = create_engine(database_url)
    committing = []

    # Holds each request's commit until the other is committing too, so without
    # a lesson lock both check completion before either new shape is visible.
    @event.listens_for(engine, "commit")
    def hold_commit(conn):
        hold_for_the_other_request(engine, committing)

    def session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = session
    try:
        with ThreadPoolExecutor(2) as pool:
            responses = list(
                pool.map(lambda id: rate(client, session_id, id), MINOR_SHAPES[1:])
            )
    finally:
        engine.dispose()

    assert [r.status_code for r in responses] == [200, 200]
    unlocked = db.scalars(select(Item.id).where(Item.id.in_(MINOR_PASSAGES)))
    assert sorted(unlocked) == sorted(MINOR_PASSAGES)


def test_two_of_3_shapes_leave_the_lesson_incomplete(client, db, onboarded):
    session = start(client, "continue")
    for id in MINOR_SHAPES[:2]:
        rate(client, session["id"], id)
    assert client.get("/api/home").json()["next_lesson"] == "minor"
    assert all(item(db, id) is None for id in MINOR_PASSAGES)


def test_rating_all_3_shapes_completes_the_lesson_and_creates_its_passages(
    client, db, onboarded
):
    session = start(client, "continue")
    for id in MINOR_SHAPES:
        rate(client, session["id"], id)
    assert client.get("/api/home").json()["next_lesson"] == "diminished"
    for id in MINOR_PASSAGES:
        stored = item(db, id)
        assert (stored.kind, stored.box, stored.due_at) == ("passage", 1, NOW)
    unlocked = {p["id"] for p in client.get("/api/passages").json() if p["unlocked"]}
    assert {f"passage:{id}" for id in unlocked} >= MINOR_PASSAGES


def test_rating_in_a_finished_session_is_409_and_changes_nothing(client, db, onboarded):
    session = start(client)
    finish(client, session["id"])
    assert rate(client, session["id"], "passage:la-bamba").status_code == 409
    assert item(db, "passage:la-bamba").box == 1
    assert ratings(db) == []


def test_invalid_rating_value_is_422(client, db, onboarded):
    session = start(client)
    assert rate(client, session["id"], "passage:la-bamba", "meh").status_code == 422
    assert ratings(db) == []


def test_rating_in_an_unknown_session_is_404(client, db, onboarded):
    assert rate(client, 999, "passage:la-bamba").status_code == 404
    assert ratings(db) == []


@pytest.mark.parametrize("item_id", ["passage:no-such-song", "shape:sus4:0"])
def test_rating_an_unknown_item_is_404(client, db, onboarded, item_id):
    assert rate(client, start(client)["id"], item_id).status_code == 404
    assert ratings(db) == []


# A lesson shape is created by its first rating, so its retry must not rate it again.
@pytest.mark.parametrize("item_id", ["passage:la-bamba", "shape:minor:0"])
def test_retried_rating_is_stored_once(client, db, onboarded, item_id):
    session_id = start(client)["id"]
    for _ in range(2):
        assert rate(client, session_id, item_id, position=0).status_code == 200
    assert [(r.item_id, r.box_before, r.box_after) for r in ratings(db)] == [
        (item_id, 1, 2)
    ]
    assert (item(db, item_id).box, item(db, item_id).reviews) == (2, 1)


# The player may tap another button on retry, but the first rating already counted.
@pytest.mark.parametrize("retried", ["easy", "unfamiliar"])
def test_retried_rating_returns_the_original_response(client, db, onboarded, retried):
    session_id = start(client)["id"]
    original = rate(client, session_id, "passage:la-bamba", "easy", position=0)
    freeze(LATER)
    retry = rate(client, session_id, "passage:la-bamba", retried, position=0)
    assert (retry.status_code, retry.json()) == (200, original.json())
    assert original.json()["box"] == 2
    assert item(db, "passage:la-bamba").due_at == NOW + timedelta(days=3)


def test_concurrent_retries_are_stored_once(client, db, onboarded, database_url):
    session_id = start(client)["id"]
    engine = create_engine(database_url)
    arrived = []

    # Holds each request after it locks the item, so both have missed the other's
    # rating; the second then waits on the row lock and must lose at the insert.
    class RacingSession(Session):
        def get(self, entity, ident, **kw):
            found = super().get(entity, ident, **kw)
            if entity is Item:
                hold_for_the_other_request(engine, arrived)
            return found

    def session():
        with RacingSession(engine) as s:
            yield s

    app.dependency_overrides[get_session] = session
    try:
        with ThreadPoolExecutor(2) as pool:
            responses = list(
                pool.map(
                    lambda _: rate(client, session_id, "passage:la-bamba", position=0),
                    range(2),
                )
            )
    finally:
        engine.dispose()

    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    assert [(r.box_before, r.box_after) for r in ratings(db)] == [(1, 2)]
    assert item(db, "passage:la-bamba").reviews == 1


def test_ratings_at_different_positions_are_stored_apart(client, db, onboarded):
    session_id = start(client, "continue")["id"]
    for position in (0, 1):
        rate(client, session_id, "shape:minor:0", position=position)
    assert [(r.box_before, r.box_after) for r in ratings(db)] == [(1, 2), (2, 3)]


def test_the_same_position_in_another_session_is_a_new_rating(client, db, onboarded):
    for _ in range(2):
        rate(client, start(client)["id"], "passage:la-bamba", position=0)
    assert [(r.box_before, r.box_after) for r in ratings(db)] == [(1, 2), (2, 3)]


def test_resume_lists_a_retried_rating_once(client, db, onboarded):
    session_id = start(client)["id"]
    for _ in range(2):
        rate(client, session_id, "shape:major:0", position=0)
    assert get(client, session_id)["rated"] == ["shape:major:0"]


# POST /api/sessions/{id}/finish


def test_finish_returns_the_summary(client, db, onboarded):
    session = start(client)
    rate(client, session["id"], "passage:la-bamba", "easy")
    rate(client, session["id"], "shape:major:0", "unfamiliar")
    freeze(LATER)
    summary = finish(client, session["id"])
    assert summary["duration_seconds"] == 25 * 60
    assert summary["items_rated"] == 2
    assert {
        i["id"]: (i["box"], datetime.fromisoformat(i["due_at"]))
        for i in summary["next_due"]
    } == {
        "passage:la-bamba": (2, NOW + timedelta(days=3)),
        "shape:major:0": (1, NOW + timedelta(days=1)),
    }
    assert summary["streak"] == 1


def test_finish_stores_finished_at(client, db, onboarded):
    session = start(client)
    freeze(LATER)
    finish(client, session["id"])
    db.expire_all()
    assert db.get(PracticeSession, session["id"]).finished_at == LATER


def test_finishing_without_ratings_is_not_a_practice_day(client, db, onboarded):
    summary = finish(client, start(client)["id"])
    assert (summary["items_rated"], summary["next_due"], summary["streak"]) == (
        0,
        [],
        0,
    )


def test_finish_unknown_session_is_404(client, db, onboarded):
    assert client.post("/api/sessions/999/finish").status_code == 404


# GET /api/sessions


def test_sessions_are_listed_newest_first(client, db, onboarded):
    first = start(client)
    rate(client, first["id"], "passage:la-bamba")
    freeze(LATER)
    finish(client, first["id"])
    second = start(client, "continue", length="open")
    response = client.get("/api/sessions")
    assert response.status_code == 200
    assert [
        (
            s["id"],
            s["action"],
            s["length"],
            datetime.fromisoformat(s["started_at"]),
            s["items_rated"],
            s["duration_seconds"],
        )
        for s in response.json()
    ] == [
        (second["id"], "continue", "open", LATER, 0, None),
        (first["id"], "today", "25", NOW, 1, 25 * 60),
    ]


def test_sessions_are_empty_before_any_session(client, db, onboarded):
    assert client.get("/api/sessions").json() == []


# GET /api/sessions/{id}


def get(client, session_id: int) -> dict:
    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize(
    ("action", "body"),
    [("today", {}), ("continue", {}), ("pick_a_song", {"passage": "la-bamba"})],
)
def test_get_returns_the_stored_steps_with_their_cards(
    client, db, onboarded, action, body
):
    session = start(client, action, **body)
    assert get(client, session["id"])["steps"] == session["steps"]


def test_get_returns_the_session(client, db, onboarded):
    session = start(client, "continue", length="open")
    stored = get(client, session["id"])
    assert (stored["id"], stored["action"], stored["length"]) == (
        session["id"],
        "continue",
        "open",
    )
    assert datetime.fromisoformat(stored["started_at"]) == NOW
    assert (stored["finished_at"], stored["rated"]) == (None, [])


def test_get_shows_when_the_session_finished(client, db, onboarded):
    session = start(client)
    freeze(LATER)
    finish(client, session["id"])
    assert datetime.fromisoformat(get(client, session["id"])["finished_at"]) == LATER


def test_get_lists_only_this_sessions_ratings(client, db, onboarded):
    rate(client, start(client)["id"], "passage:la-bamba")
    session = start(client)
    rate(client, session["id"], "shape:major:0")
    assert get(client, session["id"])["rated"] == ["shape:major:0"]


def test_get_unknown_session_is_404(client, db, onboarded):
    assert client.get("/api/sessions/999").status_code == 404


def test_resume_shows_the_same_steps_and_both_ratings(client, db, onboarded):
    session = start(client)
    rate(client, session["id"], "shape:major:0", "challenging")
    rate(client, session["id"], "passage:la-bamba", "easy")
    resumed = get(client, session["id"])
    assert resumed["steps"] == session["steps"]
    assert resumed["rated"] == ["shape:major:0", "passage:la-bamba"]


# The key journey


def test_key_journey_shows_on_home_and_progress(client, db, onboarded):
    session = start(client)
    for kind, id in steps(session):
        if kind == "review":
            assert rate(client, session["id"], id, "easy").status_code == 200
    for id in MINOR_SHAPES:
        assert rate(client, session["id"], id, "easy").status_code == 200

    freeze(LATER)
    summary = finish(client, session["id"])
    assert (summary["items_rated"], summary["streak"]) == (6, 1)

    home = client.get("/api/home").json()
    # Only the newly unlocked minor passages are due; everything rated moved to box 2.
    assert (home["streak"], home["week_days"]) == (1, 1)
    assert (home["due_count"], home["next_lesson"]) == (
        len(MINOR_PASSAGES),
        "diminished",
    )

    progress = {i["id"]: i["box"] for i in client.get("/api/progress").json()}
    assert {
        id: progress[id] for id in [*MAJOR_PASSAGES, *MINOR_SHAPES]
    } == dict.fromkeys([*MAJOR_PASSAGES, *MINOR_SHAPES], 2)

    [history] = client.get("/api/sessions").json()
    assert (history["id"], history["items_rated"]) == (session["id"], 6)
