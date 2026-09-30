"""
Speech-to-text transcription stage.

Takes the raw voice-note bytes fetched by app/services/whatsapp/media.py
(fetch_voice_note) and turns them into text, so downstream stages can
reason about what the user said.
"""

import io
import os

from dotenv import load_dotenv
from elevenlabs.client import AsyncElevenLabs

load_dotenv()


async def transcribe_voice_note(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """
    Transcribe an inbound WhatsApp voice note to text with ElevenLabs Scribe.

    Args:
        audio_bytes: Raw audio payload (typically OGG/Opus from WhatsApp).
        mime_type: MIME type reported by WhatsApp's media API.

    Returns:
        The transcribed text.
    """
    client = AsyncElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    # Build a (filename, file-like, content_type) tuple so the SDK sends
    # a proper multipart upload with the right MIME type.
    extension = mime_type.rsplit("/", 1)[-1].split(";")[0] or "ogg"
    file_tuple = (f"audio.{extension}", io.BytesIO(audio_bytes), mime_type)

    transcription = await client.speech_to_text.convert(
        file=file_tuple,
        model_id="scribe_v2",
        tag_audio_events=True,  # tag events like laughter, applause, etc.
        diarize=True,  # annotate who is speaking
    )

    # The SDK returns an object, not a dict. Single-channel audio yields a
    # chunk model with a .text attribute; multichannel yields a wrapper
    # with a .transcripts list instead.
    text = getattr(transcription, "text", None)
    if text is None and hasattr(transcription, "transcripts"):
        text = " ".join(t.text for t in transcription.transcripts)

    return (text or "").strip()
