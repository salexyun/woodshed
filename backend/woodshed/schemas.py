from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from woodshed.domain.placement import Check
from woodshed.domain.planner import Action, StepKind
from woodshed.domain.scheduler import Rating


def _known_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"unknown timezone {name!r}") from None
    return name


Quality = Literal["major", "minor", "diminished", "augmented"]
StuckOn = Literal["same_material", "what_to_practice", "technique", "theory"]
WeeklyGoal = Annotated[int, Field(ge=1, le=7)]
Timezone = Annotated[str, AfterValidator(_known_timezone)]
Cue = Annotated[str, Field(min_length=1)]
Length = Literal["25", "open"]


class Profile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    years_playing: Annotated[int, Field(ge=0)]
    stuck_on: StuckOn
    cue: Cue
    weekly_goal_days: WeeklyGoal = 4
    timezone: Timezone


class Onboarding(Profile):
    claimed_qualities: list[Quality]
    checks: dict[Quality, Check]


class ProfileUpdate(BaseModel):
    cue: Cue | None = None
    weekly_goal_days: WeeklyGoal | None = None


class Lesson(BaseModel):
    quality: Quality
    explanation: str
    shapes: list[tuple[int, int, int]]
    passages: list[str]


class Passage(BaseModel):
    id: str
    title: str
    artist: str | None
    kind: Literal["song", "exercise"]
    chords: list[str]
    shapes: list[tuple[int, int, int]]
    lesson: Quality
    unlocked: bool


class Home(BaseModel):
    streak: int
    week_days: int
    weekly_goal_days: int
    due_count: int
    next_lesson: Quality | None
    cue: str


class ProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    box: int
    due_at: datetime


class NewSession(BaseModel):
    action: Action
    length: Length
    passage: str | None = None


class Step(BaseModel):
    kind: StepKind
    id: str
    card: str | None = None
    root: str | None = None


class Plan(BaseModel):
    id: int
    steps: list[Step]


class NewRating(BaseModel):
    item_id: str
    rating: Rating
    # The item's index among the plan's rated items; a retry sends the same one.
    position: int | None = None


class Summary(BaseModel):
    duration_seconds: int
    items_rated: int
    next_due: list[ProgressItem]
    streak: int


class PastSession(BaseModel):
    id: int
    action: Action
    length: Length
    started_at: datetime
    items_rated: int
    duration_seconds: int | None


class SessionDetail(BaseModel):
    id: int
    action: Action
    length: Length
    started_at: datetime
    finished_at: datetime | None
    steps: list[Step]
    rated: list[str]
