"""Evaluation comparison — mode A (multiple employees, same cycle) and mode B
(same employee, across time) are the same endpoint; both just enforce the
existing per-evaluation visibility check and pivot scores by item_name."""
import uuid

import httpx

from conftest import _create_user, _token, auth
from test_evaluation_lifecycle import _new, org  # noqa: F401


async def _score_all(api, org, eid, score):
    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()
    scores = [{"evaluation_item_id": it["id"], "score": score} for it in detail["items"]]
    await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]),
                  json={"scores": scores, "comments": []})


async def test_compare_requires_2_to_5_ids(api, org):
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = r.json()["id"]

    r1 = await api.get("/api/evaluations/compare", headers=auth(org["hr"]), params={"ids": [eid]})
    assert r1.status_code == 400

    r2 = await api.get("/api/evaluations/compare", headers=auth(org["hr"]),
                       params={"ids": [eid] * 6})  # de-duped to 1 -> still fails count check
    assert r2.status_code == 400


async def test_compare_same_employee_across_time(api, org):
    """Mode B: same employee, two evaluations (e.g. two annual cycles)."""
    r1 = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid1 = r1.json()["id"]
    await _score_all(api, org, eid1, 3)

    r2 = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid2 = r2.json()["id"]
    await _score_all(api, org, eid2, 5)

    r = await api.get("/api/evaluations/compare", headers=auth(org["hr"]), params={"ids": [eid1, eid2]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["columns"]) == 2
    assert {c["emp_code"] for c in body["columns"]} == {"E1"}
    assert len(body["rows"]) == 28
    row0 = body["rows"][0]
    assert float(row0["scores"][eid1]) == 3
    assert float(row0["scores"][eid2]) == 5


async def test_compare_multiple_employees_same_cycle(api, org, db):
    """Mode A: two different employees, same reporting line."""
    e2 = str(uuid.uuid4())
    s_emp = (await db.fetchrow(
        "select id from employees where company_id=$1 and emp_code='S1'", uuid.UUID(org["cid"])
    ))["id"]
    await db.execute("insert into employees (id,company_id,emp_code,full_name,level,supervisor_id) "
                     "values ($1,$2,'E2','Second','operational',$3)", e2, org["cid"], s_emp)

    r1 = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid1 = r1.json()["id"]
    await _score_all(api, org, eid1, 4)

    r2 = await api.post("/api/evaluations", headers=auth(org["sup"]),
                        json={"employee_id": e2, "template_id": org["template_id"], "kind": "annual"})
    assert r2.status_code == 201, r2.text
    eid2 = r2.json()["id"]
    await _score_all(api, org, eid2, 2)

    r = await api.get("/api/evaluations/compare", headers=auth(org["hr"]), params={"ids": [eid1, eid2]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert {c["emp_code"] for c in body["columns"]} == {"E1", "E2"}


async def test_compare_enforces_visibility(api, org, db):
    """An evaluation outside the caller's org chain (and not HR/GM/MD) 404s
    the whole comparison, same as opening it directly would."""
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

    r1 = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid1 = r1.json()["id"]
    r2 = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid2 = r2.json()["id"]

    # the "other" employee's login isn't in the subject's org chain and isn't
    # HR/GM/MD, so comparing must 404 the same way GET /{id} would
    r = await api.get("/api/evaluations/compare", headers=auth(other_token), params={"ids": [eid1, eid2]})
    assert r.status_code == 404

    await db.execute("delete from auth.users where id=$1", uuid.UUID(uid))
    await db.execute("delete from employees where id=$1", uuid.UUID(other_emp))


async def test_compare_is_audit_logged(api, org, db):
    r1 = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid1 = r1.json()["id"]
    r2 = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid2 = r2.json()["id"]

    r = await api.get("/api/evaluations/compare", headers=auth(org["hr"]), params={"ids": [eid1, eid2]})
    assert r.status_code == 200

    row = await db.fetchrow(
        "select action, after from audit_logs where company_id=$1 and action='evaluations_compared' "
        "order by created_at desc limit 1", org["cid"])
    assert row is not None
    assert eid1 in row["after"] and eid2 in row["after"]
