from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

INTERVAL_DAYS = (1, 3, 7, 14, 30)
CYCLE_OF_FOURTHS = ("C", "F", "B♭", "E♭", "A♭", "D♭", "G♭", "B", "E", "A", "D", "G")


class Rating(StrEnum):
    EASY = "easy"
    CHALLENGING = "challenging"
    UNFAMILIAR = "unfamiliar"


@dataclass(frozen=True)
class Item:
    id: str
    due_at: datetime


def rate(box: int, rating: Rating, now: datetime) -> tuple[int, datetime]:
    match rating:
        case Rating.EASY:
            box = min(box + 1, len(INTERVAL_DAYS))
        case Rating.UNFAMILIAR:
            box = 1
    return box, now + timedelta(days=INTERVAL_DAYS[box - 1])


def _quality(item: Item) -> str | None:
    kind, _, rest = item.id.partition(":")
    return rest.partition(":")[0] if kind == "shape" else None


def _arrangeable(rest: list[Item], after: str | None) -> bool:
    # A quality filling more than every other slot of `rest` must repeat; one slot
    # fewer when `rest` follows that quality. Passages have no quality.
    counts = Counter(q for i in rest if (q := _quality(i)) is not None)
    return all(n <= (len(rest) + (q != after)) // 2 for q, n in counts.items())


def due(items: list[Item], now: datetime, limit: int) -> list[Item]:
    overdue = sorted(
        (i for i in items if i.due_at <= now), key=lambda i: (i.due_at, i.id)
    )
    pending = overdue[:limit]
    ordered: list[Item] = []
    while pending:
        last = _quality(ordered[-1]) if ordered else None
        pick = next(
            (
                i
                for i in pending
                if (last is None or _quality(i) != last)
                and _arrangeable([j for j in pending if j is not i], _quality(i))
            ),
            pending[0],
        )
        pending.remove(pick)
        ordered.append(pick)
    return ordered


def review_root(reviews: int) -> str:
    return CYCLE_OF_FOURTHS[reviews % len(CYCLE_OF_FOURTHS)]
