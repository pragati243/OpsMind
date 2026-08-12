"""Document persistence model."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import TimestampedModel


class Document(TimestampedModel):
    """Store a source policy document before its content is indexed for retrieval."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source_path: Mapped[str] = mapped_column(String(512), unique=True)
    content: Mapped[str] = mapped_column(Text)
    sensitivity_tier: Mapped[str] = mapped_column(String(30), default="public")
    min_clearance_level: Mapped[int] = mapped_column(Integer, default=1)
    owning_department: Mapped[str] = mapped_column(String(100), default="Operations")
