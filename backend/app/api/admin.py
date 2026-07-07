"""Platform admin API (super_admin only). Tenant provisioning — Step 6."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_session
from app.core.security import CurrentUser, require_roles
from app.schemas.tenant import TenantCreate, TenantOut
from app.services.provisioning import create_tenant

router = APIRouter(prefix="/api/admin")


@router.post("/tenants", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def provision_tenant(
    payload: TenantCreate,
    user: CurrentUser = Depends(require_roles()),   # no roles listed => super_admin only
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
