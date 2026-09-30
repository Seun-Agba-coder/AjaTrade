"""WhatsApp webhook endpoints: verification and message delivery."""

import logging
from pyexpat.errors import messages

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

from app.schemas.memory import storage, User
# from app.onboarding.state_machine import OnboardingStateMachine
from app.services.whatsapp_onboarding import WhatsAppService
from app.onboarding.messages import create_language_message, create_role_message
from app.onboarding.messages import LANGUAGES, ROLES

import os
from dotenv import load_dotenv

load_dotenv()


logger = logging.getLogger("webhook")

router = APIRouter()



# onboarding = OnboardingStateMachine(storage)


whatsapp = WhatsAppService(
    access_token=os.getenv("WHATSAPP_ACCESS_TOKEN"),
    phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
)



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
    
    payload_json = await request.json()
    value = payload_json["entry"][0]["changes"][0]["value"]

    messages = value.get("messages")
    if not messages:
        print("Webhook event has no incoming message. Ignoring it.")
        return {"status": "ignored"}

    message = messages[0]

    phone = message["from"]
    user = storage.get_user(phone)
    if user is None:
    # This is a new user.
        user = User(
        phone=phone,
        state="new",
    )

        storage.save_user(user)

        # Send language selection.
        response = create_language_message()

        await whatsapp.send_message(
        recipient=phone,
        message=response,
    )
        
        return {"status": "received"}
    elif storage.get_state(phone) == "new" :
        # Get the selected WhatsApp list option
        interactive = message.get("interactive", {})
        list_reply = interactive.get("list_reply")
        user = storage.get_user(phone)

        if list_reply:
            selected_language_id = list_reply.get("id")

            language = LANGUAGES.get(selected_language_id)

            if language:
                user.language = language

                # Move them to the next state.
                user.state = "awaiting_consent"

                storage.save_user(user)

                print(
                f"User {user.phone} selected {user.language}"
            )
            response = create_role_message()

            # For now, just confirm it worked.
            await whatsapp.send_message(
                recipient=phone,
                message={
                    "type": "text",
                    "text": {
                        "body": f"You selected {user.language}."
                    }
                },
            )
            # For now, just confirm it worked.
            await whatsapp.send_message(
                recipient=phone,
                message=response,
            )

            return {"status": "received"}
    elif  storage.get_user(phone).role == None: 
        # Get the selected WhatsApp button option
        interactive = message.get("interactive", {})
        button_reply = interactive.get("button_reply")
        user = storage.get_user(phone)

        if button_reply:
            selected_role_id = button_reply.get("id")

            if selected_role_id:
                user.role = ROLES.get(selected_role_id)

                # Move them to the next state.
                user.state = "onboarding_complete"

                storage.save_user(user)

                print(
                f"User {user.phone} selected role {user.role}"
            )

            # For now, just confirm it worked.
            await whatsapp.send_message(
                recipient=phone,
                message={
                    "type": "text",
                    "text": {
                        "body": f"You selected role {user.role}. ask any question\n"
                    }
                },
            )
             # For now, just confirm it worked.
            await whatsapp.send_message(
                            recipient=phone,
                            message={
                                "type": "text",
                                "text": {
                                    "body": f"Do you have any questions to ask about your farmland?\n"
                                }
                            },
                        )

            return {"status": "received"}





    
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
