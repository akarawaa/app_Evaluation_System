"""Per-tenant attendance-score brackets (company_attendance_brackets, HR-owned).

Real HR policy (FMHR07 p.4, photographed 2026-08-29) scores each of 4
categories independently by which bracket the raw count falls in -- not a
per-unit linear deduction. services/attendance_formula.py's old
"full_score - coef*count" model could not represent this at all: sick leave
scores 10 for 0-5 days *with a medical certificate*, then drops unevenly --
8, 6, 4, 2, 1, 0 -- not a constant per-day penalty. This module replaces it
as the active scoring path; 0017's table/endpoints are left in place
(harmless, unused) rather than dropped.

Absence of any rows for a company+category means "use DEFAULTS" -- the
brackets transcribed directly from the photographed policy, so a tenant
that never opens the settings page still scores exactly like the real paper
form did.
"""
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.services.audit import write_audit

CATEGORIES = ("personal", "absent", "sick", "late")

# Transcribed from the photographed policy document (FMHR07 p.4):
#   personal (ลากิจ):  0=10, 1-3=7, 4-7=4, 8-12=1, 13+=0
#   absent   (ขาดงาน): 0=10, 1=6, 2=3, 3+=0
#     (>=3 consecutive days is also a termination trigger per the document --
#      a policy/workflow matter, not something this scoring table encodes)
#   sick     (ลาป่วย): 0-5=10 (0-5 days *with a medical certificate*), 6-10=8,
#             11-15=6, 16-20=4, 21-25=2, 26-30=1, 31+=0
#   late     (สาย):    1-3=7, 4-7=4, 8-10=1, 11+=0
#     (the 0-count bracket's score wasn't legible in the photo -- defaulted
#      to 10 to match the "never happened" bracket in the other 3
#      categories; flagged in docs/PROJECT_STATUS.md for HR to confirm)
DEFAULTS: dict[str, list[tuple[float, Optional[float], float]]] = {
    "personal": [(0, 0, 10), (1, 3, 7), (4, 7, 4), (8, 12, 1), (13, None, 0)],
    "absent":   [(0, 0, 10), (1, 1, 6), (2, 2, 3), (3, None, 0)],
    "sick":     [(0, 5, 10), (6, 10, 8), (11, 15, 6), (16, 20, 4), (21, 25, 2), (26, 30, 1), (31, None, 0)],
    "late":     [(0, 0, 10), (1, 3, 7), (4, 7, 4), (8, 10, 1), (11, None, 0)],
}


async def get_brackets(session: AsyncSession, company_id: str) -> dict[str, list[dict]]:
    rows = (await session.execute(text(
        "select category, min_value, max_value, score, sort_order "
        "from company_attendance_brackets where company_id = :cid "
        "order by category, sort_order"
    ), {"cid": company_id})).mappings().all()

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append({
            "min_value": float(r["min_value"]),
            "max_value": float(r["max_value"]) if r["max_value"] is not None else None,
            "score": float(r["score"]),
        })

    return {
        cat: by_cat[cat] if by_cat.get(cat) else
             [{"min_value": lo, "max_value": hi, "score": sc} for lo, hi, sc in DEFAULTS[cat]]
        for cat in CATEGORIES
    }


def _score_for(brackets: list[dict], count: float) -> float:
    for b in brackets:
        if count >= b["min_value"] and (b["max_value"] is None or count <= b["max_value"]):
            return b["score"]
    # A gap HR left uncovered while editing -- fail toward 0 rather than
    # guessing, so the gap is visibly wrong (score 0 for a value that should
    # clearly score higher) instead of silently generous.
    return 0.0


def compute_score(brackets: dict[str, list[dict]], sick_days: float, personal_days: float,
                   late_count: float, absent_days: float) -> float:
    return (
        _score_for(brackets["sick"], sick_days)
        + _score_for(brackets["personal"], personal_days)
        + _score_for(brackets["late"], late_count)
        + _score_for(brackets["absent"], absent_days)
    )


def _validate(category: str, items: list[dict]) -> list[dict]:
    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"หมวด {category} ต้องมีอย่างน้อย 1 ช่วง")
    ordered = sorted(items, key=lambda b: b["min_value"])
    for b in ordered:
        if b["min_value"] < 0 or b["score"] < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "ค่าต้องไม่ติดลบ")
        if b["max_value"] is not None and b["max_value"] < b["min_value"]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "ค่าสูงสุดของช่วงต้องไม่น้อยกว่าค่าต่ำสุด")
    if ordered[0]["min_value"] != 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"หมวด {category} ต้องเริ่มจาก 0")
    if ordered[-1]["max_value"] is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"หมวด {category} ต้องมีช่วงสุดท้ายไม่จำกัดบน (เว้นว่างค่าสูงสุดของแถวสุดท้าย)")
    for prev, nxt in zip(ordered, ordered[1:]):
        if prev["max_value"] is None or nxt["min_value"] != prev["max_value"] + 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                f"หมวด {category}: ช่วงต้องต่อเนื่องกันไม่มีช่องว่างหรือทับซ้อน "
                                f"(ช่วงถัดไปต้องเริ่มที่ {(prev['max_value'] or 0) + 1})")
    return ordered


async def set_brackets(session: AsyncSession, user: CurrentUser, category: str, items: list[dict]) -> list[dict]:
    if category not in CATEGORIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "หมวดไม่ถูกต้อง")
    ordered = _validate(category, items)

    await session.execute(text(
        "delete from company_attendance_brackets where company_id = :cid and category = :cat"
    ), {"cid": user.company_id, "cat": category})
    for i, b in enumerate(ordered):
        await session.execute(text(
            "insert into company_attendance_brackets "
            "(company_id, category, min_value, max_value, score, sort_order) "
            "values (:cid, :cat, :mn, :mx, :sc, :so)"
        ), {"cid": user.company_id, "cat": category, "mn": b["min_value"],
            "mx": b["max_value"], "sc": b["score"], "so": i})

    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="attendance_brackets_updated", entity_type="company_attendance_brackets",
                      after={"category": category, "brackets": ordered})
    return ordered
