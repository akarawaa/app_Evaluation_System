"""HR-configurable attendance formula (0017, the older linear model):
RBAC, persistence, tenant isolation.

Superseded by the bracket-based model (0023, services/attendance_brackets.py
+ test_attendance_brackets.py) as the *active* scoring path -- the real
policy scores each category by which bracket it falls in, which a linear
"full_score - coef*count" deduction can't represent. This table/endpoint is
left in place (harmless, unused by set_attendance/import from this point on)
rather than dropped, so persistence/RBAC/isolation still get covered here --
just not "does it feed compute" anymore, since it doesn't."""
from conftest import auth
from test_evaluation_lifecycle import _new, org  # noqa: F401


async def test_defaults_when_unset(api, org):
    r = await api.get("/api/settings/attendance-formula", headers=auth(org["hr"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"full_score": 40.0, "coef_absent": 4.0, "coef_personal": 1.0,
                     "coef_sick": 0.5, "coef_late": 1.0}


async def test_only_hr_can_update(api, org):
    r = await api.put("/api/settings/attendance-formula", headers=auth(org["sup"]),
                       json={"full_score": 30, "coef_absent": 1, "coef_personal": 1,
                             "coef_sick": 1, "coef_late": 1})
    assert r.status_code == 403


async def test_negative_coefficients_rejected(api, org):
    r = await api.put("/api/settings/attendance-formula", headers=auth(org["hr"]),
                       json={"full_score": 40, "coef_absent": -1, "coef_personal": 1,
                             "coef_sick": 1, "coef_late": 1})
    assert r.status_code == 422  # pydantic ge=0 constraint


async def test_updated_formula_persists(api, org):
    r = await api.put("/api/settings/attendance-formula", headers=auth(org["hr"]), json={
        "full_score": 30, "coef_absent": 2, "coef_personal": 2, "coef_sick": 2, "coef_late": 2,
    })
    assert r.status_code == 200, r.text
    assert r.json()["full_score"] == 30.0

    r2 = await api.get("/api/settings/attendance-formula", headers=auth(org["hr"]))
    assert r2.json() == {"full_score": 30.0, "coef_absent": 2.0, "coef_personal": 2.0,
                          "coef_sick": 2.0, "coef_late": 2.0}

    # Superseded (see module docstring): this formula no longer feeds
    # set_attendance's compute -- brackets do (test_attendance_brackets.py
    # covers that). Confirm it really has no effect, so this table staying
    # around never silently resurrects the old behavior.
    e = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = e.json()["id"]
    r3 = await api.put(f"/api/evaluations/{eid}/attendance", headers=auth(org["hr"]), json={
        "sick_days": 1, "personal_days": 0, "late_count": 0, "late_minutes": 0, "absent_days": 0,
    })
    # bracket defaults: sick=1 -> 0-5=10, personal/late/absent all 0-count=10 each -> 40, not 28
    assert float(r3.json()["attendance"]["attendance_score"]) == 40.0


async def test_formula_is_tenant_isolated(api, org, world):
    """Negative test (per project convention): tenant A's custom formula must
    not leak into or affect tenant B's compute."""
    await api.put("/api/settings/attendance-formula", headers=auth(org["hr"]), json={
        "full_score": 5, "coef_absent": 5, "coef_personal": 5, "coef_sick": 5, "coef_late": 5,
    })
    # world["A"] is a separate tenant/company from org["hr"]'s — must still see defaults
    r = await api.get("/api/settings/attendance-formula", headers=auth(world["A"]["token"]))
    assert r.status_code == 200
    assert r.json()["full_score"] == 40.0
