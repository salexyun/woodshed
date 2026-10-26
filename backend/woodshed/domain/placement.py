from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

LESSON_ORDER = ("major", "minor", "diminished", "augmented")
PLACED_BOX = 2


class Playing(StrEnum):
    GOT_IT = "got_it"
    CLOSE = "close"
    NO_IDEA = "no_idea"


@dataclass(frozen=True)
class Check:
    playing: Playing
    theory_correct: bool


@dataclass(frozen=True)
class Placement:
    known: tuple[str, ...]
    lesson: str | None
    items: dict[str, int]


def place(claimed_qualities: Iterable[str], checks: Mapping[str, Check]) -> Placement:
    claimed = set(claimed_qualities)
    known = tuple(
        q
        for q in LESSON_ORDER
        if q in claimed
        and (c := checks.get(q))
        and c.playing == Playing.GOT_IT
        and c.theory_correct
    )
    return Placement(
        known=known,
        lesson=next((q for q in LESSON_ORDER if q not in known), None),
        items={f"shape:{q}:{i}": PLACED_BOX for q in known for i in range(3)},
    )
