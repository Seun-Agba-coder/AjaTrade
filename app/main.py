"""Application factory and FastAPI instance."""

import logging

from fastapi import FastAPI

from app.api.router import api_router

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title="WhatsApp Webhook",
        version="0.1.0",
        description="Receives and verifies WhatsApp Cloud API webhook events.",
    )
    application.include_router(api_router)
    return application


app = create_app()
