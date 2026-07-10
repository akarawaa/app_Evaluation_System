"""Employee + branch management (admin UI backend).

Referential checks (branch_id / supervisor_id / manager_id) are done via a
SELECT under the caller's RLS-scoped session rather than a bare FK lookup:
a plain foreign key only proves the row exists *somewhere*, not that it
belongs to the caller's tenant. Because every query here runs through
get_tenant_session, RLS silently filters out rows from other tenants, so
"not found" and "belongs to a different company" collapse into the same
400 response — no separate tenant check needed.
"""
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.services.audit import write_audit

_LIST_SQL = """
select e.id, e.emp_code, e.full_name, e.position, e.level, e.status,
       e.branch_id, b.name as branch_name,
       e.supervisor_id, sup.full_name as supervisor_name,
       e.manager_id, mgr.full_name as manager_name
from employees e
left join branches  b   on b.id   = e.branch_id
left join employees sup on sup.id = e.supervisor_id
left join employees mgr on mgr.id = e.manager_id
"""


async def list_employees(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(text(_LIST_SQL + " order by e.emp_code"))).mappings().all()
    return [dict(r) for r in rows]


async def _exists_in_tenant(session: AsyncSession, table: str, row_id) -> bool:
    row = (await session.execute(
        text(f"select 1 from {table} where id = :id"), {"id": str(row_id)}  # noqa: S608 (table is a fixed literal, not user input)
    )).first()
    return row is not None


async def _validate_refs(
    session: AsyncSession,
    *,
    employee_id: Optional[str],
    branch_id: Optional[UUID],
    supervisor_id: Optional[UUID],
    manager_id: Optional[UUID],
) -> None:
    if branch_id is not None and not await _exists_in_tenant(session, "branches", branch_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "branch not found")
    for label, ref in (("supervisor_id", supervisor_id), ("manager_id", manager_id)):
        if ref is None:
            continue
        if employee_id is not None and str(ref) == str(employee_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label} cannot be the employee itself")
        if not await _exists_in_tenant(session, "employees", ref):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{label} not found")


async def create_employee(session: AsyncSession, user: CurrentUser, payload) -> dict:
    await _validate_refs(
        session, employee_id=None, branch_id=payload.branch_id,
        supervisor_id=payload.supervisor_id, manager_id=payload.manager_id,
    )
    row = (await session.execute(text(
        "insert into employees "
        "(company_id, branch_id, emp_code, full_name, position, level, supervisor_id, manager_id) "
        "values (:cid, :branch_id, :emp_code, :full_name, :position, :level, :sup, :mgr) "
        "returning id"
    ), {
        "cid": user.company_id,
        "branch_id": str(payload.branch_id) if payload.branch_id else None,
        "emp_code": payload.emp_code,
        "full_name": payload.full_name,
        "position": payload.position,
        "level": payload.level,
        "sup": str(payload.supervisor_id) if payload.supervisor_id else None,
        "mgr": str(payload.manager_id) if payload.manager_id else None,
    })).mappings().one()

    detail = await get_employee(session, str(row["id"]))
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="create", entity_type="employees", entity_id=row["id"], after=detail)
    return detail


async def get_employee(session: AsyncSession, employee_id: str) -> dict:
    row = (await session.execute(
        text(_LIST_SQL + " where e.id = :id"), {"id": employee_id}
    )).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "employee not found")
    return dict(row)


async def update_employee(session: AsyncSession, user: CurrentUser, employee_id: str, payload) -> dict:
    before = await get_employee(session, employee_id)
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        return before

    await _validate_refs(
        session, employee_id=employee_id,
        branch_id=payload.branch_id if "branch_id" in fields else None,
        supervisor_id=payload.supervisor_id if "supervisor_id" in fields else None,
        manager_id=payload.manager_id if "manager_id" in fields else None,
    )

    set_clauses, params = [], {"id": employee_id}
    for col in ("branch_id", "emp_code", "full_name", "position", "level",
                "supervisor_id", "manager_id", "status"):
        if col in fields:
            value = fields[col]
            set_clauses.append(f"{col} = :{col}")
            params[col] = str(value) if isinstance(value, UUID) else value
    if not set_clauses:
        return before

    await session.execute(
        text(f"update employees set {', '.join(set_clauses)} where id = :id"),  # noqa: S608
        params,
    )
    after = await get_employee(session, employee_id)
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="update", entity_type="employees", entity_id=employee_id,
                      before=before, after=after)
    return after


async def list_branches(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(
        text("select id, name from branches order by name")
    )).mappings().all()
    return [dict(r) for r in rows]


async def create_branch(session: AsyncSession, user: CurrentUser, name: str) -> dict:
    row = (await session.execute(text(
        "insert into branches (company_id, name) values (:cid, :name) returning id, name"
    ), {"cid": user.company_id, "name": name})).mappings().one()
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="create", entity_type="branches", entity_id=row["id"], after=dict(row))
    return dict(row)


async def update_branch(session: AsyncSession, user: CurrentUser, branch_id: str, name: str) -> dict:
    before = (await session.execute(
        text("select id, name from branches where id = :id"), {"id": branch_id}
    )).mappings().first()
    if before is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "branch not found")

    row = (await session.execute(text(
        "update branches set name = :name where id = :id returning id, name"
    ), {"id": branch_id, "name": name})).mappings().one()
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="update", entity_type="branches", entity_id=branch_id,
                      before=dict(before), after=dict(row))
    return dict(row)
