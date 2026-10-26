from datetime import UTC, datetime, timedelta

import pytest

from woodshed.domain.scheduler import Item, due, rate, review_root

NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
INTERVAL_DAYS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}


def item(item_id: str, days_overdue: float) -> Item:
    return Item(id=item_id, due_at=NOW - timedelta(days=days_overdue))


@pytest.mark.parametrize(
    ("box", "rating", "new_box"),
    [
        *[(box, "easy", min(box + 1, 5)) for box in range(1, 6)],
        *[(box, "challenging", box) for box in range(1, 6)],
        *[(box, "unfamiliar", 1) for box in range(1, 6)],
    ],
)
def test_rate_moves_box_and_sets_due_at_from_new_box_interval(box, rating, new_box):
    assert rate(box, rating, NOW) == (
        new_box,
        NOW + timedelta(days=INTERVAL_DAYS[new_box]),
    )


def test_easy_in_box_5_stays_in_box_5_for_30_days():
    assert rate(5, "easy", NOW) == (5, NOW + timedelta(days=30))


def test_due_includes_item_due_exactly_now_and_excludes_future_items():
    on_time, future = item("shape:major:1", 0), item("shape:minor:1", -1)
    assert due([future, on_time], NOW, 10) == [on_time]


def test_due_orders_most_overdue_first():
    items = [
        item("shape:major:1", 1),
        item("shape:minor:1", 5),
        item("shape:diminished:1", 3),
    ]
    assert [i.id for i in due(items, NOW, 10)] == [
        "shape:minor:1",
        "shape:diminished:1",
        "shape:major:1",
    ]


def test_due_returns_at_most_limit_items():
    items = [
        item("shape:major:1", 5),
        item("shape:minor:1", 4),
        item("shape:major:2", 3),
    ]
    assert [i.id for i in due(items, NOW, 2)] == ["shape:major:1", "shape:minor:1"]


def test_due_interleaves_so_consecutive_items_differ_in_quality():
    items = [
        item("shape:minor:1", 5),
        item("shape:minor:2", 4),
        item("shape:major:1", 3),
    ]
    assert [i.id for i in due(items, NOW, 10)] == [
        "shape:minor:1",
        "shape:major:1",
        "shape:minor:2",
    ]


def test_due_repeats_quality_when_interleaving_is_impossible():
    items = [
        item("shape:minor:3", 3),
        item("shape:minor:1", 5),
        item("shape:minor:2", 4),
    ]
    assert [i.id for i in due(items, NOW, 10)] == [
        "shape:minor:1",
        "shape:minor:2",
        "shape:minor:3",
    ]


def test_due_defers_most_overdue_item_when_that_avoids_a_repeat():
    items = [
        item("shape:major:1", 5),
        item("shape:minor:1", 4),
        item("shape:minor:2", 3),
    ]
    assert [i.id for i in due(items, NOW, 10)] == [
        "shape:minor:1",
        "shape:major:1",
        "shape:minor:2",
    ]


def test_due_treats_passages_as_having_no_shared_quality():
    items = [
        item("passage:a", 5),
        item("passage:b", 4),
        item("shape:minor:1", 3),
        item("shape:minor:2", 2),
    ]
    assert [i.id for i in due(items, NOW, 10)] == [
        "passage:a",
        "shape:minor:1",
        "passage:b",
        "shape:minor:2",
    ]


def test_due_allows_consecutive_passages():
    items = [item("passage:a", 5), item("passage:b", 4)]
    assert [i.id for i in due(items, NOW, 10)] == ["passage:a", "passage:b"]


@pytest.mark.parametrize(
    ("reviews", "root"),
    list(
        enumerate(
            ["C", "F", "B♭", "E♭", "A♭", "D♭", "G♭", "B", "E", "A", "D", "G", "C"]
        )
    ),
)
def test_review_root_steps_through_cycle_of_fourths_from_c(reviews, root):
    assert review_root(reviews) == root
