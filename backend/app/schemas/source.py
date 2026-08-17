from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ContentResponse(BaseModel):
    id: UUID
    source_id: UUID
    content: str
    content_hash: str | None
    word_count: int | None
    extraction_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceResponse(BaseModel):
    id: UUID
    research_run_id: UUID
    title: str
    url: str | None
    publisher: str | None
    author: str | None
    published_at: datetime | None
    retrieved_at: datetime
    source_type: str
    credibility_score: float | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    content: ContentResponse | None = None

    model_config = ConfigDict(from_attributes=True)
