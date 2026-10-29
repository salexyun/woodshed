from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from woodshed.api import get_now
from woodshed.content import PASSAGES
from woodshed.main import app
from woodshed.models import Item, PracticeSession, Rating

# A Monday. Berlin is UTC+1 here, since DST ended on Sunday 25 October.
NOW = datetime(2026, 10, 26, 18, 30, tzinfo=UTC)
PASS = {"playing": "got_it", "theory_correct": True}
QUALITIES = ["major", "minor", "diminished", "augmented"]
CUE = "after dinner, before dishes"

# Places major only: minor's playing check is just "close".
ANSWERS = {
    "years_playing": 3,
    "stuck_on": "what_to_practice",
    "claimed_qualities": ["major", "minor"],
    "checks": {"major": PASS, "minor": {"playing": "close", "theory_correct": True}},
    "cue": CUE,
    "weekly_goal_days": 5,
    "timezone": "Europe/Berlin",
}
MAJOR_PASSAGES = [f"passage:{p.id}" for p in PASSAGES if p.lesson == "major"]


def freeze(now: datetime) -> None:
    app.dependency_overrides[get_now] = lambda: now


@pytest.fixture(autouse=True)
def frozen_now(client):
    freeze(NOW)


def onboard(client, **changes):
    assert client.post("/api/onboarding", json=ANSWERS | changes).status_code == 201


def add_item(db, id: str, box: int = 1, due_at: datetime = NOW) -> None:
    kind = id.partition(":")[0]
    db.add(Item(id=id, kind=kind, box=box, due_at=due_at, reviews=0, created_at=NOW))
    db.commit()


def practice(db, finished_at: datetime | None, ratings: int = 1) -> None:
    started_at = (finished_at or NOW) - timedelta(minutes=25)
    session = PracticeSession(
        action="today", length="25", started_at=started_at, finished_at=finished_at
    )
    db.add(session)
    db.flush()
    db.add_all(
        Rating(
            session_id=session.id,
            item_id=MAJOR_PASSAGES[0],
            value="easy",
            box_before=1,
            box_after=2,
            rated_at=started_at,
        )
        for _ in range(ratings)
    )
    db.commit()


def home(client) -> dict:
    response = client.get("/api/home")
    assert response.status_code == 200
    return response.json()


def progress_items(client) -> list[dict]:
    response = client.get("/api/progress")
    assert response.status_code == 200
    return response.json()


def progress(client) -> dict[str, tuple[int, datetime]]:
    return {
        i["id"]: (i["box"], datetime.fromisoformat(i["due_at"]))
        for i in progress_items(client)
    }


def test_home_is_404_before_onboarding(client, db):
    assert client.get("/api/home").status_code == 404


def test_home_after_onboarding(client, db):
    onboard(client)
    assert home(client) == {
        "streak": 0,
        "week_days": 0,
        "weekly_goal_days": 5,
        "due_count": len(MAJOR_PASSAGES),
        "next_lesson": "minor",
        "cue": CUE,
    }


def test_home_shows_the_updated_cue_and_goal(client, db):
    onboard(client)
    client.patch("/api/profile", json={"cue": "after coffee", "weekly_goal_days": 2})
    body = home(client)
    assert (body["cue"], body["weekly_goal_days"]) == ("after coffee", 2)


def test_streak_allows_one_missed_day(client, db):
    onboard(client)
    # Local practice days: Fri 23, Sun 25 and Mon 26 October.
    for day in (23, 25, 26):
        practice(db, datetime(2026, 10, day, 12, tzinfo=UTC))
    assert home(client)["streak"] == 3


def test_streak_ends_after_two_missed_days(client, db):
    onboard(client)
    # Local practice days: Thu 22 and Sun 25 October.
    for day in (22, 25):
        practice(db, datetime(2026, 10, day, 12, tzinfo=UTC))
    assert home(client)["streak"] == 1


