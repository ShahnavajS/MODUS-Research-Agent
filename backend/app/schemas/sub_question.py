from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SubQuestionResponse(BaseModel):
    id: UUID
    research_run_id: UUID
    question: str
    sequence_number: int
    status: str
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
