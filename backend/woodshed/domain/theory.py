import re

LETTERS = "CDEFGAB"
NATURALS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SEMITONES = {
    "major": (4, 7),
    "minor": (3, 7),
    "diminished": (3, 6),
    "augmented": (4, 8),
}
SYMBOLS = {"m": "minor", "°": "diminished", "+": "augmented"}
CHORD = re.compile(r"([A-G][♯♭]?)([m°+]?)")
OPEN_STRINGS = (7, 11, 4)  # G, B, E
MAX_SPAN = 4


def pitch_class(note: str) -> int:
    return (NATURALS[note[0]] + note.count("♯") - note.count("♭")) % 12


def spell(letter: str, pitch: int) -> str:
    # Center the offset on 0 so it reads as the fewest sharps or flats.
    offset = (pitch - NATURALS[letter] + 6) % 12 - 6
    return letter + ("♯" * offset if offset > 0 else "♭" * -offset)


def triad(root: str, quality: str) -> tuple[str, str, str]:
    third, fifth = SEMITONES[quality]
    letter, pitch = LETTERS.index(root[0]), pitch_class(root)
    return (
        root,
        spell(LETTERS[(letter + 2) % 7], pitch + third),
        spell(LETTERS[(letter + 4) % 7], pitch + fifth),
    )


def shape(root: str, quality: str, inversion: int) -> tuple[int, int, int]:
    notes = triad(root, quality)
    # Close voicing: the bass note sets the inversion and the other tones stack above it.
    pitches = [pitch_class(notes[(inversion + i) % 3]) for i in range(3)]
    # A voicing whose lowest fret is `base` is never narrower than taking each
    # string's first matching fret at or above `base`, so the first fit is lowest.
    for base in range(12):
        g, b, e = (
            base + (pitch - open_ - base) % 12
            for pitch, open_ in zip(pitches, OPEN_STRINGS)
        )
        if max(g, b, e) - min(g, b, e) <= MAX_SPAN:
            return g, b, e
    raise ValueError(f"no shape for {root} {quality}, inversion {inversion}")


def parse_chord(symbol: str) -> tuple[str, str]:
    if not (match := CHORD.fullmatch(symbol)):
        raise ValueError(f"unknown chord symbol: {symbol!r}")
    root, suffix = match.groups()
    return root, SYMBOLS.get(suffix, "major")
