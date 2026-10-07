# States: new -> awaiting_language -> awaiting_consent -> awaiting_role -> active / declined
#
# new: first contact from this number
# awaiting_language: language list shown, awaiting reply
# awaiting_consent: privacy notice + I agree / Read more / Don't save my chats
# awaiting_role: Farmer / Trader / Manufacturer
# active: fully onboarded, normal pipeline
# declined: consent declined, no chat history or memory saved
#
# Multi-step flows store the per-user state in the User object (PostgreSQL).

from datetime import datetime, timezone

from app.schemas.memory import User
from app.storage import storage as default_storage
from app.onboarding.messages import (
    LANGUAGES,
    ROLES,
    GOODBYE_MESSAGES,
    WELCOME_MESSAGES,
    create_role_message,
    language_question,
    create_language_message,
    consent_message,
    role_message,
    restart_message,
    text_message,
    full_privacy_notice,
    service_menu,
    greeting_message,
    ROLE_COMPLETE_MESSAGE,
)


class OnboardingStateMachine:
    def __init__(self, storage=None):
        self.storage = storage or default_storage

    async def get_or_create_user(self, phone: str, name: str | None = None) -> User:
        user = await self.storage.get_user(phone)
        if user is None:
            user = User(phone=phone, name=name)
            await self.storage.save_user(user)
        return user

    async def restart(self, user: User):
        """Reset onboarding back to the beginning."""
        user.state = "new"
        user.language = None
        user.consent_status = "pending"
        user.consent_at = None
        user.consent_version = None
        user.role = None
        user.name = None
        user.preferred_name = None
        await self.storage.save_user(user)

    async def process(self, phone: str, message: dict, name: str | None = None):
        user = await self.get_or_create_user(phone, name)
        answer = self.normalize_input(message)

        # Global restart command.
        if answer in {"menu", "start over"}:
            await self.restart(user)
            return language_question()

        if user.state == "new":
            return await self.handle_new(user)

        if user.state == "awaiting_language":
            return await self.handle_language(user, answer)

        if user.state == "awaiting_consent":
            return await self.handle_consent(user, answer)

        if user.state == "awaiting_role" :
            return await self.handle_role(user, answer)

        if user.state == "active" :
            return self.handle_active(user, answer)

        if user.state == "declined":
            return await self.handle_declined(user, answer)

        # Safety fallback: never lock a user out.
        user.state = "new"
        await self.storage.save_user(user)
        return language_question()

    async def handle_new(self, user: User):
        # The first message always starts with the language list.
        # The profile name (set by the webhook) is used for the greeting.
        name = user.name  # set by the webhook before calling process()
        if name:
            user.name = name
        user.state = "awaiting_language"
        await self.storage.save_user(user)
        return create_language_message(name=name)

    async def handle_language(self, user: User, answer: str | None):
        language = None
        print("handle_language answer:", answer)

        # Interactive list selection.
        if answer in LANGUAGES:
            language = LANGUAGES[answer]


        if language is None:
            return self.invalid_answer(
                language_question(),
                "Please tap one of the language options.",
            )

        user.language = language
        print("language selected:", language)
        user.state = "awaiting_consent"
        await self.storage.save_user(user)
        return consent_message(user.language)

    async def handle_consent(self, user: User, answer: str | None):
        language = user.language or "english"

        if answer == "consent_yes":
            user.consent_status = "granted"
            user.consent_at = datetime.now(timezone.utc)
            user.consent_version = "v1"
            user.state = "awaiting_role"
            await self.storage.save_user(user)
            return create_role_message(language)

        if answer == "consent_no":
            # Declined: keep only what is needed to run the service (phone for
            # dedupe). No chat history or memory is saved.
            user.consent_status = "declined"
            user.state = "awaiting_role"
            await self.storage.save_user(user)
            return [text_message("we would not store any of our chat history"), create_role_message(language)]
        
        if answer == "consent_read_more":
            # Show the fuller notice, then re-show the buttons.
            messages = [
                text_message(full_privacy_notice(language)),
                consent_message(language),
            ]
            return messages

        return self.invalid_answer(
            consent_message(user.language),
            "Please tap one of the options.",
        )

    async def handle_role(self, user: User, answer: str | None):
        print("Role selected:", answer)
        role = None
        language = user.language or "english"

        # Interactive button selection.
        print("handle_role answer:", answer)
        if answer in ROLES:
            role = ROLES[answer]

        # # Allow typed numbers.
        # if role is None and answer == "1":
        #     role = "farmer"
        # elif role is None and answer == "2":
        #     role = "trader"
        # elif role is None and answer == "3":
        #     role = "manufacturer"
        if role is None:
            return self.invalid_answer(
                role_message(language),
                "Please tap one of the role options.",
            )

        user.role = role
        user.state = "active"
        await self.storage.save_user(user)

        return [ text_message(
            "Thanks! The main AjaTrade assistant pipeline will handle "
            "your message here.") , service_menu(user.language, name=user.preferred_name or user.name)]
    async def handle_declined(self, user: User, answer: str | None):
        language = user.language or "en"

        if answer.lower() == "yes":
            await self.restart(user)
            return language_question()

        return restart_message(language)

    def invalid_answer(self, current_question: dict, instruction: str):
        """Keep the user in their current state and show the question again."""
        question = current_question.copy()
        if question.get("type") == "text":
            question["text"]["body"] = f"{instruction}\n\n{question['text']['body']}"
        elif question.get("type") == "interactive":
            body = question["interactive"].setdefault("body", {})
            body["text"] = f"{instruction}\n\n{body.get('text', '')}"
        return question

    def handle_active(self, user: User, message: dict):
        """Placeholder for the main AjaTrade pipeline."""
        if message == "crop_detection":
            return text_message("Please send a photo or voice note of your crop problem, and we will diagnose it for you.")
        elif message == "market_price":
            return text_message("Please send the name of the crop you want to check the market price for, and we will provide you with today's market price.")
        elif message == "connect_vendor":
            return text_message("Please send the name of the fertilizer or herbicide you are looking for, and we will help you find a vendor.")

  
    def normalize_input(self, message: dict) -> str | None:
        """Return the meaningful answer from a WhatsApp message: an interactive
        reply ID, an ordinary text body, or a typed number."""
        interactive = message.get("interactive", {})
        if "button_reply" in interactive:
            return interactive["button_reply"].get("id")
        if "list_reply" in interactive:
            return interactive["list_reply"].get("id")

        text = (message.get("text", {}).get("body") or "").strip().lower()
        if text:
            return text
        return None
