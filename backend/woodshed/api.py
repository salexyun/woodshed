from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from woodshed import schemas
from woodshed.content import PASSAGES, passage_item_id
from woodshed.db import get_session
from woodshed.domain import scheduler, streak
from woodshed.domain.placement import LESSON_ORDER, place
from woodshed.domain.scheduler import INTERVAL_DAYS
from woodshed.models import Item, PracticeSession, Profile, Rating


def get_now() -> datetime:
    return datetime.now(UTC)


Db = Annotated[Session, Depends(get_session)]
Now = Annotated[datetime, Depends(get_now)]

router = APIRouter(prefix="/api")


def _profile(db: Session) -> Profile:
    if profile := db.get(Profile, 1):
        return profile
    raise HTTPException(404, "not onboarded")


def _new_item(id: str, box: int, due_at: datetime, now: datetime) -> Item:
    kind = id.partition(":")[0]
    return Item(id=id, kind=kind, box=box, due_at=due_at, reviews=0, created_at=now)


@router.get("/profile", response_model=schemas.Profile)
def get_profile(db: Db) -> Profile:
    return _profile(db)


@router.post("/onboarding", status_code=201, response_model=schemas.Profile)
def onboard(answers: schemas.Onboarding, db: Db, now: Now) -> Profile:
    if db.get(Profile, 1):
        raise HTTPException(409, "already onboarded")
    placement = place(answers.claimed_qualities, answers.checks)
    profile = Profile(
        id=1,
        created_at=now,
        **answers.model_dump(exclude={"claimed_qualities", "checks"}),
    )
    db.add(profile)
    db.add_all(
        _new_item(id, box, now + timedelta(days=INTERVAL_DAYS[box - 1]), now)
        for id, box in placement.items.items()
    )
    # Placing a quality counts as completing its lesson, which unlocks its passages.
    db.add_all(
        _new_item(passage_item_id(p.id), 1, now, now)
        for p in PASSAGES
        if p.lesson in placement.known
    )
    db.commit()
    return profile


@router.patch("/profile", response_model=schemas.Profile)
def update_profile(changes: schemas.ProfileUpdate, db: Db) -> Profile:
    profile = _profile(db)
    for field, value in changes.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    db.commit()
    return profile


@router.get("/home", response_model=schemas.Home)
def home(db: Db, now: Now) -> schemas.Home:
    profile = _profile(db)
    tz = ZoneInfo(profile.timezone)
    today = now.astimezone(tz).date()
    sessions = db.execute(
        select(PracticeSession.finished_at, func.count(Rating.id))
        .outerjoin(Rating)
        .group_by(PracticeSession.id)
    )
    days = streak.practice_days((streak.Session(*s) for s in sessions), tz)
    items = [scheduler.Item(i.id, i.due_at) for i in db.scalars(select(Item))]
    shapes = Counter(scheduler.quality(i) for i in items)
    return schemas.Home(
        streak=streak.streak(days, today),
        week_days=streak.week_progress(days, today),
        weekly_goal_days=profile.weekly_goal_days,
        due_count=len(scheduler.due(items, now, limit=len(items))),
        next_lesson=next((q for q in LESSON_ORDER if shapes[q] < 3), None),
        cue=profile.cue,
    )


@router.get("/progress", response_model=list[schemas.ProgressItem])
def progress(db: Db) -> list[Item]:
    return list(db.scalars(select(Item).order_by(Item.id)))
