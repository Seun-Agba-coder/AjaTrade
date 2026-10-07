"""PostgreSQL-backed user storage built on SQLAlchemy (async).

Same public interface as before: ``get_user``, ``save_user``, ``get_state`` and
``get_role``, all ``async``, returning ``None`` when a user does not exist, so
handlers and the state machine keep calling ``storage.get_user(...)``.

All SQL/SQLAlchemy access lives behind :class:`PostgresStorage`. Every call has
a timeout and one retry, and raises :class:`StorageUnavailableError` if the
database stays unreachable.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Awaitable, Callable, Optional, TypeVar

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.schemas.memory import User
from app.storage.models import UserRow, Base


logger = logging.getLogger("storage")

CONNECT_TIMEOUT_SECONDS = 5.0
QUERY_TIMEOUT_SECONDS = 5.0
RETRY_DELAY_SECONDS = 0.2

T = TypeVar("T")


class StorageUnavailableError(RuntimeError):
    """Raised when the database cannot be reached after one retry."""


def mask_phone(phone: str | None) -> str:
    """Mask a phone number so logs never contain the full number."""
    if not phone:
        return ""
    if len(phone) <= 4:
        return "*" * len(phone)
    return f"{phone[:2]}{'*' * (len(phone) - 4)}{phone[-2:]}"


def to_async_url(url: str) -> str:
    """Return a SQLAlchemy async (asyncpg) URL for a plain Postgres URL."""
    url = (url or "").strip()
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def _row_to_user(row: UserRow) -> User:
    """Convert a database row into the plain ``User`` the rest of the app uses."""
    return User(
        phone=row.wa_id,
        name=row.name,
        preferred_name=row.preferred_name,
        state=row.state,
        language=row.language,
        language_source=row.language_source,
        language_attempts=row.language_attempts or 0,
        role=row.role,
        consent_status=row.consent_status,
        consent_at=row.consent_at,
        consent_version=row.consent_version,
        created_at=row.created_at,
        last_seen_at=row.last_seen_at,
    )


class PostgresStorage:
    """User storage backed by PostgreSQL through SQLAlchemy."""

    def __init__(self, dsn: str | None = None):
        raw = dsn if dsn is not None else os.getenv("DATABASE_URL", "")
        self._dsn = to_async_url(raw) if raw else ""
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        """Create the async engine and verify it once.

        Never raises: if the database is missing or unreachable it is logged
        and the app keeps running (queries then fail into
        :class:`StorageUnavailableError`).
        """
        if not self._dsn:
            logger.error("DATABASE_URL is not set; user storage is disabled")
            return
        self._engine = create_async_engine(
            self._dsn,
            pool_size=5,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={
                "timeout": CONNECT_TIMEOUT_SECONDS,
                "command_timeout": QUERY_TIMEOUT_SECONDS,
            },
        )
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False
        )
        try:
            await self._ping()
            await self._create_tables()
            logger.info("Connected to PostgreSQL")
        except Exception as error:  # noqa: BLE001 - startup must not crash
            logger.error("Could not reach PostgreSQL at startup: %s", error)

    async def _ping(self) -> None:
        """Run a cheap query to confirm the connection works."""
        if self._session_factory is None:
            raise StorageUnavailableError("database is not connected")
        async with self._session_factory() as session:
            await asyncio.wait_for(
                session.execute(text("SELECT 1")), QUERY_TIMEOUT_SECONDS
            )


    async def _create_tables(self) -> None:
        """Create any missing tables (development convenience)."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables ready: %s", list(Base.metadata.tables.keys()))

    async def close(self) -> None:
        """Dispose of the engine and its pool."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    async def _execute(
        self, operation: Callable[[AsyncSession], Awaitable[T]]
    ) -> T:
        """Run one database operation with a timeout and a single retry."""
        if self._session_factory is None:
            raise StorageUnavailableError("database is not connected")

        last_error: Exception = StorageUnavailableError("unknown database error")
        for attempt in range(2):  # one attempt plus one retry
            try:
                async with self._session_factory() as session:
                    return await asyncio.wait_for(
                        operation(session), QUERY_TIMEOUT_SECONDS
                    )
            except (SQLAlchemyError, asyncio.TimeoutError, OSError) as error:
                last_error = error
                logger.warning(
                    "Database call failed (attempt %d/2): %s", attempt + 1, error
                )
                if attempt == 0:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
        raise StorageUnavailableError(str(last_error)) from last_error

    async def get_user(self, phone: str) -> Optional[User]:
        """Return the user, or ``None`` if they do not exist yet."""

        async def operation(session: AsyncSession) -> Optional[User]:
            result = await session.execute(
                select(UserRow).where(UserRow.wa_id == phone)
            )
            row = result.scalar_one_or_none()
            return _row_to_user(row) if row is not None else None

        return await self._execute(operation)

    async def save_user(self, user: User) -> None:
        """Insert the user, or update the existing row."""

        async def operation(session: AsyncSession) -> None:
            insert_values = {
                "wa_id": user.phone,
                "name": user.name,
                "preferred_name": user.preferred_name,
                "state": user.state,
                "language": user.language,
                "language_source": user.language_source,
                "language_attempts": user.language_attempts,
                "role": user.role,
                "consent_status": user.consent_status,
                "consent_at": user.consent_at,
                "consent_version": user.consent_version,
            }
            update_values = {
                key: value
                for key, value in insert_values.items()
                if key != "wa_id"
            }
            update_values["last_seen_at"] = func.now()

            statement = (
                pg_insert(UserRow)
                .values(**insert_values)
                .on_conflict_do_update(
                    index_elements=[UserRow.wa_id], set_=update_values
                )
            )
            await session.execute(statement)
            await session.commit()

        await self._execute(operation)

    async def get_state(self, phone: str) -> str | None:
        """Return the user's current onboarding state."""
        user = await self.get_user(phone)
        return user.state if user else None

    async def get_role(self, phone: str) -> str | None:
        """Return the user's role."""
        user = await self.get_user(phone)
        return user.role if user else None


storage = PostgresStorage()
