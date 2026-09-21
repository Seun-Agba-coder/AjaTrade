# main.py
import hashlib
import hmac
import logging
import os
from dotenv import load_dotenv


from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook")
load_dotenv()  # reads .env from project root

app = FastAPI()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")  # from Meta app dashboard



@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta calls this once when you register the webhook URL."""
    if mode == "subscribe" and token == VERIFY_TOKEN:
        # Must echo the challenge back as plain text
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    if not APP_SECRET:
        return True  # skip in local dev; always set it in production
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))


async def handle_message(message: dict, contact_name: str | None):
    """Do the real work here (transcribe voice, call your AI, send reply...)."""
    sender = message["from"]
    msg_type = message["type"]

    if msg_type == "text":
        logger.info("Text from %s (%s): %s", sender, contact_name, message["text"]["body"])
    elif msg_type == "audio":
        media_id = message["audio"]["id"]
        logger.info("Voice note from %s, media_id=%s", sender, media_id)
        # 1. GET https://graph.facebook.com/<version>/<media_id> -> media URL
        # 2. download with your access token, then transcribe
    elif msg_type == "image":
        logger.info("Image from %s, media_id=%s", sender, message["image"]["id"])
    else:
        logger.info("Unhandled message type: %s", msg_type)


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    print(raw_body)

    if not verify_signature(raw_body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {c["wa_id"]: c["profile"]["name"] for c in value.get("contacts", [])}

            for message in value.get("messages", []):
                name = contacts.get(message["from"])
                background_tasks.add_task(handle_message, message, name)

            # delivery/read receipts arrive under value["statuses"]; ignored here

    # Respond 200 fast, otherwise Meta retries the delivery
    return {"status": "received"}