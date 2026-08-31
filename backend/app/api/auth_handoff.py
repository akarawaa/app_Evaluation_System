"""POST /api/auth/exchange -- adopt a session handed off from hr-portal.

The portal (platform-core/docs/PORTAL.md C3) verified the user's Supabase JWT
and minted a single-use magic-link `token_hash`. Here we redeem it for a real
{access_token, refresh_token} pair via GoTrue (the same path a magic-link
email would hit, so it runs app.custom_access_token_hook and carries the
right claims).

Thin proxy over GoTrue's public /verify; the token_hash is the credential
(single-use, short TTL). No auth dependency -- there is no session yet.
"""
import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services import auth_admin

logger = structlog.get_logger()
router = APIRouter(prefix="/api")


class ExchangeIn(BaseModel):
    token_hash: str = Field(min_length=16, max_length=512)


class SessionOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int | None = None


@router.post("/auth/exchange", response_model=SessionOut)
async def exchange(body: ExchangeIn) -> SessionOut:
    try:
        session = await auth_admin.exchange_magiclink_for_session(body.token_hash)
    except RuntimeError as exc:
        logger.warning("handoff_exchange_failed", error=str(exc))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "handoff token invalid or expired") from exc
    return SessionOut(**session)
