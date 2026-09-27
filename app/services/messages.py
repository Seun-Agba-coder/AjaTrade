"""Handling for individual WhatsApp messages."""

import logging

from app.schemas.webhook import Message

logger = logging.getLogger("webhook")


async def handle_message(message: Message, contact_name: str | None) -> None:
    """Do the real work here (transcribe voice, call your AI, send reply...)."""
    sender = message.from_
    msg_type = message.type

    if msg_type == "text" and message.text is not None:
        logger.info("Text from %s (%s): %s", sender, contact_name, message.text.body)
    elif msg_type == "audio" and message.audio is not None:
        logger.info("Voice note from %s, media_id=%s", sender, message.audio.id)
        # 1. GET https://graph.facebook.com/<version>/<media_id> -> media URL
        # 2. download with your access token, then transcribe
    elif msg_type == "image" and message.image is not None:
        logger.info("Image from %s, media_id=%s", sender, message.image.id)
    else:
        logger.info("Unhandled message type: %s", msg_type)
