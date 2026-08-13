"""Deactivating a login (PATCH /api/users/{id}/status) -- bans via GoTrue
without touching profiles/user_roles, so past evaluations the person
scored/approved/were subject to stay intact. See docs/PROJECT_STATUS.md and
0022_user_account_status.sql."""
import httpx

from conftest import AUTH_URL, _HDRS, PW, auth


async def _can_still_log_in(email: str) -> bool:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{AUTH_URL}/auth/v1/token", params={"grant_type": "password"},
                         headers=_HDRS, json={"email": email, "password": PW})
    return r.status_code == 200


async def test_hr_admin_deactivates_user_in_own_company(api, world):
    r = await api.patch(f"/api/users/{world['emp_uid']}/status", json={"active": False},
                        headers=auth(world["A"]["token"]))
    assert r.status_code == 200
    assert r.json()["active"] is False
    assert not await _can_still_log_in(world["emp_email"])

    r2 = await api.patch(f"/api/users/{world['emp_uid']}/status", json={"active": True},
                         headers=auth(world["A"]["token"]))
    assert r2.status_code == 200
    assert await _can_still_log_in(world["emp_email"])


async def test_hr_admin_cannot_deactivate_user_in_another_company(api, world):
    r = await api.patch(f"/api/users/{world['emp_uid']}/status", json={"active": False},
                        headers=auth(world["B"]["token"]))
    assert r.status_code == 404
    assert await _can_still_log_in(world["emp_email"])


async def test_hr_admin_cannot_deactivate_own_account(api, world):
    r = await api.patch(f"/api/users/{world['A']['uid']}/status", json={"active": False},
                        headers=auth(world["A"]["token"]))
    assert r.status_code == 400


async def test_super_admin_deactivates_via_explicit_company_id(api, world):
    r = await api.patch(f"/api/users/{world['emp_uid']}/status",
                        params={"company_id": world["A"]["company_id"]},
                        json={"active": False}, headers=auth(world["super_token"]))
    assert r.status_code == 200
    assert not await _can_still_log_in(world["emp_email"])

    # restore for fixture teardown / other tests in the module
    await api.patch(f"/api/users/{world['emp_uid']}/status",
                    params={"company_id": world["A"]["company_id"]},
                    json={"active": True}, headers=auth(world["super_token"]))
