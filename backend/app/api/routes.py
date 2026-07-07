"""Phase 1 API surface (thin). Every DB call goes through the tenant session,
so RLS scopes results to the caller's company automatically."""
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_session
from app.core.security import CurrentUser, get_current_user, require_roles
from app.schemas.branch import BranchCreate, BranchOut
from app.services.audit import write_audit

router = APIRouter(prefix="/api")


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "company_id": user.company_id,
        "is_super_admin": user.is_super_admin,
        "roles": user.roles,
    }


@router.get("/employees")
async def list_employees(session: AsyncSession = Depends(get_tenant_session)) -> list[dict]:
    rows = (
        await session.execute(
            text(
                "select id, emp_code, full_name, level, status "
                "from employees order by emp_code"
            )
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/branches", response_model=list[BranchOut])
async def list_branches(session: AsyncSession = Depends(get_tenant_session)) -> list[dict]:
    rows = (
        await session.execute(text("select id, name from branches order by name"))
    ).mappings().all()
    return [dict(r) for r in rows]


@router.post("/branches", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
async def create_branch(
    payload: BranchCreate,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    # company_id comes from the verified JWT, never from the client body.
    # RLS also re-checks company_id on INSERT (defense in depth).
    row = (
        await session.execute(
            text(
                "insert into branches (company_id, name) values (:cid, :name) "
                "returning id, name"
            ),
            {"cid": user.company_id, "name": payload.name},
        )
    ).mappings().one()
    await write_audit(
        session,
        company_id=user.company_id,
        actor_id=user.id,
        action="create",
        entity_type="branches",
        entity_id=row["id"],
        after=dict(row),
    )
    return dict(row)
