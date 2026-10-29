from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from woodshed.domain.placement import Check


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
