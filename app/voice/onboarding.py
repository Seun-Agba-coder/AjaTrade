"""Voice-note onboarding: step 1, language detection; step 2, consent.

Mirrors ``app.onboarding.state_machine.OnboardingStateMachine``: the same
states, the same ``storage.get_user`` / ``storage.save_user`` calls and the same
stored values, so the two flows agree on where a user is.

Step 1 (done): a first voice note is downloaded, transcribed, its language
detected and the user moved to ``awaiting_consent``, including the
low-confidence path (VOICE_SPEC section 4).

Step 2 (this change): on reaching ``awaiting_consent``, the welcome script is
sent before the consent buttons, and a voice note is mapped to one of the three
consent choices exactly like a button tap (``consent_yes`` / ``consent_no`` /
``consent_read_more``), storing what the text flow stores. A transcript that
maps to nothing replays the step; after two failed replays the bot goes quiet
and waits (VOICE_SPEC 6.3).

Interim behaviour, flagged to the owner:
- Replies are text, not mp3 voice notes, until the cached-audio pipeline
  (section 6.4) is built. The user is never left in silence.
- The welcome, ask and goodbye scripts are interim English; the per-language
  packs and cached audio come with section 6.4. The consent and role
  interactive messages do use the user's language.
- Audio arriving in ``awaiting_role`` replays the role buttons instead of
  silence; full voice role handling is step 3. A user who has just consented
  audibly keeps moving instead of being stuck.
- ``consent_message`` falls back to English when a language has no consent
  buttons in the shared text assets (Pidgin stored value, Hausa key with
  trailing spaces). Not fixed here per VOICE_SPEC rule 2.
- Unclear-answer replays are counted in memory on this instance. They are flow
  control, not user data, so nothing is persisted (AGENTS.md: nothing stores
  state beyond the user record without consent).

Not built yet: voice replies to the role step (its buttons replay for now),
``handle_active``, ``handle_declined`` and ``restart``. States other than
``new``, ``awaiting_language``, ``awaiting_consent`` and ``awaiting_role``
are left untouched.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from rich_click import option

from app.onboarding.messages import (
    GOODBYE_MESSAGES,
    LANGUAGES,
    STORAGE_FALLBACK_MESSAGE,
    consent_message,
    create_role_message,
    full_privacy_notice,
    text_message,
)
from app.schemas.memory import User
from app.services.speech_to_text import transcribe_voice_note
from app.services.translation import (
    CONSENT_MAPPING_FALLBACK,
    LANGUAGE_DETECTION_FALLBACK,
    consent_detector,
    language_detector,
)
from app.services.whatsapp.get_media import fetch_voice_note
from app.storage import StorageUnavailableError, mask_phone
from app.storage import storage as default_storage
from app.voice.scripts import (
    CONSENT_ACCEPTED_ACK,
    LOW_CONFIDENCE_RETRY,
    MAX_STEP_REPLAYS,
    PIDGIN_DEFAULT_NOTICE,
    STEP_REPLAY_UNCLEAR,
    get__welcoming_script,
)

logger = logging.getLogger("voice")

# A detected language is trusted at or above this confidence (VOICE_SPEC 4).
LANGUAGE_CONFIDENCE_THRESHOLD = 0.7

# The consent step repeats itself below this confidence (VOICE_SPEC 6.3).
CONSENT_CONFIDENCE_THRESHOLD = 0.6

# The welcome, ack and goodbye scripts are interim English until the
# per-language packs exist (VOICE_SPEC 6.4 / 7).
INTERIM_SCRIPT_LANGUAGE = "english"

# Classifier code -> the row id the text flow's language list uses. The value
# stored on the user then comes from LANGUAGES, so the two flows cannot drift.
CLASSIFIER_CODE_TO_OPTION_ID: dict[str, str] = {
    "yo": "lang_yo",
    "ha": "lang_ha",
    "ig": "lang_ig",
    "pcm": "lang_pcm",
    "en": "lang_en",
}


def classifier_code_to_stored_language(code: str | None) -> str | None:
    """Return the value the text flow stores for a classifier code.

    Built from ``LANGUAGES`` so the voice flow never hardcodes a language
    string. Returns ``None`` for ``other`` and for unknown codes.
    """
    option_id = CLASSIFIER_CODE_TO_OPTION_ID.get((code or "").strip().lower())
    return LANGUAGES.get(option_id) if option_id else None


class VoiceOnboarding:
    """Onboarding for users whose first message is a voice note."""

    def __init__(self, storage=None):
        self.storage = storage or default_storage
        # Replay counters for unclear answers, per phone, in memory only.
        # Flow control, not user data; reset when a step is answered.
        self._consent_replays: dict[str, int] = {}

    async def get_or_create_user(
        self, phone: str, name: str | None = None
    ) -> User:
        user = await self.storage.get_user(phone)
        if user is None:
            user = User(phone=phone, name=name)
            await self.storage.save_user(user)
        return user

    async def process(
        self, phone: str, message: dict, name: str | None = None
    ) -> dict | list[dict] | None:
        """Handle one inbound voice note and return the messages to send."""
        try:
            user = await self.get_or_create_user(phone, name)
        except StorageUnavailableError as error:
            # A polite fallback instead of a dead webhook (AGENTS.md).
            logger.error(
                "Storage unavailable for %s: %s", mask_phone(phone), error
            )
            return text_message(STORAGE_FALLBACK_MESSAGE)

        previous_state = user.state
        message_id = message.get("id")

        if user.state == "new":
            reply = await self.handle_new(user, message)
        elif user.state == "awaiting_language":
            reply = await self.handle_language(user, message)
        elif user.state == "awaiting_consent":
            reply = await self.handle_consent(user, message)
        elif user.state == "awaiting_role":
            # Interim guard: the role step is not built for voice yet (step
            # 3), but a voice user who has just consented must not be met
            # with silence. Replay the role buttons; state does not change.
            logger.info(
                "Voice: role step not built; replaying it for %s",
                mask_phone(phone),
            )
            reply = create_role_message(user.language or INTERIM_SCRIPT_LANGUAGE)
        else:
            # Steps 4 and later, and the active/declined states, are not
            # built yet. Never move the user.
            logger.info(
                "Voice: no step for state=%s (%s), message_id=%s",
                user.state,
                mask_phone(phone),
                message_id,
            )
            return None

        logger.info(
            "Voice transition %s: %s -> %s, message_id=%s",
            mask_phone(phone),
            previous_state,
            user.state,
            message_id,
        )
        return reply

    async def handle_new(
        self, user: User, message: dict
    ) -> dict | list[dict] | None:
        """First voice note: switch to awaiting_language, then detect."""
        user.state = "awaiting_language"
        await self.storage.save_user(user)
        return await self.handle_language(user, message)

    async def handle_language(
        self, user: User, message: dict
    ) -> dict | list[dict] | None:
        """Transcribe the voice note, detect the language and advance."""
        result = language_detector(message)

        code = result["language"]
        confidence = result["confidence"]
        logger.info(
            "Voice language detection for %s: %s (confidence=%.2f, other=%s)",
            mask_phone(user.phone),
            code,
            confidence,
            result["detected_other"],
        )

        stored_language = classifier_code_to_stored_language(code)
        if stored_language and confidence >= LANGUAGE_CONFIDENCE_THRESHOLD:
            user.language = stored_language
            user.language_source = "detected"
            user.language_attempts = 0
            user.state = "awaiting_consent"
            await self.storage.save_user(user)
            return self.consent_prompt(user.language)

        return await self.low_confidence(user)

    async def handle_consent(
        self, user: User, message: dict
    ) -> dict | list[dict] | None:
        """Map the transcript to one consent option and act like the button tap.

        VOICE_SPEC 6.3: the answer is treated exactly as if the button was
        tapped, so the stored values match the text flow.
        # """
        # result = await self.detect_consent(message, user.language)
        # option = result["option"]
        # confidence = result["confidence"]
        # logger.info(
        #     "Voice consent mapping for %s: %s (confidence=%.2f)",
        #     mask_phone(user.phone),
        #     option,
        #     confidence,
        # )

    
        if message == "consent_yes":
            return await self.grant_consent(user)
        if message == "consent_no":
            return await self.decline_consent(user)
        return await self.show_privacy_notice(user)

    async def detect_consent(self, message: dict, language: str | None) -> dict:
        """Transcribe the voice note, then map it to a consent option.

        Returns the mapping result, or the ``unclear`` fallback when the voice
        note cannot be fetched or transcribed, which the caller replays. The
        audio and the transcript are never stored.
        """
        media_id = (message.get("audio") or {}).get("id")
        if not media_id:
            logger.error("Voice message without a media id; treating it as unclear")
            return dict(CONSENT_MAPPING_FALLBACK)

        try:
            audio_bytes, mime_type = await fetch_voice_note(media_id)
            transcript = await transcribe_voice_note(audio_bytes, mime_type)
        except Exception as error:  # noqa: BLE001 - never silence the user
            logger.error(
                "Voice note %s could not be transcribed: %s", media_id, error
            )
            return dict(CONSENT_MAPPING_FALLBACK)

        return await consent_detector(transcript, language)

    async def replay_consent(self, user: User) -> dict | list[dict] | None:
        """Replay the step with an unclear note before the buttons again.

        After two failed replays, send nothing more and wait for a button tap
        or a clearer voice note (VOICE_SPEC 6.3).
        """
        replays = self._consent_replays.get(user.phone, 0) + 1
        self._consent_replays[user.phone] = replays
        if replays > MAX_STEP_REPLAYS:
            logger.info(
                "Voice consent unclear %d times for %s; waiting",
                replays,
                mask_phone(user.phone),
            )
            return None
        logger.info(
            "Voice consent unclear for %s; replaying the step (%d/%d)",
            mask_phone(user.phone),
            replays,
            MAX_STEP_REPLAYS,
        )
        return [
            text_message(STEP_REPLAY_UNCLEAR),
            *self.consent_prompt(user.language),
        ]

    async def grant_consent(self, user: User) -> list[dict]:
        """Store consent exactly like the text flow's consent_yes, then the role step.

        The role prompt voice note is not built yet (step 3), so the ack is
        followed by the text flow's role message in the user's language.
        """
        user.consent_status = "granted"
        user.consent_at = datetime.now(timezone.utc)
        user.consent_version = "v1"
        user.state = "awaiting_role"
        self._consent_replays.pop(user.phone, None)
        await self.storage.save_user(user)

        return [
            text_message(CONSENT_ACCEPTED_ACK),
            create_role_message(user.language or INTERIM_SCRIPT_LANGUAGE),
        ]

    async def decline_consent(self, user: User) -> dict:
        """Store consent exactly like the text flow's consent_no, then goodbye.

        Only what is needed to run the service stays on the record (VOICE_SPEC
        6.6). The goodbye is interim English wording until the goodbye script
        is generated per language (section 7).
        """
        user.consent_status = "declined"
        user.consent_at = None
        user.consent_version = None
        user.state = "declined"
        self._consent_replays.pop(user.phone, None)
        await self.storage.save_user(user)

        return text_message(GOODBYE_MESSAGES[INTERIM_SCRIPT_LANGUAGE])

    async def show_privacy_notice(self, user: User) -> list[dict]:
        """Send the fuller notice, then the buttons again (no state change)."""
        return [
            text_message(full_privacy_notice(INTERIM_SCRIPT_LANGUAGE)),
            self.consent_buttons(user.language),
        ]

    def consent_prompt(self, language: str) -> list[dict]:
        """Welcome script, then the text flow's consent buttons.

        The welcome script is interim English until the per-language scripts
        and cached audio exist (VOICE_SPEC 6.4); the buttons are translated.
        """
        return [
            text_message(get__welcoming_script(INTERIM_SCRIPT_LANGUAGE)),
            self.consent_buttons(language),
        ]

    def consent_buttons(self, language: str) -> dict:
        """Return the text flow's consent buttons for a stored language.

        Interim guard: ``consent_message`` reads its button labels with
        ``CONSENST_BUTTONS[language]``, which raises KeyError for the Pidgin
        value the text flow itself stores, for Hausa (its key has trailing
        spaces) and for the short codes the typed-number path stores. English is
        the fallback so a user is never dropped mid-onboarding. Flagged to the
        owner rather than fixed in the text flow here.
        """
        try:
            return consent_message(language)
        except KeyError:
            logger.error(
                "No consent buttons for language=%r; falling back to English",
                language,
            )
            return consent_message(INTERIM_SCRIPT_LANGUAGE)

    # async def detect_language(self, message: dict) -> dict:
        """Download and transcribe the voice note, then classify its language.

        Returns the classifier result, or the ``other``/0.0 fallback when the
        voice note cannot be fetched or transcribed, which the caller treats as
        low confidence. The audio and the transcript are never stored.
        """
        media_id = (message.get("audio") or {}).get("id")
        if not media_id:
            logger.error("Voice message without a media id; treating it as unclear")
            return dict(LANGUAGE_DETECTION_FALLBACK)

        try:
            audio_bytes, mime_type = await fetch_voice_note(media_id)
            transcript = await transcribe_voice_note(audio_bytes, mime_type)
        except Exception as error:  # noqa: BLE001 - never silence the user
            logger.error(
                "Voice note %s could not be transcribed: %s", media_id, error
            )
            return dict(LANGUAGE_DETECTION_FALLBACK)

        return await language_detector(transcript)

    # async def low_confidence(self, user: User) -> dict | list[dict]:
    #     """Retry once, then default to Pidgin (VOICE_SPEC 4)."""
    #     attempts = user.language_attempts or 0

    #     if attempts >= 1:
    #         # Second failure: default to Pidgin and continue to consent.
    #         language = LANGUAGES["lang_pcm"]
    #         user.language = language
    #         user.language_source = "default_fallback"
    #         user.language_attempts = 0
    #         user.state = "awaiting_consent"
    #         await self.storage.save_user(user)
    #         return [
    #             text_message(PIDGIN_DEFAULT_NOTICE),
    #             *self.consent_prompt(language),
    #         ]

    #     # First failure: ask for another voice note and keep the state.
    #     user.language_attempts = attempts + 1
    #     await self.storage.save_user(user)
    #     return text_message(LOW_CONFIDENCE_RETRY)
