"""
Generic, domain-agnostic finding deduplication engine.

Merges semantically equivalent claims without vector databases or extra LLM calls.
Preserves all evidence links and traces provenance of merged findings.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.utils import STOP_WORDS as _STOP_WORDS

_NUMERIC_PATTERN = re.compile(
    r"(?:\$\s*[\d,.]+(?:\s*(?:billion|million|trillion|k|m|b))?|\b\d+(?:[.,]\d+)?\s*(?:%|percent|x|months?|years?|weeks?|days?|hours?|bps)?|\b\d+:\d+(?:\s*to\s*\d+:\d+)?|\b\d+\s*-\s*\d+\s*(?:%|percent)?)",
    re.IGNORECASE,
)


def extract_numbers(text: str) -> List[str]:
    """Extract normalized numbers, percentages, currencies, and ranges from text."""
    matches = _NUMERIC_PATTERN.findall(text)
    return [re.sub(r"\s+", "", m.lower()) for m in matches if m.strip()]


def _stem_word(w: str) -> str:
    """Lightweight suffix normalization for English research terms."""
    w = w.lower()
    if len(w) > 4:
        for suffix in ("ing", "tion", "tions", "ment", "ments", "ed", "es", "ies", "s"):
            if w.endswith(suffix):
                return w[:-len(suffix)]
    return w


def normalize_statement(text: str) -> str:
    """Normalize statement text for semantic comparison."""
    clean = text.lower().strip()
    clean = re.sub(r"^[\s\d\-.*•\"'\[\]()]+", "", clean)
    prefixes = [
        r"it is reported that",
        r"research indicates that",
        r"studies show that",
        r"evidence shows that",
        r"according to the report",
        r"findings suggest that",
        r"data shows that",
    ]
    for p in prefixes:
        clean = re.sub(rf"^{p}\s+", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"[^\w\s%$\-:]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def statement_tokens(text: str) -> Set[str]:
    """Extract stemmed content words from normalized text."""
    norm = normalize_statement(text)
    words = re.findall(r"[a-z0-9%$:\-]+", norm)
    return {_stem_word(w) for w in words if w not in _STOP_WORDS and len(w) > 1}


def are_findings_duplicate(stmt_a: str, stmt_b: str, threshold: float = 0.50) -> bool:
    """
    Determine if two finding statements are near-duplicates using:
    1. Stemmed content token Jaccard similarity.
    2. Numeric claim compatibility (must share numbers if specific metrics exist).
    3. Substring / concept containment.
    """
    if stmt_a.strip().lower() == stmt_b.strip().lower():
        return True

    tokens_a = statement_tokens(stmt_a)
    tokens_b = statement_tokens(stmt_b)

    if not tokens_a or not tokens_b:
        return False

    # Check numeric claims: if both have numbers, they must have overlap in numbers
    nums_a = set(extract_numbers(stmt_a))
    nums_b = set(extract_numbers(stmt_b))
    if nums_a and nums_b and not (nums_a & nums_b):
        return False

    # Jaccard similarity of stemmed content tokens
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    jaccard = len(intersection) / len(union) if union else 0.0

    # Containment ratio relative to smaller set
    min_len = min(len(tokens_a), len(tokens_b))
    containment = len(intersection) / min_len if min_len > 0 else 0.0

    if jaccard >= threshold or (containment >= 0.65 and min_len >= 3):
        return True

    return False


class CanonicalFindingGroup:
    """Represents a canonical finding and its merged duplicates."""

    def __init__(self, canonical_statement: str, finding_type: str, importance: str, initial_finding_id: Any):
        self.canonical_statement = canonical_statement
        self.finding_type = finding_type
        self.importance = importance
        self.canonical_finding_id = initial_finding_id
        self.merged_statements: List[str] = [canonical_statement]
        self.merged_finding_ids: List[Any] = [initial_finding_id]
        self.source_ids: Set[Any] = set()
        self.evidence_items: List[Any] = []
        self.confidence_scores: List[float] = []

    def add_duplicate(self, statement: str, finding_id: Any, confidence: float, source_id: Optional[Any] = None):
        self.merged_statements.append(statement)
        self.merged_finding_ids.append(finding_id)
        self.confidence_scores.append(confidence)
        if source_id:
            self.source_ids.add(source_id)
        if len(statement) > len(self.canonical_statement) and len(statement) < 300:
            self.canonical_statement = statement


def deduplicate_findings(
    finding_candidates: List[Dict[str, Any]],
    similarity_threshold: float = 0.55,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Deduplicate a list of finding dicts/candidates into canonical findings.
    
    Returns:
      (canonical_findings_list, duplicate_findings_merged_count)
    """
    if not finding_candidates:
        return [], 0

    groups: List[CanonicalFindingGroup] = []

    for item in finding_candidates:
        f = item.model_dump() if hasattr(item, "model_dump") else (item if isinstance(item, dict) else dict(item))
        stmt = f.get("statement", "").strip()
        f_id = f.get("id")
        f_type = f.get("finding_type", "fact")
        f_imp = f.get("importance", "medium")
        f_conf = f.get("confidence", 0.80)
        source_id = f.get("source_id")

        matched_group: Optional[CanonicalFindingGroup] = None
        for group in groups:
            if are_findings_duplicate(stmt, group.canonical_statement, threshold=similarity_threshold):
                matched_group = group
                break

        if matched_group:
            matched_group.add_duplicate(stmt, f_id, f_conf, source_id)
            if f.get("evidence"):
                matched_group.evidence_items.extend(f["evidence"])
            elif f.get("excerpt"):
                matched_group.evidence_items.append(f)
        else:
            group = CanonicalFindingGroup(stmt, f_type, f_imp, f_id)
            if source_id:
                group.source_ids.add(source_id)
            if f.get("evidence"):
                group.evidence_items.extend(f["evidence"])
            elif f.get("excerpt"):
                group.evidence_items.append(f)
            group.confidence_scores.append(f_conf)
            groups.append(group)

    canonical_findings: List[Dict[str, Any]] = []
    total_merged = 0

    for group in groups:
        duplicates_count = len(group.merged_statements) - 1
        total_merged += duplicates_count

        canonical_findings.append({
            "id": group.canonical_finding_id,
            "statement": group.canonical_statement,
            "finding_type": group.finding_type,
            "importance": group.importance,
            "confidence_scores": group.confidence_scores,
            "distinct_sources_count": len(group.source_ids),
            "merged_count": len(group.merged_statements),
            "merged_finding_ids": group.merged_finding_ids,
            "merged_statements": group.merged_statements,
            "evidence": group.evidence_items,
            "evidence_items": group.evidence_items,
        })

    return canonical_findings, total_merged
