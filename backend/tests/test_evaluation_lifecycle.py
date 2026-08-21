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
            "gm": await make("gm", "gm"),
            "hr": await make("hr", "hr_admin"),
            "emp": await make("emp", "employee", e_emp),
        }

    # Clone the master template into this tenant, same as real tenant
    # provisioning (app.clone_master_templates) -- creating an evaluation
    # against the shared master row directly is rejected now (see
    # services/evaluations.create): evaluations must reference a template
    # that belongs to the SAME company as the employee being evaluated, or
    # a confused/super_admin caller could mix one tenant's employee with
    # another tenant's custom criteria.
    master = await db.fetchrow(
        "select id, name, version, applies_to_level from criteria_templates "
        "where company_id is null and applies_to_level='operational' limit 1"
    )
    tmpl = await db.fetchval(
        "insert into criteria_templates (company_id, name, version, applies_to_level, status) "
        "values ($1, $2, $3, $4, 'active') returning id",
        cid, master["name"], master["version"], master["applies_to_level"],
    )
    categories = await db.fetch(
        "select id, sort_order, name from criteria_categories where template_id = $1 order by sort_order",
        master["id"],
    )
    for cat in categories:
        new_cat = await db.fetchval(
            "insert into criteria_categories (template_id, company_id, sort_order, name) "
            "values ($1, $2, $3, $4) returning id",
            tmpl, cid, cat["sort_order"], cat["name"],
        )
        await db.execute(
            "insert into criteria_items "
            "(category_id, company_id, sort_order, name, weight, desc_1, desc_2, desc_3, desc_4, desc_5) "
            "select $1, $2, sort_order, name, weight, desc_1, desc_2, desc_3, desc_4, desc_5 "
            "from criteria_items where category_id = $3",
            new_cat, cid, cat["id"],
        )

    yield {"cid": cid, "e_emp": e_emp, "template_id": str(tmpl), **tokens}

    for uid in user_ids:
        await db.execute("delete from auth.users where id=$1", uid)
    await db.execute("delete from companies where id=$1", cid)


def _new(org):
    return {"employee_id": org["e_emp"], "template_id": org["template_id"], "kind": "annual"}


async def _acknowledge(api, org, eid):
    """The employee signs between the dept manager's approval and GM/MD's, so
    every walk to md_approved has to pass through here (see
    services/acknowledgement.py). Shared with the other test modules that
    drive the full chain."""
    r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                       data={"decision": "acknowledged"})
    assert r.status_code == 200, r.text


async def test_create_rejects_template_from_another_company(api, org, db):
    """A template must belong to the SAME company as the employee being
    evaluated -- otherwise a confused/super_admin caller could mix one
    tenant's employee with another tenant's (possibly customized) criteria,
    and the resulting evaluation would snapshot the wrong company's items."""
    other_cid = str(uuid.uuid4())
    await db.execute("insert into companies (id,name,slug) values ($1,'Other',$2)",
                     other_cid, f"other-{uuid.uuid4().hex[:8]}")
    other_tmpl = await db.fetchval(
        "insert into criteria_templates (company_id, name, version, applies_to_level, status) "
        "values ($1, 'Other Template', 1, 'operational', 'active') returning id",
        other_cid,
    )
    try:
        payload = {"employee_id": org["e_emp"], "template_id": str(other_tmpl), "kind": "annual"}
        r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=payload)
        assert r.status_code == 400
    finally:
        await db.execute("delete from companies where id=$1", other_cid)


