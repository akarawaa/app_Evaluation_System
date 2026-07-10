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
