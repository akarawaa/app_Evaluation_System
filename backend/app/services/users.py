"""Tenant-scoped user listing for hr_admin self-service (no super_admin
required). For hr_admin this leans on RLS to scope implicitly to the
caller's own tenant -- appropriate because an hr_admin's own company_id IS
the tenant being managed. super_admin's company_id points at the reserved
platform tenant instead, and RLS bypasses entirely for super_admin, so an
explicit company_id filter (same pattern as services/tenant_admin.py) is
required when a super_admin browses a specific company -- otherwise every
tenant's users would merge into one undifferentiated list.

Login active/banned status lives in auth.users, which normal sessions can't
read -- app.list_company_users() (0022_user_account_status.sql) is a
SECURITY DEFINER function that exposes just that, self-guarded the same way
as app.find_profile_by_email."""
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_users(session: AsyncSession, company_id: Optional[str] = None) -> list[dict]:
    rows = (await session.execute(
        text("select * from app.list_company_users(:cid)"), {"cid": company_id},
    )).mappings().all()
    return [dict(r) for r in rows]
