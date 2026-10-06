"""SQLAlchemy models.

The ``users`` table is the only table in scope for now. ``messages``,
``conversation_memory`` and ``vendor_requests`` are later items and must be
added additively.

These models are the single source of truth for the schema: Alembic reads
``Base.metadata`` for autogeneration, and ``app.storage`` reads and writes rows
through them.
"""

from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""


class UserRow(Base):
    """A user, keyed by WhatsApp id (``wa_id``)."""

    __tablename__ = "users"

    wa_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="new", default="new"
    )
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="pending", default="pending"
    )
    consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
