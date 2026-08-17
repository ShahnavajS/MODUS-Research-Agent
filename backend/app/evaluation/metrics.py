"""
Research Quality Metrics Calculator.

Calculates deterministic, application-level quality signals for research runs.
Tracks source lifecycle distribution, evidence grounding, conclusion traceability,
and strict mathematical consistency.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def calculate_research_quality_metrics(
    discovered_sources_count: int,
    relevant_sources_count: int,
    rejected_irrelevant_count: int,
    fetch_success_count: int,
    failed_sources_count: int,
    evidence_eligible_count: int,
    findings_count: int,
    grounded_findings_count: int,
    unsupported_findings_count: int,
    contradictions_count: int,
    conclusions_count: int,
    conclusions_with_findings_count: int,
    execution_mode: str = "real",
    source_type_distribution: Optional[Dict[str, int]] = None,
    timing_breakdown: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Calculates deterministic application-level research quality signals.

    These metrics measure pipeline coverage, evidence linkage completeness,
    source lifecycle transparency, and provenance integrity.

    Enforces strict mathematical consistency:
      - fetch_success_count <= relevant_sources_count <= discovered_sources_count
      - evidence_eligible_count <= fetch_success_count
      - grounded_findings_count <= findings_count
    """
    # Source coverage: what fraction of discovered sources were successfully fetched
    source_coverage = (
        round(fetch_success_count / discovered_sources_count, 4)
        if discovered_sources_count > 0
        else 0.0
    )

    # Evidence coverage: what fraction of findings have valid grounded evidence
    evidence_coverage = (
        round(grounded_findings_count / findings_count, 4)
        if findings_count > 0
        else 0.0
    )

    # Fetch success rate
    successful_fetch_rate = (
        round(fetch_success_count / relevant_sources_count, 4)
        if relevant_sources_count > 0
        else 0.0
    )

    # Evidence eligibility rate
    evidence_eligibility_rate = (
        round(evidence_eligible_count / fetch_success_count, 4)
        if fetch_success_count > 0
        else 0.0
    )

    # Conclusion traceability: all conclusions reference real findings
    conclusion_traceability = (
        conclusions_with_findings_count == conclusions_count
        if conclusions_count > 0
        else False
    )

    metrics: Dict[str, Any] = {
        "execution_mode": execution_mode,
        # Source lifecycle metrics
        "discovered_sources": discovered_sources_count,
        "relevant_sources": relevant_sources_count,
        "rejected_irrelevant_sources": rejected_irrelevant_count,
        "fetch_success_sources": fetch_success_count,
        "failed_sources": failed_sources_count,
        "evidence_eligible_sources": evidence_eligible_count,
        # Coverage & rates
        "source_coverage": source_coverage,
        "successful_fetch_rate": successful_fetch_rate,
        "evidence_eligibility_rate": evidence_eligibility_rate,
        "evidence_coverage": evidence_coverage,
        # Finding metrics
        "total_findings": findings_count,
        "grounded_findings": grounded_findings_count,
        "unsupported_findings": unsupported_findings_count,
        # Contradiction & conclusion
        "contradiction_count": contradictions_count,
        "conclusion_traceability": conclusion_traceability,
    }

    if source_type_distribution:
        metrics["source_type_distribution"] = source_type_distribution

    if timing_breakdown:
        metrics["timing_breakdown"] = timing_breakdown

    return metrics
