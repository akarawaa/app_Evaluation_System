from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    emp_code: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    position: Optional[str] = Field(default=None, max_length=200)
    level: str = Field(default="operational", pattern=r"^(operational|supervisor)$")
    branch_id: Optional[UUID] = None
    supervisor_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None


class EmployeeUpdate(BaseModel):
    """All fields optional; only keys explicitly present in the request are
    applied (see model_dump(exclude_unset=True) in the service)."""
    emp_code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    position: Optional[str] = Field(default=None, max_length=200)
    level: Optional[str] = Field(default=None, pattern=r"^(operational|supervisor)$")
    status: Optional[str] = Field(default=None, pattern=r"^(active|inactive)$")
    branch_id: Optional[UUID] = None
    supervisor_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None


class EmployeeOut(BaseModel):
    id: UUID
    emp_code: str
    full_name: str
    position: Optional[str] = None
    level: str
    status: str
    branch_id: Optional[UUID] = None
    branch_name: Optional[str] = None
    supervisor_id: Optional[UUID] = None
    supervisor_name: Optional[str] = None
    manager_id: Optional[UUID] = None
    manager_name: Optional[str] = None
