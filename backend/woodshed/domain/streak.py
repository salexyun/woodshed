from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Session:
    finished_at: datetime | None
    ratings: int


def practice_days(sessions: Iterable[Session], tz: ZoneInfo) -> set[date]:
    return {
        s.finished_at.astimezone(tz).date()
        for s in sessions
        if s.finished_at and s.ratings
    }


def streak(days: Iterable[date], today: date) -> int:
    # A run survives one missed day, so consecutive practice days may be 2 apart.
    count, last = 0, today
    for day in sorted(days, reverse=True):
        if (last - day).days > 2:
            break
        count, last = count + 1, day
    return count


def week_progress(days: Iterable[date], today: date) -> int:
    week = today.isocalendar()[:2]
    return sum(day.isocalendar()[:2] == week for day in days)
