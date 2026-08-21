"""Phase 1 API surface (thin). Every DB call goes through the tenant session,
so RLS scopes results to the caller's company automatically."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_session
from app.core.security import CurrentUser, get_current_user, require_roles
from app.schemas.attendance_formula import AttendanceFormulaIn, AttendanceFormulaOut
from app.schemas.branch import BranchCreate, BranchOut
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate
from app.schemas.employee_import import ImportResult
from app.schemas.tenant import ActiveCompanyIn, InviteUserIn, UserStatusIn
from app.schemas.user import UserOut
from app.services import attendance_formula as attendance_formula_svc
from app.services import company_access as company_access_svc
from app.services import email as email_svc
from app.services import employees as emp_svc
from app.services import employee_import as import_svc
from app.services import tenant_admin as tenant_admin_svc
from app.services import users as users_svc
from app.services.audit import write_audit

router = APIRouter(prefix="/api")


def _resolve_company(user: CurrentUser, company_id: Optional[str]) -> Optional[str]:
    """super_admin may pass company_id explicitly to browse a specific tenant's
    employees/branches/users (see TenantDetail's "จัดการพนักงาน & สาขา" link) --
    RLS bypasses entirely for super_admin so this is the only thing scoping the
    query, unlike hr_admin whose own company_id already scopes everything via
    RLS with no filter needed. Nobody else may pass this param -- it would
    otherwise be a direct cross-tenant read/write."""
    if company_id is None:
        return None
    if not user.is_super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only super_admin may specify company_id")
    return company_id


@router.get("/me")
async def me(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    # Own employee_id lets the frontend precisely gate evaluation actions
    # (e.g. "am I this evaluation's evaluator?") instead of relying on role
    # alone. company/branch name are shown in the header so a person who
    # holds accounts in more than one tenant can tell which one they're in.
    employee_id = None
    company_name = None
    branch_name = None
    row = (
        await session.execute(
            text(
                "select p.employee_id, c.name as company_name, b.name as branch_name "
                "from profiles p "
                "left join companies c on c.id = p.company_id "
                "left join employees e on e.id = p.employee_id "
                "left join branches b on b.id = e.branch_id "
                "where p.id = :id"
            ),
            {"id": user.id},
        )
    ).first()
    if row:
        employee_id = str(row[0]) if row[0] is not None else None
        company_name = row[1]
        branch_name = row[2]

    return {
        "id": user.id,
        "email": user.email,
        "company_id": user.company_id,
        "company_name": company_name,
        "branch_name": branch_name,
        "is_super_admin": user.is_super_admin,
        "roles": user.roles,
        "employee_id": employee_id,
    }


@router.get("/me/companies")
async def my_companies(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[dict]:
    """Every company this login holds a role in -- lets the frontend decide
    whether to show a company switcher at all (nothing renders for the
    common case of exactly one company)."""
    return await company_access_svc.list_my_companies(session)


@router.post("/me/active-company")
async def set_active_company(
    payload: ActiveCompanyIn,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await company_access_svc.switch_active_company(
        session, user.id, user.company_id, str(payload.company_id),
    )


@router.post("/auth/password-changed", status_code=status.HTTP_204_NO_CONTENT)
async def password_changed(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> None:
    """The frontend calls this right after Supabase Auth confirms a password
    change (self-service reset or in-app change). Supabase owns the actual
    credential; this just gives the change an entry in *our* audit trail and
    fires the "was this you?" notice, same as any other security-relevant
    event in the system already gets logged."""
    row = (await session.execute(
        text("select display_name from profiles where id = :id"), {"id": user.id}
    )).first()
    display_name = row[0] if row else None

    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="password_changed", entity_type="profiles", entity_id=user.id)

    if user.email:
        subject, body = email_svc.password_changed_email(display_name)
        await email_svc.send_email(user.email, subject, body)


@router.get("/employees", response_model=list[EmployeeOut])
async def list_employees(
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[dict]:
    return await emp_svc.list_employees(session, _resolve_company(user, company_id))


@router.post("/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.create_employee(session, user, payload, _resolve_company(user, company_id))


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
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.get_employee(session, employee_id, _resolve_company(user, company_id))


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.update_employee(session, user, employee_id, payload, _resolve_company(user, company_id))


@router.get("/templates")
async def list_templates(session: AsyncSession = Depends(get_tenant_session)) -> list[dict]:
    # Master rows (company_id is null) are a cloning source only (see
    # app.clone_master_templates, run once at tenant provisioning) -- every
    # tenant gets its own copy at that point, so master should never appear
    # as a selectable option itself. Excluding it also fixes a real bug: for
    # super_admin, RLS has no company filter at all (is_super_admin()
    # bypasses it), so without this exclusion the list merged master +
    # EVERY tenant's own copy into one dropdown with identical-looking
    # duplicate names and no way to tell them apart.
    rows = (
        await session.execute(
            text(
                "select id, name, applies_to_level, status from criteria_templates "
                "where company_id is not null "
                "order by name, version"
            )
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/branches", response_model=list[BranchOut])
async def list_branches(
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[dict]:
    return await emp_svc.list_branches(session, _resolve_company(user, company_id))


@router.post("/branches", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
async def create_branch(
    payload: BranchCreate,
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.create_branch(session, user, payload.name, _resolve_company(user, company_id))


@router.patch("/branches/{branch_id}", response_model=BranchOut)
async def update_branch(
    branch_id: str,
    payload: BranchCreate,
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await emp_svc.update_branch(session, user, branch_id, payload.name, _resolve_company(user, company_id))


@router.get("/users", response_model=list[UserOut])
async def list_users(
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[dict]:
    return await users_svc.list_users(session, _resolve_company(user, company_id))


@router.post("/users/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    payload: InviteUserIn,
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    # Self-service: hr_admin invites into their OWN tenant only. super_admin
    # may target a specific tenant via company_id (see _resolve_company) --
    # never accepted from anyone else, so there is no way to target another
    # company through this endpoint otherwise.
    target_company = _resolve_company(user, company_id) or user.company_id
    return await tenant_admin_svc.invite_user(
        session, user.id, target_company,
        payload.email, payload.password, payload.role,
        str(payload.employee_id) if payload.employee_id else None,
    )


@router.patch("/users/{profile_id}/status")
async def set_user_status(
    profile_id: str,
    payload: UserStatusIn,
    company_id: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    target_company = _resolve_company(user, company_id) or user.company_id
    return await tenant_admin_svc.set_user_status(session, user.id, target_company, profile_id, payload.active)


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
