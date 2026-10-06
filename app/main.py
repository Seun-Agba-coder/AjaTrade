"""Application factory and FastAPI instance."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.storage import storage

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Open the storage pool on startup and close it on shutdown."""
    await storage.connect()
    try:
        yield
    finally:
        await storage.close()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title="WhatsApp Webhook",
        version="0.1.0",
        description="Receives and verifies WhatsApp Cloud API webhook events.",
        lifespan=lifespan,
    )
    application.include_router(api_router)
    return application


app = create_app()
