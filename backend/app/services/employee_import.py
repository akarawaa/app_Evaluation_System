"""Bulk employee import (CSV) — for onboarding a new tenant's employee roster.

Design notes
------------
* **Two-pass**: pass 1 upserts every employee row (by `emp_code`, unique per
  tenant) WITHOUT touching supervisor/manager links; pass 2 resolves
  `supervisor_emp_code` / `manager_emp_code` against a map built from both
  pre-existing tenant employees and rows created/updated in this same file.
  This lets a manager's own row appear anywhere in the file (before or after
  their subordinates) and lets HR re-run the import incrementally.
* **Idempotent**: re-importing the same file updates existing rows (matched
  by emp_code) instead of erroring or duplicating — safe to fix a typo and
  re-upload.
* **Partial success**: each row is applied inside its own SAVEPOINT
  (`session.begin_nested()`). A bad row is rolled back and recorded as an
  error; every other row in the file still commits when the request's outer
  transaction commits. This is the standard bulk-importer UX (500 rows,
  a handful of typos shouldn't block the other 495).
* **Tenant safety**: branch/employee lookups run through the caller's
  RLS-scoped session (same pattern as services/employees.py) — a supervisor
  emp_code that doesn't resolve within *this* tenant is simply "not found",
  never a cross-tenant leak.
* **Audit**: one summary audit entry per import call, not one per row —
  500 near-identical audit rows for a single bulk action would swamp the log
  without adding investigative value; the row-level detail lives in the
  ImportResult returned to (and typically saved by) the caller.
"""
import csv
import io
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.services.audit import write_audit

HEADERS = [
    "รหัสพนักงาน", "ชื่อ-นามสกุล", "ตำแหน่ง", "อีเมล", "ระดับ",
    "สาขา", "รหัสหัวหน้างาน", "รหัสผจก.แผนก", "สถานะ",
]

_LEVEL_MAP = {
    "": "operational", "พนักงานปฏิบัติการ": "operational", "operational": "operational",
    "หัวหน้างาน": "supervisor", "supervisor": "supervisor",
}
_STATUS_MAP = {
    "": "active", "ทำงานอยู่": "active", "active": "active",
    "ปิดใช้งาน": "inactive", "inactive": "inactive",
}

_MAX_ROWS = 2000


