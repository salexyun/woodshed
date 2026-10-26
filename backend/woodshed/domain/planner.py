from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from woodshed.domain.scheduler import Item, due, quality
from woodshed.domain.theory import SEMITONES

Action = Literal["today", "continue", "test_me", "pick_a_song"]
LESSON_ORDER = tuple(SEMITONES)
TODAY_REVIEWS = 3
TEST_ME_ITEMS = 10


@dataclass(frozen=True)
class Step:
    kind: Literal["review", "lesson", "passage", "challenge", "theory"]
    id: str


def _passage(passage_id: str) -> list[Step]:
    return [Step("passage", passage_id), Step("challenge", passage_id)]


def _test_me(items: list[Item], last_session: list[str], now: datetime) -> list[Step]:
    by_id = {i.id: i for i in items}
    picked = {i.id: i for i in due(items, now, TEST_ME_ITEMS)}
    picked |= {i: by_id[i] for i in last_session if i in by_id}
    picked |= {i.id: i for i in sorted(items, key=lambda i: (i.box, i.due_at, i.id))}
    chosen = list(picked.values())[:TEST_ME_ITEMS]
    qualities = dict.fromkeys(q for i in chosen if (q := quality(i)) is not None)
    return [Step("review", i.id) for i in chosen] + [
        Step("theory", q) for q in qualities
    ]


def plan(
    action: Action,
    items: list[Item],
    completed_lessons: set[str],
    last_session: list[str],
    now: datetime,
    passage: str | None = None,
) -> list[Step]:
    lesson = next((q for q in LESSON_ORDER if q not in completed_lessons), None)
    match action:
        case "today":
            reviews = [Step("review", i.id) for i in due(items, now, TODAY_REVIEWS)]
            if lesson:
                return [*reviews, Step("lesson", lesson)]
            listed = {s.id for s in reviews}
            passages = [
                i for i in items if i.id.startswith("passage:") and i.id not in listed
            ]
            # Never-rated passages count as the least recently practiced.
            stalest = min(
                passages,
                key=lambda i: (
                    i.last_rated_at is not None,
                    i.last_rated_at or now,
                    i.id,
                ),
                default=None,
            )
            return reviews + (_passage(stalest.id) if stalest else [])
        case "continue":
            return [Step("lesson", lesson)] if lesson else []
        case "test_me":
            return _test_me(items, last_session, now)
        case "pick_a_song":
            if passage is None or not passage.startswith("passage:"):
                raise ValueError(f"{passage!r} is not a passage")
            # A passage unlocks when its item is created, so no item means locked.
            if passage not in {i.id for i in items}:
                raise ValueError(f"passage {passage!r} is locked")
            return _passage(passage)
    raise ValueError(f"unknown action {action!r}")
