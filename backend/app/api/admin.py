"""Platform admin API (super_admin only). Tenant provisioning + management."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_session
from app.core.security import CurrentUser, require_roles
from app.schemas.tenant import InviteUserIn, TenantCreate, TenantOut, TenantStatusUpdate
from app.services import tenant_admin as tenant_svc
from app.services.provisioning import create_tenant

router = APIRouter(prefix="/api/admin")


@router.get("/tenants")
async def list_tenants(
    user: CurrentUser = Depends(require_roles()),   # no roles listed => super_admin only
    session: AsyncSession = Depends(get_tenant_session),
) -> list[dict]:
    return await tenant_svc.list_tenants(session)


@router.post("/tenants", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def provision_tenant(
    payload: TenantCreate,
    user: CurrentUser = Depends(require_roles()),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await create_tenant(
        session,
        actor_id=user.id,
        name=payload.name,
        slug=payload.slug,
        hr_email=payload.hr_email,
        hr_password=payload.hr_password,
    )


@router.get("/tenants/{company_id}")
async def get_tenant(
    company_id: str,
    user: CurrentUser = Depends(require_roles()),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await tenant_svc.get_tenant(session, company_id)


@router.patch("/tenants/{company_id}/status")
async def update_tenant_status(
    company_id: str,
    payload: TenantStatusUpdate,
    user: CurrentUser = Depends(require_roles()),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await tenant_svc.update_tenant_status(session, user.id, company_id, payload.status)


@router.post("/tenants/{company_id}/users", status_code=status.HTTP_201_CREATED)
async def invite_user(
    company_id: str,
    payload: InviteUserIn,
    user: CurrentUser = Depends(require_roles()),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await tenant_svc.invite_user(
        session, user.id, company_id,
        payload.email, payload.password, payload.role,
        str(payload.employee_id) if payload.employee_id else None,
    )
