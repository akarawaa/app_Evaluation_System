"""Attendance: HR-owned raw data -> auto-computed score (+override) + bulk CSV import."""
from conftest import auth
from test_evaluation_lifecycle import _acknowledge, _new, org  # noqa: F401

HEADER = "รหัสพนักงาน,จำนวนวันลาป่วย,จำนวนวันลากิจ,จำนวนครั้งมาสาย,จำนวนนาทีสายรวม,จำนวนวันขาดงาน"


def _att_csv(*rows: str) -> bytes:
    return ("﻿" + HEADER + "\n" + "\n".join(rows)).encode("utf-8")


async def _make_eval(api, org):  # noqa: ANN001
    r = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_evaluator_cannot_set_attendance(api, org):
    eid = await _make_eval(api, org)
    r = await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["sup"]),
                       json={"sick_days": 1})
    assert r.status_code == 403


async def test_hr_sets_attendance_auto_computed(api, org):
    eid = await _make_eval(api, org)
    # Bracket defaults (services/attendance_brackets.py, transcribed from the
    # real policy FMHR07 p.4): sick=1 -> 0-5 bracket=10, personal=2 -> 1-3
    # bracket=7, late=3 -> 1-3 bracket=7, absent=1 -> 1-1 bracket=6.
    # 10+7+7+6 = 30
    r = await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]), json={
        "sick_days": 1, "personal_days": 2, "late_count": 3, "late_minutes": 30, "absent_days": 1,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["attendance"]["attendance_score"]) == 30.0
    assert body["attendance"]["attendance_score_overridden"] is False


async def test_hr_can_override_and_override_survives_re_edit(api, org):
    eid = await _make_eval(api, org)
    r = await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]), json={
        "sick_days": 0, "personal_days": 0, "late_count": 0, "late_minutes": 0, "absent_days": 0,
        "attendance_score": 12,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["attendance"]["attendance_score"]) == 12
    assert body["attendance"]["attendance_score_overridden"] is True

    # re-editing the raw figures WITHOUT touching attendance_score must not
    # silently recompute over the manual override
    r2 = await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]), json={
        "sick_days": 5, "personal_days": 0, "late_count": 0, "late_minutes": 0, "absent_days": 0,
    })
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert float(body2["attendance"]["attendance_score"]) == 12
    assert body2["attendance"]["attendance_score_overridden"] is True
    assert body2["attendance"]["sick_days"] == 5  # figures still update

    # clear_override goes back to the formula
    r3 = await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]), json={
        "sick_days": 0, "personal_days": 0, "late_count": 0, "late_minutes": 0, "absent_days": 0,
        "clear_override": True,
    })
    body3 = r3.json()
    assert float(body3["attendance"]["attendance_score"]) == 40
    assert body3["attendance"]["attendance_score_overridden"] is False


async def test_attendance_score_feeds_total(api, org):
    eid = await _make_eval(api, org)
    await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]), json={
        "sick_days": 0, "personal_days": 0, "late_count": 0, "late_minutes": 0, "absent_days": 0,
    })
    r = await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))
    assert float(r.json()["attendance_score"]) == 40


async def test_cannot_set_attendance_after_finalize(api, org):
    eid = await _make_eval(api, org)
    for it in (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()["items"]:
        await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]),
                       json={"scores": [{"evaluation_item_id": it["id"], "score": 4}], "comments": []})
    await api.post(f"/api/evaluations/{eid}/submit", headers=auth(org["sup"]))
    await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["dept"]), json={})
    await _acknowledge(api, org, eid)
    await api.post(f"/api/evaluations/{eid}/approve", headers=auth(org["md"]), json={})
    r = await api.post(f"/api/evaluations/{eid}/finalize", headers=auth(org["hr"]), json={})
    assert r.status_code == 200, r.text

    r2 = await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]), json={"sick_days": 1})
    assert r2.status_code == 409


async def test_attendance_import_template(api, org):
    r = await api.get("/api/evaluations/attendance-import-template", headers=auth(org["hr"]))
    assert r.status_code == 200
    assert r.content.decode("utf-8-sig").splitlines()[0] == HEADER


async def test_attendance_import_updates_matching_evaluation(api, org):
    eid = await _make_eval(api, org)
    csv_bytes = _att_csv("E1,1,0,2,20,0")
    r = await api.post("/api/evaluations/attendance-import", headers=auth(org["hr"]),
                        files={"file": ("att.csv", csv_bytes, "text/csv")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["updated"] == 1
    assert body["errors"] == []

    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()
    # sick=1 -> 0-5 bracket=10, personal=0 -> 0-0 bracket=10, late=2 -> 1-3
    # bracket=7, absent=0 -> 0-0 bracket=10. 10+10+7+10 = 37
    assert float(detail["attendance"]["attendance_score"]) == 37.0


async def test_attendance_import_skips_overridden(api, org):
    eid = await _make_eval(api, org)
    await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]), json={
        "sick_days": 0, "personal_days": 0, "late_count": 0, "late_minutes": 0, "absent_days": 0,
        "attendance_score": 5,
    })
    csv_bytes = _att_csv("E1,0,0,0,0,0")
    r = await api.post("/api/evaluations/attendance-import", headers=auth(org["hr"]),
                        files={"file": ("att.csv", csv_bytes, "text/csv")})
    body = r.json()
    assert body["updated"] == 0
    assert body["skipped_overridden"] == 1

    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["hr"]))).json()
    assert float(detail["attendance"]["attendance_score"]) == 5


async def test_attendance_import_no_open_evaluation_errors(api, org):
    csv_bytes = _att_csv("NOSUCHCODE,0,0,0,0,0")
    r = await api.post("/api/evaluations/attendance-import", headers=auth(org["hr"]),
                        files={"file": ("att.csv", csv_bytes, "text/csv")})
    body = r.json()
    assert body["updated"] == 0
    assert len(body["errors"]) == 1
    assert body["errors"][0]["emp_code"] == "NOSUCHCODE"


async def test_attendance_import_rbac(api, org):
    csv_bytes = _att_csv("E1,0,0,0,0,0")
    r = await api.post("/api/evaluations/attendance-import", headers=auth(org["sup"]),
                        files={"file": ("att.csv", csv_bytes, "text/csv")})
    assert r.status_code == 403
