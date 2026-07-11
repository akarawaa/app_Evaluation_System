from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    hr_email: str = Field(min_length=3, max_length=200)
    hr_password: str = Field(min_length=8, max_length=128)


class TenantOut(BaseModel):
    company: dict
    hr_user_id: str
    templates_cloned: int


class TenantStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(active|suspended)$")


class InviteUserIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern=r"^(hr_admin|manager|dept_manager|md|gm|employee)$")
    employee_id: Optional[UUID] = None
