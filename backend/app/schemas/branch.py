from uuid import UUID

from pydantic import BaseModel, Field


class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class BranchOut(BaseModel):
    id: UUID           # serialized to string in JSON; accepts UUID from the DB
    name: str
