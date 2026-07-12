"""Per-tenant attendance-score formula (company_attendance_formula, HR-owned).

The formula is: full_score - coef_absent*absent_days - coef_personal*personal_days
              - coef_sick*sick_days - coef_late*late_count, floored at 0.

Absence of a row for a company means "use DEFAULTS" — the same starting
values every tenant got before this was configurable, so tenants that never
touch the settings page keep working exactly as before.
"""
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.services.audit import write_audit

DEFAULTS = {
    "full_score": 40.0, "coef_absent": 4.0, "coef_personal": 1.0,
    "coef_sick": 0.5, "coef_late": 1.0,
}

_COLUMNS = list(DEFAULTS.keys())


async def get_formula(session: AsyncSession, company_id: str) -> dict:
    row = (await session.execute(text(
        f"select {', '.join(_COLUMNS)} from company_attendance_formula where company_id = :cid"  # noqa: S608
    ), {"cid": company_id})).mappings().first()
    if row is None:
        return dict(DEFAULTS)
    return {k: float(row[k]) for k in _COLUMNS}


def compute_score(formula: dict, sick_days: int, personal_days: int, late_count: int, absent_days: int) -> float:
    score = (
        formula["full_score"]
        - formula["coef_absent"] * absent_days
        - formula["coef_personal"] * personal_days
        - formula["coef_sick"] * sick_days
        - formula["coef_late"] * late_count
    )
    return max(0.0, score)


async def set_formula(session: AsyncSession, user: CurrentUser, payload) -> dict:
    values = {k: getattr(payload, k) for k in _COLUMNS}
    if any(v < 0 for v in values.values()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ค่าสัมประสิทธิ์ต้องไม่ติดลบ")

    cols = ", ".join(_COLUMNS)
    placeholders = ", ".join(f":{k}" for k in _COLUMNS)
    set_clause = ", ".join(f"{k} = excluded.{k}" for k in _COLUMNS)
    await session.execute(text(
        f"insert into company_attendance_formula (company_id, {cols}) "  # noqa: S608
        f"values (:cid, {placeholders}) "
        f"on conflict (company_id) do update set {set_clause}, updated_at = now()"
    ), {"cid": user.company_id, **values})

    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="attendance_formula_updated", entity_type="company_attendance_formula",
                      after=values)
    return await get_formula(session, user.company_id)