async def test_create_rejects_master_template_directly(api, org, db):
    """The shared master row (company_id is null) is a cloning source only
    (see app.clone_master_templates) -- every tenant gets its own copy at
    provisioning, and must use that, never the master row itself."""
    master_id = await db.fetchval(
        "select id from criteria_templates where company_id is null and applies_to_level='operational' limit 1"
    )
    payload = {"employee_id": org["e_emp"], "template_id": str(master_id), "kind": "annual"}
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=payload)
    assert r.status_code == 400


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
    # BARS anchors are snapshotted onto each item (desc_1..5 filled by seed)
    assert all(ev["items"][0][f"desc_{n}"] for n in range(1, 6))

    # supervisor scores all items = 4; HR records attendance (override 30, since
    # attendance is HR-owned data, not something the evaluator sets)
    scores = [{"evaluation_item_id": it["id"], "score": 4} for it in ev["items"]]
    r = await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]),
                      json={"scores": scores})
    assert r.status_code == 200, r.text
    d = r.json()
    assert float(d["eval_score"]) == 112 and float(d["eval_max"]) == 140

    r = await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]),
                      json={"attendance_score": 30})
    assert r.status_code == 200, r.text

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

    # MD is blocked until the employee has been shown the result and signed
    r = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    assert r.status_code == 409
    await _acknowledge(api, org, eid)

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


def _ids(inbox):
    return {row["id"]: row["action"] for row in inbox}


async def test_inbox_routes_through_each_step(api, org):
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    ev = r.json()
    eid = ev["id"]

    # right after creation: supervisor's inbox shows 'score'; nobody else's does
    sup_inbox = (await api.get("/api/evaluations/inbox", headers=auth(org["sup"]))).json()
    assert _ids(sup_inbox).get(eid) == "score"
    for tok in (org["dept"], org["md"], org["hr"], org["emp"]):
        assert eid not in _ids((await api.get("/api/evaluations/inbox", headers=auth(tok))).json())

    scores = [{"evaluation_item_id": it["id"], "score": 4} for it in ev["items"]]
    await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]), json={"scores": scores})
    await api.post(f"/api/evaluations/{eid}/submit", headers=auth(org["sup"]), json={})

    # now dept manager's inbox has it; supervisor's no longer does
    dept_inbox = (await api.get("/api/evaluations/inbox", headers=auth(org["dept"]))).json()
    assert _ids(dept_inbox).get(eid) == "dept_approve"
    sup_inbox = (await api.get("/api/evaluations/inbox", headers=auth(org["sup"]))).json()
    assert eid not in _ids(sup_inbox)

    await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["dept"]), json={})
    md_inbox = (await api.get("/api/evaluations/inbox", headers=auth(org["md"]))).json()
    assert _ids(md_inbox).get(eid) == "md_approve"

    await _acknowledge(api, org, eid)
    await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    hr_inbox = (await api.get("/api/evaluations/inbox", headers=auth(org["hr"]))).json()
    assert _ids(hr_inbox).get(eid) == "finalize"

    await api.post(f"/api/evaluations/{eid}/finalize", headers=auth(org["hr"]), json={})
    hr_inbox = (await api.get("/api/evaluations/inbox", headers=auth(org["hr"]))).json()
    assert eid not in _ids(hr_inbox)


async def test_pdf_export(api, org):
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    ev = r.json()
    eid = ev["id"]
    scores = [{"evaluation_item_id": it["id"], "score": 4} for it in ev["items"]]
    await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]), json={"scores": scores})
    await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]),
                  json={"attendance_score": 30})
    r = await api.get(f"/api/evaluations/{eid}/pdf", headers=auth(org["sup"]))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


async def test_unlinked_profile_cannot_approve_managerless_employee(api, org, db):
    """Regression: Python's `None == None` is True (unlike SQL NULL = NULL).
    A subject with no manager_id set, evaluated by a profile with no
    employee_id linked (e.g. org['hr'], created without one), must NOT
    let that unlinked profile slip through the dept-manager check just
    because both sides happen to be unset."""
    sup_emp_id = (await db.fetchrow(
        "select supervisor_id from employees where id=$1", uuid.UUID(org["e_emp"])
    ))["supervisor_id"]

    orphan = str(uuid.uuid4())
    await db.execute(
        "insert into employees (id,company_id,emp_code,full_name,level,supervisor_id,manager_id) "
        "values ($1,$2,'ORPH','Orphan','operational',$3,null)",
        orphan, org["cid"], sup_emp_id,
    )

    r = await api.post("/api/evaluations", headers=auth(org["sup"]),
                       json={"employee_id": orphan, "template_id": org["template_id"], "kind": "annual"})
    assert r.status_code == 201, r.text
    ev = r.json()
    scores = [{"evaluation_item_id": it["id"], "score": 3} for it in ev["items"]]
    await api.put(f"/api/evaluations/{ev['id']}/scores", headers=auth(org["sup"]), json={"scores": scores})
    await api.post(f"/api/evaluations/{ev['id']}/submit", headers=auth(org["sup"]), json={})

    # org["hr"] has no employee_id linked; orphan has no manager_id set.
    # Before the fix, None == None let this succeed.
    r = await api.post(f"/api/evaluations/{ev['id']}/approve", headers=auth(org["hr"]), json={})
    assert r.status_code == 403

    r = await api.post(f"/api/evaluations/{ev['id']}/return", headers=auth(org["hr"]), json={})
    assert r.status_code == 403

    await db.execute("delete from employees where id=$1", orphan)


