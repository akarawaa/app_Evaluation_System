"""Tenant management for super_admin: list/detail, suspend/reactivate
(enforced in get_tenant_session), and inviting additional users into an
existing tenant. Uses the `world` fixture (tenant A/B + super_admin) from
conftest.py.
"""
import uuid

import httpx

from conftest import _token, auth


async def test_list_tenants_requires_super_admin(api, world):
    r = await api.get("/api/admin/tenants", headers=auth(world["A"]["token"]))
    assert r.status_code == 403


async def test_list_tenants_includes_seeded_companies(api, world):
    r = await api.get("/api/admin/tenants", headers=auth(world["super_token"]))
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert world["A"]["company_id"] in ids
    assert world["B"]["company_id"] in ids
    # the reserved platform tenant must never show up in the customer list
    assert not any(t["slug"] == "__platform__" for t in r.json())


async def test_get_tenant_detail_lists_users(api, world):
    r = await api.get(f"/api/admin/tenants/{world['A']['company_id']}", headers=auth(world["super_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == world["A"]["company_id"]
    hr_user = next(u for u in body["users"] if u["display_name"] == "tenantA")
    assert "hr_admin" in hr_user["roles"]


async def test_get_tenant_not_found(api, world):
    r = await api.get(f"/api/admin/tenants/{uuid.uuid4()}", headers=auth(world["super_token"]))
    assert r.status_code == 404


async def test_get_tenant_detail_requires_super_admin(api, world):
    r = await api.get(f"/api/admin/tenants/{world['A']['company_id']}", headers=auth(world["A"]["token"]))
    assert r.status_code == 403


async def test_suspend_blocks_tenant_access_then_reactivate_restores_it(api, world):
    cid = world["A"]["company_id"]
    token = world["A"]["token"]

    assert (await api.get("/api/employees", headers=auth(token))).status_code == 200

    r = await api.patch(f"/api/admin/tenants/{cid}/status", headers=auth(world["super_token"]), json={"status": "suspended"})
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"

    r = await api.get("/api/employees", headers=auth(token))
    assert r.status_code == 403

    r = await api.patch(f"/api/admin/tenants/{cid}/status", headers=auth(world["super_token"]), json={"status": "active"})
    assert r.status_code == 200

    assert (await api.get("/api/employees", headers=auth(token))).status_code == 200


async def test_suspend_requires_super_admin(api, world):
    r = await api.patch(f"/api/admin/tenants/{world['A']['company_id']}/status",
                        headers=auth(world["A"]["token"]), json={"status": "suspended"})
    assert r.status_code == 403


async def test_invite_user_and_login(api, world, db):
    cid = world["A"]["company_id"]
    email = f"invited-{uuid.uuid4().hex[:8]}@test.local"
    r = await api.post(f"/api/admin/tenants/{cid}/users", headers=auth(world["super_token"]), json={
        "email": email, "password": "Passw0rd!123", "role": "dept_manager",
    })
    assert r.status_code == 201, r.text
    new_uid = r.json()["user_id"]

    detail = (await api.get(f"/api/admin/tenants/{cid}", headers=auth(world["super_token"]))).json()
    invited = next(u for u in detail["users"] if u["id"] == new_uid)
    assert invited["roles"] == ["dept_manager"]

    async with httpx.AsyncClient(timeout=20) as c:
        token = await _token(c, email)
    me = (await api.get("/api/me", headers=auth(token))).json()
    assert me["company_id"] == cid
    assert me["roles"] == ["dept_manager"]

    await db.execute("delete from auth.users where id=$1", uuid.UUID(new_uid))


async def test_invite_user_requires_super_admin(api, world):
    r = await api.post(f"/api/admin/tenants/{world['A']['company_id']}/users",
                       headers=auth(world["A"]["token"]),
                       json={"email": "x@test.local", "password": "Passw0rd!123", "role": "manager"})
    assert r.status_code == 403


async def test_invite_user_cannot_mint_super_admin(api, world):
    r = await api.post(f"/api/admin/tenants/{world['A']['company_id']}/users", headers=auth(world["super_token"]), json={
        "email": "x@test.local", "password": "Passw0rd!123", "role": "super_admin",
    })
    assert r.status_code == 422   # rejected by the schema's role pattern


async def test_invite_user_cross_tenant_employee_rejected(api, world):
    bob = next(e for e in (await api.get("/api/employees", headers=auth(world["B"]["token"]))).json()
              if e["full_name"] == "Bob B")
    r = await api.post(f"/api/admin/tenants/{world['A']['company_id']}/users", headers=auth(world["super_token"]), json={
        "email": f"x-{uuid.uuid4().hex[:6]}@test.local", "password": "Passw0rd!123",
        "role": "manager", "employee_id": bob["id"],
    })
    assert r.status_code == 400


# ── revoke_role (hr_admin self-service, /api/users/{profile_id}/roles/{code}) ──
# For a department transfer: pull one role off an existing account without
# banning the whole login (contrast with set_user_status, tested elsewhere).

async def test_hr_admin_revokes_a_role_login_still_works(api, world):
    r = await api.delete(f"/api/users/{world['emp_uid']}/roles/employee", headers=auth(world["A"]["token"]))
    assert r.status_code == 200, r.text
    assert r.json() == {"user_id": world["emp_uid"], "role": "employee"}

    detail = (await api.get(f"/api/admin/tenants/{world['A']['company_id']}", headers=auth(world["super_token"]))).json()
    target = next(u for u in detail["users"] if u["id"] == world["emp_uid"])
    assert target["roles"] == []
    assert target["active"] is True  # login itself untouched -- only the role row is gone

    # The banned-login path (set_user_status) is what actually blocks access;
    # revoking a role alone doesn't ban anything, so /me still succeeds (the
    # JWT's roles claim is only refreshed on next login/token-refresh, per
    # the auth hook -- app.list_company_users() above is the live source of
    # truth in the meantime, already asserted empty).
    me = await api.get("/api/me", headers=auth(world["emp_token"]))
    assert me.status_code == 200


async def test_revoke_role_requires_hr_admin(api, world):
    r = await api.delete(f"/api/users/{world['emp_uid']}/roles/employee", headers=auth(world["emp_token"]))
    assert r.status_code == 403


async def test_revoke_role_rejects_invalid_role_code(api, world):
    r = await api.delete(f"/api/users/{world['emp_uid']}/roles/bogus", headers=auth(world["A"]["token"]))
    assert r.status_code == 400

    # super_admin is never grantable/revocable through this tenant-scoped API.
    r = await api.delete(f"/api/users/{world['emp_uid']}/roles/super_admin", headers=auth(world["A"]["token"]))
    assert r.status_code == 400


async def test_revoke_role_404_when_user_lacks_that_role(api, world):
    r = await api.delete(f"/api/users/{world['emp_uid']}/roles/hr_admin", headers=auth(world["A"]["token"]))
    assert r.status_code == 404


async def test_hr_admin_cannot_revoke_own_role(api, world):
    r = await api.delete(f"/api/users/{world['A']['uid']}/roles/hr_admin", headers=auth(world["A"]["token"]))
    assert r.status_code == 400


async def test_revoke_role_is_tenant_isolated(api, world):
    # hr_admin of tenant A's own company_id scopes the lookup (they can't
    # pass company_id themselves -- _resolve_company would 403 that) -- tenant
    # B's profile_id simply isn't found under tenant A's company_id.
    r = await api.delete(f"/api/users/{world['B']['uid']}/roles/hr_admin", headers=auth(world["A"]["token"]))
    assert r.status_code == 404


async def test_super_admin_revokes_role_via_company_id(api, world):
    r = await api.delete(
        f"/api/users/{world['emp_uid']}/roles/employee?company_id={world['A']['company_id']}",
        headers=auth(world["super_token"]),
    )
    assert r.status_code == 200, r.text
