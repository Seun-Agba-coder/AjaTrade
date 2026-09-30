"""Entrypoint: ``uvicorn app.main:app --reload --host 0.0.0.0 --port 8000``."""

# netstat -ano | findstr :8000

from app.main import app

__all__ = ["app"]
