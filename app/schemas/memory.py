"""User model.

Persistence now lives in :mod:`app.storage`; this module only holds the shape
of a user, matching the ``users`` table columns.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    phone: str
    name: str | None = None
    preferred_name: str | None = None
    state: str = "new"
    language: str | None = None
    role: str | None = None
    consent_status: str = "pending"
    consent_at: datetime | None = None
    consent_version: str | None = None
    created_at: datetime | None = None
    last_seen_at: datetime | None = None
