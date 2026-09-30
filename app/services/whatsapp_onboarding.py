import httpx


class WhatsAppService:

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        api_version: str = "v23.0",
    ):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_version = api_version

        self.url = (
            f"https://graph.facebook.com/"
            f"{self.api_version}/"
            f"{self.phone_number_id}/messages"
        )

    async def send_message(
        self,
        recipient: str,
        message: dict,
    ):
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            **message,
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                headers=headers,
                json=payload,
            )

            response.raise_for_status()

            return response.json()