from datetime import datetime
from typing import List
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ConclusionResponse(BaseModel):
    id: UUID
    research_run_id: UUID
    statement: str
    confidence: float
    created_at: datetime
    updated_at: datetime
    finding_ids: List[UUID] = []

    model_config = ConfigDict(from_attributes=True)
