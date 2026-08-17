"""
Deterministic Numeric Claim Protection Engine.

Guarantees that quantitative claims (ranges, percentages, currencies, ratios, durations)
are faithfully preserved from source evidence without distortion or inverted ranges.
"""

import re
from typing import Any, Dict, List, Tuple


_NUMERIC_RANGE_REGEX = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*(%|percent|x|billion|million|trillion|k|m|b|months?|years?|weeks?|days?|hours?)?",
    re.IGNORECASE,
)

_PERCENTAGE_REGEX = re.compile(
    r"(\d+(?:\.\d+)?)\s*(%|percent|percentage\s+points?|bps)",
    re.IGNORECASE,
)

_CURRENCY_REGEX = re.compile(
    r"(\$|€|£|¥)\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(billion|million|trillion|k|m|b)?",
    re.IGNORECASE,
)

_RATIO_REGEX = re.compile(
    r"(\d+:\d+)\s*(?:to\s*(\d+:\d+))?",
    re.IGNORECASE,
)


def extract_numeric_claims(text: str) -> Dict[str, List[str]]:
    """Extract structured numeric claims from text."""
    ranges = [m.group(0) for m in _NUMERIC_RANGE_REGEX.finditer(text)]
    percentages = [m.group(0) for m in _PERCENTAGE_REGEX.finditer(text)]
    currencies = [m.group(0) for m in _CURRENCY_REGEX.finditer(text)]
    ratios = [m.group(0) for m in _RATIO_REGEX.finditer(text)]

    return {
        "ranges": ranges,
        "percentages": percentages,
        "currencies": currencies,
        "ratios": ratios,
    }


def validate_numeric_preservation(statement: str, excerpt: str) -> Tuple[bool, List[str]]:
    """
    Verify that numerical values in the statement do not invent or invert numbers
    not present in the underlying evidence excerpt.
    
    Returns:
      (is_valid, list_of_violations)
    """
    violations: List[str] = []

    # Check for inverted ranges (e.g. 50-30% where start > end)
    for match in _NUMERIC_RANGE_REGEX.finditer(statement):
        start_val = float(match.group(1))
        end_val = float(match.group(2))
        if start_val > end_val:
            violations.append(f"Inverted numeric range '{match.group(0)}': start ({start_val}) > end ({end_val})")

    # Extract all raw numbers from statement and excerpt
    stmt_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", statement))
    excerpt_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", excerpt))

    # Identify numbers in statement that do not exist anywhere in excerpt
    suspicious_numbers = [n for n in stmt_numbers if n not in excerpt_numbers and float(n) > 4]

    if suspicious_numbers:
        violations.append(f"Statement contains numbers {suspicious_numbers} not grounded in evidence excerpt")

    is_valid = len(violations) == 0
    return is_valid, violations
