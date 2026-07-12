"""Bulk attendance import (CSV) — HR loads raw attendance figures for many
employees at once, mirroring services/employee_import.py's pattern.

Design notes
------------
* Attendance is keyed by `evaluation_id` (evaluation_attendance's PK), not by
  employee directly, so each row is matched to that employee's single
  currently-open (non-finalized) evaluation. No open evaluation, or more than
  one, is reported as a per-row error rather than guessed at.
* **Idempotent**: re-importing updates the same evaluation's attendance row.
* **Respects a prior manual override**: if HR already overrode a specific
  evaluation's score by hand (services.evaluations.set_attendance), bulk
  import does not silently recompute over it — the row is counted under
  skipped_overridden and left alone, same rule as the single-record endpoint.
* **Partial success**: one SAVEPOINT per row.
"""
import csv
import io

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.services import attendance_formula
from app.services.audit import write_audit

HEADERS = [
    "รหัสพนักงาน", "จำนวนวันลาป่วย", "จำนวนวันลากิจ",
    "จำนวนครั้งมาสาย", "จำนวนนาทีสายรวม", "จำนวนวันขาดงาน",
]

_MAX_ROWS = 2000


def build_template_csv() -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(HEADERS)
    writer.writerow(["EMP001", "1", "0", "2", "20", "0"])
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def _get(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


def _int(row: dict, key: str) -> int:
    raw = _get(row, key)
    if raw == "":
        return 0
    return int(raw)


async def import_attendance(session: AsyncSession, user: CurrentUser, raw: bytes) -> dict:
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

    errors: list[dict] = []
    updated = skipped_overridden = 0
    formula = await attendance_formula.get_formula(session, user.company_id)

    for i, row in enumerate(rows, start=2):  # row 1 is the header
        emp_code = _get(row, "รหัสพนักงาน")
        if not emp_code:
            errors.append({"row": i, "emp_code": None, "message": "ต้องมีรหัสพนักงาน"})
            continue

        try:
            sick_days = _int(row, "จำนวนวันลาป่วย")
            personal_days = _int(row, "จำนวนวันลากิจ")
            late_count = _int(row, "จำนวนครั้งมาสาย")
            late_minutes = _int(row, "จำนวนนาทีสายรวม")
            absent_days = _int(row, "จำนวนวันขาดงาน")
        except ValueError:
            errors.append({"row": i, "emp_code": emp_code, "message": "ตัวเลขไม่ถูกต้อง"})
            continue

        evs = (await session.execute(text(
            "select ev.id from evaluations ev join employees emp on emp.id = ev.employee_id "
            "where emp.emp_code = :code and ev.status != 'finalized'"
        ), {"code": emp_code})).all()
        if not evs:
            errors.append({"row": i, "emp_code": emp_code, "message": "ไม่พบใบประเมินที่ยังไม่ปิดของพนักงานนี้"})
            continue
        if len(evs) > 1:
            errors.append({"row": i, "emp_code": emp_code, "message": "พบใบประเมินที่ยังไม่ปิดมากกว่า 1 ใบ กรอกผ่านหน้าใบประเมินโดยตรงแทน"})
            continue
        eval_id = str(evs[0][0])

        try:
            async with session.begin_nested():
                existing = (await session.execute(text(
                    "select attendance_score_overridden from evaluation_attendance where evaluation_id = :id"
                ), {"id": eval_id})).mappings().first()
                if existing and existing["attendance_score_overridden"]:
                    skipped_overridden += 1
                    continue

                score = attendance_formula.compute_score(formula, sick_days, personal_days, late_count, absent_days)
                await session.execute(text(
                    "insert into evaluation_attendance "
                    "(evaluation_id, company_id, sick_days, personal_days, late_count, late_minutes, absent_days, "
                    " attendance_score, attendance_score_overridden) "
                    "values (:e,:c,:sd,:pd,:lc,:lm,:ad,:ascore,false) "
                    "on conflict (evaluation_id) do update set sick_days=excluded.sick_days, "
                    "personal_days=excluded.personal_days, late_count=excluded.late_count, "
                    "late_minutes=excluded.late_minutes, absent_days=excluded.absent_days, "
                    "attendance_score=excluded.attendance_score, attendance_score_overridden=false, updated_at=now()"
                ), {"e": eval_id, "c": user.company_id, "sd": sick_days, "pd": personal_days,
                    "lc": late_count, "lm": late_minutes, "ad": absent_days, "ascore": score})
                await session.execute(text("select app.recompute_evaluation_totals(:id)"), {"id": eval_id})
        except Exception as exc:  # noqa: BLE001 — surfaced per-row, not fatal to the batch
            errors.append({"row": i, "emp_code": emp_code, "message": str(exc).splitlines()[0]})
            continue
        updated += 1

    result = {"updated": updated, "skipped_overridden": skipped_overridden, "errors": errors}
    await write_audit(
        session, company_id=user.company_id, actor_id=user.id,
        action="attendance_imported", entity_type="evaluations",
        after={"updated": updated, "skipped_overridden": skipped_overridden, "error_count": len(errors)},
    )
    return result
