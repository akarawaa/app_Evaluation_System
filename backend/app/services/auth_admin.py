"""Supabase Auth admin calls (service_role). Used to create tenant users.
This is the only place the service_role key is used — keep it server-side."""
import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


async def create_auth_user(email: str, password: str) -> str:
    """Create a confirmed auth user via GoTrue admin API; return its uuid.

    Render's outbound connection to Supabase occasionally fails on the very
    first attempt after a cold start (DNS/TLS not warmed up yet) -- retry
    once on a connection-level failure before giving up.
    """
    settings = get_settings()
    url = f"{settings.supabase_url}/auth/v1/admin/users"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    payload = {"email": email, "password": password, "email_confirm": True}

    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(url, headers=headers, json=payload)
            break
        except httpx.RequestError as exc:
            last_error = exc
            logger.warning("auth_admin_connect_failed", attempt=attempt,
                            error_type=type(exc).__name__, error=str(exc))
    else:
        logger.error("auth_admin_create_user_failed", error_type=type(last_error).__name__,
                      error=str(last_error))
        raise RuntimeError(f"auth admin unreachable: {last_error}") from last_error

    if resp.status_code >= 400:
        logger.error("auth_admin_create_user_rejected", status=resp.status_code, body=resp.text)
        raise RuntimeError(f"auth admin create user failed: {resp.status_code} {resp.text}")
    return resp.json()["id"]
