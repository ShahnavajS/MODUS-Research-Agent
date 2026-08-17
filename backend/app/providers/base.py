from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SubQuestionCandidate(BaseModel):
    question: str = Field(..., description="Decomposed sub-question text")
    sequence_number: int = Field(1, description="Order sequence number")
    rationale: Optional[str] = Field(None, description="Rationale for sub-inquiry")
    priority: str = Field("medium", description="Priority: low, medium, high")


class SourceDocumentInput(BaseModel):
    source_id: str = Field(..., description="Unique ID of source in database")
    title: str = Field(..., description="Title of source document")
    url: str = Field(..., description="Canonical URL of source")
    source_type: str = Field("general_web", description="Domain classification type")
    credibility: float = Field(0.70, description="Domain credibility rating")
    content: str = Field(..., description="Extracted plain text content")


class FindingCandidate(BaseModel):
    source_id: Optional[str] = Field(None, description="Optional ID of the source supporting this finding")
    statement: str = Field(..., description="Structured finding statement")
    finding_type: str = Field("fact", description="Type: fact, trend, claim, observation, prediction, risk, opportunity, metric, benefit, deployment, governance")
    confidence: float = Field(0.85, description="Confidence score 0.0 - 1.0")
    importance: str = Field("medium", description="Importance: low, medium, high, critical")
    source_url: str = Field(..., description="Source URL where evidence was found")
    excerpt: str = Field(..., description="Direct text excerpt serving as evidence")
    relevance_score: float = Field(0.9, description="Relevance score of excerpt")
    evidence_type: str = Field("supporting", description="Type: supporting, contradicting, contextual")
    rationale: Optional[str] = Field(None, description="Extraction rationale")


class ContradictionCandidate(BaseModel):
    finding_a_statement: str = Field(..., description="Statement of first finding")
    finding_b_statement: str = Field(..., description="Statement of second finding")
    description: str = Field(..., description="Description of the conflict")
    severity: str = Field("medium", description="Severity: low, medium, high")
    contradiction_category: str = Field(
        "DIRECT_CONTRADICTION",
        description="Category: DIRECT_CONTRADICTION | SCOPE_MISMATCH | TIME_PERIOD_MISMATCH | DEFINITION_MISMATCH | METHODOLOGY_MISMATCH | FORECAST_DISAGREEMENT | CONTEXTUAL_TENSION",
    )


class ConclusionCandidate(BaseModel):
    statement: str = Field(..., description="High-level synthesized conclusion statement")
    confidence: float = Field(0.88, description="Confidence score 0.0 - 1.0")
    supporting_finding_statements: List[str] = Field(..., description="Statements of member findings that support this conclusion")
    limitations: Optional[str] = Field(None, description="Scope limitations or uncertainty notes")


class AIProvider(ABC):
    """
    Abstract Base Class for AI Intelligence Providers.
    Defines structured operations for question decomposition, finding extraction,
    evidence linkage, contradiction detection, and conclusion generation.
    """

    @abstractmethod
    async def decompose_question(self, question: str) -> List[SubQuestionCandidate]:
        """Decompose a high-level research question into structured sub-questions."""
        pass

    @abstractmethod
    async def extract_findings_and_evidence(
        self, source_url: str, source_content: str, research_question: str
    ) -> List[FindingCandidate]:
        """Extract structured findings and supporting evidence excerpts from source text."""
        pass

    async def extract_findings_from_source_batch(
        self, sources: List[SourceDocumentInput], research_question: str
    ) -> List[FindingCandidate]:
        """Extract structured findings from a batch of verified source documents."""
        # Default fallback: iterate over sources
        all_findings = []
        for s in sources:
            findings = await self.extract_findings_and_evidence(
                source_url=s.url, source_content=s.content, research_question=research_question
            )
            for f in findings:
                f.source_id = s.source_id
                f.source_url = s.url
            all_findings.extend(findings)
        return all_findings

    @abstractmethod
    async def detect_contradictions_from_findings(
        self, findings: List[Dict[str, Any]]
    ) -> List[ContradictionCandidate]:
        """Identify contradictions or conflicts between extracted findings."""
        pass

    @abstractmethod
    async def generate_conclusions_from_findings(
        self, question: str, findings: List[Dict[str, Any]]
    ) -> List[ConclusionCandidate]:
        """Synthesize high-level conclusions derived strictly from member findings."""
        pass
