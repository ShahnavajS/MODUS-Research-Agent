import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.models.source import ResearchSource
    from app.models.content import SourceContent


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    source_content_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("source_contents.id", ondelete="SET NULL"), nullable=True, index=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False, default="supporting")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="evidences")
    source: Mapped["ResearchSource"] = relationship("ResearchSource", back_populates="evidences")
    source_content: Mapped["SourceContent | None"] = relationship("SourceContent", back_populates="evidences")
