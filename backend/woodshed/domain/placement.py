from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from woodshed.domain.theory import SEMITONES

# SEMITONES lists qualities most to least common, which is the lesson order.
LESSON_ORDER = tuple(SEMITONES)
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


PASSED = Check(Playing.GOT_IT, theory_correct=True)


def place(claimed_qualities: Iterable[str], checks: Mapping[str, Check]) -> Placement:
    claimed = set(claimed_qualities)
    known = tuple(q for q in LESSON_ORDER if q in claimed and checks.get(q) == PASSED)
    return Placement(
        known=known,
        lesson=next((q for q in LESSON_ORDER if q not in known), None),
        items={f"shape:{q}:{i}": PLACED_BOX for q in known for i in range(3)},
    )
