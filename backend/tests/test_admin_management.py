"""Employee/branch admin UI backend (branches + employees CRUD, org-chain
assignment). Uses the `world` fixture (tenant A/B hr_admins + a cross-tenant
employee login) from conftest.py.
"""
import uuid

from conftest import auth


async def test_branch_create_and_rename(api, world):
    name = f"Branch-{uuid.uuid4().hex[:6]}"
    r = await api.post("/api/branches", headers=auth(world["A"]["token"]), json={"name": name})
    assert r.status_code == 201, r.text
    branch = r.json()

    new_name = f"{name}-renamed"
    r = await api.patch(f"/api/branches/{branch['id']}", headers=auth(world["A"]["token"]), json={"name": new_name})
    assert r.status_code == 200
    assert r.json()["name"] == new_name

    # not visible/renamable from the other tenant
    r = await api.patch(f"/api/branches/{branch['id']}", headers=auth(world["B"]["token"]), json={"name": "hack"})
    assert r.status_code == 404


async def test_employee_create_with_org_chain(api, world):
    sup_code = f"S{uuid.uuid4().hex[:5]}"
    r = await api.post("/api/employees", headers=auth(world["A"]["token"]),
                       json={"emp_code": sup_code, "full_name": "Supervisor One", "level": "supervisor"})
    assert r.status_code == 201
    sup = r.json()

    emp_code = f"E{uuid.uuid4().hex[:5]}"
    r = await api.post("/api/employees", headers=auth(world["A"]["token"]), json={
        "emp_code": emp_code, "full_name": "New Hire", "level": "operational",
        "supervisor_id": sup["id"],
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["supervisor_id"] == sup["id"]
    assert body["supervisor_name"] == "Supervisor One"


async def test_employee_update_org_chain(api, world):
    r = await api.post("/api/employees", headers=auth(world["A"]["token"]),
                       json={"emp_code": f"M{uuid.uuid4().hex[:5]}", "full_name": "Mgr", "level": "supervisor"})
    mgr = r.json()
    r = await api.post("/api/employees", headers=auth(world["A"]["token"]),
                       json={"emp_code": f"E{uuid.uuid4().hex[:5]}", "full_name": "Worker"})
    worker = r.json()

    r = await api.patch(f"/api/employees/{worker['id']}", headers=auth(world["A"]["token"]),
                        json={"manager_id": mgr["id"], "status": "inactive"})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["manager_id"] == mgr["id"]
    assert updated["status"] == "inactive"


async def test_self_supervisor_rejected(api, world):
    r = await api.post("/api/employees", headers=auth(world["A"]["token"]),
                       json={"emp_code": f"X{uuid.uuid4().hex[:5]}", "full_name": "Solo"})
    emp = r.json()
    r = await api.patch(f"/api/employees/{emp['id']}", headers=auth(world["A"]["token"]),
                        json={"supervisor_id": emp["id"]})
    assert r.status_code == 400


async def test_cross_tenant_supervisor_rejected(api, world):
    # world already seeds one employee per tenant (Alice in A, Bob in B)
    a_employees = (await api.get("/api/employees", headers=auth(world["A"]["token"]))).json()
    bob_in_b = next(e for e in (await api.get("/api/employees", headers=auth(world["B"]["token"]))).json()
                    if e["full_name"] == "Bob B")

    r = await api.post("/api/employees", headers=auth(world["A"]["token"]), json={
        "emp_code": f"Y{uuid.uuid4().hex[:5]}", "full_name": "Cross Try",
        "supervisor_id": bob_in_b["id"],   # belongs to tenant B, not A
    })
    assert r.status_code == 400

    # same check on the branch_id path
    b_branch = await api.post("/api/branches", headers=auth(world["B"]["token"]), json={"name": "B-Only"})
    r = await api.patch(f"/api/employees/{a_employees[0]['id']}", headers=auth(world["A"]["token"]),
                        json={"branch_id": b_branch.json()["id"]})
    assert r.status_code == 400


async def test_employee_rbac_update_requires_hr_admin(api, world):
    r = await api.post("/api/employees", headers=auth(world["A"]["token"]),
                       json={"emp_code": f"Z{uuid.uuid4().hex[:5]}", "full_name": "Target"})
    emp = r.json()
    r = await api.patch(f"/api/employees/{emp['id']}", headers=auth(world["emp_token"]),
                        json={"full_name": "Hacked"})
    assert r.status_code == 403
