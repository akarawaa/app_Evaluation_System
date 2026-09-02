from typing import Optional

from pydantic import BaseModel, Field


class AttendanceBracketItem(BaseModel):
    min_value: float = Field(ge=0)
    max_value: Optional[float] = None  # None = unbounded top bracket
    score: float = Field(ge=0)


class AttendanceBracketsSetIn(BaseModel):
    items: list[AttendanceBracketItem]
