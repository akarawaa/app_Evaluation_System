"""Cron-triggered endpoint only -- no user JWT accepted here. An external
scheduler (same idea as the UptimeRobot keep-alive ping already documented
for cold starts) hits this once a day with a shared secret header. See
services/notifications.py for why this exists as a batch digest instead of
per-event pushes."""
from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import get_settings
from app.core.db import service_session
from app.services import notifications as notifications_svc

router = APIRouter(prefix="/api/notifications")


@router.post("/daily-digest")
async def trigger_daily_digest(
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> dict:
    settings = get_settings()
    # Fail closed: an unset secret must never be satisfied by an unset
    # header, and the check happens before any DB session is opened so an
    # unauthenticated probe never touches the database.
    if not settings.cron_secret or x_cron_secret != settings.cron_secret:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid cron secret")

    async with service_session() as session:
        return await notifications_svc.send_daily_digests(session)
