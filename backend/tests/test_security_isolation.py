"""Step 8 — automated security & multi-tenant isolation tests.

Covers: auth required on every protected endpoint, tenant scoping of reads,
cross-tenant invisibility of writes, RBAC (403), super_admin provisioning, and
security response headers.
"""
import uuid

import pytest

from conftest import auth

# minimal valid bodies so the ONLY failure for no-token requests is auth (401)
_POST_BODIES = {
    "/api/branches": {"name": "x"},
    "/api/employees": {"emp_code": "x", "full_name": "x"},
    "/api/admin/tenants": {
        "name": "x", "slug": "x-slug",
        "hr_email": "x@test.local", "hr_password": "Passw0rd!123",
    },
}


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/me"),
    ("GET", "/api/employees"),
    ("GET", "/api/branches"),
    ("POST", "/api/branches"),
    ("POST", "/api/employees"),
    ("POST", "/api/admin/tenants"),
])
async def test_endpoint_requires_auth(api, method, path):
    body = _POST_BODIES.get(path) if method == "POST" else None
    r = await api.request(method, path, json=body)
    assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


async def test_me_is_scoped_to_own_tenant(api, world):
    r = await api.get("/api/me", headers=auth(world["A"]["token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["company_id"] == world["A"]["company_id"]
    assert "hr_admin" in body["roles"]


async def test_employees_are_tenant_isolated(api, world):
    a = [e["full_name"] for e in (await api.get("/api/employees", headers=auth(world["A"]["token"]))).json()]
    b = [e["full_name"] for e in (await api.get("/api/employees", headers=auth(world["B"]["token"]))).json()]
    assert "Alice A" in a and "Bob B" not in a
    assert "Bob B" in b and "Alice A" not in b


async def test_created_branch_not_visible_to_other_tenant(api, world):
    marker = f"A-only-{uuid.uuid4().hex[:6]}"
    r = await api.post("/api/branches", headers=auth(world["A"]["token"]), json={"name": marker})
    assert r.status_code == 201
    b_branches = (await api.get("/api/branches", headers=auth(world["B"]["token"]))).json()
    assert all(x["name"] != marker for x in b_branches)


async def test_created_employee_not_visible_to_other_tenant(api, world):
    code = f"Z{uuid.uuid4().hex[:5]}"
    r = await api.post("/api/employees", headers=auth(world["A"]["token"]),
                       json={"emp_code": code, "full_name": "Secret A"})
    assert r.status_code == 201
    b_emps = (await api.get("/api/employees", headers=auth(world["B"]["token"]))).json()
    assert all(e["emp_code"] != code for e in b_emps)


async def test_rbac_employee_cannot_create_employee(api, world):
    r = await api.post("/api/employees", headers=auth(world["emp_token"]),
                       json={"emp_code": "N1", "full_name": "Nope"})
    assert r.status_code == 403


async def test_rbac_hr_admin_cannot_provision_tenant(api, world):
    r = await api.post("/api/admin/tenants", headers=auth(world["A"]["token"]), json={
        "name": "Nope", "slug": f"nope-{uuid.uuid4().hex[:6]}",
        "hr_email": "n@test.local", "hr_password": "Passw0rd!123",
    })
    assert r.status_code == 403


async def test_super_admin_can_provision_and_clone(api, world, db):
    slug = f"prov-{uuid.uuid4().hex[:8]}"
    hr_email = f"hr-{slug}@test.local"
    r = await api.post("/api/admin/tenants", headers=auth(world["super_token"]), json={
        "name": "Provisioned", "slug": slug,
        "hr_email": hr_email, "hr_password": "Passw0rd!123",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["templates_cloned"] == 2
    # cleanup the provisioned tenant + its hr user
    await db.execute("delete from companies where id=$1", body["company"]["id"])
    await db.execute("delete from auth.users where email=$1", hr_email)


async def test_security_headers_present(api):
    r = await api.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
    assert r.headers.get("X-Request-ID")


async def test_invalid_token_rejected(api):
    r = await api.get("/api/me", headers=auth("not.a.real.jwt"))
    assert r.status_code == 401
