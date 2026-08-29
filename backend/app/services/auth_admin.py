"""App shim over `hr_platform_core.auth_admin` (platform-core/py, PLATFORM_ARCHITECTURE.md §12).

The GoTrue admin calls live in the shared package now. This module keeps
Evaluate's historical surface -- `create_auth_user(email, password)` and
`set_user_ban(user_id, banned)` -- binding this app's `get_settings()` onto
the package's `SupabaseCreds`. The magic-link bridge functions in the
package are unused here (Evaluate has no LINE login).
"""
from hr_platform_core.auth_admin import SupabaseCreds
from hr_platform_core.auth_admin import create_auth_user as _create_auth_user
from hr_platform_core.auth_admin import set_user_ban as _set_user_ban

from app.core.config import get_settings

__all__ = ["create_auth_user", "set_user_ban"]


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
