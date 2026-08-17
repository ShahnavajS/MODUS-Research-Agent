import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from app.models.base import Base
from app.models.associations import conclusion_findings

if TYPE_CHECKING:
    from app.models.run import ResearchRun
    from app.models.evidence import Evidence
    from app.models.contradiction import Contradiction
    from app.models.conclusion import Conclusion


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False, default="fact", index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    importance: Mapped[str] = mapped_column(String(50), nullable=False, default="medium", server_default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    research_run: Mapped["ResearchRun"] = relationship("ResearchRun", back_populates="findings")
    evidences: Mapped[List["Evidence"]] = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")
    conclusions: Mapped[List["Conclusion"]] = relationship("Conclusion", secondary=conclusion_findings, back_populates="findings")
