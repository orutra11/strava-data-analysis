from sqlalchemy import INTEGER, DATE, REAL, BOOLEAN, UUID
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column

import datetime
import uuid


class Base(DeclarativeBase):
    type_annotation_map = {
        int: INTEGER,
        float: REAL,
        bool: BOOLEAN,
        datetime.date: DATE,
        uuid.UUID: UUID,
    }


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(primary_key=True)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athletes.id"))
    name: Mapped[str]
    search_for: Mapped[str]
    valid: Mapped[bool]
    date: Mapped[datetime.datetime]
    distance: Mapped[float]
    elapsed_str: Mapped[str]
    elapsed_seconds: Mapped[int]
    pace_str: Mapped[str]
    pace_seconds: Mapped[int]
    pace_units: Mapped[str]


class Split(Base):
    __tablename__ = "splits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.id"))
    index: Mapped[int]
    pace_str: Mapped[str]
    pace_seconds: Mapped[int]
    pace_units: Mapped[str]
    elevation: Mapped[int]
    elevation_units: Mapped[str]
