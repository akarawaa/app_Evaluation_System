from pydantic import BaseModel

from app.schemas.employee_import import ImportRowError


class AttendanceImportResult(BaseModel):
    updated: int
    skipped_overridden: int  # rows whose target evaluation has a manual HR override; left untouched
    errors: list[ImportRowError]
