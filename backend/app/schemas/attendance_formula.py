from pydantic import BaseModel, Field


class AttendanceFormulaIn(BaseModel):
    full_score: float = Field(ge=0)
    coef_absent: float = Field(ge=0)
    coef_personal: float = Field(ge=0)
    coef_sick: float = Field(ge=0)
    coef_late: float = Field(ge=0)


class AttendanceFormulaOut(AttendanceFormulaIn):
    pass
