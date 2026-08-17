import uuid
from datetime import datetime
from typing import Any, List, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.question import ResearchQuestion
    from app.models.sub_question import ResearchSubQuestion
    from app.models.source import ResearchSource
    from app.models.finding import Finding
    from app.models.contradiction import Contradiction
    from app.models.conclusion import Conclusion


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", server_default="queued", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    question: Mapped["ResearchQuestion"] = relationship("ResearchQuestion", back_populates="runs")
    sub_questions: Mapped[List["ResearchSubQuestion"]] = relationship("ResearchSubQuestion", back_populates="research_run", cascade="all, delete-orphan")
    sources: Mapped[List["ResearchSource"]] = relationship("ResearchSource", back_populates="research_run", cascade="all, delete-orphan")
    findings: Mapped[List["Finding"]] = relationship("Finding", back_populates="research_run", cascade="all, delete-orphan")
    contradictions: Mapped[List["Contradiction"]] = relationship("Contradiction", back_populates="research_run", cascade="all, delete-orphan")
    conclusions: Mapped[List["Conclusion"]] = relationship("Conclusion", back_populates="research_run", cascade="all, delete-orphan")
