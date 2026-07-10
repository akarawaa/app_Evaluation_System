from typing import Optional

from pydantic import BaseModel


class ImportRowError(BaseModel):
    row: int
    emp_code: Optional[str] = None
    message: str


class ImportResult(BaseModel):
    created: int
    updated: int
    linked: int          # supervisor/manager relationships resolved
    branches_created: int
    errors: list[ImportRowError]
