"""Phase 1 API surface (thin). Every DB call goes through the tenant session,
so RLS scopes results to the caller's company automatically."""
from fastapi import APIRouter, Depends, Response, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_session
from app.core.security import CurrentUser, get_current_user, require_roles
from app.schemas.branch import BranchCreate, BranchOut
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate
from app.schemas.employee_import import ImportResult
from app.services import employees as emp_svc
from app.services import employee_import as import_svc

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


@router.get("/employees", response_model=list[EmployeeOut])
async def list_employees(session: AsyncSession = Depends(get_tenant_session)) -> list[dict]:
    return await emp_svc.list_employees(session)


@router.post("/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.create_employee(session, user, payload)


@router.get("/employees/import-template")
async def employee_import_template(
    user: CurrentUser = Depends(require_roles("hr_admin")),
) -> Response:
    return Response(
        content=import_svc.build_template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="employee-import-template.csv"'},
    )


@router.post("/employees/import", response_model=ImportResult)
async def import_employees(
    file: UploadFile,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    raw = await file.read()
    return await import_svc.import_employees(session, user, raw)


# NOTE: the two routes above are literal paths ("import-template", "import")
# and MUST stay registered before /employees/{employee_id} below, or FastAPI
# would match them as employee_id path parameters instead.
@router.get("/employees/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: str,
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.get_employee(session, employee_id)


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.update_employee(session, user, employee_id, payload)


@router.get("/templates")
async def list_templates(session: AsyncSession = Depends(get_tenant_session)) -> list[dict]:
    # RLS returns master (company_id is null) + this tenant's templates
    rows = (
        await session.execute(
            text(
                "select id, name, applies_to_level, status from criteria_templates "
                "order by name, version"
            )
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/branches", response_model=list[BranchOut])
async def list_branches(session: AsyncSession = Depends(get_tenant_session)) -> list[dict]:
    return await emp_svc.list_branches(session)


@router.post("/branches", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
async def create_branch(
    payload: BranchCreate,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.create_branch(session, user, payload.name)


@router.patch("/branches/{branch_id}", response_model=BranchOut)
async def update_branch(
    branch_id: str,
    payload: BranchCreate,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.update_branch(session, user, branch_id, payload.name)
