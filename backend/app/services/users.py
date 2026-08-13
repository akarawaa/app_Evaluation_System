"""Tenant-scoped user listing for hr_admin self-service (no super_admin
required). For hr_admin this leans on RLS to scope implicitly to the
caller's own tenant -- appropriate because an hr_admin's own company_id IS
the tenant being managed. super_admin's company_id points at the reserved
platform tenant instead, and RLS bypasses entirely for super_admin, so an
explicit company_id filter (same pattern as services/tenant_admin.py) is
required when a super_admin browses a specific company -- otherwise every
tenant's users would merge into one undifferentiated list."""
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_users(session: AsyncSession, company_id: Optional[str] = None) -> list[dict]:
    sql = (
        "select p.id, p.display_name, p.employee_id, "
        "coalesce(array_agg(r.code) filter (where r.code is not null), '{}') as roles "
        "from profiles p "
        "left join user_roles ur on ur.profile_id = p.id "
        "left join roles r on r.id = ur.role_id "
        + ("where p.company_id = :cid " if company_id else "")
        + "group by p.id, p.display_name, p.employee_id "
        "order by p.display_name"
    )
    rows = (await session.execute(text(sql), {"cid": company_id} if company_id else {})).mappings().all()
    return [dict(r) for r in rows]