def test_streak_is_0_when_the_last_practice_was_three_days_ago(client, db):
    onboard(client)
    practice(db, datetime(2026, 10, 23, 12, tzinfo=UTC))  # Friday
    assert home(client)["streak"] == 0


def test_week_counts_practice_days_since_monday(client, db):
    onboard(client)
    freeze(datetime(2026, 10, 29, 18, 30, tzinfo=UTC))  # Thursday
    # Sun 25 is last week; Mon 26 counts once despite two sessions; Wed 28 counts.
    for finished_at in (
        datetime(2026, 10, 25, 12, tzinfo=UTC),
        datetime(2026, 10, 26, 9, tzinfo=UTC),
        datetime(2026, 10, 26, 20, tzinfo=UTC),
        datetime(2026, 10, 28, 12, tzinfo=UTC),
    ):
        practice(db, finished_at)
    assert home(client)["week_days"] == 2
    assert home(client)["streak"] == 3


def test_practice_day_is_the_local_date_of_finished_at(client, db):
    onboard(client)
    # Sunday 23:30 UTC is already Monday 00:30 in Berlin, so it is this week's.
    practice(db, datetime(2026, 10, 25, 23, 30, tzinfo=UTC))
    assert (home(client)["streak"], home(client)["week_days"]) == (1, 1)


@pytest.mark.parametrize(
    ("finished_at", "ratings"), [(None, 1), (NOW - timedelta(hours=1), 0)]
)
def test_unfinished_or_unrated_sessions_are_not_practice(
    client, db, finished_at, ratings
):
    onboard(client)
    practice(db, finished_at, ratings)
    assert (home(client)["streak"], home(client)["week_days"]) == (0, 0)


def test_due_count_counts_every_due_item(client, db):
    onboard(client, claimed_qualities=QUALITIES, checks=dict.fromkeys(QUALITIES, PASS))
    # Passages are due now; placed shapes come due 3 days later.
    assert home(client)["due_count"] == len(PASSAGES)
    freeze(NOW + timedelta(days=3))
    assert home(client)["due_count"] == 12 + len(PASSAGES)


def test_due_count_skips_items_due_later(client, db):
    onboard(client, claimed_qualities=[], checks={})
    add_item(db, "shape:major:0", due_at=NOW)
    add_item(db, "shape:major:1", due_at=NOW + timedelta(seconds=1))
    assert home(client)["due_count"] == 1


@pytest.mark.parametrize(
    ("minor_shapes", "next_lesson"), [(0, "minor"), (2, "minor"), (3, "diminished")]
)
def test_next_lesson_is_the_first_without_all_3_shapes(
    client, db, minor_shapes, next_lesson
):
    onboard(client)
    for inversion in range(minor_shapes):
        add_item(db, f"shape:minor:{inversion}")
    assert home(client)["next_lesson"] == next_lesson


def test_next_lesson_is_null_when_every_lesson_is_done(client, db):
    onboard(client, claimed_qualities=QUALITIES, checks=dict.fromkeys(QUALITIES, PASS))
    assert home(client)["next_lesson"] is None


def test_progress_lists_every_item_with_box_and_due_at(client, db):
    onboard(client)
    assert progress(client) == {
        **{f"shape:major:{i}": (2, NOW + timedelta(days=3)) for i in range(3)},
        **{id: (1, NOW) for id in MAJOR_PASSAGES},
    }


def test_progress_items_have_only_id_box_and_due_at(client, db):
    onboard(client)
    assert all(set(i) == {"id", "box", "due_at"} for i in progress_items(client))


def test_progress_reflects_the_stored_box(client, db):
    onboard(client)
    item = db.scalars(select(Item).where(Item.id == "shape:major:1")).one()
    item.box, item.due_at = 5, NOW + timedelta(days=30)
    db.commit()
    assert progress(client)["shape:major:1"] == (5, NOW + timedelta(days=30))


def test_progress_is_empty_without_items(client, db):
    onboard(client, claimed_qualities=[], checks={})
    assert progress_items(client) == []
