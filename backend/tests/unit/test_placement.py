import pytest

from woodshed.domain.placement import LESSON_ORDER, Check, Placement, place

QUALITIES = ("major", "minor", "diminished", "augmented")
PASS = Check(playing="got_it", theory_correct=True)


def shape_items(*qualities: str) -> dict[str, int]:
    return {f"shape:{q}:{inversion}": 2 for q in qualities for inversion in range(3)}


def test_lesson_order_is_most_to_least_common():
    assert LESSON_ORDER == QUALITIES


def test_no_qualities_claimed_starts_at_major_with_no_items():
    assert place([], {}) == Placement(known=(), lesson="major", items={})


def test_all_checks_passed_knows_every_quality_and_no_lesson_remains():
    assert place(QUALITIES, dict.fromkeys(QUALITIES, PASS)) == Placement(
        known=QUALITIES, lesson=None, items=shape_items(*QUALITIES)
    )


@pytest.mark.parametrize(
    "check",
    [
        Check(playing="got_it", theory_correct=False),
        Check(playing="close", theory_correct=True),
        Check(playing="no_idea", theory_correct=True),
        Check(playing="close", theory_correct=False),
    ],
)
def test_quality_is_known_only_when_got_it_and_theory_correct(check):
    assert place(["major"], {"major": check}) == Placement(
        known=(), lesson="major", items={}
    )


def test_mixed_results_start_at_first_quality_in_lesson_order_not_known():
    checks = {
        "major": PASS,
        "minor": Check(playing="got_it", theory_correct=False),
        "diminished": Check(playing="close", theory_correct=True),
        "augmented": PASS,
    }
    assert place(QUALITIES, checks) == Placement(
        known=("major", "augmented"),
        lesson="minor",
        items=shape_items("major", "augmented"),
    )


def test_known_qualities_follow_lesson_order_whatever_the_claim_order():
    claimed = ["augmented", "minor", "major"]
    assert place(claimed, dict.fromkeys(claimed, PASS)).known == (
        "major",
        "minor",
        "augmented",
    )


@pytest.mark.parametrize("quality", QUALITIES)
def test_known_quality_yields_its_3_shape_items_in_box_2(quality):
    assert place([quality], {quality: PASS}).items == {
        f"shape:{quality}:0": 2,
        f"shape:{quality}:1": 2,
        f"shape:{quality}:2": 2,
    }
