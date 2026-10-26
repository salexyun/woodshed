import pytest

from woodshed.domain.theory import parse_chord, shape, triad

QUALITIES = ["major", "minor", "diminished", "augmented"]
ROOTS = ["C", "F", "B♭", "E♭", "A♭", "D♭", "G♭", "B", "E", "A", "D", "G"]

# Independent of the implementation, so the tests check it rather than mirror it.
PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
OPEN_STRINGS = (7, 11, 4)  # G, B, E


def pitch_class(note: str) -> int:
    return (PITCH[note[0]] + note.count("♯") - note.count("♭")) % 12


@pytest.mark.parametrize(
    ("root", "quality", "notes"),
    [
        ("D", "major", ("D", "F♯", "A")),
        ("C", "diminished", ("C", "E♭", "G♭")),
        ("C", "major", ("C", "E", "G")),
        ("C", "minor", ("C", "E♭", "G")),
        ("C", "augmented", ("C", "E", "G♯")),
        ("F♯", "minor", ("F♯", "A", "C♯")),
        ("B♭", "major", ("B♭", "D", "F")),
        ("C♯", "diminished", ("C♯", "E", "G")),
        ("E♭", "augmented", ("E♭", "G", "B")),
    ],
)
def test_triad_spells_root_third_fifth(root, quality, notes):
    assert triad(root, quality) == notes


@pytest.mark.parametrize(
    ("quality", "inversion", "frets"),
    [
        ("major", 0, (5, 5, 3)),
        ("major", 1, (9, 8, 8)),
        ("major", 2, (0, 1, 0)),
        ("minor", 0, (5, 4, 3)),
        ("minor", 1, (8, 8, 8)),
        ("minor", 2, (12, 13, 11)),
        ("augmented", 0, (5, 5, 4)),
        ("augmented", 1, (9, 9, 8)),
        ("augmented", 2, (1, 1, 0)),
    ],
)
def test_c_shape_matches_expected_frets(quality, inversion, frets):
    assert shape("C", quality, inversion) == frets


@pytest.mark.parametrize("inversion", range(3))
@pytest.mark.parametrize("quality", QUALITIES)
@pytest.mark.parametrize("root", ROOTS)
def test_shape_is_lowest_playable_voicing_of_its_triad(root, quality, inversion):
    assert_plays_triad(root, quality, inversion)


def assert_plays_triad(root, quality, inversion):
    frets = shape(root, quality, inversion)
    notes = triad(root, quality)
    played = [(open_ + fret) % 12 for open_, fret in zip(OPEN_STRINGS, frets)]

    assert len(frets) == 3
    assert min(frets) >= 0
    assert max(frets) - min(frets) <= 4
    assert min(frets) < 12  # otherwise the same shape fits an octave lower
    assert sorted(played) == sorted(pitch_class(n) for n in notes)
    # The bass note sets the inversion.
    assert played[0] == pitch_class(notes[inversion])


@pytest.mark.parametrize(
    ("symbol", "parsed"),
    [
        ("F♯m", ("F♯", "minor")),
        ("C", ("C", "major")),
        ("B♭", ("B♭", "major")),
        ("Am", ("A", "minor")),
        ("C♯°", ("C♯", "diminished")),
        ("C+", ("C", "augmented")),
    ],
)
def test_parse_chord_splits_root_and_quality(symbol, parsed):
    assert parse_chord(symbol) == parsed


@pytest.mark.parametrize("symbol", ["C7", "Cm+", "C°m", "H", ""])
def test_parse_chord_rejects_unknown_symbols(symbol):
    with pytest.raises(ValueError):
        parse_chord(symbol)


# The chords in the §4 passage table. Checking content.PASSAGES itself belongs to #6.
@pytest.mark.parametrize("inversion", range(3))
@pytest.mark.parametrize(
    "symbol", ["C", "F", "G", "D", "A", "E", "Am", "F♯m", "Dm", "C♯°", "C+"]
)
def test_passage_chord_produces_valid_shape(symbol, inversion):
    assert_plays_triad(*parse_chord(symbol), inversion)
