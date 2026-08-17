from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class QuestionCreate(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000, description="The research question string")
    status: str = Field("active", description="Question status e.g. active, answered, archived")


class QuestionUpdate(BaseModel):
    question: str | None = Field(None, min_length=5, max_length=1000, description="The updated research question string")
    status: str | None = Field(None, description="Updated status")


class QuestionResponse(BaseModel):
    id: UUID
    project_id: UUID
    question: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
