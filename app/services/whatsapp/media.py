"""
WhatsApp Cloud API — media (voice note) retrieval.
 
Meta's flow for downloading inbound media is two calls:
  1. GET  https://graph.facebook.com/{version}/{media_id}
     -> returns a short-lived, signed media URL + metadata (mime_type, sha256, file_size)
  2. GET  <that url>  with your access token as a Bearer header
     -> returns the raw binary bytes
 
The media URL from step 1 expires quickly (minutes), so always fetch it fresh —
never cache or reuse it.
"""
 
import httpx
from fastapi import HTTPException
 
from app.config import get_settings  # WHATSAPP_ACCESS_TOKEN, WHATSAPP_API_VERSION
import os
 
 
GRAPH_BASE_URL = f"https://graph.facebook.com/{get_settings().whatsapp_api_version}"
 
 
async def get_media_url(media_id: str) -> dict:
    """Step 1: resolve a media_id to a temporary download URL + metadata."""
    headers = {"Authorization": f"Bearer {os.getenv('WHATSAPP_ACCESS_TOKEN', '')}"}
 
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(f"{GRAPH_BASE_URL}/{media_id}", headers=headers)
 
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to resolve WhatsApp media_id={media_id}: {response.text}",
        )
 
    return response.json()  # {"url": ..., "mime_type": ..., "sha256": ..., "file_size": ..., "id": ...}
 
 
async def download_media(media_url: str) -> bytes:
    """Step 2: download the actual binary from the signed media URL."""
    headers = {"Authorization": f"Bearer {os.getenv('WHATSAPP_ACCESS_TOKEN', '')}"}
 
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(media_url, headers=headers)
 
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to download WhatsApp media binary: {response.status_code}",
        )
 
    return response.content
 
 
async def fetch_voice_note(media_id: str) -> tuple[bytes, str]:
    """
    Convenience wrapper: media_id -> (audio_bytes, mime_type).
    This is what your webhook handler / STT stage should call.
    """
    meta = await get_media_url(media_id)
    audio_bytes = await download_media(meta["url"])
    return audio_bytes, meta.get("mime_type", "audio/ogg")