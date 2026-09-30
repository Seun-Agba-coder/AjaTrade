# from datetime import datetime, timezone

# from app.schemas.memory import Storage, User
# from app.onboarding.messages import (
#     LANGUAGES,
#     CONSENT_MESSAGES,
#     GOODBYE_MESSAGES,
#     ROLE_MESSAGES,
#     WELCOME_MESSAGES,
#     RESTART_MESSAGES,
#     language_question,
# )


# STATES = {
#     "new",
#     "awaiting_language",
#     "awaiting_consent",
#     "awaiting_role",
#     "active",
#     "declined",
# }


# VALID_ROLES = {
#     "role_farmer": "farmer",
#     "role_trader": "trader",
#     "role_manufacturer": "manufacturer",
# }


# def text_message(text: str):
#     """Simple WhatsApp text message."""
#     return {
#         "type": "text",
#         "text": {
#             "body": text
#         },
#     }


# def consent_message(language: str):
#     return {
#         "type": "interactive",
#         "interactive": {
#             "type": "button",
#             "body": {
#                 "text": CONSENT_MESSAGES.get(
#                     language,
#                     CONSENT_MESSAGES["en"],
#                 )
#             },
#             "action": {
#                 "buttons": [
#                     {
#                         "type": "reply",
#                         "reply": {
#                             "id": "consent_yes",
#                             "title": "Yes",
#                         },
#                     },
#                     {
#                         "type": "reply",
#                         "reply": {
#                             "id": "consent_no",
#                             "title": "No",
#                         },
#                     },
#                 ]
#             },
#         },
#     }


# def role_message(language: str):
#     return {
#         "type": "interactive",
#         "interactive": {
#             "type": "button",
#             "body": {
#                 "text": ROLE_MESSAGES.get(
#                     language,
#                     ROLE_MESSAGES["en"],
#                 )
#             },
#             "action": {
#                 "buttons": [
#                     {
#                         "type": "reply",
#                         "reply": {
#                             "id": "role_farmer",
#                             "title": "Farmer",
#                         },
#                     },
#                     {
#                         "type": "reply",
#                         "reply": {
#                             "id": "role_trader",
#                             "title": "Trader",
#                         },
#                     },
#                     {
#                         "type": "reply",
#                         "reply": {
#                             "id": "role_manufacturer",
#                             "title": "Manufacturer",
#                         },
#                     },
#                 ],
#             },
#         },
#     }


# def restart_message(language: str):
#     return {
#         "type": "interactive",
#         "interactive": {
#             "type": "button",
#             "body": {
#                 "text": RESTART_MESSAGES.get(
#                     language,
#                     RESTART_MESSAGES["en"],
#                 )
#             },
#             "action": {
#                 "buttons": [
#                     {
#                         "type": "reply",
#                         "reply": {
#                             "id": "restart_yes",
#                             "title": "Start over",
#                         },
#                     }
#                 ],
#             },
#         },
#     }


# def get_message_text(message: dict) -> str:
#     """
#     Extract ordinary text from a WhatsApp message.

#     Returns an empty string for media/interactive messages.
#     """
#     return (
#         message
#         .get("text", {})
#         .get("body", "")
#         .strip()
#         .lower()
#     )


# def get_interactive_id(message: dict) -> str | None:
#     """
#     Extract reply/list IDs from WhatsApp interactive messages.
#     """

#     interactive = message.get("interactive", {})

#     if "button_reply" in interactive:
#         return interactive["button_reply"].get("id")

#     if "list_reply" in interactive:
#         return interactive["list_reply"].get("id")

#     return None


# def normalize_input(message: dict) -> str | None:
#     """
#     Returns the meaningful answer from a WhatsApp message.

#     Supports:
#     - interactive reply IDs
#     - ordinary text
#     - typed numbers 1, 2, 3
#     """

#     interactive_id = get_interactive_id(message)

#     if interactive_id:
#         return interactive_id

#     text = get_message_text(message)

#     if text:
#         return text

#     return None


# def handle_active_user(user: User, message: dict):
#     """
#     Placeholder for the main AjaTrade pipeline.

#     TODO:
#     Replace this with the real pipeline:
#         voice -> speech-to-text -> translation ->
#         farming/trade reasoning -> response

#         image -> crop disease analysis -> reasoning -> response

#         text -> intent/LLM pipeline -> response
#     """

#     return text_message(
#         "Thanks! The main AjaTrade assistant pipeline will handle "
#         "your message here."
#     )


# class OnboardingStateMachine:

#     def __init__(self, storage: Storage):
#         self.storage = storage

#     def get_or_create_user(self, phone: str) -> User:
#         user = self.storage.get_user(phone)

#         if user:
#             return user

