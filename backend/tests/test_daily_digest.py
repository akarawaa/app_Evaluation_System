"""Daily digest endpoint (services/notifications.py) -- cron-secret gating,
plus the routing query itself: right person notified for the right stage,
and distinct people get distinct counts rather than being merged/dropped.

Success-path tests need a real CRON_SECRET configured in backend/.env (left
blank by default, same "feature disabled until configured" convention as
BREVO_API_KEY) -- they skip gracefully if it isn't set rather than failing,
since a blank secret is a valid local state, not a bug.
"""
import json
from pathlib import Path

import pytest

from conftest import auth
from test_evaluation_lifecycle import _new, org  # noqa: F401


def _cron_secret() -> str:
    env = Path(__file__).resolve().parents[1] / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("CRON_SECRET="):
            return line.split("=", 1)[1].strip()
    return ""


async def _digest_after(db, api, secret, company_id):
    r = await api.post("/api/notifications/daily-digest", headers={"X-Cron-Secret": secret})
    assert r.status_code == 200, r.text
    row = await db.fetchrow(
        "select after from audit_logs where company_id = $1 and action = 'digest_emails_sent' "
        "order by created_at desc limit 1",
        company_id,
    )
    assert row is not None, "digest run wrote no audit row for this company"
    return json.loads(row["after"])


async def test_missing_secret_rejected(api):
    r = await api.post("/api/notifications/daily-digest")
    assert r.status_code == 403


async def test_wrong_secret_rejected(api):
    r = await api.post("/api/notifications/daily-digest", headers={"X-Cron-Secret": "definitely-wrong"})
    assert r.status_code == 403


async def test_digest_targets_evaluator_at_draft(api, org, db):
    secret = _cron_secret()
    if not secret:
        pytest.skip("CRON_SECRET not set in backend/.env locally")

    await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))

    after = await _digest_after(db, api, secret, org["cid"])
    assert after == {"recipients": 1, "items": 1}


async def test_digest_target_switches_to_dept_manager_on_submit(api, org, db):
    secret = _cron_secret()
    if not secret:
        pytest.skip("CRON_SECRET not set in backend/.env locally")

    ev = await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))
    eid = ev.json()["id"]
    detail = (await api.get(f"/api/evaluations/{eid}", headers=auth(org["sup"]))).json()
    scores = [{"evaluation_item_id": it["id"], "score": 4} for it in detail["items"]]
    await api.put(f"/api/evaluations/{eid}/scores", headers=auth(org["sup"]),
                  json={"scores": scores, "comments": []})
    await api.post(f"/api/evaluations/{eid}/submit", headers=auth(org["sup"]), json={})

    # Still exactly one pending item, one recipient -- but it's now the dept
    # manager's turn, not the evaluator's (proven properly below by the
    # two-distinct-recipients test, since counts alone can't tell WHO).
    after = await _digest_after(db, api, secret, org["cid"])
    assert after == {"recipients": 1, "items": 1}


async def test_digest_counts_distinct_people_separately(api, org, db):
    """Two subjects sharing the same supervisor/manager: one evaluation left
    at draft (targets the evaluator), the other scored+submitted (targets
    the dept manager) -- two different people, so recipients must be 2, not
    1 (which would mean the grouping collapsed distinct targets together)."""
    secret = _cron_secret()
    if not secret:
        pytest.skip("CRON_SECRET not set in backend/.env locally")

    emps = (await api.get("/api/employees", headers=auth(org["hr"]))).json()
    s1 = next(e for e in emps if e["emp_code"] == "S1")["id"]
    d1 = next(e for e in emps if e["emp_code"] == "D1")["id"]

    e2 = (await api.post("/api/employees", headers=auth(org["hr"]), json={
        "emp_code": "E2", "full_name": "Subject Two", "level": "operational",
        "supervisor_id": s1, "manager_id": d1,
    })).json()["id"]

    # eval #1 stays at draft -> targets the evaluator (org's built-in subject)
    await api.post("/api/evaluations", headers=auth(org["sup"]), json=_new(org))

    # eval #2 -> score + submit -> targets the dept manager
    ev2 = await api.post("/api/evaluations", headers=auth(org["sup"]),
                          json={"employee_id": e2, "template_id": org["template_id"], "kind": "annual"})
    eid2 = ev2.json()["id"]
    detail2 = (await api.get(f"/api/evaluations/{eid2}", headers=auth(org["sup"]))).json()
    scores2 = [{"evaluation_item_id": it["id"], "score": 4} for it in detail2["items"]]
    await api.put(f"/api/evaluations/{eid2}/scores", headers=auth(org["sup"]),
                  json={"scores": scores2, "comments": []})
    await api.post(f"/api/evaluations/{eid2}/submit", headers=auth(org["sup"]), json={})

    after = await _digest_after(db, api, secret, org["cid"])
    assert after == {"recipients": 2, "items": 2}