async def test_cross_tenant_cannot_see_evaluation(api, org, world):
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = r.json()["id"]
    # a user from a different tenant must not see it
    r = await api.get(f"/api/evaluations/{eid}", headers=auth(world["A"]["token"]))
    assert r.status_code == 404


async def test_gm_approves_at_md_stage(api, org):
    """GM is interchangeable with MD at the MD/GM approval stage."""
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    ev = r.json()
    eid = ev["id"]
    scores = [{"evaluation_item_id": it["id"], "score": 4} for it in ev["items"]]
    await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]), json={"scores": scores})
    await api.post(f"/api/evaluations/{eid}/submit", headers=auth(org["sup"]), json={})
    await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["dept"]), json={})
    await _acknowledge(api, org, eid)

    # GM's inbox shows it at the MD stage, and GM can approve it
    gm_inbox = _ids((await api.get("/api/evaluations/inbox", headers=auth(org["gm"]))).json())
    assert gm_inbox.get(eid) == "md_approve"
    r = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["gm"]), json={})
    assert r.status_code == 200 and r.json()["status"] == "md_approved"


async def test_read_visibility(api, org, db):
    """subject sees own; org chain sees subordinates'; HR/GM/MD see all;
    an unrelated same-tenant employee sees nothing of it."""
    # an unrelated employee + login in the same tenant
    other_emp = str(uuid.uuid4())
    await db.execute("insert into employees (id,company_id,emp_code,full_name,level) "
                     "values ($1,$2,'OTH','Unrelated','operational')", other_emp, org["cid"])
    async with httpx.AsyncClient(timeout=20) as c:
        email = f"other-{uuid.uuid4().hex[:8]}@test.local"
        uid = await _create_user(c, email)
        await db.execute("insert into profiles (id,company_id,employee_id,display_name) values ($1,$2,$3,'other')",
                         uid, org["cid"], other_emp)
        await db.execute("insert into user_roles (profile_id,role_id,company_id) select $1,id,$2 from roles where code='employee'",
                         uid, org["cid"])
        other_token = await _token(c, email)

    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = r.json()["id"]

    async def ids_for(token):
        return {e["id"] for e in (await api.get("/api/evaluations", headers=auth(token))).json()}

    # subject (the evaluated employee) sees own
    assert eid in await ids_for(org["emp"])
    assert (await api.get(f"/api/evaluations/{eid}", headers=auth(org["emp"]))).status_code == 200
    # supervisor + dept manager (org chain) see it
    assert eid in await ids_for(org["sup"])
    assert eid in await ids_for(org["dept"])
    # HR / GM / MD see everything
    assert eid in await ids_for(org["hr"])
    assert eid in await ids_for(org["gm"])
    assert eid in await ids_for(org["md"])
    # an unrelated same-tenant employee sees nothing of it
    assert eid not in await ids_for(other_token)
    assert (await api.get(f"/api/evaluations/{eid}", headers=auth(other_token))).status_code == 404
    assert (await api.get(f"/api/evaluations/{eid}/pdf", headers=auth(other_token))).status_code == 404

    await db.execute("delete from auth.users where id=$1", uuid.UUID(uid))
    await db.execute("delete from employees where id=$1", other_emp)
