"""Handling for individual WhatsApp messages."""

import logging

from app.schemas.webhook import Message
from app.services.speech_to_text import transcribe_voice_note
from app.services.translation import translate_to_english, translate_for_speech
from app.services.whatsapp.get_media import fetch_voice_note, fetch_whatsapp_image
from app.services.disease_detection import diagnose
from app.services.text_to_speech import text_to_speech
from app.services.whatsapp.send_media import send_text, send_voice_note
from app.schemas.memory import storage



logger = logging.getLogger("webhook")


async def handle_message(message: Message, contact_name: str | None) -> None:
    """Do the real work here (transcribe voice, call your AI, send reply...)."""
    language_selected = storage.get_user(message.from_).language
    logger.info("Handling message from %s (%s), language=%s", message.from_, contact_name, language_selected)
    sender = message.from_
    msg_type = message.type
    logger.info("sender info %s", sender)
    if msg_type == "text" and message.text is not None:
        logger.info("Text from %s (%s): %s", sender, contact_name, message.text.body)
    elif msg_type == "audio" and message.audio is not None:
        logger.info("Voice note from %s, media_id=%s", sender, message.audio.id)
        print("Message type is audio, fetching voice note...")
        audio_bytes, mime_type = await fetch_voice_note(message.audio.id)
        logger.info(
            "Fetched voice note media_id=%s from %s: %d bytes (%s)",
            message.audio.id,
            message.from_,
            len(audio_bytes),
            mime_type,
        )
        transcription_text = await transcribe_voice_note(audio_bytes, mime_type)
        logger.info("Transcription: %s", transcription_text)

        translated_text = await translate_to_english(transcription_text)

        logger.info("Translated text: %s", translated_text)
    elif msg_type == "image" and message.image is not None:
        logger.info("Image from %s, media_id=%s", sender, message.image.id)
        mime_type, image_bytes = await fetch_whatsapp_image(message.image.id)
        logger.info(
            "Fetched image media_id=%s from %s: %d bytes (%s)",
            message.image.id,
            sender,
            len(image_bytes),
            mime_type,
        )

        diagnosis = diagnose(image_bytes, mime_type)
        logger.info("Diagnosis for media_id=%s: %s", message.image.id, diagnosis)
        translated_farmer_message, spitch_lang_code = await translate_for_speech(diagnosis["farmer_message"], language_selected)
        logger.info("Translated farmer message: %s (Spitch code: %s)", translated_farmer_message, spitch_lang_code)
        voice_note = await text_to_speech(translated_farmer_message, language_selected)
        if voice_note:
            sent = await send_voice_note(sender, voice_note)
            logger.info("Sent diagnosis voice note to %s: success=%s", sender, sent)
        else:
            sent = await send_text(sender, diagnosis["farmer_message"])
            logger.info(
                "TTS unavailable for %s; sent text fallback to %s: success=%s",
                language_selected,
                sender,
                sent,
            )
    else:
        logger.info("Unhandled message type: %s", msg_type)
