import os
import json
from dotenv import load_dotenv
from groq import AsyncGroq

# Load our environment variables
load_dotenv()

# The client reads GROQ_API_KEY from the environment; explicit for clarity.
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# "openai/gpt-oss-120b" is the stronger model (better for Yoruba/Hausa/Igbo/Pidgin).
# "openai/gpt-oss-20b" is faster and cheaper. Switch here, or set GROQ_MODEL in .env.
# MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MODEL = "openai/gpt-oss-20b"

# gpt-oss models reason before answering. "low" keeps latency down for translation.
REASONING_EFFORT = "low"

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

TRANSLATE_PROMPT = (
    "Translate the user's message into {language}. "
    "Output only the translation, with no explanations, notes, or quotation marks."
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

VALID_LANGUAGES = ("yoruba", "hausa", "igbo", "pidgin", "english", "unknown")


async def _chat(system_prompt: str, user_text: str) -> str:
    """Single Groq chat call. Returns the model's text reply."""
    completion = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0.2,
        reasoning_effort=REASONING_EFFORT,
    )
    return (completion.choices[0].message.content or "").strip()


async def translate_to_english(text: str) -> dict:
    fallback = {"language": "unknown", "is_mixed": False, "english": text, "unclear": True}
    try:
        raw = await _chat(SYSTEM_PROMPT, text)
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
        print(raw)
        result = json.loads(raw)
        if "language" not in result or "english" not in result:
            return fallback
        if result["language"] not in VALID_LANGUAGES:
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

    system_prompt = TRANSLATE_PROMPT.format(language=LANGUAGE_NAMES[language])

    try:
        translated = (await _chat(system_prompt, text)).strip('"').strip()
        if not translated:
            raise ValueError("empty translation")
        return translated, SPITCH_LANG_CODES[language]
    except Exception as e:
        print(f"Error translating to {language}: {e}")
        return text, SPITCH_LANG_CODES["english"]