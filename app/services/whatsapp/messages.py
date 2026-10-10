"""Handling for individual WhatsApp messages (active, onboarded users).

Incoming pipeline (voice): Whisper STT -> Groq translation to English.
Incoming pipeline (photo): existing disease_detection diagnosis.

For voice and text messages the English text is routed through the brain
router (crop_detection case flow, intent classification, stubs). For photo
messages the existing diagnosis path is preserved unchanged; only the stored
metadata (media_ref, case_id) is augmented.

"""

import asyncio
import logging
from typing import Any

from app.schemas.webhook import Message
from app.services.speech_to_text import transcribe_voice_note
from app.services.translation import translate_to_english, translate_for_speech
from app.services.whatsapp.get_media import fetch_voice_note, fetch_whatsapp_image
from app.services.chat_history import record_message
from app.services.diagnoses.disease_detection import diagnose
from app.services.text_to_speech import text_to_speech
from app.services.whatsapp.send_media import send_text, send_voice_note
from app.storage import StorageUnavailableError, mask_phone, storage
from app.services.brain import (
    RoutedReply,
    _welcome_back_and_menu,
    _stub_service_reply,
    route_message,
    send_wait_notice,
)

logger = logging.getLogger("webhook")


def _is_consented(user) -> bool:
    """Return True when the user has granted consent for chat history."""
    return user is not None and getattr(user, "consent_status", None) == "granted"


async def _save_inbound(
    phone: str,
    msg_type: str,
    text: str | None,
    wa_message_id: str | None,
    media_ref: str | None = None,
    case_id: Any = None,
    user=None,
) -> None:
    """Save an inbound message when the user has consented, with dedupe."""
    if not _is_consented(user):
        return
    # Durable dedupe: ignore a retry whose message id is already stored.
    if wa_message_id and await storage.message_seen(wa_message_id):
        logger.info("Duplicate inbound message %s from %s; ignoring (DB dedupe)",
                     wa_message_id, mask_phone(phone))
        return
    await record_message(
        phone,
        "in",
        msg_type,
        text,
        wa_message_id=wa_message_id,
        language=user.language if user else None,
        media_ref=media_ref,
        case_id=case_id,
        user=user,
    )


def _menu_payload(language: str | None, name: str | None) -> dict[str, Any]:
    """Service menu list message. Fallback to English when language unknown."""
    try:
        from app.onboarding.messages import service_menu
        return service_menu(language or "english", name=name)
    except Exception as error:
        logger.warning("Could not build service menu: %s", error)
        return {
            "type": "text",
            "text": {"body": "AjaTrade here. Send a photo or voice note about your crop problem, ask for a market price, or ask for a vendor."},
        }


def _schedule_wait_notice(user) -> None:
    """Send the pregenerated 'please wait' voice note in the background.

    Fires once per request, right when a photo or voice note arrives and
    processing starts. Fire-and-forget: the send never delays the diagnosis,
    and it is never retried if processing turns out to be slow.
    """
    if user is None:
        return
    try:
        asyncio.create_task(send_wait_notice(user))
    except Exception as error:  # noqa: BLE001 - never block the reply
        logger.warning("Could not schedule wait notice: %s", error)


