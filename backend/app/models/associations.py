from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.types import UUID
from app.models.base import Base

conclusion_findings = Table(
    "conclusion_findings",
    Base.metadata,
    Column("conclusion_id", UUID(as_uuid=True), ForeignKey("conclusions.id", ondelete="CASCADE"), primary_key=True),
    Column("finding_id", UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True),
)
