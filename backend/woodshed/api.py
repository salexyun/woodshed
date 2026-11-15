import random
from collections.abc import Collection
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from woodshed import content, schemas
from woodshed.content import (
    CHALLENGE_CARDS,
    LESSONS,
    PASSAGES,
    passage_item_id,
    shape_item_id,
)
from woodshed.db import get_session
from woodshed.domain import planner, scheduler, streak
from woodshed.domain.placement import LESSON_ORDER, place
from woodshed.domain.scheduler import INTERVAL_DAYS
from woodshed.domain.theory import shape
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


def _unlock_passages(lessons: Collection[str], now: datetime) -> list[Item]:
    return [
        _new_item(passage_item_id(p.id), 1, now, now)
        for p in PASSAGES
        if p.lesson in lessons
    ]


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
    # Placing a quality counts as completing its lesson.
    db.add_all(_unlock_passages(placement.known, now))
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


SHAPE_LESSONS = {
    shape_item_id(lesson.quality, i): lesson.quality
    for lesson in LESSONS
    for i in range(3)
}


def _completed_lessons(db: Session) -> set[str]:
    # A lesson is completed when its 3 shape items exist (§8).
    shapes = set(db.scalars(select(Item.id).where(Item.kind == "shape")))
    missing = {lesson for id, lesson in SHAPE_LESSONS.items() if id not in shapes}
    return set(SHAPE_LESSONS.values()) - missing


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


def _practice_days(db: Session, tz: ZoneInfo) -> set[date]:
    sessions = db.execute(
        select(PracticeSession.finished_at, func.count(Rating.id))
        .outerjoin(Rating)
        .group_by(PracticeSession.id)
    )
    return streak.practice_days((streak.Session(*s) for s in sessions), tz)


@router.get("/home", response_model=schemas.Home)
def home(db: Db, now: Now) -> schemas.Home:
    profile = _profile(db)
    tz = ZoneInfo(profile.timezone)
    today = now.astimezone(tz).date()
    days = _practice_days(db, tz)
    items = [scheduler.Item(i.id, i.due_at) for i in db.scalars(select(Item))]
    completed = _completed_lessons(db)
    return schemas.Home(
        streak=streak.streak(days, today),
        week_days=streak.week_progress(days, today),
        weekly_goal_days=profile.weekly_goal_days,
        due_count=len(scheduler.due(items, now, limit=len(items))),
        next_lesson=next((q for q in LESSON_ORDER if q not in completed), None),
        cue=profile.cue,
    )


@router.get("/progress", response_model=list[schemas.ProgressItem])
def progress(db: Db) -> list[Item]:
    return list(db.scalars(select(Item).order_by(Item.id)))


def _step(step: planner.Step, reviews: dict[str, int]) -> schemas.Step:
    # Only shape reviews name a root (§5.1); a passage is played as written.
    names_root = step.kind == "review" and step.id in SHAPE_LESSONS
    # Each lesson and each passage (via its challenge step) gets a card (§4).
    has_card = step.kind in ("lesson", "challenge")
    return schemas.Step(
        kind=step.kind,
        id=step.id,
        card=random.choice(CHALLENGE_CARDS) if has_card else None,
        root=scheduler.review_root(reviews[step.id]) if names_root else None,
    )


@router.post("/sessions", status_code=201)
def start_session(body: schemas.NewSession, db: Db, now: Now) -> schemas.Plan:
    _profile(db)
    rows = list(db.scalars(select(Item)))
    # An abandoned session has no ratings, so it can't be the last one (§5.4).
    last = select(func.max(Rating.session_id)).scalar_subquery()
    last_session = db.scalars(
        select(Rating.item_id).where(Rating.session_id == last).order_by(Rating.id)
    )
    try:
        steps = planner.plan(
            body.action,
            [scheduler.Item(i.id, i.due_at, i.box, i.last_rated_at) for i in rows],
            _completed_lessons(db),
            list(last_session),
            now,
            passage_item_id(body.passage) if body.passage else None,
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    session = PracticeSession(action=body.action, length=body.length, started_at=now)
    db.add(session)
    db.commit()
    reviews = {i.id: i.reviews for i in rows}
    return schemas.Plan(id=session.id, steps=[_step(s, reviews) for s in steps])


def _open_session(db: Session, id: int) -> PracticeSession:
    session = db.get(PracticeSession, id)
    if session is None:
        raise HTTPException(404, "unknown session")
    if session.finished_at:
        raise HTTPException(409, "session is finished")
    return session


@router.post("/sessions/{id}/ratings", response_model=schemas.ProgressItem)
def rate(id: int, body: schemas.NewRating, db: Db, now: Now) -> Item:
    session = _open_session(db, id)
    item = db.get(Item, body.item_id)
    if item is None:
        # Lesson shapes are created by their first rating (§5.5).
        if (lesson := SHAPE_LESSONS.get(body.item_id)) is None:
            raise HTTPException(404, "unknown item")
        item = _new_item(body.item_id, 1, now, now)
        db.add(item)
        if lesson in _completed_lessons(db):
            db.add_all(_unlock_passages({lesson}, now))
    box_before = item.box
    item.box, item.due_at = scheduler.rate(item.box, body.rating, now)
    item.reviews += 1
    item.last_rated_at = now
    db.add(
        Rating(
            session_id=session.id,
            item_id=item.id,
            value=body.rating,
            box_before=box_before,
            box_after=item.box,
            rated_at=now,
        )
    )
    db.commit()
    return item


def _duration(session: PracticeSession) -> int | None:
    if session.finished_at is None:
        return None
    return int((session.finished_at - session.started_at).total_seconds())


@router.post("/sessions/{id}/finish")
def finish_session(id: int, db: Db, now: Now) -> schemas.Summary:
    profile = _profile(db)
    session = _open_session(db, id)
    session.finished_at = now
    rated = list(
        db.scalars(
            select(Item)
            .where(Item.id.in_(select(Rating.item_id).where(Rating.session_id == id)))
            .order_by(Item.due_at, Item.id)
        )
    )
    tz = ZoneInfo(profile.timezone)
    summary = schemas.Summary(
        duration_seconds=_duration(session),
        items_rated=len(rated),
        next_due=rated,
        streak=streak.streak(_practice_days(db, tz), now.astimezone(tz).date()),
    )
    db.commit()
    return summary


@router.get("/sessions")
def list_sessions(db: Db) -> list[schemas.PastSession]:
    rows = db.execute(
        select(PracticeSession, func.count(distinct(Rating.item_id)))
        .outerjoin(Rating)
        .group_by(PracticeSession.id)
        .order_by(PracticeSession.id.desc())
    )
    return [
        schemas.PastSession(
            id=s.id,
            action=s.action,
            length=s.length,
            started_at=s.started_at,
            items_rated=items_rated,
            duration_seconds=_duration(s),
        )
        for s, items_rated in rows
    ]
