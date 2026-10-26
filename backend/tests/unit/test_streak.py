from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from woodshed.domain.streak import Session, practice_days, streak, week_progress

NEW_YORK = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")


def d(day: int) -> date:
    """A date in October 2026; Mon 19 to Sun 25 is ISO week 43."""
    return date(2026, 10, day)


def utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


def test_finished_session_with_a_rating_is_a_practice_day():
    session = Session(finished_at=utc(20, 18), ratings=1)
    assert practice_days([session], NEW_YORK) == {d(20)}


@pytest.mark.parametrize(
    "session",
    [
        Session(finished_at=None, ratings=3),
        Session(finished_at=utc(20, 18), ratings=0),
    ],
    ids=["unfinished", "no_ratings"],
)
def test_session_without_finish_or_rating_is_not_a_practice_day(session):
    assert practice_days([session], NEW_YORK) == set()


def test_sessions_on_the_same_local_day_count_once():
    sessions = [
        Session(finished_at=utc(20, 14), ratings=2),
        Session(finished_at=utc(20, 22), ratings=1),
    ]
    assert practice_days(sessions, NEW_YORK) == {d(20)}


@pytest.mark.parametrize(
    ("finished_at", "tz", "local_day"),
    [
        (utc(21, 3, 30), NEW_YORK, d(20)),  # 23:30 EDT on the 20th
        (utc(20, 14, 30), TOKYO, d(20)),  # 23:30 JST on the 20th
        (utc(20, 15, 30), TOKYO, d(21)),  # 00:30 JST on the 21st
    ],
    ids=["new_york_2330", "tokyo_2330", "tokyo_0030"],
)
def test_practice_day_is_the_local_date_not_the_utc_date(finished_at, tz, local_day):
    session = Session(finished_at=finished_at, ratings=1)
    assert practice_days([session], tz) == {local_day}


@pytest.mark.parametrize(
    ("days", "today", "expected"),
    [
        (set(), d(22), 0),
        ({d(22)}, d(22), 1),
        ({d(20), d(21), d(22)}, d(22), 3),
        ({d(20), d(22)}, d(22), 2),
        ({d(16), d(18), d(20), d(22)}, d(22), 4),
        ({d(19), d(22)}, d(22), 1),
        ({d(15), d(16), d(19), d(21), d(22)}, d(22), 3),
    ],
    ids=[
        "no_days",
        "today_only",
        "three_in_a_row",
        "one_day_gap_continues",
        "repeated_one_day_gaps_continue",
        "two_day_gap_breaks",
        "counts_only_current_run",
    ],
)
def test_streak_counts_practice_days_in_the_current_run(days, today, expected):
    assert streak(days, today) == expected


@pytest.mark.parametrize(
    ("today", "expected"),
    [(d(22), 2), (d(23), 2), (d(24), 2), (d(25), 0)],
    ids=[
        "last_day_today",
        "last_day_yesterday",
        "last_day_day_before",
        "last_day_three_days_ago",
    ],
)
def test_streak_is_current_until_two_full_days_are_missed(today, expected):
    assert streak({d(21), d(22)}, today) == expected


@pytest.mark.parametrize(
    ("days", "today", "expected"),
    [
        (set(), d(21), 0),
        ({d(19), d(21), d(25)}, d(25), 3),
        ({d(18), d(19)}, d(19), 1),
        ({d(19), d(21), d(25)}, d(26), 0),
        ({d(25), d(26)}, d(26), 1),
        (
            {date(2026, 12, 27), date(2026, 12, 29), date(2027, 1, 1)},
            date(2027, 1, 2),
            2,
        ),
    ],
    ids=[
        "no_days",
        "monday_to_sunday",
        "previous_sunday_excluded",
        "monday_resets",
        "monday_counts_only_itself",
        "iso_week_spans_new_year",
    ],
)
def test_week_progress_counts_practice_days_in_the_current_iso_week(
    days, today, expected
):
    assert week_progress(days, today) == expected
