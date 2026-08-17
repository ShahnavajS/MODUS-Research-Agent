import re
from typing import Any, Dict, List
from app.providers.base import (
    AIProvider,
    ConclusionCandidate,
    ContradictionCandidate,
    FindingCandidate,
    SubQuestionCandidate,
)


class MockAIProvider(AIProvider):
    """
    Development Mock AI Provider.
    Generates deterministic, input-dependent structured outputs for testing the research pipeline.
    NOTE: Used for local testing/development prior to live LLM provider integration.
    """

    async def decompose_question(self, question: str) -> List[SubQuestionCandidate]:
        clean_q = question.strip()
        topic = clean_q.rstrip("?.!")

        return [
            SubQuestionCandidate(
                question=f"What is the current adoption state and core market benchmarks for {topic}?",
                sequence_number=1,
            ),
            SubQuestionCandidate(
                question=f"What primary operational benefits and ROI metrics are achieved through {topic}?",
                sequence_number=2,
            ),
            SubQuestionCandidate(
                question=f"What key implementation risks, infrastructure bottlenecks, and cost constraints impact {topic}?",
                sequence_number=3,
            ),
        ]

    async def extract_findings_and_evidence(
        self, source_url: str, source_content: str, research_question: str
    ) -> List[FindingCandidate]:
        candidates: List[FindingCandidate] = []
        sentences = [s.strip() for s in re.split(r"[.\n]+", source_content) if len(s.strip()) > 20]

        # Extract 2 structured findings with direct excerpts
        if len(sentences) >= 1:
            excerpt1 = sentences[0]
            candidates.append(
                FindingCandidate(
                    statement=excerpt1[:150],
                    finding_type="fact",
                    confidence=0.88,
                    importance="high",
                    source_url=source_url,
                    excerpt=excerpt1,
                    relevance_score=0.95,
                    evidence_type="supporting",
                )
            )

        if len(sentences) >= 2:
            excerpt2 = sentences[1]
            candidates.append(
                FindingCandidate(
                    statement=excerpt2[:150],
                    finding_type="risk",
                    confidence=0.82,
                    importance="medium",
                    source_url=source_url,
                    excerpt=excerpt2,
                    relevance_score=0.90,
                    evidence_type="supporting",
                )
            )

        return candidates

    async def detect_contradictions_from_findings(
        self, findings: List[Dict[str, Any]]
    ) -> List[ContradictionCandidate]:
        # If we have both a 'fact' finding and a 'risk' finding, detect contradiction
        fact_finding = next((f for f in findings if f.get("finding_type") == "fact"), None)
        risk_finding = next((f for f in findings if f.get("finding_type") == "risk"), None)

        if fact_finding and risk_finding:
            return [
                ContradictionCandidate(
                    finding_a_statement=fact_finding["statement"],
                    finding_b_statement=risk_finding["statement"],
                    description=(
                        "Tension detected between immediate top-line efficiency gains and "
                        "extended capital payback periods driven by infrastructure installation costs."
                    ),
                    severity="medium",
                    contradiction_category="CONTEXTUAL_TENSION",
                )
            ]
        return []

    async def generate_conclusions_from_findings(
        self, question: str, findings: List[Dict[str, Any]]
    ) -> List[ConclusionCandidate]:
        if not findings:
            return []

        supporting_statements = [f["statement"] for f in findings[:4]]
        topic = question.strip().rstrip("?.!")

        statement = (
            f"Synthesized conclusion for '{topic}': Research confirms quantifiable operational efficiency gains, "
            f"supported by {len(supporting_statements)} distinct empirical findings. "
            f"However, strategic roadmaps must factor in payback timelines and infrastructure integration complexity."
        )

        return [
            ConclusionCandidate(
                statement=statement,
                confidence=0.89,
                supporting_finding_statements=supporting_statements,
            )
        ]
