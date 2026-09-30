"""WhatsApp webhook endpoints: verification and message delivery."""

import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import PlainTextResponse

from app.config import Settings, get_settings
from app.core.security import verify_signature
from app.schemas.webhook import WebhookPayload
from app.services.whatsapp.messages import handle_message

logger = logging.getLogger("webhook")

router = APIRouter()


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    """Meta calls this once when you register the webhook URL."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        # Must echo the challenge back as plain text
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Accept a webhook delivery, then process it out-of-band."""
    raw_body = await request.body()
    print("Received webhook payload:", raw_body.decode("utf-8"))

    if not verify_signature(
        raw_body,
        request.headers.get("X-Hub-Signature-256"),
        settings.whatsapp_app_secret,
    ):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = WebhookPayload.model_validate(await request.json())

    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            contacts = {contact.wa_id: contact.profile.name for contact in value.contacts}

            for message in value.messages:
                name = contacts.get(message.from_)
                background_tasks.add_task(handle_message, message, name)

            # delivery/read receipts arrive under value["statuses"]; ignored here

    # Respond 200 fast, otherwise Meta retries the delivery
    return {"status": "received"}
