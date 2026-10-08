"""Chat-history model.

Persistence lives in :mod:`app.storage`; this module only holds the shape of
one stored message, matching the ``messages`` table columns (SPEC.md section 3).
"""

from dataclasses import dataclass


@dataclass
class ChatMessage:
    """One incoming or outgoing message held in ``messages``.

    ``text`` is the message text, the transcript for a voice note, or the
    diagnosis summary for a photo. Raw audio and photos are never stored.
    """

    wa_id: str
    direction: str
    msg_type: str
    text: str | None = None
    wa_message_id: str | None = None
    language: str | None = None
    intent: str | None = None
