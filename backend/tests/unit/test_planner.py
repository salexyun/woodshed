from datetime import UTC, datetime, timedelta

import pytest

from woodshed.domain.planner import Step, plan
from woodshed.domain.scheduler import Item

NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
ALL_LESSONS = {"major", "minor", "diminished", "augmented"}


def item(
    item_id: str, days_overdue: float, box: int = 1, days_since_rated: float = 1
) -> Item:
    return Item(
        id=item_id,
        due_at=NOW - timedelta(days=days_overdue),
        box=box,
        last_rated_at=NOW - timedelta(days=days_since_rated),
    )


def reviews(*ids: str) -> list[Step]:
    return [Step("review", i) for i in ids]


DUE = [
    item("shape:major:1", 4),
    item("shape:minor:1", 3),
    item("shape:major:2", 2),
    item("shape:minor:2", 1),
]
NOT_DUE = [item("shape:major:3", -2), item("shape:minor:3", -1)]


@pytest.mark.parametrize(
    ("completed", "lesson"),
    [
        (set(), "major"),
        ({"major"}, "minor"),
        ({"major", "minor", "diminished"}, "augmented"),
        ({"minor"}, "major"),
    ],
)
def test_todays_plan_is_up_to_3_due_reviews_then_next_lesson(completed, lesson):
    assert plan("today", DUE + NOT_DUE, completed, [], NOW) == [
        *reviews("shape:major:1", "shape:minor:1", "shape:major:2"),
        Step("lesson", lesson),
    ]


def test_todays_plan_with_empty_review_queue_is_next_lesson_only():
    assert plan("today", NOT_DUE, {"major"}, [], NOW) == [Step("lesson", "minor")]


def test_todays_plan_with_no_items_is_first_lesson():
    assert plan("today", [], set(), [], NOW) == [Step("lesson", "major")]


def test_todays_plan_when_all_lessons_done_is_least_recently_practiced_passage():
    passages = [
        item("passage:la-bamba", -5, days_since_rated=2),
        item("passage:let-it-be", -3, days_since_rated=9),
        item("passage:stand-by-me", -1, days_since_rated=4),
    ]
    assert plan("today", DUE + passages, ALL_LESSONS, [], NOW) == [
        *reviews("shape:major:1", "shape:minor:1", "shape:major:2"),
        Step("passage", "passage:let-it-be"),
        Step("challenge", "passage:let-it-be"),
    ]


def test_todays_plan_when_all_lessons_done_and_nothing_due_is_passage_only():
    passages = [
        item("passage:la-bamba", -5, days_since_rated=2),
        item("passage:twist-and-shout", -1, days_since_rated=6),
    ]
    assert plan("today", passages, ALL_LESSONS, [], NOW) == [
        Step("passage", "passage:twist-and-shout"),
        Step("challenge", "passage:twist-and-shout"),
    ]


def test_todays_plan_skips_passage_already_due_for_review():
    passages = [
        item("passage:let-it-be", 1, days_since_rated=9),
        item("passage:stand-by-me", -1, days_since_rated=4),
        item("passage:la-bamba", -5, days_since_rated=2),
    ]
    assert plan("today", passages, ALL_LESSONS, [], NOW) == [
        Step("review", "passage:let-it-be"),
        Step("passage", "passage:stand-by-me"),
        Step("challenge", "passage:stand-by-me"),
    ]


def test_todays_plan_breaks_ties_among_never_rated_passages_by_id():
    passages = [
        Item("passage:stand-by-me", NOW + timedelta(days=1)),
        Item("passage:la-bamba", NOW + timedelta(days=2)),
        item("passage:let-it-be", -1, days_since_rated=30),
    ]
    assert plan("today", passages, ALL_LESSONS, [], NOW) == [
        Step("passage", "passage:la-bamba"),
        Step("challenge", "passage:la-bamba"),
    ]


@pytest.mark.parametrize(
    ("completed", "lesson"), [(set(), "major"), ({"major", "minor"}, "diminished")]
)
def test_continue_is_next_lesson_without_reviews(completed, lesson):
    assert plan("continue", DUE, completed, [], NOW) == [Step("lesson", lesson)]


def test_test_me_orders_due_then_last_session_then_lowest_boxes():
    items = [
        item("shape:major:1", 2, box=3),
        item("shape:minor:1", 1, box=4),
        item("shape:diminished:1", -1, box=5),
        item("shape:major:2", -2, box=3),
        item("shape:minor:2", -3, box=1),
        item("shape:major:3", -4, box=2),
        item("shape:minor:3", -5, box=2),
    ]
    last_session = ["shape:major:2", "shape:diminished:1", "shape:major:1"]
    steps = plan("test_me", items, ALL_LESSONS, last_session, NOW)
    assert [s for s in steps if s.kind == "review"] == reviews(
        "shape:major:1",
        "shape:minor:1",
        "shape:major:2",
        "shape:diminished:1",
        "shape:minor:2",
        "shape:major:3",
        "shape:minor:3",
    )


def test_test_me_with_empty_review_queue_starts_with_last_session():
    items = [item("shape:minor:1", -1, box=1), item("shape:major:1", -2, box=4)]
    steps = plan("test_me", items, {"major", "minor"}, ["shape:major:1"], NOW)
    assert [s for s in steps if s.kind == "review"] == reviews(
        "shape:major:1", "shape:minor:1"
    )


def test_test_me_returns_at_most_10_items():
    items = [item(f"shape:major:{n}", n) for n in range(1, 4)] + [
        item(f"passage:p{n}", -n, box=n % 5 + 1) for n in range(12)
    ]
    steps = plan("test_me", items, ALL_LESSONS, [], NOW)
    assert len([s for s in steps if s.kind == "review"]) == 10


def test_test_me_ends_with_one_theory_question_per_distinct_quality():
    items = [
        item("shape:minor:1", 3),
        item("shape:major:1", 2),
        item("shape:minor:2", 1),
        item("passage:let-it-be", -1),
    ]
    steps = plan("test_me", items, {"major", "minor"}, [], NOW)
    assert steps[-2:] == [Step("theory", "minor"), Step("theory", "major")]
    assert len([s for s in steps if s.kind == "theory"]) == 2


def test_pick_a_song_is_chosen_passage_plus_challenge_card():
    items = [*DUE, item("passage:la-bamba", 1), item("passage:let-it-be", -1)]
    steps = plan(
        "pick_a_song", items, {"major", "minor"}, [], NOW, passage="passage:let-it-be"
    )
    assert steps == [
        Step("passage", "passage:let-it-be"),
        Step("challenge", "passage:let-it-be"),
    ]


def test_pick_a_song_rejects_locked_passage():
    with pytest.raises(ValueError):
        plan("pick_a_song", DUE, {"major"}, [], NOW, passage="passage:let-it-be")


@pytest.mark.parametrize("passage", ["shape:major:1", None])
def test_pick_a_song_rejects_anything_but_a_passage(passage):
    with pytest.raises(ValueError, match="not a passage"):
        plan("pick_a_song", DUE, {"major"}, [], NOW, passage=passage)
