"""App shim over `hr_platform_core.auth_admin` (platform-core/py, PLATFORM_ARCHITECTURE.md §12).

The GoTrue admin calls live in the shared package now. This module keeps
Evaluate's historical surface -- `create_auth_user(email, password)` and
`set_user_ban(user_id, banned)` -- plus `exchange_magiclink_for_session`
(used by api/auth_handoff.py for the hr-portal SSO handoff, PORTAL.md C3).
`generate_magiclink_token` is minted by the portal, not here.
"""
from hr_platform_core.auth_admin import SupabaseCreds
from hr_platform_core.auth_admin import create_auth_user as _create_auth_user
from hr_platform_core.auth_admin import (
    exchange_magiclink_for_session as _exchange_magiclink_for_session,
)
from hr_platform_core.auth_admin import set_user_ban as _set_user_ban

from app.core.config import get_settings

__all__ = ["create_auth_user", "set_user_ban", "exchange_magiclink_for_session"]


def _creds() -> SupabaseCreds:
    s = get_settings()
    return SupabaseCreds(
        url=s.supabase_url,
        service_role_key=s.supabase_service_role_key,
        anon_key=s.supabase_anon_key,
    )


async def create_auth_user(email: str, password: str) -> str:
    return await _create_auth_user(_creds(), email, password)


async def set_user_ban(user_id: str, banned: bool) -> None:
    await _set_user_ban(_creds(), user_id, banned)


async def exchange_magiclink_for_session(token_hash: str) -> dict:
    return await _exchange_magiclink_for_session(_creds(), token_hash)
