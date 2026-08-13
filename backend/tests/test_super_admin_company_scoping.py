"""super_admin browsing employees/branches/users via explicit ?company_id=
(the "จัดการพนักงาน & สาขาของบริษัทนี้" flow from TenantDetail.tsx).

Before this, list_employees/list_branches/list_users relied purely on
implicit RLS scoping, which is a no-op for super_admin (is_super_admin()
bypasses every RLS policy) -- so a super_admin visiting the People page saw
every tenant's employees/users merged into one list with no way to tell them
apart. See docs/SECURITY.md "super_admin ดูข้อมูลพนักงาน/สาขา/user แยกตามบริษัท".
"""
from conftest import auth


async def test_super_admin_company_id_scopes_employees(api, world):
    r = await api.get("/api/employees", params={"company_id": world["A"]["company_id"]},
                      headers=auth(world["super_token"]))
    assert r.status_code == 200
    codes = {e["emp_code"] for e in r.json()}
    assert codes == {"A001"}


async def test_super_admin_company_id_scopes_users(api, world):
    r = await api.get("/api/users", params={"company_id": world["B"]["company_id"]},
                      headers=auth(world["super_token"]))
    assert r.status_code == 200
    for u in r.json():
        assert u["display_name"] != world["A"]["email"]


async def test_super_admin_without_company_id_still_sees_everything(api, world):
    """Documented behaviour, not a target to fix here: omitting company_id
    keeps the old cross-tenant-merge behavior for super_admin -- callers that
    need company-scoped results must pass it explicitly."""
    r = await api.get("/api/employees", headers=auth(world["super_token"]))
    assert r.status_code == 200
    codes = {e["emp_code"] for e in r.json()}
    assert {"A001", "B001"}.issubset(codes)


async def test_hr_admin_cannot_pass_company_id_for_another_tenant(api, world):
    """The critical negative test: a non-super_admin must never be able to use
    this param to read another tenant's data."""
    r = await api.get("/api/employees", params={"company_id": world["B"]["company_id"]},
                      headers=auth(world["A"]["token"]))
    assert r.status_code == 403


async def test_hr_admin_cannot_pass_company_id_for_own_tenant_either(api, world):
    """Even passing your OWN company_id explicitly is rejected -- the param is
    super_admin-only, full stop, not just "can't target someone else's"."""
    r = await api.get("/api/employees", params={"company_id": world["A"]["company_id"]},
                      headers=auth(world["A"]["token"]))
    assert r.status_code == 403


async def test_invite_via_company_id_lands_in_target_company_not_super_admins_own(api, world):
    email = f"invited-{world['A']['company_id'][:8]}@test.local"
    r = await api.post(
        "/api/users/invite", params={"company_id": world["A"]["company_id"]},
        json={"email": email, "password": "Passw0rd!123", "role": "manager"},
        headers=auth(world["super_token"]),
    )
    assert r.status_code == 201

    r2 = await api.get("/api/users", params={"company_id": world["A"]["company_id"]},
                       headers=auth(world["super_token"]))
    assert any(u["display_name"] == email for u in r2.json())
