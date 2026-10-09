"""Storage backends for AjaTrade.

Handlers and the WhatsApp adapter import ``storage`` from here and never
touch SQL. The SQLAlchemy models live in :mod:`app.storage.models`.
"""

from app.storage.models import (
    Base,
    ConversationMemoryRow,
    DiagnosisLogRow,
    MessageRow,
    UserRow,
    OpenCase,
    UserFlow,
    UserStep,
    new_case_id,
    VISION_MODEL_NAME,
    TEXT_MODEL_NAME,
)
from app.storage.postgres import (
    PostgresStorage,
    StorageUnavailableError,
    mask_phone,
    storage,
)

__all__ = [
    "Base",
    "ConversationMemoryRow",
    "DiagnosisLogRow",
    "MessageRow",
    "UserRow",
    "OpenCase",
    "UserFlow",
    "UserStep",
    "new_case_id",
    "VISION_MODEL_NAME",
    "TEXT_MODEL_NAME",
    "PostgresStorage",
    "StorageUnavailableError",
    "mask_phone",
    "storage",
]
