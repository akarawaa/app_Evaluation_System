"""Phase 1 API surface (thin). Every DB call goes through the tenant session,
so RLS scopes results to the caller's company automatically."""
from fastapi import APIRouter, Depends, Response, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_session
from app.core.security import CurrentUser, get_current_user, require_roles
from app.schemas.attendance_formula import AttendanceFormulaIn, AttendanceFormulaOut
from app.schemas.branch import BranchCreate, BranchOut
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate
from app.schemas.employee_import import ImportResult
from app.schemas.tenant import InviteUserIn
from app.schemas.user import UserOut
from app.services import attendance_formula as attendance_formula_svc
from app.services import employees as emp_svc
from app.services import employee_import as import_svc
from app.services import tenant_admin as tenant_admin_svc
from app.services import users as users_svc

router = APIRouter(prefix="/api")


@router.get("/me")
async def me(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    # Own employee_id lets the frontend precisely gate evaluation actions
    # (e.g. "am I this evaluation's evaluator?") instead of relying on role
    # alone. super_admin isn't tied to an employee row, so skip the lookup.
    employee_id = None
    if not user.is_super_admin:
        row = (
            await session.execute(
                text("select employee_id from profiles where id = :id"), {"id": user.id}
            )
        ).first()
        employee_id = str(row[0]) if row and row[0] is not None else None

    return {
        "id": user.id,
        "email": user.email,
        "company_id": user.company_id,
        "is_super_admin": user.is_super_admin,
        "roles": user.roles,
        "employee_id": employee_id,
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


@router.get("/users", response_model=list[UserOut])
async def list_users(
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[dict]:
    return await users_svc.list_users(session)


@router.post("/users/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    payload: InviteUserIn,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    # Self-service: hr_admin invites into their OWN tenant only — company_id
    # comes from the verified JWT, never accepted from the request body, so
    # there is no way to target another company through this endpoint.
    return await tenant_admin_svc.invite_user(
        session, user.id, user.company_id,
        payload.email, payload.password, payload.role,
        str(payload.employee_id) if payload.employee_id else None,
    )


@router.get("/settings/attendance-formula", response_model=AttendanceFormulaOut)
async def get_attendance_formula(
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await attendance_formula_svc.get_formula(session, user.company_id)


@router.put("/settings/attendance-formula", response_model=AttendanceFormulaOut)
async def set_attendance_formula(
    payload: AttendanceFormulaIn,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await attendance_formula_svc.set_formula(session, user, payload)
