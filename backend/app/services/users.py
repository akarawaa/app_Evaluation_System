"""Tenant-scoped user listing for hr_admin self-service (no super_admin
required). Unlike services/tenant_admin.py, this leans on RLS to scope
implicitly to the caller's own tenant -- appropriate here because an
hr_admin's own company_id IS the tenant being managed (unlike super_admin,
whose company_id points at the reserved platform tenant, so tenant_admin.py
must filter explicitly by a company_id path param instead)."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_users(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(text(
        "select p.id, p.display_name, p.employee_id, "
        "coalesce(array_agg(r.code) filter (where r.code is not null), '{}') as roles "
        "from profiles p "
        "left join user_roles ur on ur.profile_id = p.id "
        "left join roles r on r.id = ur.role_id "
        "group by p.id, p.display_name, p.employee_id "
        "order by p.display_name"
    ))).mappings().all()
    return [dict(r) for r in rows]
