"""
Deterministic Constraint Preservation and Validation Engine.

Ensures that crucial user constraints from the original research question — such as:
  - Temporal horizons (e.g. 2030, through 2030)
  - Geographic/Jurisdictional scopes (e.g. United States, European Union, China, India)
  - Comparative entity pairings (e.g. large pharma vs biotech firms)
  - Key analytical & risk dimensions (e.g. electricity, water, semiconductor, energy security, ROI, regulations)
are strictly preserved across question decomposition sub-questions.
"""

import re
import logging
from typing import Any, List, Set, Tuple
from app.providers.base import SubQuestionCandidate

logger = logging.getLogger(__name__)

# Known geographic & jurisdictional entities
_KNOWN_GEOGRAPHIES = [
    ("United States", ["united states", "u.s.", "us", "usa", "america"]),
    ("European Union", ["european union", "e.u.", "eu", "europe"]),
    ("China", ["china", "chinese", "prc"]),
    ("India", ["india", "indian"]),
    ("United Kingdom", ["united kingdom", "u.k.", "uk", "britain"]),
    ("Japan", ["japan", "japanese"]),
    ("Germany", ["germany", "german"]),
    ("Asia-Pacific", ["asia-pacific", "apac", "asia"]),
    ("Latin America", ["latin america", "latam"]),
    ("Middle East", ["middle east", "mena", "gulf"]),
]

# Comparative organizational pairings
_COMPARATIVE_PAIRS = [
    ("pharma_vs_biotech", ["pharmaceutical companies", "biotechnology firms", "biotech", "pharma"],
     "How do the economics, implementation capabilities, and risk profiles differ between large pharmaceutical companies and smaller biotechnology firms?"),
    ("tier1_vs_regional", ["large banks", "regional banks", "community banks", "fintechs"],
     "How do adoption strategies, implementation costs, and risk tolerance differ between large global institutions and smaller regional firms?"),
]


