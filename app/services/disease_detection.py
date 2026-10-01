from groq import Groq
import base64, os
from dotenv import load_dotenv
load_dotenv()
import json 



SYSTEM_PROMPT = """
You are a crop health assistant for smallholder farmers in Nigeria.
You receive one photo of a crop and must return a diagnosis as JSON.

RULES
1. First judge the photo. If it is blurry, too dark, too far away, not a plant,
   or shows no crop, set image_status accordingly, explain in photo_quality,
   and set the diagnosis fields to null. Do not guess from a bad photo.
2. Describe the visible symptoms BEFORE naming any disease.
3. Never overstate certainty. If symptoms fit more than one cause, lower the
   confidence and list the alternatives. "unknown" is an acceptable category.
4. If the plant looks healthy, use category "healthy". Do not invent a disease.
5. Common crops and problems to consider: cassava (mosaic disease, bacterial
   blight, brown streak), maize (fall armyworm, streak virus, leaf blight),
   tomato (early blight, late blight, Tuta absoluta), rice (blast),
   cocoa (black pod), yam (anthracnose), pepper and cowpea (common leaf
   diseases and pests). Other crops are possible.
6. recommended_actions: low-cost and cultural steps only (remove infected
   plants, clean cuttings, spacing, sanitation, crop rotation). Also Advice the farmer on
   chemical products both( names and doses) to use to treat the disease.
7. farmer_message: simple English, short sentences, under 60 words, no jargon.
   
8. Output ONLY the JSON object below. No markdown, no code fences, no extra text.

JSON SCHEMA (fill in every field; use null where a rule above says so)
{
  "image_status": "ok | unclear | not_a_plant | no_crop_visible",
  "photo_quality": {
    "usable": true or false,
    "issues": ["list of problems, empty if none"],
    "retake_advice": "one sentence, or null"
  },
  "crop": {
    "name": "crop name, or null",
    "confidence": "low | medium | high"
  },
  "diagnosis": {
    "primary": {
      "name": "disease or pest name, or 'healthy' or 'unknown'",
      "category": "fungal | bacterial | viral | pest | nutrient | abiotic | healthy | unknown",
      "confidence": "low | medium | high"
    },
    "alternatives": [
      { "name": "other possible cause", "category": "same options as above" }
    ],
    "visible_symptoms": ["what you can actually see, one item each"]
  },
  "recommended_actions": ["short action, low-cost steps first"],
  "see_extension_officer": {
    "needed": true or false,
    "reason": "one sentence"
  },
  "farmer_message": "the short plain-language message for the farmer"
}
"""
REQUIRED_KEYS = ["image_status", "photo_quality", "farmer_message"]
client = Groq(api_key=os.environ["GROQ_API_KEY"])

def diagnose(image_bytes: bytes, mime_type="image/jpeg", farmer_text=None):
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    if farmer_text and farmer_text.strip():
        instruction = (
            "Diagnose this crop photo. Reply with JSON only.\n\n"
            "The farmer also wrote this note (context only, may be incomplete "
            f"or wrong):\n\"\"\"{farmer_text.strip()}\"\"\""
        )
    else:
        instruction = "Diagnose this crop photo. Reply with JSON only."

    completion = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": f"{instruction}"},
                {"type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            ]},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_completion_tokens=800,
    )
    raw = completion.choices[0].message.content
    try:
        result = json.loads(raw)
        if not all(k in result for k in REQUIRED_KEYS):
            raise ValueError("missing keys")
        return result
    except (json.JSONDecodeError, ValueError):
        return {
            "image_status": "unclear",
            "photo_quality": {"usable": False, "issues": ["parse error"],
                              "retake_advice": "Please send a clearer photo."},
            "farmer_message": "I could not read that photo well. Please send a clear, close photo of one affected leaf in daylight.",
        }