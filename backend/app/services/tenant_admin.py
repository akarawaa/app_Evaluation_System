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
from app.services.auth_admin import create_auth_user, set_user_ban

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

    users = (await session.execute(
        text("select * from app.list_company_users(:cid)"), {"cid": company_id},
    )).mappings().all()

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


async def set_user_status(
    session: AsyncSession, actor_id: str, company_id: str, profile_id: str, active: bool,
) -> dict:
    """Deactivate/reactivate a login (ban via GoTrue, see auth_admin.set_user_ban)
    without touching the profile/user_roles rows -- past evaluations they
    scored/approved/were subject to stay intact."""
    if profile_id == actor_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot deactivate your own account")

    owner = (await session.execute(
        text("select 1 from profiles where id = :pid and company_id = :cid"),
        {"pid": profile_id, "cid": company_id},
    )).first()
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found in this tenant")

    await set_user_ban(profile_id, banned=not active)

    await write_audit(
        session, company_id=company_id, actor_id=actor_id,
        action="user_activated" if active else "user_deactivated",
        entity_type="profiles", entity_id=profile_id,
    )
    return {"user_id": profile_id, "active": active}


async def link_user_employee(
    session: AsyncSession, actor_id: str, company_id: str, profile_id: str,
    employee_id: Optional[str],
) -> dict:
    """Bind (or unbind, employee_id=None) a login to an employee record.

    This is what makes a "หัวหน้างาน"/"ผจก.แผนก" role actually functional:
    evaluator/dept-manager authorization is checked against the org chain
    (employees.supervisor_id/manager_id), not the role alone (see
    services/evaluations.py). A profile invited with that role but no
    employee_id linked can log in and see menus, but can never actually
    score or approve anything -- there is nothing on the org chain that
    could ever equal an unset employee_id (see _same_employee's None-guard).
    """
    owner = (await session.execute(
        text("select 1 from profiles where id = :pid and company_id = :cid"),
        {"pid": profile_id, "cid": company_id},
    )).first()
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found in this tenant")

    if employee_id is not None:
        emp = (await session.execute(text(
            "select 1 from employees where id = :eid and company_id = :cid"
        ), {"eid": employee_id, "cid": company_id})).first()
        if emp is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "employee not found in this tenant")

        # One login per employee: two accounts both claiming to BE the same
        # employee would make "who is this evaluation's evaluator" ambiguous.
        other = (await session.execute(text(
            "select 1 from profiles where employee_id = :eid and company_id = :cid and id != :pid"
        ), {"eid": employee_id, "cid": company_id, "pid": profile_id})).first()
        if other is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "this employee is already linked to another account")

    await session.execute(text(
        "update profiles set employee_id = :eid where id = :pid"
    ), {"eid": employee_id, "pid": profile_id})

    await write_audit(
        session, company_id=company_id, actor_id=actor_id,
        action="user_employee_linked", entity_type="profiles", entity_id=profile_id,
        after={"employee_id": employee_id},
    )
    return {"user_id": profile_id, "employee_id": employee_id}
