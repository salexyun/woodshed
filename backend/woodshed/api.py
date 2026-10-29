from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from woodshed import content, schemas
from woodshed.content import LESSONS, PASSAGES, passage_item_id, shape_item_id
from woodshed.db import get_session
from woodshed.domain.placement import place
from woodshed.domain.scheduler import INTERVAL_DAYS
from woodshed.domain.theory import shape
from woodshed.models import Item, Profile


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


def _lesson(lesson: content.Lesson) -> schemas.Lesson:
    return schemas.Lesson(
        quality=lesson.quality,
        explanation=lesson.explanation,
        shapes=[shape("C", lesson.quality, inversion) for inversion in range(3)],
        passages=[p.id for p in PASSAGES if p.lesson == lesson.quality],
    )


@router.get("/lessons")
def list_lessons() -> list[schemas.Lesson]:
    return [_lesson(lesson) for lesson in LESSONS]


@router.get("/lessons/{quality}")
def get_lesson(quality: str) -> schemas.Lesson:
    if lesson := next((x for x in LESSONS if x.quality == quality), None):
        return _lesson(lesson)
    raise HTTPException(404, "unknown lesson")


def _completed_lessons(db: Session) -> set[str]:
    # A lesson is completed when its 3 shape items exist (§8).
    shapes = set(db.scalars(select(Item.id).where(Item.kind == "shape")))
    return {
        lesson.quality
        for lesson in LESSONS
        if all(shape_item_id(lesson.quality, i) in shapes for i in range(3))
    }


def _passage(passage: content.Passage, completed: set[str]) -> schemas.Passage:
    return schemas.Passage(**asdict(passage), unlocked=passage.lesson in completed)


@router.get("/passages")
def list_passages(db: Db) -> list[schemas.Passage]:
    completed = _completed_lessons(db)
    return [_passage(passage, completed) for passage in PASSAGES]


@router.get("/passages/{id}")
def get_passage(id: str, db: Db) -> schemas.Passage:
    if passage := next((p for p in PASSAGES if p.id == id), None):
        return _passage(passage, _completed_lessons(db))
    raise HTTPException(404, "unknown passage")
