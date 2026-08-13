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


async def set_user_ban(user_id: str, banned: bool) -> None:
    """Deactivate/reactivate a login via GoTrue's ban_duration, without
    touching the profile/user_roles rows -- so past evaluations they
    scored/approved/were subject to stay intact. Same retry-once-on-cold-start
    pattern as create_auth_user."""
    settings = get_settings()
    url = f"{settings.supabase_url}/auth/v1/admin/users/{user_id}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    # GoTrue has no "ban forever" value -- a 100-year duration is the
    # conventional stand-in; "none" clears any existing ban.
    payload = {"ban_duration": "876000h" if banned else "none"}

    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.put(url, headers=headers, json=payload)
            break
        except httpx.RequestError as exc:
            last_error = exc
            logger.warning("auth_admin_connect_failed", attempt=attempt,
                            error_type=type(exc).__name__, error=str(exc))
    else:
        logger.error("auth_admin_set_ban_failed", error_type=type(last_error).__name__,
                      error=str(last_error))
        raise RuntimeError(f"auth admin unreachable: {last_error}") from last_error

    if resp.status_code >= 400:
        logger.error("auth_admin_set_ban_rejected", status=resp.status_code, body=resp.text)
        raise RuntimeError(f"auth admin set ban failed: {resp.status_code} {resp.text}")
