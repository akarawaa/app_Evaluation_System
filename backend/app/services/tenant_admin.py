"""Tenant management for super_admin: list/inspect tenants, suspend/reactivate,
and invite additional users into an existing tenant.

Unlike the hr_admin-scoped services (employees.py, employee_import.py) that
lean on RLS to implicitly scope every query to `user.company_id`, a
super_admin's own company_id points at the reserved platform tenant, not the
tenant being managed. Every query here explicitly filters by the `company_id`
path parameter instead of relying on RLS to narrow it — RLS still guards the
row (is_super_admin() must be true to see across tenants at all), but the
*which tenant* filter is explicit, not implicit.
"""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit import write_audit
from app.services.auth_admin import create_auth_user

PLATFORM_SLUG = "__platform__"
INVITABLE_ROLES = {"hr_admin", "manager", "dept_manager", "md", "gm", "employee"}


async def list_tenants(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(text(
        "select c.id, c.name, c.slug, c.status, c.created_at, "
        "(select count(*) from employees e where e.company_id = c.id) as employee_count, "
        "(select count(*) from profiles p where p.company_id = c.id) as user_count "
        "from companies c where c.slug <> :platform "
        "order by c.created_at desc"
    ), {"platform": PLATFORM_SLUG})).mappings().all()
    return [dict(r) for r in rows]


async def get_tenant(session: AsyncSession, company_id: str) -> dict:
    company = (await session.execute(text(
        "select id, name, slug, status, created_at from companies where id = :id"
    ), {"id": company_id})).mappings().first()
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tenant not found")

    users = (await session.execute(text(
        "select p.id, p.display_name, p.employee_id, "
        "coalesce(array_agg(r.code) filter (where r.code is not null), '{}') as roles "
        "from profiles p "
        "left join user_roles ur on ur.profile_id = p.id "
        "left join roles r on r.id = ur.role_id "
        "where p.company_id = :id "
        "group by p.id, p.display_name, p.employee_id "
        "order by p.display_name"
    ), {"id": company_id})).mappings().all()

    out = dict(company)
    out["users"] = [dict(u) for u in users]
    return out


async def update_tenant_status(session: AsyncSession, actor_id: str, company_id: str, new_status: str) -> dict:
    before = (await session.execute(
        text("select status from companies where id = :id"), {"id": company_id}
    )).first()
    if before is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tenant not found")

    row = (await session.execute(text(
        "update companies set status = :s where id = :id "
        "returning id, name, slug, status, created_at"
    ), {"s": new_status, "id": company_id})).mappings().one()

    await write_audit(
        session, company_id=company_id, actor_id=actor_id,
        action="tenant_status_changed", entity_type="companies", entity_id=company_id,
        before={"status": before[0]}, after={"status": new_status},
    )
    return dict(row)


async def invite_user(
    session: AsyncSession, actor_id: str, company_id: str,
    email: str, password: str, role_code: str, employee_id: Optional[str] = None,
) -> dict:
    if role_code not in INVITABLE_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid role: {role_code}")

    company = (await session.execute(
        text("select id from companies where id = :id"), {"id": company_id}
    )).first()
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tenant not found")

    if employee_id is not None:
        emp = (await session.execute(text(
            "select id from employees where id = :eid and company_id = :cid"
        ), {"eid": employee_id, "cid": company_id})).first()
        if emp is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "employee not found in this tenant")

    uid = await create_auth_user(email, password)
    await session.execute(text(
        "insert into profiles (id, company_id, employee_id, display_name) "
        "values (:id, :cid, :eid, :dn)"
    ), {"id": uid, "cid": company_id, "eid": employee_id, "dn": email})
    await session.execute(text(
        "insert into user_roles (profile_id, role_id, company_id) "
        "select :id, id, :cid from roles where code = :code"
    ), {"id": uid, "cid": company_id, "code": role_code})

    await write_audit(
        session, company_id=company_id, actor_id=actor_id,
        action="user_invited", entity_type="profiles", entity_id=uid,
        after={"email": email, "role": role_code},
    )
    return {"user_id": uid, "email": email, "role": role_code}


async def grant_company_access(
    session: AsyncSession, actor_id: str, company_id: str, email: str, role_code: str,
) -> dict:
    """Give an EXISTING account a role in another company (super_admin only --
    see app.find_profile_by_email / app.switch_active_company in
    0021_multi_company_access.sql). A brand-new person still goes through
    invite_user; this is only for someone who already has a login."""
    if role_code not in INVITABLE_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid role: {role_code}")

    company = (await session.execute(
        text("select id from companies where id = :id"), {"id": company_id}
    )).first()
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tenant not found")

    profile_id = (await session.execute(
        text("select app.find_profile_by_email(:email)"), {"email": email}
    )).scalar_one_or_none()
    if profile_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no existing account for that email")

    existing = (await session.execute(text(
        "select 1 from user_roles where profile_id = :pid and company_id = :cid"
    ), {"pid": profile_id, "cid": company_id})).first()
    if existing is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "already has a role in this company")

    await session.execute(text(
        "insert into user_roles (profile_id, role_id, company_id) "
        "select :id, id, :cid from roles where code = :code"
    ), {"id": profile_id, "cid": company_id, "code": role_code})

    await write_audit(
        session, company_id=company_id, actor_id=actor_id,
        action="role_granted", entity_type="profiles", entity_id=profile_id,
        after={"email": email, "role": role_code},
    )
    return {"user_id": str(profile_id), "email": email, "role": role_code}
