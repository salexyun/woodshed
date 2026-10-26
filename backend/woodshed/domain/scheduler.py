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
    box: int = 1
    last_rated_at: datetime | None = None


def rate(box: int, rating: Rating, now: datetime) -> tuple[int, datetime]:
    match rating:
        case Rating.EASY:
            box = min(box + 1, len(INTERVAL_DAYS))
        case Rating.UNFAMILIAR:
            box = 1
    return box, now + timedelta(days=INTERVAL_DAYS[box - 1])


def quality(item: Item) -> str | None:
    kind, _, rest = item.id.partition(":")
    return rest.partition(":")[0] if kind == "shape" else None


def _repeats(pick: Item, pending: list[Item], last: str | None) -> int:
    """Fewest repeated qualities left in the session if `pick` comes next."""
    q = quality(pick)
    rest = [i for i in pending if i is not pick]
    counts = Counter(k for i in rest if (k := quality(i)) is not None)
    # n items of one quality need n - 1 others between them, one more if the first
    # follows `pick`. Passages have no quality, so they separate anything.
    forced = (2 * n - len(rest) - 1 + (k == q) for k, n in counts.items())
    return (q is not None and q == last) + max([0, *forced])


def due(items: list[Item], now: datetime, limit: int) -> list[Item]:
    overdue = sorted(
        (i for i in items if i.due_at <= now), key=lambda i: (i.due_at, i.id)
    )
    pending = overdue[:limit]
    ordered: list[Item] = []
    while pending:
        last = quality(ordered[-1]) if ordered else None
        # min keeps the most overdue item among equally good picks.
        pick = min(pending, key=lambda i: _repeats(i, pending, last))
        pending.remove(pick)
        ordered.append(pick)
    return ordered


def review_root(reviews: int) -> str:
    return CYCLE_OF_FOURTHS[reviews % len(CYCLE_OF_FOURTHS)]
