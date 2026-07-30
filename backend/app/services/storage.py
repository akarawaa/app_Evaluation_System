"""Supabase Storage calls (service_role), same pattern as auth_admin.py --
raw httpx against the REST API rather than the supabase-py SDK, service_role
key never leaves the server."""
import httpx

from app.core.config import get_settings

BUCKET = "acknowledgement-scans"


async def upload_object(path: str, content: bytes, content_type: str) -> None:
    settings = get_settings()
    url = f"{settings.supabase_url}/storage/v1/object/{BUCKET}/{path}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": content_type or "application/octet-stream",
        # Evidence: never silently overwrite a prior scan for the same path.
        "x-upsert": "false",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, content=content)
    if resp.status_code >= 400:
        raise RuntimeError(f"storage upload failed: {resp.status_code} {resp.text}")


async def download_object(path: str) -> bytes:
    settings = get_settings()
    url = f"{settings.supabase_url}/storage/v1/object/{BUCKET}/{path}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"storage download failed: {resp.status_code} {resp.text}")
    return resp.content
