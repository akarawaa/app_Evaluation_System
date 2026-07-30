"""Employee acknowledgement, recorded between the dept manager's approval and
GM/MD's — paper method only."""
import uuid

from conftest import auth
from test_evaluation_lifecycle import _new, org  # noqa: F401


async def _to_dept_approved(api, org):
    """Walk an evaluation to the point where the employee signs."""
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = r.json()["id"]
    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()
    scores = [{"evaluation_item_id": it["id"], "score": 4} for it in detail["items"]]
    await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]),
                  json={"scores": scores, "comments": []})
    await api.post(f"/api/evaluations/{eid}/submit", headers=auth(org["sup"]), json={})
    r = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["dept"]), json={})
    assert r.status_code == 200 and r.json()["status"] == "dept_approved", r.text
    return eid


async def test_records_paper_acknowledgement(api, org):
    eid = await _to_dept_approved(api, org)
    r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                       data={"decision": "acknowledged", "signed_at": "2026-07-30"})
    assert r.status_code == 200, r.text
    assert r.json()["decision"] == "acknowledged"

    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()
    assert detail["acknowledgement"]["method"] == "paper"
    assert detail["acknowledgement"]["decision"] == "acknowledged"


async def test_disagreement_is_still_an_acknowledgement(api, org):
    eid = await _to_dept_approved(api, org)
    r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                       data={"decision": "acknowledged_disagreed",
                             "comment": "ไม่เห็นด้วยกับคะแนนหมวดปริมาณงาน"})
    assert r.status_code == 200, r.text
    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()
    assert detail["acknowledgement"]["decision"] == "acknowledged_disagreed"
    # ...and it still unblocks GM/MD: dissent is not a veto
    r2 = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    assert r2.status_code == 200, r2.text


async def test_refusal_requires_witness_but_still_unblocks_md(api, org):
    eid = await _to_dept_approved(api, org)
    r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                       data={"decision": "refused"})
    assert r.status_code == 400

    r2 = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                        data={"decision": "refused", "witness_name": "วิชัย ขยันดี"})
    assert r2.status_code == 200, r2.text
    # an uncooperative employee must not be able to freeze the evaluation
    r3 = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    assert r3.status_code == 200, r3.text


async def test_md_blocked_until_employee_signs(api, org):
    eid = await _to_dept_approved(api, org)
    r = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    assert r.status_code == 409

    await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                   data={"decision": "acknowledged"})
    r2 = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    assert r2.status_code == 200 and r2.json()["status"] == "md_approved"


async def test_cannot_acknowledge_before_dept_approved(api, org):
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = r.json()["id"]
    r2 = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                        data={"decision": "acknowledged"})
    assert r2.status_code == 409


async def test_cannot_acknowledge_twice(api, org):
    eid = await _to_dept_approved(api, org)
    r1 = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                        data={"decision": "acknowledged"})
    assert r1.status_code == 200
    r2 = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                        data={"decision": "acknowledged"})
    assert r2.status_code == 409


async def test_supervisor_and_dept_manager_can_record(api, org):
    """They are the ones sitting with the employee; requiring HR to key every
    signature would be a bottleneck."""
    for tok in (org["sup"], org["dept"]):
        eid = await _to_dept_approved(api, org)
        r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(tok),
                           data={"decision": "acknowledged"})
        assert r.status_code == 200, r.text


async def test_md_and_subject_cannot_record(api, org):
    """GM/MD approve the very next step, so recording and approving stay in
    separate hands; the subject cannot sign themselves off either."""
    eid = await _to_dept_approved(api, org)
    for tok in (org["md"], org["gm"], org["emp"]):
        r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(tok),
                           data={"decision": "acknowledged"})
        assert r.status_code == 403, f"unexpected {r.status_code}"


async def test_return_supersedes_acknowledgement(api, org):
    """The employee signed for scores that a return is about to change, so the
    signature stops counting — but is kept as history, and a fresh one is
    required before GM/MD can approve again."""
    eid = await _to_dept_approved(api, org)
    await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                   data={"decision": "acknowledged"})

    r = await api.post(f"/api/evaluations/{eid}/return", headers=auth(org["md"]),
                       json={"comment": "ขอให้ทบทวนคะแนนหมวด 2"})
    assert r.status_code == 200 and r.json()["status"] == "returned"
    # no longer the active acknowledgement
    assert r.json()["acknowledgement"] is None

    # re-submit through the chain; MD is blocked again until a fresh signature
    await api.post(f"/api/evaluations/{eid}/submit", headers=auth(org["sup"]), json={})
    await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["dept"]), json={})
    r2 = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    assert r2.status_code == 409

    # a second acknowledgement is accepted (the unique index only covers active rows)
    r3 = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                        data={"decision": "acknowledged"})
    assert r3.status_code == 200, r3.text
    r4 = await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    assert r4.status_code == 200


async def test_superseded_acknowledgement_is_kept_as_history(api, org, db):
    eid = await _to_dept_approved(api, org)
    await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                   data={"decision": "acknowledged", "comment": "รอบแรก"})
    await api.post(f"/api/evaluations/{eid}/return", headers=auth(org["md"]), json={})

    rows = await db.fetch(
        "select comment, superseded_at from evaluation_acknowledgements where evaluation_id=$1",
        uuid.UUID(eid))
    assert len(rows) == 1
    assert rows[0]["comment"] == "รอบแรก"          # not deleted
    assert rows[0]["superseded_at"] is not None    # just no longer active


async def test_attachment_round_trips(api, org):
    eid = await _to_dept_approved(api, org)
    files = {"file": ("signed.pdf", b"%PDF-1.4 fake scan content", "application/pdf")}
    r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                       data={"decision": "acknowledged"}, files=files)
    assert r.status_code == 200, r.text

    r2 = await api.get(f"/api/evaluations/{eid}/acknowledgement-attachment", headers=auth(org["hr"]))
    assert r2.status_code == 200
    assert r2.content == b"%PDF-1.4 fake scan content"


async def test_attachment_endpoint_404_without_attachment(api, org):
    eid = await _to_dept_approved(api, org)
    await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                   data={"decision": "acknowledged"})
    r = await api.get(f"/api/evaluations/{eid}/acknowledgement-attachment", headers=auth(org["hr"]))
    assert r.status_code == 404


async def test_list_shows_acknowledgement_status(api, org):
    eid = await _to_dept_approved(api, org)
    evs = (await api.get("/api/evaluations", headers=auth(org["hr"]))).json()
    assert next(e for e in evs if e["id"] == eid)["acknowledgement_decision"] is None

    await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                   data={"decision": "acknowledged"})
    evs2 = (await api.get("/api/evaluations", headers=auth(org["hr"]))).json()
    assert next(e for e in evs2 if e["id"] == eid)["acknowledgement_decision"] == "acknowledged"
