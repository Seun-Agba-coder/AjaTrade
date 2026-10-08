"""Storage backends for AjaTrade.

Handlers and the WhatsApp adapter import ``storage`` from here and never
touch SQL. The SQLAlchemy models live in :mod:`app.storage.models`.
"""

from app.storage.models import Base, MessageRow, UserRow
from app.storage.postgres import (
    PostgresStorage,
    StorageUnavailableError,
    mask_phone,
    storage,
)

__all__ = [
    "Base",
    "MessageRow",
    "UserRow",
    "PostgresStorage",
    "StorageUnavailableError",
    "mask_phone",
    "storage",
]
