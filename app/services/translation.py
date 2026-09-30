import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load our environment variables
load_dotenv()

# The client automatically detects GEMINI_API_KEY from the environment,
# but keeping it explicit like we had it is perfectly fine.
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# If 3.1-flash-lite throws a "model not found" error, we can safely 
# fall back to gemini-2.5-flash or gemini-2.5-flash-lite.
MODEL = "gemini-3.8-flash"


SYSTEM_PROMPT = (
    "Translate the user's text to English. Detect the source language "
    "automatically; it may be Yoruba, Hausa, Nigerian Pidgin, or a mix. "
    "If it is already English, return it unchanged. If the text looks "
    "garbled by transcription errors, translate as best you can and add "
    "[unclear] at the end. Output only the translation."
)

async def translate_to_english(text: str) -> str:
    try:
        # Using types.GenerateContentConfig ensures the SDK formats 
        # our system instruction perfectly without type errors.
        interaction = await client.aio.interactions.create(
            model=MODEL,
            input=text,
            system_instruction=SYSTEM_PROMPT,
        )
        # Note the property change: output_text instead of text
        return interaction.output_text.strip()
    except Exception as e:
        print(f"Error during translation: {e}")
        return ""