async def handle_message(message: Message, contact_name: str | None) -> None:
    """Do the real work here for an active, onboarded user."""
    sender = message.from_
    try:
        user = await storage.get_user(sender)
    except StorageUnavailableError as error:
        logger.error(
            "Storage unavailable for %s: %s", mask_phone(sender), error
        )
        user = None
    language_selected = user.language if user else None

    logger.info(
        "Handling message from %s (%s), language=%s",
        mask_phone(sender),
        contact_name,
        language_selected,
    )
    msg_type = message.type
    logger.info("sender info %s", mask_phone(sender))

    if msg_type == "text" and message.text is not None:
        logger.info(
            "Text from %s (%s): %s",
            mask_phone(sender),
            contact_name,
            message.text.body,
        )
        english_text = message.text.body
        # Store inbound text (dedupe + consent checked inside).
        await _save_inbound(
            sender,
            "text",
            english_text,
            wa_message_id=message.id,
            user=user,
        )
        # Route through the brain.
        reply = await _route_text_or_voice(user, english_text)
        await _send_routed_reply(sender, user, reply, language_selected)

    elif msg_type == "audio" and message.audio is not None:
        logger.info(
            "Voice note from %s, media_id=%s", mask_phone(sender), message.audio.id
        )
        # "Please wait" voice note: send it in the background before the slow
        # steps (fetch, STT, translation, model calls).
        _schedule_wait_notice(user)
        # (await is a syntax error; use asyncio or just call directly)
        audio_bytes, mime_type = await fetch_voice_note(message.audio.id)
        logger.info(
            "Fetched voice note media_id=%s from %s: %d bytes (%s)",
            message.audio.id,
            mask_phone(sender),
            len(audio_bytes),
            mime_type,
        )
        transcription_text = await transcribe_voice_note(audio_bytes, mime_type)
        logger.info("Transcription: %s", transcription_text)

        # Translate to English for the brain.
        translate_result = await translate_to_english(transcription_text)
        english_text = translate_result.get("english", transcription_text)
        logger.info("Translated text: %s", english_text)

        # Store the transcript, never the audio bytes.
        await _save_inbound(
            sender,
            "voice",
            transcription_text,
            wa_message_id=message.id,
            user=user,
        )

        # Route the English text through the brain.
        reply = await _route_text_or_voice(user, english_text)
        await _send_routed_reply(sender, user, reply, language_selected)

    elif msg_type == "image" and message.image is not None:
        logger.info(
            "Image from %s, media_id=%s", mask_phone(sender), message.image.id
        )
        # "Please wait" voice note: sent in the background as soon as the photo
        # is received, before the diagnosis reply is ready. Once per request.
        _schedule_wait_notice(user)
        mime_type, image_bytes = await fetch_whatsapp_image(message.image.id)
        logger.info(
            "Fetched image media_id=%s from %s: %d bytes (%s)",
            message.image.id,
            mask_phone(sender),
            len(image_bytes),
            mime_type,
        )
        logger.info("Farmer's caption: %s", message.image.caption)

        translated_text = None
        if message.image.caption:
            result = await translate_to_english(message.image.caption)
            translated_text = result.get("english")

        diagnosis = diagnose(image_bytes, mime_type, farmer_text=translated_text)
        logger.info("Diagnosis for media_id=%s: %s", message.image.id, diagnosis)

        # Store the diagnosis text + the WhatsApp media id (temporary), never
        # the photo bytes.
        await _save_inbound(
            sender,
            "image",
            diagnosis.get("farmer_message"),
            wa_message_id=message.id,
            media_ref=message.image.id,
            user=user,
        )

        translated_farmer_message, spitch_lang_code = await translate_for_speech(
            diagnosis["farmer_message"], language_selected
        )
        logger.info(
            "Translated farmer message: %s (Spitch code: %s)",
            translated_farmer_message, spitch_lang_code,
        )
        voice_note = await text_to_speech(translated_farmer_message, language_selected)
        if voice_note:
            sent = await send_voice_note(sender, voice_note)
            logger.info(
                "Sent diagnosis voice note to %s: success=%s",
                mask_phone(sender),
                sent,
            )
            await _save_inbound(
                sender,
                "voice",
                translated_farmer_message,
                wa_message_id=message.id,
                user=user,
            )
        else:
            sent = await send_text(sender, diagnosis["farmer_message"])
            logger.info(
                "TTS unavailable for %s; sent text fallback to %s: success=%s",
                language_selected,
                mask_phone(sender),
                sent,
            )
            await _save_inbound(
                sender,
                "text",
                diagnosis["farmer_message"],
                user=user,
            )
    else:
        logger.info("Unhandled message type: %s", msg_type)


async def _route_text_or_voice(user, english_text: str) -> RoutedReply:
    """Route a text or voice (now in English) message through the brain."""
    if user is None or getattr(user, "consent_status", None) != "granted":
        # Not consented: do not route, do not store beyond dedupe.
        return RoutedReply(messages=[], english_text=None)

    # The "please wait" voice note is sent at the start of photo/voice
    # processing (see _schedule_wait_notice), once per request.

    return await route_message(user, english_text)


async def _send_routed_reply(
    phone: str,
    user,
    reply: RoutedReply,
    language_selected: str | None,
) -> None:
    """Send the router's reply, translate+TTS where needed, and record it."""
    if not reply.messages:
        return

    # If the router signals a flow switch or case close, apply it.
    if reply.close_case:
        try:
            await storage.close_case(phone)
        except Exception as error:
            logger.warning("Could not close case for %s: %s", phone, error)

    if reply.new_flow:
        try:
            user_obj = await storage.get_user(phone)
            if user_obj is not None:
                user_obj.flow = reply.new_flow
                user_obj.step = None
                user_obj.current_case_id = None
                user_obj.case_started_at = None
                user_obj.last_activity_at = None
                user_obj.case_crop = None
                user_obj.case_part = None
                user_obj.case_symptoms = []
                user_obj.questions_asked = 0
                user_obj.diagnoses_in_case = 0
                await storage.save_user(user_obj)
        except Exception as error:
            logger.warning("Could not set flow=%s for %s: %s", reply.new_flow, phone, error)

    for msg in reply.messages:
        kind = msg.get("type")
        if kind == "text":
            body = msg.get("text", {}).get("body", "")
            # Translate the English body into the user's language, then TTS.
            translated, spitch_code = await translate_for_speech(body, language_selected)
            voice_note = await text_to_speech(translated, language_selected or "english")
            if voice_note:
                sent = await send_voice_note(phone, voice_note)
                logger.info(
                    "Sent routed voice reply to %s: success=%s",
                    mask_phone(phone),
                    sent,
                )
                # await _save_inbound(phone, "voice", translated, user=user)
            else:
                sent = await send_text(phone, translated)
                logger.info(
                    "TTS unavailable for %s; sent text fallback to %s: success=%s",
                    language_selected,
                    mask_phone(phone),
                    sent,
                )
                await _save_inbound(phone, "text", translated, user=user)

        elif kind == "interactive":
            # Menu / interactive replies: send as-is, record the text.
            sent = await send_text(phone, _interactive_text(msg))
            logger.info(
                "Sent routed interactive reply to %s: success=%s",
                mask_phone(phone),
                sent,
            )
            await _save_inbound(phone, "button", _interactive_text(msg), user=user)

        else:
            logger.warning("Unhandled routed message type: %s", kind)


def _interactive_text(msg: dict[str, Any]) -> str:
    """Best-effort user-visible text from an interactive payload."""
    interactive = msg.get("interactive") or {}
    body = interactive.get("body") or {}
    return body.get("text", "")

