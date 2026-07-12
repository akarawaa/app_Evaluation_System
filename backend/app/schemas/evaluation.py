from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EvaluationCreate(BaseModel):
    employee_id: UUID
    template_id: UUID
    kind: str = Field(pattern=r"^(annual|probation)$")
    probation_checkpoint: Optional[str] = Field(default=None, pattern=r"^(30|60|90|119)$")
    cycle_id: Optional[UUID] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class ScoreIn(BaseModel):
    evaluation_item_id: UUID
    score: float

    @field_validator("score")
    @classmethod
    def _half_steps_1_to_5(cls, v: float) -> float:
        if v < 1 or v > 5 or (v * 2) != int(v * 2):
            raise ValueError("score must be between 1 and 5 in 0.5 steps")
        return v


class CommentIn(BaseModel):
    category_order: int
    comment: Optional[str] = None


class ScoresUpdate(BaseModel):
    scores: list[ScoreIn] = []
    comments: list[CommentIn] = []


class AttendanceSet(BaseModel):
    """HR-only: raw attendance facts for the period. The score is normally
    computed from these (see services.evaluations.compute_attendance_score);
    attendance_score lets HR override the computed value with a manual one.
    clear_override discards a previous manual override and goes back to the
    formula (recomputed from the figures in this same request)."""
    sick_days: int = Field(default=0, ge=0)
    personal_days: int = Field(default=0, ge=0)
    late_count: int = Field(default=0, ge=0)
    late_minutes: int = Field(default=0, ge=0)
    absent_days: int = Field(default=0, ge=0)
    attendance_score: Optional[float] = Field(default=None, ge=0, le=40)
    clear_override: bool = False


class ApproveIn(BaseModel):
    comment: Optional[str] = None


class FinalizeIn(BaseModel):
    probation_decision: Optional[str] = Field(default=None, pattern=r"^(hire|not_hire|extend|other)$")
    probation_extend_days: Optional[int] = None
    decision_note: Optional[str] = None
    comment: Optional[str] = None
