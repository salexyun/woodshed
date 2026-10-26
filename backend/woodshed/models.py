from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    type_annotation_map: ClassVar = {datetime: DateTime(timezone=True)}


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    years_playing: Mapped[int]
    stuck_on: Mapped[str]
    cue: Mapped[str]
    weekly_goal_days: Mapped[int]
    timezone: Mapped[str]
    created_at: Mapped[datetime]


class Item(Base):
    __tablename__ = "item"

    id: Mapped[str] = mapped_column(primary_key=True)
    kind: Mapped[str]
    box: Mapped[int]
    due_at: Mapped[datetime]
    reviews: Mapped[int]
    last_rated_at: Mapped[datetime | None]
    created_at: Mapped[datetime]


class Session(Base):
    __tablename__ = "session"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str]
    length: Mapped[str]
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]


class Rating(Base):
    __tablename__ = "rating"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("session.id"))
    item_id: Mapped[str] = mapped_column(ForeignKey("item.id"))
    value: Mapped[str]
    box_before: Mapped[int]
    box_after: Mapped[int]
    rated_at: Mapped[datetime]
