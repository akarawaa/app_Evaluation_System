"""Side-by-side evaluation comparison — either multiple employees in the same
cycle, or the same employee across time (development tracking). Both are the
same operation underneath: pick 2-5 evaluations, pivot their item scores into
one table. Which "mode" it is is just what the caller selected in the UI.

Visibility: each evaluation is loaded through view_detail(), the exact same
per-evaluation access check used by GET /api/evaluations/{id} (subject sees
own, org chain sees reports', HR/GM/MD see all, everyone else 404s) — so a
comparison can never include a row the caller couldn't already open directly.
"""
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.services.audit import write_audit
from app.services.evaluations import view_detail

_MIN_EVALS = 2
_MAX_EVALS = 5


async def build_comparison(session: AsyncSession, user: CurrentUser, eval_ids: list[str]) -> dict:
    eval_ids = list(dict.fromkeys(eval_ids))  # de-dupe, keep order
    if not (_MIN_EVALS <= len(eval_ids) <= _MAX_EVALS):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"เลือกได้ {_MIN_EVALS}-{_MAX_EVALS} ใบประเมิน")

    evaluations = [await view_detail(session, user, eid) for eid in eval_ids]

    emp_rows = (await session.execute(text(
        "select id, emp_code, full_name, position from employees where id = any(:ids)"
    ), {"ids": [ev["employee_id"] for ev in evaluations]})).mappings().all()
    emp_by_id = {str(r["id"]): dict(r) for r in emp_rows}

    columns = []
    for ev in evaluations:
        emp = emp_by_id.get(str(ev["employee_id"]), {})
        columns.append({
            "evaluation_id": ev["id"],
            "emp_code": emp.get("emp_code"),
            "full_name": emp.get("full_name"),
            "position": emp.get("position"),
            "kind": ev["kind"],
            "status": ev["status"],
            "eval_score": ev["eval_score"],
            "eval_max": ev["eval_max"],
            "attendance_score": ev["attendance_score"],
            "total_score": ev["total_score"],
            "percentage": ev["percentage"],
            "created_at": ev["created_at"],
        })

    # Align rows by item_name (templates may differ across kind/level); order
    # follows first appearance so the more complete template's ordering wins.
    row_order: list[tuple[str, str]] = []  # (category_name, item_name)
    row_index: dict[tuple[str, str], dict] = {}
    for ev in evaluations:
        for it in ev["items"]:
            key = (it["category_name"], it["item_name"])
            if key not in row_index:
                row_index[key] = {"category_name": it["category_name"], "item_name": it["item_name"],
                                  "scores": {}}
                row_order.append(key)
            row_index[key]["scores"][str(ev["id"])] = it["score"]

    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="evaluations_compared", entity_type="evaluations",
                      after={"evaluation_ids": eval_ids})

    return {"columns": columns, "rows": [row_index[k] for k in row_order]}
