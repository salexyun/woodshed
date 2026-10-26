import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from woodshed.api import get_now
from woodshed.content import PASSAGES
from woodshed.main import app
from woodshed.models import Item, Profile

NOW = datetime(2026, 10, 26, 18, 30, tzinfo=UTC)
PASS = {"playing": "got_it", "theory_correct": True}
CUE = "after dinner, before dishes"

ANSWERS = {
    "years_playing": 3,
    "stuck_on": "what_to_practice",
    "claimed_qualities": ["major", "minor"],
    "checks": {"major": PASS, "minor": {"playing": "close", "theory_correct": True}},
    "cue": CUE,
    "weekly_goal_days": 5,
    "timezone": "Europe/Berlin",
}

PROFILE = {
    "years_playing": 3,
    "stuck_on": "what_to_practice",
    "cue": CUE,
    "weekly_goal_days": 5,
    "timezone": "Europe/Berlin",
}


@pytest.fixture(autouse=True)
def frozen_now(client):
    app.dependency_overrides[get_now] = lambda: NOW


def onboard(client, **changes):
    return client.post("/api/onboarding", json=ANSWERS | changes)


def items(db) -> dict[str, Item]:
    return {item.id: item for item in db.scalars(select(Item))}


def passage_ids(quality: str) -> set[str]:
    return {f"passage:{p.id}" for p in PASSAGES if p.lesson == quality}


def test_get_profile_is_404_before_onboarding(client, db):
    assert client.get("/api/profile").status_code == 404


def test_onboarding_returns_201_with_the_profile(client, db):
    response = onboard(client)
    assert response.status_code == 201
    assert response.json() == PROFILE


def test_get_profile_returns_the_profile_after_onboarding(client, db):
    onboard(client)
    response = client.get("/api/profile")
    assert response.status_code == 200
    assert response.json() == PROFILE


def test_onboarding_stores_the_profile_at_now(client, db):
    onboard(client)
    profile = db.scalars(select(Profile)).one()
    assert (profile.id, profile.created_at) == (1, NOW)


def test_weekly_goal_defaults_to_4(client, db):
    answers = ANSWERS.copy()
    del answers["weekly_goal_days"]
    assert client.post("/api/onboarding", json=answers).json()["weekly_goal_days"] == 4


def test_second_onboarding_is_409_and_keeps_the_first_profile(client, db):
    onboard(client)
    assert onboard(client, cue="after coffee").status_code == 409
    assert client.get("/api/profile").json()["cue"] == CUE


def test_placed_quality_gets_shapes_in_box_2_due_in_3_days(client, db):
    onboard(client)
    shapes = {id: item for id, item in items(db).items() if item.kind == "shape"}
    assert set(shapes) == {f"shape:major:{i}" for i in range(3)}
    for item in shapes.values():
        assert (item.box, item.due_at) == (2, NOW + timedelta(days=3))
        assert (item.reviews, item.last_rated_at, item.created_at) == (0, None, NOW)


def test_placed_quality_gets_its_passages_in_box_1_due_now(client, db):
    onboard(client)
    passages = {id: item for id, item in items(db).items() if item.kind == "passage"}
    assert set(passages) == passage_ids("major")
    for item in passages.values():
        assert (item.box, item.due_at) == (1, NOW)
        assert (item.reviews, item.last_rated_at, item.created_at) == (0, None, NOW)


def test_unplaced_qualities_get_no_items(client, db):
    assert onboard(client).status_code == 201
    assert not any(":minor:" in id or id in passage_ids("minor") for id in items(db))


def test_placing_every_quality_creates_every_passage(client, db):
    qualities = ["major", "minor", "diminished", "augmented"]
    onboard(client, claimed_qualities=qualities, checks=dict.fromkeys(qualities, PASS))
    created = set(items(db))
    assert len(created) == 12 + len(PASSAGES)
    assert {f"passage:{p.id}" for p in PASSAGES} <= created


def test_no_qualities_placed_creates_no_items(client, db):
    assert onboard(client, claimed_qualities=[], checks={}).status_code == 201
    assert items(db) == {}


@pytest.mark.parametrize(
    "changes",
    [
        {"weekly_goal_days": 0},
        {"weekly_goal_days": 8},
        {"years_playing": -1},
        {"stuck_on": "motivation"},
        {"claimed_qualities": ["sus4"]},
        {"checks": {"major": {"playing": "nailed_it", "theory_correct": True}}},
        {"timezone": "Not/A_Zone"},
        {"cue": None},
    ],
)
def test_invalid_onboarding_is_422_and_creates_nothing(client, db, changes):
    assert onboard(client, **changes).status_code == 422
    assert db.scalar(select(func.count()).select_from(Profile)) == 0
    assert items(db) == {}


def test_failed_item_insert_leaves_no_profile(client, db):
    # An existing row makes the item insert collide, so the whole onboarding must roll back.
    db.add(
        Item(
            id="shape:major:0",
            kind="shape",
            box=1,
            due_at=NOW,
            reviews=0,
            last_rated_at=None,
            created_at=NOW,
        )
    )
    db.commit()
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/onboarding", json=ANSWERS
    )
    assert not response.is_success
    assert db.scalar(select(func.count()).select_from(Profile)) == 0
    assert set(items(db)) == {"shape:major:0"}
    # Nothing was left behind, so a retry after clearing the collision succeeds.
    db.execute(delete(Item))
    db.commit()
    assert onboard(client).status_code == 201


def test_patch_profile_updates_cue_and_goal(client, db):
    onboard(client)
    response = client.patch(
        "/api/profile", json={"cue": "after coffee", "weekly_goal_days": 2}
    )
    assert response.status_code == 200
    assert response.json() == PROFILE | {"cue": "after coffee", "weekly_goal_days": 2}
    assert client.get("/api/profile").json() == response.json()


@pytest.mark.parametrize("body", [{"cue": "after coffee"}, {"weekly_goal_days": 7}])
def test_patch_profile_leaves_omitted_fields_alone(client, db, body):
    onboard(client)
    assert client.patch("/api/profile", json=body).json() == PROFILE | body


@pytest.mark.parametrize("goal", [0, 8])
def test_patch_goal_outside_1_to_7_is_422(client, db, goal):
    onboard(client)
    assert (
        client.patch("/api/profile", json={"weekly_goal_days": goal}).status_code == 422
    )
    assert client.get("/api/profile").json()["weekly_goal_days"] == 5


def test_patch_profile_is_404_before_onboarding(client, db):
    assert client.patch("/api/profile", json={"cue": "after coffee"}).status_code == 404


def test_cue_is_never_logged(client, db, caplog):
    caplog.set_level(logging.DEBUG)
    onboard(client)
    client.patch("/api/profile", json={"cue": "after the late news"})
    client.get("/api/profile")
    assert CUE not in caplog.text
    assert "after the late news" not in caplog.text
