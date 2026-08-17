from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ContradictionResponse(BaseModel):
    id: UUID
    research_run_id: UUID
    finding_a_id: UUID
    finding_b_id: UUID
    finding_a_statement: str | None = None
    finding_b_statement: str | None = None
    description: str
    severity: str
    contradiction_category: str = "DIRECT_CONTRADICTION"
    resolution_status: str
    resolution_notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
