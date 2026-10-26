from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Lesson:
    quality: str
    explanation: str


# Songs store only title, artist and chords: no lyrics or tabs, for copyright.
@dataclass(frozen=True)
class Passage:
    id: str
    title: str
    artist: str | None
    kind: Literal["song", "exercise"]
    chords: tuple[str, ...]
    lesson: str


LESSONS = (
    Lesson(
        "major",
        "A major triad is a root, a major 3rd (4 frets up) and a perfect 5th "
        "(7 frets up): 1 3 5. It sounds bright and settled. On the G-B-E strings "
        "there are 3 shapes, named by the note on the G string: root position "
        "(root lowest), 1st inversion (3rd lowest) and 2nd inversion (5th "
        "lowest). All three hold the same notes and follow each other up the "
        "neck. In C: 5-5-3, 9-8-8, then 0-1-0 (or 12-13-12). Slide any shape "
        "to change key.",
    ),
    Lesson(
        "minor",
        "A minor triad lowers the major 3rd by one fret: 1 ♭3 5. The root and "
        "5th stay put. It sounds darker and sadder than major. To find a minor "
        "shape, take the major shape and lower the string holding the 3rd: the "
        "B string in root position, the G string in 1st inversion and the E "
        "string in 2nd inversion. In C: 5-4-3, 8-8-8, 12-13-11.",
    ),
    Lesson(
        "diminished",
        "A diminished triad is minor with the 5th lowered by one fret: 1 ♭3 ♭5, "
        "two minor 3rds stacked. It sounds tense and unstable, and wants to "
        "resolve, usually up a half step: C♯° leads to Dm. To find a shape, take "
        "the minor shape and lower the string holding the 5th: the E string in "
        "root position, the B string in 1st inversion and the G string in 2nd "
        "inversion. In C: 5-4-2, 8-7-8, 11-13-11.",
    ),
    Lesson(
        "augmented",
        "An augmented triad is major with the 5th raised by one fret: 1 3 ♯5, "
        "two major 3rds stacked. It sounds restless and unresolved, and pulls "
        "forward: in C C+ F the raised 5th climbs into the next chord. It's "
        "symmetric: every note is 4 frets from the next, so all 3 inversions "
        "are the same shape moved 4 frets. In C: 5-5-4, 9-9-8, 13-13-12. That "
        "one shape also plays E+ and G♯+.",
    ),
)

PASSAGES = (
    Passage("la-bamba", "La Bamba", "Ritchie Valens", "song", ("C", "F", "G"), "major"),
    Passage(
        "twist-and-shout",
        "Twist and Shout",
        "The Beatles",
        "song",
        ("D", "G", "A"),
        "major",
    ),
    Passage(
        "sweet-home-alabama",
        "Sweet Home Alabama",
        "Lynyrd Skynyrd",
        "song",
        ("D", "C", "G"),
        "major",
    ),
    Passage(
        "let-it-be", "Let It Be", "The Beatles", "song", ("C", "G", "Am", "F"), "minor"
    ),
    Passage(
        "stand-by-me",
        "Stand By Me",
        "Ben E. King",
        "song",
        ("A", "F♯m", "D", "E"),
        "minor",
    ),
    Passage(
        "passing-diminished",
        "Passing diminished",
        None,
        "exercise",
        ("C", "C♯°", "Dm", "G"),
        "diminished",
    ),
    Passage(
        "augmented-lead-in",
        "Augmented lead-in",
        None,
        "exercise",
        ("C", "C+", "F"),
        "augmented",
    ),
)

CHALLENGE_CARDS = (
    "Use only the nearest shape: no jumps.",
    "Same chords, reggae offbeat strum.",
    "Play it up an octave.",
    "Improvise a 4-bar riff using only these shapes.",
    "Play it as quietly as you can, then as loudly, with every note clear.",
    "Pick each string on its own, low to high, instead of strumming.",
    "Change chord on every beat instead of every bar.",
    "Play each chord in a different inversion than last time through.",
)


def shape_item_id(quality: str, inversion: int) -> str:
    return f"shape:{quality}:{inversion}"


def passage_item_id(passage_id: str) -> str:
    return f"passage:{passage_id}"
