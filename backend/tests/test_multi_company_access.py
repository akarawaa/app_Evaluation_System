"""Multi-company account switching (0021_multi_company_access.sql). One login
can hold roles in more than one company and switch which one is active;
these tests exercise the real auth hook end-to-end (fresh tokens, not mocked
claims) since the whole point is proving the JWT's company_id/roles claims
are re-scoped correctly on switch and never leak the outgoing company."""
import uuid

from conftest import _token, auth


async def test_switch_to_granted_company_updates_active_company(api, world):
    r = await api.post(
        f"/api/admin/tenants/{world['B']['company_id']}/users/grant",
        headers=auth(world["super_token"]), json={"email": world["A"]["email"], "role": "hr_admin"},
    )
    assert r.status_code == 201, r.text

    r = await api.get("/api/me/companies", headers=auth(world["A"]["token"]))
    assert r.status_code == 200, r.text
    ids = {c["company_id"] for c in r.json()}
    assert ids == {world["A"]["company_id"], world["B"]["company_id"]}

    r = await api.post("/api/me/active-company", headers=auth(world["A"]["token"]),
                        json={"company_id": world["B"]["company_id"]})
    assert r.status_code == 200, r.text

    fresh = await _token(api, world["A"]["email"])
    r = await api.get("/api/me", headers=auth(fresh))
    me = r.json()
    assert me["company_id"] == world["B"]["company_id"]
    assert me["company_name"] == "tenantB"


async def test_cannot_switch_to_company_without_a_role(api, world):
    before = (await api.get("/api/me", headers=auth(world["emp_token"]))).json()

    r = await api.post("/api/me/active-company", headers=auth(world["emp_token"]),
                        json={"company_id": world["B"]["company_id"]})
    assert r.status_code == 403, r.text

    after = (await api.get("/api/me", headers=auth(world["emp_token"]))).json()
    assert after["company_id"] == before["company_id"] == world["A"]["company_id"]


async def test_switched_session_only_sees_new_company_data(api, world):
    r = await api.post(
        f"/api/admin/tenants/{world['B']['company_id']}/users/grant",
        headers=auth(world["super_token"]), json={"email": world["A"]["email"], "role": "hr_admin"},
    )
    assert r.status_code == 201, r.text

    fresh_a = await _token(api, world["A"]["email"])
    r = await api.post("/api/me/active-company", headers=auth(fresh_a),
                        json={"company_id": world["B"]["company_id"]})
    assert r.status_code == 200, r.text

    fresh_b = await _token(api, world["A"]["email"])
    r = await api.get("/api/employees", headers=auth(fresh_b))
    names = {e["full_name"] for e in r.json()}
    assert "Bob B" in names
    assert "Alice A" not in names


async def test_roles_claim_is_scoped_to_active_company(api, world):
    r = await api.post(
        f"/api/admin/tenants/{world['B']['company_id']}/users/grant",
        headers=auth(world["super_token"]), json={"email": world["A"]["email"], "role": "manager"},
    )
    assert r.status_code == 201, r.text

    # still active in A -- a stale/buggy hook would leak B's "manager" role
    # into this claim even without switching (that was the actual bug found)
    fresh_a = await _token(api, world["A"]["email"])
    r = await api.get("/api/me", headers=auth(fresh_a))
    assert r.json()["roles"] == ["hr_admin"]

    r = await api.post("/api/me/active-company", headers=auth(fresh_a),
                        json={"company_id": world["B"]["company_id"]})
    assert r.status_code == 200, r.text

    fresh_b = await _token(api, world["A"]["email"])
    r = await api.get("/api/me", headers=auth(fresh_b))
    me = r.json()
    assert me["roles"] == ["manager"]
    assert me["company_id"] == world["B"]["company_id"]


async def test_grant_requires_super_admin(api, world):
    r = await api.post(
        f"/api/admin/tenants/{world['B']['company_id']}/users/grant",
        headers=auth(world["A"]["token"]), json={"email": world["B"]["email"], "role": "hr_admin"},
    )
    assert r.status_code == 403, r.text


async def test_grant_requires_existing_user(api, world):
    r = await api.post(
        f"/api/admin/tenants/{world['B']['company_id']}/users/grant",
        headers=auth(world["super_token"]),
        json={"email": f"nobody-{uuid.uuid4().hex[:8]}@test.local", "role": "hr_admin"},
    )
    assert r.status_code == 404, r.text