#         user = User(phone=phone)
#         self.storage.save_user(user)

#         return user

#     def restart(self, user: User):
#         """
#         Reset onboarding back to the beginning.
#         """

#         user.state = "new"
#         user.language = None
#         user.consent = None
#         user.consent_at = None
#         user.consent_text_version = None
#         user.role = None

#         self.storage.save_user(user)

#     def process(self, phone: str, message: dict):
#         user = self.get_or_create_user(phone)

#         answer = normalize_input(message)

#         # Global restart command.
#         if answer in {"menu", "start over"}:
#             self.restart(user)

#             return language_question()

#         if user.state == "new":
#             return self.handle_new(user)

#         if user.state == "awaiting_language":
#             return self.handle_language(user, answer)

#         if user.state == "awaiting_consent":
#             return self.handle_consent(user, answer)

#         if user.state == "awaiting_role":
#             return self.handle_role(user, answer)

#         if user.state == "active":
#             return handle_active_user(user, message)

#         if user.state == "declined":
#             return self.handle_declined(user, answer)

#         # Safety fallback.
#         user.state = "new"
#         self.storage.save_user(user)

#         return language_question()

#     def handle_new(self, user: User):
#         user.state = "awaiting_language"

#         self.storage.save_user(user)

#         return language_question()

#     def handle_language(
#         self,
#         user: User,
#         answer: str | None,
#     ):
#         language = None

#         # Interactive list selection.
#         if answer in LANGUAGES:
#             language = LANGUAGES[answer]

#         # Allow typed numbers.
#         elif answer == "1":
#             language = "ha"

#         elif answer == "2":
#             language = "yo"

#         elif answer == "3":
#             language = "ig"

#         elif answer == "4":
#             language = "pcm"

#         elif answer == "5":
#             language = "en"

#         if language is None:
#             return self.invalid_answer(
#                 language_question(),
#                 "Please tap one of the language options."
#             )

#         user.language = language
#         user.state = "awaiting_consent"

#         self.storage.save_user(user)

#         return consent_message(language)

#     def handle_consent(
#         self,
#         user: User,
#         answer: str | None,
#     ):
#         if answer == "consent_yes":
#             user.consent = True
#             user.consent_at = datetime.now(timezone.utc)
#             user.consent_text_version = "v1"
#             user.state = "awaiting_role"

#             self.storage.save_user(user)

#             return role_message(user.language)

#         if answer == "consent_no":
#             language = user.language or "en"

#             # The requirement says that after declining we should not
#             # store anything else about them.
#             #
#             # We retain the phone number only as the identifier needed
#             # to avoid immediately treating the same WhatsApp sender
#             # as a completely unknown request. No additional onboarding
#             # information is collected.
#             user.consent = False
#             user.state = "declined"

#             self.storage.save_user(user)

#             return text_message(
#                 GOODBYE_MESSAGES.get(
#                     language,
#                     GOODBYE_MESSAGES["en"],
#                 )
#             )

#         return self.invalid_answer(
#             consent_message(user.language or "en"),
#             "Please tap one of the options."
#         )

#     def handle_role(
#         self,
#         user: User,
#         answer: str | None,
#     ):
#         role = VALID_ROLES.get(answer)

#         if role is None:

#             # Allow typed numbers.
#             if answer == "1":
#                 role = "farmer"

#             elif answer == "2":
#                 role = "trader"

#             elif answer == "3":
#                 role = "manufacturer"

#         if role is None:
#             return self.invalid_answer(
#                 role_message(user.language or "en"),
#                 "Please tap one of the options."
#             )

#         user.role = role
#         user.state = "active"

#         self.storage.save_user(user)

#         return text_message(
#             WELCOME_MESSAGES.get(
#                 user.language or "en",
#                 WELCOME_MESSAGES["en"],
#             )
#         )

#     def handle_declined(
#         self,
#         user: User,
#         answer: str | None,
#     ):
#         language = user.language or "en"

#         if answer == "restart_yes":
#             self.restart(user)

#             return language_question()

#         return restart_message(language)

#     def invalid_answer(
#         self,
#         current_question: dict,
#         instruction: str,
#     ):
#         """
#         Off-script handling.

#         The user stays in their current state and receives the
#         current question again.
#         """

#         question = current_question.copy()

#         if question.get("type") == "text":
#             question["text"]["body"] = (
#                 f"{instruction}\n\n"
#                 f"{question['text']['body']}"
#             )

#         elif question.get("type") == "interactive":
#             interactive = question["interactive"]

#             body = interactive.setdefault("body", {})
#             body["text"] = (
#                 f"{instruction}\n\n"
#                 f"{body.get('text', '')}"
#             )

#         return question