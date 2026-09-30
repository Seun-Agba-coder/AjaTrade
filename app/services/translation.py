import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json

# Load our environment variables
load_dotenv()

# The client automatically detects GEMINI_API_KEY from the environment,
# but keeping it explicit like we had it is perfectly fine.
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# If 3.1-flash-lite throws a "model not found" error, we can safely 
# fall back to gemini-2.5-flash or gemini-2.5-flash-lite.
MODEL = "gemini-3.8-flash"

AUTO = "auto"   # sentinel: means "don't send a language, let Spitch detect"

SPITCH_LANG_CODES = {
    "english": "en",
    "yoruba": "yo",
    "hausa": "ha",
    "igbo": "ig",
    "pidgin": AUTO,
}

LANGUAGE_NAMES = {
    "yoruba": "Yoruba",
    "hausa": "Hausa",
    "igbo": "Igbo",
    "pidgin": "Nigerian Pidgin",
}

TTS_PROMPT_TEMPLATE = (
    "Translate the user's text from English into {language}. "
    "This text will be read aloud by a text-to-speech voice to a farmer, so: "
    "use simple, natural, spoken-style wording that ordinary farmers use; "
    "keep sentences short; keep crop and disease names easy to recognise; "
    "write numbers as words; do not use emojis, markdown, brackets, or symbols. "
    "{extra}"
    "Output only the translation, nothing else."
)

YORUBA_EXTRA = (
    "Write Yoruba with correct tone marks and diacritics (for example ẹ, ọ, ṣ, "
    "and accent marks) because the voice depends on them. "
)

SYSTEM_PROMPT = (
    "Translate the user's text to English and identify its source language. "
    "The text may be Yoruba, Hausa, Igbo, Nigerian Pidgin, English, or a mix. "
    "If the text mixes languages, set language to the single most prominent one, "
    "meaning the language that most of the sentence structure and words come from. "
    "Do not answer 'mixed'. Nigerian Pidgin counts as its own language, not English. "
    "If it is already English, return it unchanged. If the text looks garbled "
    "by transcription errors, translate as best you can and set unclear to true. "
    "Reply with JSON only, no markdown, in exactly this shape: "
    '{"language": "yoruba | hausa | igbo | pidgin | english | unknown", '
    '"is_mixed": true or false, '
    '"english": "the translation", "unclear": true or false}'
)
async def translate_to_english(text: str) -> dict:
    fallback = {"language": "unknown", "is_mixed": False, "english": text, "unclear": True}
    try:
        interaction = await client.aio.interactions.create(
            model=MODEL,
            input=text,
            system_instruction=SYSTEM_PROMPT,
        )
        raw = interaction.output_text.strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
        print(raw)
        result = json.loads(raw)
        if "language" not in result or "english" not in result:
            return fallback
        if result["language"] not in ("yoruba", "hausa", "igbo", "pidgin", "english", "unknown"):
            result["language"] = "unknown"   # guards against the model returning 'mixed' anyway
        return result
    except Exception as e:
        print(f"Error during translation: {e}")
        return fallback


async def translate_for_speech(text: str, language: str) -> tuple[str, str | None]:
    """
    Translate an English farmer reply into the farmer's language.

    Returns (translated_text, spitch_language_code).
    - English or unrecognised language: returns the English text with "en".
    - Translation fails: returns the English text with "en", so the farmer
      still gets an answer they can hear.
    - Language has no Spitch code configured (e.g. pidgin for now): returns
      the translation with None, so the caller can send it as text instead.
    """
    language = (language or "").strip().lower()

    if language not in LANGUAGE_NAMES:
        return text, SPITCH_LANG_CODES["english"]

    system_prompt = TTS_PROMPT_TEMPLATE.format(
        language=LANGUAGE_NAMES[language],
        extra=YORUBA_EXTRA if language == "yoruba" else "",
    )

    try:
        interaction = await client.aio.interactions.create(
            model=MODEL,
            input=text,
            system_instruction=system_prompt,
        )
        translated = interaction.output_text.strip().strip('"').strip()
        if not translated:
            raise ValueError("empty translation")
        return translated, SPITCH_LANG_CODES[language]
    except Exception as e:
        print(f"Error translating to {language}: {e}")
        return text, SPITCH_LANG_CODES["english"]

