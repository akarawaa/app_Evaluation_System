"""Tenant provisioning (Step 6). Runs as a super_admin session; RLS allows the
cross-tenant writes via is_super_admin(). Everything is one transaction, so a
failure (e.g. auth user creation) rolls the whole tenant back."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit import write_audit
from app.services.auth_admin import create_auth_user


async def create_tenant(
    session: AsyncSession,
    *,
    actor_id: str,
    name: str,
    slug: str,
    hr_email: str,
    hr_password: str,
) -> dict:
    # 1) company
    company = (
        await session.execute(
            text("insert into companies (name, slug) values (:n, :s) returning id, name, slug"),
            {"n": name, "s": slug},
        )
    ).mappings().one()
    company_id = str(company["id"])
    await write_audit(
        session, company_id=company_id, actor_id=actor_id,
        action="tenant_created", entity_type="companies",
        entity_id=company_id, after={"name": name, "slug": slug},
    )

    # 2) clone master BARS templates into the new tenant
    templates_cloned = (
        await session.execute(
            text("select app.clone_master_templates(:cid)"), {"cid": company_id}
        )
    ).scalar_one()

    # 3) first hr_admin auth user (external call; rolls back with the tx on failure)
    hr_uid = await create_auth_user(hr_email, hr_password)

    # 4) profile + hr_admin role
    await session.execute(
        text("insert into profiles (id, company_id, display_name) values (:id, :cid, :dn)"),
        {"id": hr_uid, "cid": company_id, "dn": hr_email},
    )
    await session.execute(
        text(
            "insert into user_roles (profile_id, role_id, company_id) "
            "select :id, id, :cid from roles where code = 'hr_admin'"
        ),
        {"id": hr_uid, "cid": company_id},
    )
    await write_audit(
        session, company_id=company_id, actor_id=actor_id,
        action="user_invited", entity_type="profiles",
        entity_id=hr_uid, after={"email": hr_email, "role": "hr_admin"},
    )

    return {
        "company": {"id": company_id, "name": company["name"], "slug": company["slug"]},
        "hr_user_id": hr_uid,
        "templates_cloned": templates_cloned,
    }
