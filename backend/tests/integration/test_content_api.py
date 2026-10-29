from datetime import UTC, datetime

import pytest

from woodshed.content import LESSONS, PASSAGES
from woodshed.models import Item

NOW = datetime(2026, 10, 26, 18, 30, tzinfo=UTC)
QUALITIES = ["major", "minor", "diminished", "augmented"]

# Shapes in C, root position then 1st and 2nd inversion, as (G, B, E) frets.
SHAPES_IN_C = {
    "major": [[5, 5, 3], [9, 8, 8], [0, 1, 0]],
    "minor": [[5, 4, 3], [8, 8, 8], [12, 13, 11]],
    "diminished": [[5, 4, 2], [8, 7, 8], [11, 13, 11]],
    "augmented": [[5, 5, 4], [9, 9, 8], [1, 1, 0]],
}

LESSON_PASSAGES = {
    "major": ["la-bamba", "twist-and-shout", "sweet-home-alabama"],
    "minor": ["let-it-be", "stand-by-me"],
    "diminished": ["passing-diminished"],
    "augmented": ["augmented-lead-in"],
}

LET_IT_BE = {
    "id": "let-it-be",
    "title": "Let It Be",
    "artist": "The Beatles",
    "kind": "song",
    "chords": ["C", "G", "Am", "F"],
    "lesson": "minor",
}


def explanation(quality: str) -> str:
    return next(lesson.explanation for lesson in LESSONS if lesson.quality == quality)


def add_shapes(db, quality: str, inversions=range(3)) -> None:
    db.add_all(
        Item(
            id=f"shape:{quality}:{i}",
            kind="shape",
            box=1,
            due_at=NOW,
            reviews=0,
            created_at=NOW,
        )
        for i in inversions
    )
    db.commit()


def unlocked(client) -> set[str]:
    return {p["id"] for p in client.get("/api/passages").json() if p["unlocked"]}


def test_lessons_run_from_major_to_augmented(client, db):
    response = client.get("/api/lessons")
    assert response.status_code == 200
    assert [lesson["quality"] for lesson in response.json()] == QUALITIES


@pytest.mark.parametrize("quality", QUALITIES)
def test_lesson_has_explanation_shapes_in_c_and_passages(client, db, quality):
    response = client.get(f"/api/lessons/{quality}")
    assert response.status_code == 200
    lesson = response.json()
    assert lesson["quality"] == quality
    assert lesson["explanation"] == explanation(quality)
    assert lesson["shapes"] == SHAPES_IN_C[quality]
    assert lesson["passages"] == LESSON_PASSAGES[quality]


def test_lessons_list_matches_each_lesson(client, db):
    lessons = client.get("/api/lessons").json()
    assert lessons == [client.get(f"/api/lessons/{q}").json() for q in QUALITIES]


def test_passages_list_every_passage_locked_before_any_lesson(client, db):
    response = client.get("/api/passages")
    assert response.status_code == 200
    passages = response.json()
    assert [p["id"] for p in passages] == [p.id for p in PASSAGES]
    assert passages[3] == LET_IT_BE | {"unlocked": False}
    assert not any(p["unlocked"] for p in passages)


def test_exercise_has_no_artist(client, db):
    passage = client.get("/api/passages/passing-diminished").json()
    assert (passage["kind"], passage["artist"]) == ("exercise", None)
    assert passage["chords"] == ["C", "C♯°", "Dm", "G"]


def test_completed_lesson_unlocks_only_its_passages(client, db):
    add_shapes(db, "minor")
    assert unlocked(client) == {"let-it-be", "stand-by-me"}


def test_lesson_with_two_of_three_shapes_keeps_its_passages_locked(client, db):
    add_shapes(db, "minor", inversions=[0, 1])
    assert unlocked(client) == set()


@pytest.mark.parametrize("completed", [False, True])
def test_passage_returns_its_content_and_unlock_state(client, db, completed):
    if completed:
        add_shapes(db, "minor")
    response = client.get("/api/passages/let-it-be")
    assert response.status_code == 200
    assert response.json() == LET_IT_BE | {"unlocked": completed}


def test_unknown_passage_is_404(client, db):
    assert client.get("/api/passages/wonderwall").status_code == 404
