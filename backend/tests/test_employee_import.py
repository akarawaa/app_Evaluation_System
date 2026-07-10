"""Bulk employee CSV import — template download + two-pass import behavior."""
import uuid

from conftest import auth

HEADER = "รหัสพนักงาน,ชื่อ-นามสกุล,ตำแหน่ง,ระดับ,สาขา,รหัสหัวหน้างาน,รหัสผจก.แผนก,สถานะ"


def _csv(*rows: str) -> bytes:
    return ("﻿" + HEADER + "\n" + "\n".join(rows)).encode("utf-8")


def _upload(csv_bytes: bytes):
    return {"file": ("import.csv", csv_bytes, "text/csv")}


async def test_template_download(api, world):
    r = await api.get("/api/employees/import-template", headers=auth(world["A"]["token"]))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    text = r.content.decode("utf-8-sig")
    assert text.splitlines()[0] == HEADER


async def test_import_creates_links_and_branch(api, world):
    sup = f"SUP{uuid.uuid4().hex[:5]}"
    emp = f"EMP{uuid.uuid4().hex[:5]}"
    branch = f"สาขา-{uuid.uuid4().hex[:5]}"
    csv_bytes = _csv(
        f"{sup},หัวหน้าทดสอบ,ผู้จัดการ,หัวหน้างาน,{branch},,,ทำงานอยู่",
        f"{emp},ลูกน้องทดสอบ,พนักงาน,พนักงานปฏิบัติการ,{branch},{sup},,ทำงานอยู่",
    )
    r = await api.post("/api/employees/import", headers=auth(world["A"]["token"]), files=_upload(csv_bytes))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] == 2
    assert body["updated"] == 0
    assert body["linked"] == 1
    assert body["branches_created"] == 1
    assert body["errors"] == []

    employees = (await api.get("/api/employees", headers=auth(world["A"]["token"]))).json()
    worker = next(e for e in employees if e["emp_code"] == emp)
    assert worker["supervisor_name"] == "หัวหน้าทดสอบ"
    assert worker["branch_name"] == branch


async def test_import_is_idempotent(api, world):
    code = f"IDM{uuid.uuid4().hex[:5]}"
    csv_bytes = _csv(f"{code},ชื่อเดิม,,พนักงานปฏิบัติการ,,,,ทำงานอยู่")

    r1 = await api.post("/api/employees/import", headers=auth(world["A"]["token"]), files=_upload(csv_bytes))
    assert r1.json()["created"] == 1

    csv_bytes2 = _csv(f"{code},ชื่อใหม่,,พนักงานปฏิบัติการ,,,,ทำงานอยู่")
    r2 = await api.post("/api/employees/import", headers=auth(world["A"]["token"]), files=_upload(csv_bytes2))
    body2 = r2.json()
    assert body2["created"] == 0
    assert body2["updated"] == 1

    employees = (await api.get("/api/employees", headers=auth(world["A"]["token"]))).json()
    row = next(e for e in employees if e["emp_code"] == code)
    assert row["full_name"] == "ชื่อใหม่"


async def test_import_partial_failure_reports_row_and_continues(api, world):
    good = f"OK{uuid.uuid4().hex[:5]}"
    csv_bytes = _csv(
        f"{good},คนที่ผ่าน,,พนักงานปฏิบัติการ,,,,ทำงานอยู่",
        "BAD1,คนที่ไม่ผ่าน,,ระดับผิด,,,,ทำงานอยู่",
    )
    r = await api.post("/api/employees/import", headers=auth(world["A"]["token"]), files=_upload(csv_bytes))
    body = r.json()
    assert body["created"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 3          # header=1, good=2, bad=3
    assert body["errors"][0]["emp_code"] == "BAD1"

    employees = (await api.get("/api/employees", headers=auth(world["A"]["token"]))).json()
    assert any(e["emp_code"] == good for e in employees)
    assert not any(e["emp_code"] == "BAD1" for e in employees)


async def test_import_self_reference_rejected(api, world):
    code = f"SELF{uuid.uuid4().hex[:5]}"
    csv_bytes = _csv(f"{code},วนซ้ำตัวเอง,,พนักงานปฏิบัติการ,,{code},,ทำงานอยู่")
    r = await api.post("/api/employees/import", headers=auth(world["A"]["token"]), files=_upload(csv_bytes))
    body = r.json()
    assert body["created"] == 1
    assert body["linked"] == 0
    assert any("อ้างอิงตัวเอง" in e["message"] for e in body["errors"])


async def test_import_unresolved_supervisor_code_reported(api, world):
    code = f"ORPH{uuid.uuid4().hex[:5]}"
    csv_bytes = _csv(f"{code},ไม่มีหัวหน้าจริง,,พนักงานปฏิบัติการ,,NOPE999,,ทำงานอยู่")
    r = await api.post("/api/employees/import", headers=auth(world["A"]["token"]), files=_upload(csv_bytes))
    body = r.json()
    assert body["created"] == 1
    assert body["linked"] == 0
    assert any("ไม่พบรหัสพนักงาน" in e["message"] for e in body["errors"])


async def test_import_wrong_header_rejected(api, world):
    bad_csv = "﻿col1,col2\nx,y".encode("utf-8")
    r = await api.post("/api/employees/import", headers=auth(world["A"]["token"]), files=_upload(bad_csv))
    assert r.status_code == 400


async def test_import_requires_hr_admin(api, world):
    csv_bytes = _csv(f"X{uuid.uuid4().hex[:5]},ทดสอบ,,พนักงานปฏิบัติการ,,,,ทำงานอยู่")
    r = await api.post("/api/employees/import", headers=auth(world["emp_token"]), files=_upload(csv_bytes))
    assert r.status_code == 403


async def test_import_is_tenant_scoped_for_links(api, world):
    """A supervisor emp_code that only exists in tenant B must not resolve
    when importing into tenant A — it should report 'not found', not link
    across tenants."""
    bob = next(e for e in (await api.get("/api/employees", headers=auth(world["B"]["token"]))).json()
              if e["full_name"] == "Bob B")
    code = f"XT{uuid.uuid4().hex[:5]}"
    csv_bytes = _csv(f"{code},พนักงานเอ,,พนักงานปฏิบัติการ,,{bob['emp_code']},,ทำงานอยู่")
    r = await api.post("/api/employees/import", headers=auth(world["A"]["token"]), files=_upload(csv_bytes))
    body = r.json()
    assert body["linked"] == 0
    assert any("ไม่พบรหัสพนักงาน" in e["message"] for e in body["errors"])
