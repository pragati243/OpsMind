"""SQLAlchemy declarative models for Keystone's operational data."""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return a timezone-aware timestamp suitable for ORM defaults."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class shared by all Keystone ORM models."""


class TimestampedModel(Base):
    """Abstract model providing a UTC creation timestamp."""

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
