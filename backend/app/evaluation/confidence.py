"""
Deterministic Confidence Calibration Engine.

Calculates explainable, calibrated confidence for research findings and conclusions
based on multi-factor evidence signals:
  - evidence_match_score: Quality of verbatim substring excerpt match
  - source_relevance_score: Retrieval relevance of the underlying source
  - source_credibility_score: Domain classification credibility
  - corroboration_score: Cross-source corroboration boost
  - source_role_limitations: Low-quality/discovery-only source ceiling
  - contradiction_penalty: Active conflict deduction
"""

from typing import Any, Dict, List, Optional


def calculate_calibrated_finding_confidence(
    evidence_match_score: float = 1.0,
    source_relevance: float = 0.70,
    source_credibility: float = 0.75,
    distinct_sources_count: int = 1,
    source_role: str = "SUPPORTING",
    is_contradicted: bool = False,
    contradiction_severity: str = "none",
) -> Dict[str, Any]:
    """
    Deterministically calculate multi-factor confidence score for a finding.
    
    Formula:
      base_score = 0.20 * evidence_match + 0.30 * source_relevance + 0.30 * source_credibility
      corroboration_bonus = +0.08 if sources == 2 else +0.15 if sources >= 3 else 0.0
      contradiction_penalty = -0.15 if high, -0.08 if medium, -0.04 if low, 0.0 if none
      raw_confidence = base_score + corroboration_bonus - contradiction_penalty
      
    Ceiling rules:
      - If source_role == "DISCOVERY_ONLY" and distinct_sources_count == 1: max confidence is 0.50
      - Max overall confidence is 0.95 (never 100% to reflect empirical fallibility)
      - Min confidence is 0.15
    """
    # Base components
    base_score = (
        0.20 * min(1.0, max(0.0, evidence_match_score))
        + 0.30 * min(1.0, max(0.0, source_relevance))
        + 0.30 * min(1.0, max(0.0, source_credibility))
    )

    # Corroboration boost
    if distinct_sources_count >= 3:
        corroboration_bonus = 0.15
    elif distinct_sources_count == 2:
        corroboration_bonus = 0.08
    else:
        corroboration_bonus = 0.0

    # Contradiction penalty
    if is_contradicted:
        if contradiction_severity == "high":
            contradiction_penalty = 0.15
        elif contradiction_severity == "medium":
            contradiction_penalty = 0.08
        else:
            contradiction_penalty = 0.04
    else:
        contradiction_penalty = 0.0

    raw_confidence = base_score + corroboration_bonus - contradiction_penalty

    # Apply ceiling rules
    if source_role == "DISCOVERY_ONLY" and distinct_sources_count <= 1:
        final_confidence = min(0.50, raw_confidence)
    else:
        final_confidence = min(0.95, max(0.15, raw_confidence))

    final_confidence = round(final_confidence, 2)

    return {
        "confidence": final_confidence,
        "factors": {
            "evidence_match_score": round(evidence_match_score, 2),
            "source_relevance_score": round(source_relevance, 2),
            "source_credibility_score": round(source_credibility, 2),
            "corroboration_bonus": round(corroboration_bonus, 2),
            "contradiction_penalty": round(contradiction_penalty, 2),
            "source_role": source_role,
        },
    }
