from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from woodshed.api import get_now
from woodshed.content import CHALLENGE_CARDS, PASSAGES
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


def rate(client, session_id: int, item_id: str, rating: str = "easy"):
    return client.post(
        f"/api/sessions/{session_id}/ratings",
        json={"item_id": item_id, "rating": rating},
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
    assert steps(start(client, "continue")) == [("lesson", "minor")]


def test_pick_a_song_plays_the_passage_with_a_challenge_card(client, db, onboarded):
    session = start(client, "pick_a_song", passage="la-bamba")
    assert steps(session) == [
        ("passage", "passage:la-bamba"),
        ("challenge", "passage:la-bamba"),
    ]
    assert session["steps"][1]["card"] in CHALLENGE_CARDS


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
        (s["id"], s["action"], s["length"], s["items_rated"], s["duration_seconds"])
        for s in response.json()
    ] == [
        (second["id"], "continue", "open", 0, None),
        (first["id"], "today", "25", 1, 25 * 60),
    ]


def test_sessions_are_empty_before_any_session(client, db, onboarded):
    assert client.get("/api/sessions").json() == []


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
