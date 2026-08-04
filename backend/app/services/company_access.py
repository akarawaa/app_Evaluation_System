"""Multi-company switching for a single login. See 0021_multi_company_access.sql
-- the actual validation (does this profile hold a role in the target
company?) happens inside the SECURITY DEFINER SQL functions, not here; this
module is a thin, audited wrapper around them."""
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit import write_audit


async def list_my_companies(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(text("select * from app.list_my_companies()"))
    ).mappings().all()
    return [dict(r) for r in rows]


async def switch_active_company(
    session: AsyncSession, actor_id: str, actor_company_id: str | None, target_company_id: str,
) -> dict:
    ok = (
        await session.execute(
            text("select app.switch_active_company(:cid)"), {"cid": target_company_id}
        )
    ).scalar_one()
    if not ok:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No role in that company")

    # audit_logs RLS checks company_id = current_company_id() -- the session's
    # JWT is still the pre-switch token, so the row must be filed under the
    # OUTGOING company, not the target (a fresh token after the client
    # refreshes will carry the new company_id for everything that follows).
    await write_audit(
        session, company_id=actor_company_id, actor_id=actor_id,
        action="active_company_switched", entity_type="profiles", entity_id=actor_id,
        before={"company_id": actor_company_id}, after={"company_id": target_company_id},
    )
    return {"company_id": target_company_id}
