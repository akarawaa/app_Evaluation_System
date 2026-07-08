"""Integration-test fixtures for the security/isolation suite (Step 8).

Black-box: talks to the running API (:8000), GoTrue (:54321), and Postgres
(:54322). Requires the local stack + uvicorn to be up; otherwise tests skip.
Setup/teardown use asyncpg as `postgres` (bypasses RLS) to seed and clean data.
"""
import uuid
from pathlib import Path

import asyncpg
import httpx
import pytest
import pytest_asyncio

API_URL = "http://127.0.0.1:8000"
AUTH_URL = "http://127.0.0.1:54321"
DB_DSN = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
PLATFORM_ID = "00000000-0000-0000-0000-000000000001"
PW = "Passw0rd!123"


def _service_key() -> str:
    env = Path(__file__).resolve().parents[1] / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("SUPABASE_SERVICE_ROLE_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing in backend/.env")


SERVICE_KEY = _service_key()
_HDRS = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}",
         "Content-Type": "application/json"}

_stack_ok = None   # tri-state cache: None=unknown, True/False=checked


@pytest.fixture(autouse=True)
def require_stack():
    global _stack_ok
    if _stack_ok is None:
        try:
            httpx.get(f"{API_URL}/health", timeout=3).raise_for_status()
            _stack_ok = True
        except Exception:
            _stack_ok = False
    if not _stack_ok:
        pytest.skip("API/stack not running on :8000 (start supabase + uvicorn)")


@pytest_asyncio.fixture
async def db():
    conn = await asyncpg.connect(DB_DSN)
    try:
        yield conn
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def api():
    async with httpx.AsyncClient(base_url=API_URL, timeout=20) as client:
        yield client


async def _create_user(client: httpx.AsyncClient, email: str) -> str:
    r = await client.post(f"{AUTH_URL}/auth/v1/admin/users", headers=_HDRS,
                          json={"email": email, "password": PW, "email_confirm": True})
    r.raise_for_status()
    return r.json()["id"]


async def _token(client: httpx.AsyncClient, email: str) -> str:
    r = await client.post(f"{AUTH_URL}/auth/v1/token", params={"grant_type": "password"},
                          headers=_HDRS, json={"email": email, "password": PW})
    r.raise_for_status()
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def world(db):
    """Two tenants (A, B) with hr_admins + one employee each, an employee-role
    user in A, and a platform super_admin. Cleans everything up afterwards."""
    company_ids: list[str] = []
    user_ids: list[str] = []

    async with httpx.AsyncClient(timeout=20) as c:
        async def tenant(prefix: str, role: str) -> dict:
            cid = str(uuid.uuid4())
            slug = f"{prefix}-{uuid.uuid4().hex[:8]}"
            await db.execute("insert into companies (id,name,slug) values ($1,$2,$3)",
                             cid, prefix, slug)
            company_ids.append(cid)
            email = f"{prefix}-{uuid.uuid4().hex[:8]}@test.local"
            uid = await _create_user(c, email)
            user_ids.append(uid)
            await db.execute("insert into profiles (id,company_id,display_name) values ($1,$2,$3)",
                             uid, cid, prefix)
            await db.execute(
                "insert into user_roles (profile_id,role_id,company_id) "
                "select $1,id,$2 from roles where code=$3", uid, cid, role)
            return {"company_id": cid, "email": email, "uid": uid,
                    "token": await _token(c, email)}

        a = await tenant("tenantA", "hr_admin")
        b = await tenant("tenantB", "hr_admin")
        await db.execute("insert into employees (company_id,emp_code,full_name) values ($1,'A001','Alice A')", a["company_id"])
        await db.execute("insert into employees (company_id,emp_code,full_name) values ($1,'B001','Bob B')", b["company_id"])

        emp_email = f"empA-{uuid.uuid4().hex[:8]}@test.local"
        emp_uid = await _create_user(c, emp_email)
        user_ids.append(emp_uid)
        await db.execute("insert into profiles (id,company_id,display_name) values ($1,$2,'empA')", emp_uid, a["company_id"])
        await db.execute("insert into user_roles (profile_id,role_id,company_id) select $1,id,$2 from roles where code='employee'", emp_uid, a["company_id"])
        emp_token = await _token(c, emp_email)

        su_email = f"super-{uuid.uuid4().hex[:8]}@test.local"
        su_uid = await _create_user(c, su_email)
        user_ids.append(su_uid)
        await db.execute("insert into profiles (id,company_id,display_name) values ($1,$2,'root')", su_uid, PLATFORM_ID)
        await db.execute("insert into user_roles (profile_id,role_id,company_id) select $1,id,$2 from roles where code='super_admin'", su_uid, PLATFORM_ID)
        su_token = await _token(c, su_email)

    yield {"A": a, "B": b, "emp_token": emp_token, "super_token": su_token}

    for cid in company_ids:
        await db.execute("delete from companies where id=$1", cid)
    for uid in user_ids:
        await db.execute("delete from auth.users where id=$1", uid)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
