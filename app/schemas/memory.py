from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    phone: str
    state: str = "new"
    language: str | None = None
    role: str | None = None


class InMemoryStorage:
    def __init__(self):
        # All users will be stored here while the server is running.
        # WARNING: all data is lost when the application restarts.
        self.users = {}

    def get_user(self, phone: str) -> Optional[User]:
        return self.users.get(phone)

    def save_user(self, user: User):
        self.users[user.phone] = user
    def get_state(self, phone: str):
            user = self.get_user(phone)
            return user.state if user else None

    def get_role(self, phone: str):
            user = self.get_user(phone)
            return user.role if user else None


storage = InMemoryStorage()