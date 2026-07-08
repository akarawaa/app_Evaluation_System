"""Phase 2 Step 2 — evaluation lifecycle + approval-chain authorization.

Builds a real org chain in one tenant:
  subject employee  (supervisor_id -> S, manager_id -> D)
  S = supervisor (role manager),  D = dept manager (role dept_manager)
  MD (role md),  HR (role hr_admin),  and the subject's own login (role employee)
then walks draft -> submit -> dept -> md -> finalize, asserting each step is
locked to the correct actor.
"""
import uuid

import httpx
import pytest_asyncio

from conftest import AUTH_URL, _create_user, _token, auth  # noqa: F401


@pytest_asyncio.fixture
async def org(db):
    cid = str(uuid.uuid4())
    s_emp, d_emp, e_emp = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    user_ids: list[str] = []

    await db.execute("insert into companies (id,name,slug) values ($1,'Org',$2)",
                     cid, f"org-{uuid.uuid4().hex[:8]}")
    await db.execute("insert into employees (id,company_id,emp_code,full_name,level) "
                     "values ($1,$2,'S1','Supervisor','supervisor')", s_emp, cid)
    await db.execute("insert into employees (id,company_id,emp_code,full_name,level) "
                     "values ($1,$2,'D1','DeptMgr','supervisor')", d_emp, cid)
    await db.execute("insert into employees (id,company_id,emp_code,full_name,level,supervisor_id,manager_id) "
                     "values ($1,$2,'E1','Subject','operational',$3,$4)", e_emp, cid, s_emp, d_emp)

    async with httpx.AsyncClient(timeout=20) as c:
        async def make(prefix: str, role: str, employee_id=None) -> str:
            email = f"{prefix}-{uuid.uuid4().hex[:8]}@test.local"
            uid = await _create_user(c, email)
            user_ids.append(uid)
            await db.execute("insert into profiles (id,company_id,employee_id,display_name) values ($1,$2,$3,$4)",
                             uid, cid, employee_id, prefix)
            await db.execute("insert into user_roles (profile_id,role_id,company_id) "
                             "select $1,id,$2 from roles where code=$3", uid, cid, role)
            return await _token(c, email)

        tokens = {
            "sup": await make("sup", "manager", s_emp),
            "dept": await make("dept", "dept_manager", d_emp),
            "md": await make("md", "md"),
            "hr": await make("hr", "hr_admin"),
            "emp": await make("emp", "employee", e_emp),
        }

    tmpl = (await db.fetchrow(
        "select id from criteria_templates where company_id is null and applies_to_level='operational' limit 1"
    ))["id"]

    yield {"cid": cid, "e_emp": e_emp, "template_id": str(tmpl), **tokens}

    for uid in user_ids:
        await db.execute("delete from auth.users where id=$1", uid)
    await db.execute("delete from companies where id=$1", cid)


def _new(org):
    return {"employee_id": org["e_emp"], "template_id": org["template_id"], "kind": "annual"}


async def test_full_lifecycle(api, org):
    # employee (subject) may NOT create an evaluation for themselves
    r = await api.post("/api/evaluations", headers=auth(org["emp"]), json=_new(org))
    assert r.status_code == 403

    # supervisor creates -> snapshot 28 items
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    assert r.status_code == 201, r.text
    ev = r.json()
    eid = ev["id"]
    assert len(ev["items"]) == 28

    # supervisor scores all items = 4, attendance 30
    scores = [{"evaluation_item_id": it["id"], "score": 4} for it in ev["items"]]
    r = await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]),
                      json={"scores": scores, "attendance": {"attendance_score": 30}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert float(d["eval_score"]) == 112 and float(d["eval_max"]) == 140

    # someone who is not the evaluator cannot score
    r = await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["emp"]), json={"scores": []})
    assert r.status_code == 403

    # submit (supervisor)
    r = await api.post(f"/api/evaluations/{eid}/submit", headers=auth(org["sup"]), json={})
    assert r.status_code == 200 and r.json()["status"] == "submitted"

    # MD cannot jump the queue before the dept manager
    r = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    assert r.status_code == 403

    # dept manager approves
    r = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["dept"]), json={})
    assert r.status_code == 200 and r.json()["status"] == "dept_approved"

    # MD approves
    r = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    assert r.status_code == 200 and r.json()["status"] == "md_approved"

    # non-HR cannot finalize; HR finalizes
    r = await api.post(f"/api/evaluations/{eid}/finalize", headers=auth(org["dept"]), json={})
    assert r.status_code == 403
    r = await api.post(f"/api/evaluations/{eid}/finalize", headers=auth(org["hr"]),
                       json={"probation_decision": None})
    assert r.status_code == 200
    fin = r.json()
    assert fin["status"] == "finalized"
    assert abs(float(fin["percentage"]) - 78.89) < 0.01


async def test_return_reopens_for_editing(api, org):
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    ev = r.json()
    eid = ev["id"]
    scores = [{"evaluation_item_id": it["id"], "score": 3} for it in ev["items"]]
    await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]), json={"scores": scores})
    await api.post(f"/api/evaluations/{eid}/submit", headers=auth(org["sup"]), json={})

    # dept manager returns it
    r = await api.post(f"/api/evaluations/{eid}/return", headers=auth(org["dept"]),
                       json={"comment": "revise category 1"})
    assert r.status_code == 200 and r.json()["status"] == "returned"

    # supervisor can edit again after return
    r = await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]),
                      json={"scores": [{"evaluation_item_id": ev["items"][0]["id"], "score": 5}]})
    assert r.status_code == 200


async def test_cross_tenant_cannot_see_evaluation(api, org, world):
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = r.json()["id"]
    # a user from a different tenant must not see it
    r = await api.get(f"/api/evaluations/{eid}", headers=auth(world["A"]["token"]))
    assert r.status_code == 404
