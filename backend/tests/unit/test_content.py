import dataclasses
import re

import pytest

from woodshed.content import (
    CHALLENGE_CARDS,
    LESSONS,
    PASSAGES,
    Passage,
    passage_item_id,
    shape_item_id,
)
from woodshed.domain.theory import parse_chord, shape

QUALITIES = ["major", "minor", "diminished", "augmented"]
ALL_CHORDS = sorted({chord for passage in PASSAGES for chord in passage.chords})


def test_lessons_run_major_minor_diminished_augmented():
    assert [lesson.quality for lesson in LESSONS] == QUALITIES


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda lesson: lesson.quality)
def test_lesson_explanation_is_at_most_120_words(lesson):
    assert 0 < len(lesson.explanation.split()) <= 120


@pytest.mark.parametrize("quality", QUALITIES)
def test_every_lesson_has_a_passage(quality):
    assert any(passage.lesson == quality for passage in PASSAGES)


def test_passages_match_the_spec_table():
    assert [(p.id, p.title, p.kind, p.chords, p.lesson) for p in PASSAGES] == [
        ("la-bamba", "La Bamba", "song", ("C", "F", "G"), "major"),
        ("twist-and-shout", "Twist and Shout", "song", ("D", "G", "A"), "major"),
        ("sweet-home-alabama", "Sweet Home Alabama", "song", ("D", "C", "G"), "major"),
        ("let-it-be", "Let It Be", "song", ("C", "G", "Am", "F"), "minor"),
        ("stand-by-me", "Stand By Me", "song", ("A", "F♯m", "D", "E"), "minor"),
        (
            "passing-diminished",
            "Passing diminished",
            "exercise",
            ("C", "C♯°", "Dm", "G"),
            "diminished",
        ),
        (
            "augmented-lead-in",
            "Augmented lead-in",
            "exercise",
            ("C", "C+", "F"),
            "augmented",
        ),
    ]


def test_passage_stores_no_lyrics_or_tabs():
    names = {field.name for field in dataclasses.fields(Passage)}
    assert names == {"id", "title", "artist", "kind", "chords", "lesson"}


@pytest.mark.parametrize("passage", PASSAGES, ids=lambda passage: passage.id)
def test_only_songs_have_an_artist(passage):
    assert bool(passage.artist) == (passage.kind == "song")


def test_challenge_pool_has_at_least_6_distinct_cards():
    assert len(CHALLENGE_CARDS) >= 6
    assert len(set(CHALLENGE_CARDS)) == len(CHALLENGE_CARDS)
    assert all(card.strip() for card in CHALLENGE_CARDS)


def test_lesson_and_passage_ids_are_unique():
    assert len({lesson.quality for lesson in LESSONS}) == len(LESSONS)
    assert len({passage.id for passage in PASSAGES}) == len(PASSAGES)


@pytest.mark.parametrize("passage", PASSAGES, ids=lambda passage: passage.id)
def test_passage_lesson_exists(passage):
    assert passage.lesson in QUALITIES


@pytest.mark.parametrize("chord", ALL_CHORDS)
@pytest.mark.parametrize("inversion", [0, 1, 2])
def test_every_passage_chord_has_a_playable_shape(chord, inversion):
    root, quality = parse_chord(chord)
    frets = shape(root, quality, inversion)
    assert max(frets) - min(frets) <= 4


@pytest.mark.parametrize(
    ("quality", "inversion", "item_id"),
    [
        ("major", 0, "shape:major:0"),
        ("minor", 1, "shape:minor:1"),
        ("augmented", 2, "shape:augmented:2"),
    ],
)
def test_shape_item_id(quality, inversion, item_id):
    assert shape_item_id(quality, inversion) == item_id


def test_passage_item_id():
    assert passage_item_id("let-it-be") == "passage:let-it-be"


def test_item_ids_are_unique_and_well_formed():
    ids = [shape_item_id(q, i) for q in QUALITIES for i in range(3)]
    ids += [passage_item_id(p.id) for p in PASSAGES]
    assert len(set(ids)) == 19
    pattern = re.compile(
        r"shape:(major|minor|diminished|augmented):[012]|passage:[a-z0-9-]+"
    )
    assert all(pattern.fullmatch(item_id) for item_id in ids)
