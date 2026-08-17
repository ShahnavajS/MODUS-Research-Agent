import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from app.models.base import Base
from app.models.associations import conclusion_findings

if TYPE_CHECKING:
    from app.models.run import ResearchRun
    from app.models.finding import Finding


class Conclusion(Base):
    __tablename__ = "conclusions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    research_run: Mapped["ResearchRun"] = relationship("ResearchRun", back_populates="conclusions")
    findings: Mapped[List["Finding"]] = relationship("Finding", secondary=conclusion_findings, back_populates="conclusions")
