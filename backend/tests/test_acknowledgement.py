"""Employee acknowledgement of a finalized evaluation — paper method only."""
from conftest import auth
from test_evaluation_lifecycle import _new, org  # noqa: F401


async def _finalize(api, org):
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = r.json()["id"]
    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()
    scores = [{"evaluation_item_id": it["id"], "score": 4} for it in detail["items"]]
    await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]),
                  json={"scores": scores, "comments": []})
    await api.post(f"/api/evaluations/{eid}/submit", headers=auth(org["sup"]), json={})
    await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["dept"]), json={})
    await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    r = await api.post(f"/api/evaluations/{eid}/finalize", headers=auth(org["hr"]), json={})
    assert r.status_code == 200, r.text
    return eid


async def test_hr_records_paper_acknowledgement(api, org):
    eid = await _finalize(api, org)
    r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                       data={"decision": "acknowledged", "signed_at": "2026-07-30"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["decision"] == "acknowledged"

    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()
    ack = detail["acknowledgement"]
    assert ack["method"] == "paper"
    assert ack["decision"] == "acknowledged"


async def test_disagreement_is_still_an_acknowledgement(api, org):
    eid = await _finalize(api, org)
    r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                       data={"decision": "acknowledged_disagreed",
                             "comment": "ไม่เห็นด้วยกับคะแนนหมวดปริมาณงาน"})
    assert r.status_code == 200, r.text
    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()
    assert detail["acknowledgement"]["decision"] == "acknowledged_disagreed"
    assert "ไม่เห็นด้วย" in detail["acknowledgement"]["comment"]


async def test_refusal_requires_witness(api, org):
    eid = await _finalize(api, org)
    r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                       data={"decision": "refused"})
    assert r.status_code == 400

    r2 = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                        data={"decision": "refused", "witness_name": "วิชัย ขยันดี"})
    assert r2.status_code == 200, r2.text


async def test_cannot_acknowledge_before_finalized(api, org):
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = r.json()["id"]
    r2 = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                        data={"decision": "acknowledged"})
    assert r2.status_code == 409


async def test_cannot_acknowledge_twice(api, org):
    eid = await _finalize(api, org)
    r1 = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                        data={"decision": "acknowledged"})
    assert r1.status_code == 200
    r2 = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                        data={"decision": "acknowledged"})
    assert r2.status_code == 409


async def test_only_hr_can_record_acknowledgement(api, org):
    eid = await _finalize(api, org)
    for tok in (org["sup"], org["dept"], org["md"], org["emp"]):
        r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(tok),
                           data={"decision": "acknowledged"})
        assert r.status_code == 403


async def test_attachment_round_trips(api, org):
    eid = await _finalize(api, org)
    files = {"file": ("signed.pdf", b"%PDF-1.4 fake scan content", "application/pdf")}
    r = await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                       data={"decision": "acknowledged"}, files=files)
    assert r.status_code == 200, r.text

    r2 = await api.get(f"/api/evaluations/{eid}/acknowledgement-attachment", headers=auth(org["hr"]))
    assert r2.status_code == 200
    assert r2.content == b"%PDF-1.4 fake scan content"


async def test_attachment_endpoint_404_without_attachment(api, org):
    eid = await _finalize(api, org)
    await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                   data={"decision": "acknowledged"})
    r = await api.get(f"/api/evaluations/{eid}/acknowledgement-attachment", headers=auth(org["hr"]))
    assert r.status_code == 404


async def test_list_shows_acknowledgement_status(api, org):
    eid = await _finalize(api, org)
    evs = (await api.get("/api/evaluations", headers=auth(org["hr"]))).json()
    row = next(e for e in evs if e["id"] == eid)
    assert row["acknowledgement_decision"] is None

    await api.post(f"/api/evaluations/{eid}/acknowledge-paper", headers=auth(org["hr"]),
                   data={"decision": "acknowledged"})
    evs2 = (await api.get("/api/evaluations", headers=auth(org["hr"]))).json()
    row2 = next(e for e in evs2 if e["id"] == eid)
    assert row2["acknowledgement_decision"] == "acknowledged"