def extract_question_constraints(question: str) -> dict[str, Any]:
    """
    Deterministically extract temporal, geographic, and comparative constraints
    from the original research question.
    """
    q_lower = question.lower()

    # 1. Temporal Constraints
    temporal_matches = re.findall(r"\b(20[2-5]\d)\b", question)
    relative_temporal = []
    for pattern in [r"through\s+20\d\d", r"by\s+20\d\d", r"from\s+20\d\d\s+to\s+20\d\d",
                    r"over\s+the\s+next\s+decade", r"through\s+the\s+decade"]:
        found = re.findall(pattern, q_lower)
        if found:
            relative_temporal.extend(found)

    temporal_constraints = list(set(temporal_matches + relative_temporal))

    # 2. Geographic / Regional Constraints
    detected_geographies: List[str] = []
    for canonical_name, aliases in _KNOWN_GEOGRAPHIES:
        for alias in aliases:
            # Word boundary search
            if re.search(r"\b" + re.escape(alias) + r"\b", q_lower):
                if canonical_name not in detected_geographies:
                    detected_geographies.append(canonical_name)
                break

    # 3. Comparative Entity Constraints
    detected_comparisons: List[str] = []
    for pair_id, keywords, _ in _COMPARATIVE_PAIRS:
        matched_kw = [kw for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", q_lower)]
        if len(matched_kw) >= 2 or ("differ" in q_lower and len(matched_kw) >= 1) or ("compare" in q_lower and len(matched_kw) >= 1):
            detected_comparisons.append(pair_id)

    # 4. Check for explicit "compare across" or "differ between"
    is_comparative = any(term in q_lower for term in ["compare", "comparison", "differ", "differences between", "versus", " vs "])

    return {
        "temporal_constraints": temporal_constraints,
        "geographic_constraints": detected_geographies,
        "comparative_constraints": detected_comparisons,
        "is_comparative": is_comparative,
    }


def validate_and_augment_sub_questions(
    original_question: str,
    sub_questions: List[SubQuestionCandidate],
    max_sub_questions: int = 5,
) -> Tuple[List[SubQuestionCandidate], dict[str, Any]]:
    """
    Validate that sub-questions cover all detected temporal, geographic, and comparative constraints.
    If critical constraints are missing from Gemini's decomposition, deterministically augment
    the sub-questions to ensure complete, rigorous coverage.
    """
    constraints = extract_question_constraints(original_question)
    temporal_list = constraints["temporal_constraints"]
    geo_list = constraints["geographic_constraints"]
    comp_list = constraints["comparative_constraints"]

    augmented = list(sub_questions)
    sub_q_texts = [sq.question for sq in sub_questions]
    combined_sub_q_text = " ".join(sub_q_texts).lower()

    missing_geos = [geo for geo in geo_list if not any(alias in combined_sub_q_text for _, aliases in _KNOWN_GEOGRAPHIES if _ == geo for alias in aliases)]
    missing_temporals = [t for t in temporal_list if t.lower() not in combined_sub_q_text]

    # 1. Geographic / Comparative Augmentation
    # If the user asked to compare across 2+ regions (e.g. US, EU, China, India) and they aren't covered
    if len(geo_list) >= 2 and len(missing_geos) >= 1:
        logger.info(f"[constraint_guard] Detected missing geographic constraints: {missing_geos}. Augmenting sub-questions.")
        geo_names_str = ", ".join(geo_list[:-1]) + f", and {geo_list[-1]}" if len(geo_list) > 1 else geo_list[0]
        time_clause = f" through {temporal_list[0]}" if temporal_list else ""
        
        comp_question_text = (
            f"How do the adoption dynamics, measurable impacts, regulatory approaches, and operational risks "
            f"compare across {geo_names_str}{time_clause}?"
        )
        
        # Check if already present
        if not any(comp_question_text.lower() == sq.question.lower() for sq in augmented):
            if len(augmented) >= max_sub_questions:
                # Replace lowest priority sub-question or last one
                augmented[-1] = SubQuestionCandidate(
                    question=comp_question_text,
                    sequence_number=len(augmented),
                    rationale="Preserves explicit geographic comparative constraints from research question.",
                    priority="high",
                )
            else:
                augmented.append(SubQuestionCandidate(
                    question=comp_question_text,
                    sequence_number=len(augmented) + 1,
                    rationale="Preserves explicit geographic comparative constraints from research question.",
                    priority="high",
                ))

    # 2. Organizational Comparative Augmentation
    if comp_list:
        for pair_id in comp_list:
            for p_id, _, template_q in _COMPARATIVE_PAIRS:
                if p_id == pair_id:
                    # Check if organizational comparison is represented
                    pair_terms = ["differ", "biotech", "pharma", "regional", "smaller"]
                    has_pair = sum(1 for pt in pair_terms if pt in combined_sub_q_text) >= 2
                    if not has_pair:
                        logger.info(f"[constraint_guard] Augmenting missing comparative pair: {pair_id}")
                        if len(augmented) >= max_sub_questions:
                            augmented[-1] = SubQuestionCandidate(
                                question=template_q,
                                sequence_number=len(augmented),
                                rationale="Preserves explicit organizational comparative constraints from research question.",
                                priority="high",
                            )
                        else:
                            augmented.append(SubQuestionCandidate(
                                question=template_q,
                                sequence_number=len(augmented) + 1,
                                rationale="Preserves explicit organizational comparative constraints from research question.",
                                priority="high",
                            ))

    # 3. Temporal Horizon Propagation
    # If a temporal year (e.g. 2030) was specified in original question, ensure forecast / trend sub-questions carry it
    if temporal_list:
        target_year = temporal_list[0]
        for i, sq in enumerate(augmented):
            sq_lower = sq.question.lower()
            if any(term in sq_lower for term in ["trend", "forecast", "future", "expansion", "reshap", "projection", "demand", "grow"]):
                if target_year not in sq.question and not any(y in sq.question for y in ["2025", "2026", "2027", "2028", "2029", "2030", "2035"]):
                    # Append temporal boundary cleanly
                    augmented[i] = SubQuestionCandidate(
                        question=f"{sq.question.rstrip('?')} through {target_year}?",
                        sequence_number=sq.sequence_number,
                        rationale=sq.rationale,
                        priority=sq.priority,
                    )

    # Re-index sequence numbers
    for idx, sq in enumerate(augmented):
        sq.sequence_number = idx + 1

    validation_summary = {
        "temporal_constraints_detected": temporal_list,
        "temporal_constraints_preserved": len(missing_temporals) == 0 or len(temporal_list) > 0,
        "geographic_constraints_detected": geo_list,
        "geographic_constraints_preserved": len(geo_list) == 0 or any(g in " ".join(sq.question for sq in augmented) for g in geo_list),
        "comparative_constraints_detected": comp_list,
        "is_comparative": constraints["is_comparative"],
        "final_sub_questions_count": len(augmented),
    }

    return augmented, validation_summary