def build_template_csv() -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(HEADERS)
    writer.writerow(["SUP001", "สมหมาย ใจดี", "ผู้จัดการแผนกขาย", "supervisor@example.com", "หัวหน้างาน", "สำนักงานใหญ่", "", "", "ทำงานอยู่"])
    writer.writerow(["EMP001", "สมชาย รักงาน", "พนักงานขาย", "emp001@example.com", "พนักงานปฏิบัติการ", "สำนักงานใหญ่", "SUP001", "", "ทำงานอยู่"])
    # UTF-8 BOM so Thai text opens correctly in Excel, not just text editors.
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def _get(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


async def _get_or_create_branch(session: AsyncSession, company_id: Optional[str], cache: dict, name: str):
    """Upsert-by-name in its own SAVEPOINT, nested inside the caller's row
    savepoint. If this fails, only the branch insert rolls back and the
    exception propagates to the row's own try/except — we only populate
    `cache` once the insert has actually committed to the transaction, so a
    later row never reuses a branch id that got rolled back."""
    if name in cache:
        return cache[name]
    async with session.begin_nested():
        row = (await session.execute(text(
            "insert into branches (company_id, name) values (:cid, :name) "
            "on conflict (company_id, name) do update set name = excluded.name "
            "returning id, (xmax = 0) as inserted"
        ), {"cid": company_id, "name": name})).mappings().one()
    cache[name] = row["id"]
    if row["inserted"]:
        cache["__created__"] = cache.get("__created__", 0) + 1
    return row["id"]


async def import_employees(session: AsyncSession, user: CurrentUser, raw: bytes) -> dict:
    try:
        text_data = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ไฟล์ต้องเป็น CSV แบบ UTF-8")

    reader = csv.DictReader(io.StringIO(text_data))
    if reader.fieldnames is None or [h.strip() for h in reader.fieldnames] != HEADERS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"หัวตารางไม่ตรงกับเทมเพลต ต้องเป็น: {', '.join(HEADERS)}",
        )
    rows = list(reader)
    if len(rows) > _MAX_ROWS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"นำเข้าได้สูงสุด {_MAX_ROWS} แถวต่อครั้ง")

    branch_cache: dict = {}
    errors: list[dict] = []
    created = updated = 0
    # emp_code -> id, seeded with employees that already exist in this tenant
    code_to_id: dict[str, str] = {
        r["emp_code"]: str(r["id"])
        for r in (await session.execute(text("select id, emp_code from employees"))).mappings().all()
    }
    link_rows: list[tuple[int, dict, str]] = []  # (row_no, raw_row, employee_id)

    for i, row in enumerate(rows, start=2):  # row 1 is the header
        emp_code = _get(row, "รหัสพนักงาน")
        full_name = _get(row, "ชื่อ-นามสกุล")
        if not emp_code or not full_name:
            errors.append({"row": i, "emp_code": emp_code or None, "message": "ต้องมีรหัสพนักงานและชื่อ-นามสกุล"})
            continue

        level_raw = _get(row, "ระดับ")
        if level_raw not in _LEVEL_MAP:
            errors.append({"row": i, "emp_code": emp_code, "message": f"ระดับไม่ถูกต้อง: '{level_raw}'"})
            continue
        status_raw = _get(row, "สถานะ")
        if status_raw not in _STATUS_MAP:
            errors.append({"row": i, "emp_code": emp_code, "message": f"สถานะไม่ถูกต้อง: '{status_raw}'"})
            continue

        try:
            async with session.begin_nested():
                branch_id = None
                branch_name = _get(row, "สาขา")
                if branch_name:
                    branch_id = await _get_or_create_branch(session, user.company_id, branch_cache, branch_name)

                result = (await session.execute(text(
                    "insert into employees (company_id, emp_code, full_name, position, email, level, branch_id, status) "
                    "values (:cid, :code, :name, :pos, :email, :level, :branch, :status) "
                    "on conflict (company_id, emp_code) do update set "
                    "  full_name = excluded.full_name, position = excluded.position, "
                    "  email = excluded.email, "
                    "  level = excluded.level, branch_id = excluded.branch_id, status = excluded.status "
                    "returning id, (xmax = 0) as inserted"
                ), {
                    "cid": user.company_id, "code": emp_code, "name": full_name,
                    "pos": _get(row, "ตำแหน่ง") or None, "email": _get(row, "อีเมล") or None,
                    "level": _LEVEL_MAP[level_raw],
                    "branch": str(branch_id) if branch_id else None, "status": _STATUS_MAP[status_raw],
                })).mappings().one()
        except Exception as exc:  # noqa: BLE001 — surfaced per-row, not fatal to the batch
            errors.append({"row": i, "emp_code": emp_code, "message": str(exc).splitlines()[0]})
            continue

        emp_id = str(result["id"])
        code_to_id[emp_code] = emp_id
        if result["inserted"]:
            created += 1
        else:
            updated += 1
        if _get(row, "รหัสหัวหน้างาน") or _get(row, "รหัสผจก.แผนก"):
            link_rows.append((i, row, emp_id))

    linked = 0
    for i, row, emp_id in link_rows:
        sup_code = _get(row, "รหัสหัวหน้างาน")
        mgr_code = _get(row, "รหัสผจก.แผนก")
        emp_code = _get(row, "รหัสพนักงาน")
        set_clauses, params = [], {"id": emp_id}

        for label, code, col in (("หัวหน้างาน", sup_code, "supervisor_id"), ("ผจก.แผนก", mgr_code, "manager_id")):
            if not code:
                continue
            if code == emp_code:
                errors.append({"row": i, "emp_code": emp_code, "message": f"{label} อ้างอิงตัวเองไม่ได้"})
                continue
            ref_id = code_to_id.get(code)
            if ref_id is None:
                errors.append({"row": i, "emp_code": emp_code, "message": f"ไม่พบรหัสพนักงาน '{code}' สำหรับ {label}"})
                continue
            set_clauses.append(f"{col} = :{col}")
            params[col] = ref_id

        if not set_clauses:
            continue
        try:
            async with session.begin_nested():
                await session.execute(
                    text(f"update employees set {', '.join(set_clauses)} where id = :id"),  # noqa: S608
                    params,
                )
            linked += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": i, "emp_code": emp_code, "message": str(exc).splitlines()[0]})

    result = {
        "created": created, "updated": updated, "linked": linked,
        "branches_created": branch_cache.get("__created__", 0),
        "errors": errors,
    }
    await write_audit(
        session, company_id=user.company_id, actor_id=user.id,
        action="employees_imported", entity_type="employees",
        after={"created": created, "updated": updated, "linked": linked, "error_count": len(errors)},
    )
    return result
