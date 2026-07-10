from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UserOut(BaseModel):
    id: UUID
    display_name: Optional[str] = None
    employee_id: Optional[UUID] = None
    roles: list[str]
