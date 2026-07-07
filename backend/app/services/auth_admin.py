"""Supabase Auth admin calls (service_role). Used to create tenant users.
This is the only place the service_role key is used — keep it server-side."""
import httpx

from app.core.config import get_settings


async def create_auth_user(email: str, password: str) -> str:
    """Create a confirmed auth user via GoTrue admin API; return its uuid."""
    settings = get_settings()
    url = f"{settings.supabase_url}/auth/v1/admin/users"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            url,
            headers=headers,
            json={"email": email, "password": password, "email_confirm": True},
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"auth admin create user failed: {resp.status_code} {resp.text}")
    return resp.json()["id"]
