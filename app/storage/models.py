"""SQLAlchemy models.

The ``users`` and ``messages`` tables are in scope for now.
``conversation_memory`` and ``vendor_requests`` are later items and must be
added additively.

These models are the single source of truth for the schema: Alembic reads
``Base.metadata`` for autogeneration, and ``app.storage`` reads and writes rows
through them.
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
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
    language_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"), default=0
    )
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


class MessageRow(Base):
    """One saved incoming or outgoing message (chat history).

    Rows are only written for users whose ``consent_status`` is ``granted``.
    ``text`` holds the message text, the transcript for a voice note, or the
    diagnosis summary for a photo; raw audio and photos are never stored.
    """

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_wa_id", "wa_id"),
        UniqueConstraint("wa_message_id", name="uq_messages_wa_message_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wa_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.wa_id"), nullable=False
    )
    wa_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    msg_type: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
