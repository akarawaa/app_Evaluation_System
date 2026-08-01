"""Password-changed notice endpoint (Supabase Auth owns the actual reset;
this just logs it and fires the "was this you?" email)."""
import uuid

from conftest import auth
from test_evaluation_lifecycle import org  # noqa: F401


async def test_password_changed_requires_auth(api):
    r = await api.post("/api/auth/password-changed")
    assert r.status_code == 401


async def test_password_changed_writes_audit_log(api, org, db):
    r = await api.post("/api/auth/password-changed", headers=auth(org["hr"]))
    assert r.status_code == 204

    row = await db.fetchrow(
        "select action, company_id, actor_profile_id from audit_logs "
        "where company_id=$1 and action='password_changed' order by created_at desc limit 1",
        uuid.UUID(org["cid"]))
    assert row is not None
    assert str(row["company_id"]) == org["cid"]
