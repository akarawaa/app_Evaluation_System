"""Self-service invite: hr_admin invites users into their OWN tenant without
needing super_admin. Reuses services/tenant_admin.invite_user with
company_id pinned to the caller's verified JWT claim. Uses the `world`
fixture (tenant A/B hr_admins) from conftest.py.
"""
import uuid

import httpx

from conftest import _token, auth


async def test_list_users_is_tenant_scoped(api, world):
    a_users = (await api.get("/api/users", headers=auth(world["A"]["token"]))).json()
    b_users = (await api.get("/api/users", headers=auth(world["B"]["token"]))).json()
    assert any(u["display_name"] == "tenantA" for u in a_users)
    assert not any(u["display_name"] == "tenantB" for u in a_users)
    assert any(u["display_name"] == "tenantB" for u in b_users)


async def test_list_users_requires_hr_admin(api, world):
    r = await api.get("/api/users", headers=auth(world["emp_token"]))
    assert r.status_code == 403


async def test_hr_admin_invites_into_own_tenant_and_can_login(api, world, db):
    email = f"self-invite-{uuid.uuid4().hex[:8]}@test.local"
    r = await api.post("/api/users/invite", headers=auth(world["A"]["token"]), json={
        "email": email, "password": "Passw0rd!123", "role": "manager",
    })
    assert r.status_code == 201, r.text
    new_uid = r.json()["user_id"]

    users = (await api.get("/api/users", headers=auth(world["A"]["token"]))).json()
    invited = next(u for u in users if u["id"] == new_uid)
    assert invited["roles"] == ["manager"]

    async with httpx.AsyncClient(timeout=20) as c:
        token = await _token(c, email)
    me = (await api.get("/api/me", headers=auth(token))).json()
    assert me["company_id"] == world["A"]["company_id"]
    assert me["roles"] == ["manager"]

    await db.execute("delete from auth.users where id=$1", uuid.UUID(new_uid))


async def test_hr_admin_cannot_invite_into_other_tenant(api, world, db):
    """No target company_id is accepted from the client at all -- the invite
    always lands in the caller's own tenant, so tenant B's hr_admin can never
    place a user into tenant A via this endpoint."""
    email = f"self-invite-{uuid.uuid4().hex[:8]}@test.local"
    r = await api.post("/api/users/invite", headers=auth(world["B"]["token"]), json={
        "email": email, "password": "Passw0rd!123", "role": "manager",
    })
    assert r.status_code == 201
    new_uid = r.json()["user_id"]

    a_users = (await api.get("/api/users", headers=auth(world["A"]["token"]))).json()
    assert not any(u["id"] == new_uid for u in a_users)
    b_users = (await api.get("/api/users", headers=auth(world["B"]["token"]))).json()
    assert any(u["id"] == new_uid for u in b_users)

    await db.execute("delete from auth.users where id=$1", uuid.UUID(new_uid))


async def test_invite_requires_hr_admin(api, world):
    r = await api.post("/api/users/invite", headers=auth(world["emp_token"]),
                       json={"email": "x@test.local", "password": "Passw0rd!123", "role": "manager"})
    assert r.status_code == 403


async def test_invite_cannot_mint_super_admin(api, world):
    r = await api.post("/api/users/invite", headers=auth(world["A"]["token"]), json={
        "email": "x@test.local", "password": "Passw0rd!123", "role": "super_admin",
    })
    assert r.status_code == 422   # rejected by the schema's role pattern


async def test_invite_cross_tenant_employee_link_rejected(api, world):
    bob = next(e for e in (await api.get("/api/employees", headers=auth(world["B"]["token"]))).json()
              if e["full_name"] == "Bob B")
    r = await api.post("/api/users/invite", headers=auth(world["A"]["token"]), json={
        "email": f"x-{uuid.uuid4().hex[:6]}@test.local", "password": "Passw0rd!123",
        "role": "manager", "employee_id": bob["id"],
    })
    assert r.status_code == 400


async def _invite_no_employee(api, world, token) -> str:
    email = f"link-target-{uuid.uuid4().hex[:8]}@test.local"
    r = await api.post("/api/users/invite", headers=auth(token), json={
        "email": email, "password": "Passw0rd!123", "role": "manager",
    })
    assert r.status_code == 201, r.text
    return r.json()["user_id"]


async def test_link_user_employee(api, world, db):
    """The bug this closes: a role alone (e.g. "manager") never made a login
    functional as an evaluator -- profiles.employee_id had to be set too, and
    there was no way to do that after inviting except raw SQL. Linking it
    after the fact must make /api/me report the employee_id immediately."""
    uid = await _invite_no_employee(api, world, world["A"]["token"])
    try:
        alice = next(e for e in (await api.get("/api/employees", headers=auth(world["A"]["token"]))).json()
                     if e["full_name"] == "Alice A")

        r = await api.patch(f"/api/users/{uid}/employee", headers=auth(world["A"]["token"]),
                            json={"employee_id": alice["id"]})
        assert r.status_code == 200, r.text
        assert r.json()["employee_id"] == alice["id"]

        users = (await api.get("/api/users", headers=auth(world["A"]["token"]))).json()
        linked = next(u for u in users if u["id"] == uid)
        assert linked["employee_id"] == alice["id"]

        # Unlink (null) must clear it back out.
        r = await api.patch(f"/api/users/{uid}/employee", headers=auth(world["A"]["token"]),
                            json={"employee_id": None})
        assert r.status_code == 200
        users = (await api.get("/api/users", headers=auth(world["A"]["token"]))).json()
        assert next(u for u in users if u["id"] == uid)["employee_id"] is None
    finally:
        await db.execute("delete from auth.users where id=$1", uuid.UUID(uid))


async def test_link_user_employee_cross_tenant_rejected(api, world, db):
    uid = await _invite_no_employee(api, world, world["A"]["token"])
    try:
        bob = next(e for e in (await api.get("/api/employees", headers=auth(world["B"]["token"]))).json()
                  if e["full_name"] == "Bob B")
        r = await api.patch(f"/api/users/{uid}/employee", headers=auth(world["A"]["token"]),
                            json={"employee_id": bob["id"]})
        assert r.status_code == 400
    finally:
        await db.execute("delete from auth.users where id=$1", uuid.UUID(uid))


async def test_link_user_employee_rejects_double_binding(api, world, db):
    """Two accounts must never both claim to BE the same employee -- that
    would make "who is this evaluation's evaluator" ambiguous."""
    uid1 = await _invite_no_employee(api, world, world["A"]["token"])
    uid2 = await _invite_no_employee(api, world, world["A"]["token"])
    try:
        alice = next(e for e in (await api.get("/api/employees", headers=auth(world["A"]["token"]))).json()
                     if e["full_name"] == "Alice A")
        r = await api.patch(f"/api/users/{uid1}/employee", headers=auth(world["A"]["token"]),
                            json={"employee_id": alice["id"]})
        assert r.status_code == 200

        r = await api.patch(f"/api/users/{uid2}/employee", headers=auth(world["A"]["token"]),
                            json={"employee_id": alice["id"]})
        assert r.status_code == 400
    finally:
        await db.execute("delete from auth.users where id=$1", uuid.UUID(uid1))
        await db.execute("delete from auth.users where id=$1", uuid.UUID(uid2))


async def test_link_user_employee_requires_hr_admin(api, world):
    r = await api.patch(f"/api/users/{uuid.uuid4()}/employee", headers=auth(world["emp_token"]),
                        json={"employee_id": None})
    assert r.status_code == 403
