from datetime import datetime
from typing import List
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class EvidenceResponse(BaseModel):
    id: UUID
    finding_id: UUID
    source_id: UUID
    source_content_id: UUID | None
    excerpt: str
    relevance_score: float
    evidence_type: str
    created_at: datetime
    source_title: str | None = None
    source_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FindingResponse(BaseModel):
    id: UUID
    research_run_id: UUID
    statement: str
    finding_type: str
    confidence: float
    importance: str
    created_at: datetime
    updated_at: datetime
    evidences: List[EvidenceResponse] = []

    model_config = ConfigDict(from_attributes=True)
