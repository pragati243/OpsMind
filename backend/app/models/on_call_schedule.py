"""On-call schedule persistence model."""

from datetime import date

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class OnCallSchedule(Base):
    """Store the engineer assigned to each service for a calendar week."""

    __tablename__ = "on_call_schedule"
    __table_args__ = (UniqueConstraint("service_name", "week_start", name="uq_on_call_service_week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_name: Mapped[str] = mapped_column(String(100), index=True)
    engineer_name: Mapped[str] = mapped_column(String(255))
    week_start: Mapped[date] = mapped_column(Date, index=True)
