from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.conclusion import ConclusionResponse
from app.schemas.contradiction import ContradictionResponse
from app.schemas.finding import FindingResponse
from app.schemas.source import SourceResponse
from app.schemas.sub_question import SubQuestionResponse


class RunCountsSchema(BaseModel):
    sub_questions: int = 0
    sources: int = 0
    findings: int = 0
    evidence: int = 0
    contradictions: int = 0
    conclusions: int = 0


class ResearchRunCreate(BaseModel):
    metadata_json: dict[str, Any] | None = Field(None, description="Optional runtime parameters or configuration")


class ResearchRunResponse(BaseModel):
    id: UUID
    question_id: UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    counts: RunCountsSchema = Field(default_factory=RunCountsSchema)

    model_config = ConfigDict(from_attributes=True)


class ResearchRunDetailResponse(BaseModel):
    id: UUID
    question_id: UUID
    question_text: str
    project_id: UUID
    project_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    counts: RunCountsSchema = Field(default_factory=RunCountsSchema)
    sub_questions: List[SubQuestionResponse] = []
    sources: List[SourceResponse] = []
    findings: List[FindingResponse] = []
    contradictions: List[ContradictionResponse] = []
    conclusions: List[ConclusionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TraceabilityNodeSchema(BaseModel):
    conclusion_id: UUID
    conclusion_statement: str
    conclusion_confidence: float
    findings: List[FindingResponse] = []


class RunTraceabilityResponse(BaseModel):
    run_id: UUID
    question_id: UUID
    question_text: str
    status: str
    execution_metadata: dict[str, Any] | None = None
    provenance_graph: List[TraceabilityNodeSchema] = []

    model_config = ConfigDict(from_attributes=True)
