import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.run import ResearchRun
    from app.models.finding import Finding


class Contradiction(Base):
    __tablename__ = "contradictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    contradiction_category: Mapped[str] = mapped_column(String(50), nullable=False, default="DIRECT_CONTRADICTION", server_default="DIRECT_CONTRADICTION")
    resolution_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unresolved", server_default="unresolved")
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    research_run: Mapped["ResearchRun"] = relationship("ResearchRun", back_populates="contradictions")
    finding_a: Mapped["Finding"] = relationship("Finding", foreign_keys=[finding_a_id])
    finding_b: Mapped["Finding"] = relationship("Finding", foreign_keys=[finding_b_id])
