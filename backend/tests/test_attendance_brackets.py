"""HR-configurable attendance brackets (0023): RBAC, persistence, tenant
isolation, contiguous-range validation, and that a saved bracket set
actually feeds compute (set_attendance). Mirrors test_attendance_formula.py's
conventions for the older linear model this one replaces as the active
scoring path -- see services/attendance_brackets.py for why."""
from conftest import auth
from test_evaluation_lifecycle import _new, org  # noqa: F401


async def test_defaults_when_unset(api, org):
    r = await api.get("/api/settings/attendance-brackets", headers=auth(org["hr"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["personal"] == [
        {"min_value": 0, "max_value": 0, "score": 10}, {"min_value": 1, "max_value": 3, "score": 7},
        {"min_value": 4, "max_value": 7, "score": 4}, {"min_value": 8, "max_value": 12, "score": 1},
        {"min_value": 13, "max_value": None, "score": 0},
    ]
    assert body["absent"] == [
        {"min_value": 0, "max_value": 0, "score": 10}, {"min_value": 1, "max_value": 1, "score": 6},
        {"min_value": 2, "max_value": 2, "score": 3}, {"min_value": 3, "max_value": None, "score": 0},
    ]
    assert body["sick"][0] == {"min_value": 0, "max_value": 5, "score": 10}
    assert body["sick"][-1] == {"min_value": 31, "max_value": None, "score": 0}
    assert len(body["sick"]) == 7
    assert body["late"] == [
        {"min_value": 0, "max_value": 0, "score": 10}, {"min_value": 1, "max_value": 3, "score": 7},
        {"min_value": 4, "max_value": 7, "score": 4}, {"min_value": 8, "max_value": 10, "score": 1},
        {"min_value": 11, "max_value": None, "score": 0},
    ]


async def test_only_hr_can_update(api, org):
    r = await api.put("/api/settings/attendance-brackets/sick", headers=auth(org["sup"]),
                       json={"items": [{"min_value": 0, "max_value": None, "score": 10}]})
    assert r.status_code == 403


async def test_unknown_category_rejected(api, org):
    r = await api.put("/api/settings/attendance-brackets/vacation", headers=auth(org["hr"]),
                       json={"items": [{"min_value": 0, "max_value": None, "score": 10}]})
    assert r.status_code == 400


async def test_negative_values_rejected(api, org):
    r = await api.put("/api/settings/attendance-brackets/sick", headers=auth(org["hr"]),
                       json={"items": [{"min_value": -1, "max_value": None, "score": 10}]})
    assert r.status_code == 422  # pydantic ge=0 constraint


async def test_must_start_at_zero(api, org):
    r = await api.put("/api/settings/attendance-brackets/sick", headers=auth(org["hr"]), json={
        "items": [{"min_value": 1, "max_value": 5, "score": 10}, {"min_value": 6, "max_value": None, "score": 0}],
    })
    assert r.status_code == 400


async def test_must_end_unbounded(api, org):
    r = await api.put("/api/settings/attendance-brackets/sick", headers=auth(org["hr"]), json={
        "items": [{"min_value": 0, "max_value": 100, "score": 10}],
    })
    assert r.status_code == 400


async def test_gap_between_ranges_rejected(api, org):
    r = await api.put("/api/settings/attendance-brackets/sick", headers=auth(org["hr"]), json={
        "items": [{"min_value": 0, "max_value": 3, "score": 10}, {"min_value": 5, "max_value": None, "score": 0}],
    })
    assert r.status_code == 400  # gap at count=4


async def test_overlapping_ranges_rejected(api, org):
    r = await api.put("/api/settings/attendance-brackets/sick", headers=auth(org["hr"]), json={
        "items": [{"min_value": 0, "max_value": 5, "score": 10}, {"min_value": 3, "max_value": None, "score": 0}],
    })
    assert r.status_code == 400  # counts 3-5 match both


async def test_updated_brackets_persist_and_feed_compute(api, org):
    r = await api.put("/api/settings/attendance-brackets/sick", headers=auth(org["hr"]), json={
        "items": [{"min_value": 0, "max_value": 2, "score": 10}, {"min_value": 3, "max_value": None, "score": 0}],
    })
    assert r.status_code == 200, r.text

    r2 = await api.get("/api/settings/attendance-brackets", headers=auth(org["hr"]))
    assert r2.json()["sick"] == [
        {"min_value": 0, "max_value": 2, "score": 10}, {"min_value": 3, "max_value": None, "score": 0},
    ]
    # other 3 categories untouched -- still defaults
    assert len(r2.json()["personal"]) == 5

    e = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = e.json()["id"]
    r3 = await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]), json={
        "sick_days": 3, "personal_days": 0, "late_count": 0, "late_minutes": 0, "absent_days": 0,
    })
    # sick=3days -> custom bracket scores 0; personal/late/absent all at
    # default 0-count = 10 each -> total 0+10+10+10 = 30
    assert float(r3.json()["attendance"]["attendance_score"]) == 30.0


async def test_brackets_are_tenant_isolated(api, org, world):
    """Negative test (per project convention): tenant A's custom brackets
    must not leak into or affect tenant B's compute."""
    await api.put("/api/settings/attendance-brackets/sick", headers=auth(org["hr"]), json={
        "items": [{"min_value": 0, "max_value": None, "score": 0}],
    })
    # world["A"] is a separate tenant/company from org["hr"]'s -- must still see defaults
    r = await api.get("/api/settings/attendance-brackets", headers=auth(world["A"]["token"]))
    assert r.status_code == 200
    assert len(r.json()["sick"]) == 7
    assert r.json()["sick"][0]["score"] == 10
