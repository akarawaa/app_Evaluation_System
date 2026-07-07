from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    emp_code: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    position: Optional[str] = Field(default=None, max_length=200)
    level: str = Field(default="operational", pattern=r"^(operational|supervisor)$")
    branch_id: Optional[UUID] = None


class EmployeeOut(BaseModel):
    id: UUID
    emp_code: str
    full_name: str
    level: str
    status: str
