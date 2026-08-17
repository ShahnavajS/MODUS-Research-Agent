"""
Source Relevance Scoring & Ranking Engine.

Single canonical scoring function that produces a composite relevance score
for each search candidate. The pipeline uses these scores to RANK candidates
and select the top-N, rather than applying threshold-based filtering.

Responsibilities:
  - Hard exclusion policy (social media, forums, dictionaries)
  - Domain classification and quality scoring
  - Composite relevance scoring (lexical + concept + domain quality)
  - Domain diversity enforcement
"""

import re
import logging
from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.core.utils import STOP_WORDS, normalize_url

logger = logging.getLogger(__name__)

# ─── Scoring Weights ────────────────────────────────────────────────────────

WEIGHT_TITLE = 0.35
WEIGHT_SNIPPET = 0.30
WEIGHT_CONCEPT = 0.20
WEIGHT_DOMAIN = 0.15


# ─── Hard Exclusion Policy ──────────────────────────────────────────────────

_HARD_EXCLUDED_DOMAINS: Dict[str, str] = {
    # Social media
    "tiktok.com": "hard_excluded_social_media",
    "facebook.com": "hard_excluded_social_media",
    "instagram.com": "hard_excluded_social_media",
    "twitter.com": "hard_excluded_social_media",
    "x.com": "hard_excluded_social_media",
    "threads.net": "hard_excluded_social_media",
    "snapchat.com": "hard_excluded_social_media",
    "pinterest.com": "hard_excluded_social_media",
    "tumblr.com": "hard_excluded_social_media",
    "youtube.com": "hard_excluded_social_media",
    "vimeo.com": "hard_excluded_social_media",
    "linkedin.com": "hard_excluded_social_media",
    # Community & user-generated forums
    "reddit.com": "hard_excluded_community_forum",
    "quora.com": "hard_excluded_community_forum",
    "stackoverflow.com": "hard_excluded_community_forum",
    "stackexchange.com": "hard_excluded_community_forum",
    "medium.com": "hard_excluded_community_forum",
    "substack.com": "hard_excluded_community_forum",
    "answers.yahoo.com": "hard_excluded_community_forum",
    "pastebin.com": "hard_excluded_community_forum",
    "hackernews.com": "hard_excluded_community_forum",
    "news.ycombinator.com": "hard_excluded_community_forum",
    # Dictionary & generic definitions
    "merriam-webster.com": "hard_excluded_dictionary_reference",
    "dictionary.cambridge.org": "hard_excluded_dictionary_reference",
    "wiktionary.org": "hard_excluded_dictionary_reference",
    "britannica.com": "hard_excluded_dictionary_reference",
    "dictionary.com": "hard_excluded_dictionary_reference",
    "thesaurus.com": "hard_excluded_dictionary_reference",
    "collinsdictionary.com": "hard_excluded_dictionary_reference",
    "urbandictionary.com": "hard_excluded_dictionary_reference",
    "vocabulary.com": "hard_excluded_dictionary_reference",
    # Utilities
    "calculator.net": "hard_excluded_utility",
    "calculators.org": "hard_excluded_utility",
    "calculator.com": "hard_excluded_utility",
    "rapidtables.com": "hard_excluded_utility",
    "easycalculation.com": "hard_excluded_utility",
}

_HARD_EXCLUDED_PATH_PATTERNS = [
    (re.compile(r"^https?://(?:www\.)?github\.com/[^/]+/[^/]+/(?:issues|pull|commit|blob|discussions|actions)", re.IGNORECASE), "hard_excluded_github_issue_or_pull"),
    (re.compile(r"^https?://(?:www\.)?github\.com/[^/]+/?$", re.IGNORECASE), "hard_excluded_github_user_profile"),
    (re.compile(r"^https?://(?:www\.)?investopedia\.com/terms/", re.IGNORECASE), "hard_excluded_dictionary_reference"),
]

REJECTION_REASON_AUDIT_LABELS: Dict[str, str] = {
    "hard_excluded_social_media": "SOCIAL_MEDIA_DOMAIN",
    "hard_excluded_community_forum": "COMMUNITY_FORUM_DOMAIN",
    "hard_excluded_dictionary_reference": "DICTIONARY_REFERENCE_DOMAIN",
    "hard_excluded_utility": "GENERIC_UTILITY_DOMAIN",
    "hard_excluded_github_issue_or_pull": "GITHUB_ISSUE_PR",
    "hard_excluded_github_user_profile": "GITHUB_USER_PROFILE",
    "insufficient_relevance": "INSUFFICIENT_RELEVANCE",
    "empty_url": "INVALID_URL",
    "invalid_url": "INVALID_URL",
    "domain_diversity_cap": "DOMAIN_DIVERSITY_CAP",
    "RANK_BELOW_TOP_N": "RANK_BELOW_TOP_N",
}


def is_hard_excluded(url: str) -> Tuple[bool, str]:
    """Check if URL is hard-excluded by policy. Returns (is_excluded, reason)."""
    if not url:
        return True, "empty_url"
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
    except Exception:
        return True, "invalid_url"

    for blocked_domain, reason in _HARD_EXCLUDED_DOMAINS.items():
        if domain == blocked_domain or domain.endswith(f".{blocked_domain}"):
            return True, reason

    for pattern, reason in _HARD_EXCLUDED_PATH_PATTERNS:
        if pattern.search(url):
            return True, reason

    return False, "allowed"


# Backward-compatible alias
is_hard_excluded_source = is_hard_excluded


# ─── Domain Classification ──────────────────────────────────────────────────

_DOMAIN_RULES: List[Tuple[List[str], str, float]] = [
    ([".gov", ".gov.", ".mil", ".europa.eu"], "government", 0.95),
    ([".edu", ".ac.uk", ".ac."], "academic", 0.92),
    (["sciencedirect.com", "nature.com", "ieee.org", "arxiv.org", "ncbi.nlm.nih.gov",
      "pubmed.", "springer.com", "wiley.com", "jstor.org", "researchgate.net",
      "cell.com", "biorxiv.org", "medrxiv.org"], "research", 0.90),
    (["federalreserve.gov", "bis.org", "imf.org", "worldbank.org", "sec.gov",
      "eba.europa.eu", "bankofengland.co.uk", "ecb.europa.eu", "jpmorgan.com",
      "goldmansachs.com", "morganstanley.com"], "financial_institution", 0.90),
    (["mckinsey.com", "gartner.com", "forrester.com", "deloitte.com", "pwc.com",
      "accenture.com", "bcg.com", "bain.com", "capgemini.com", "idc.com",
      "statista.com", "grandviewresearch.com", "iea.org", "epri.com"], "industry_report", 0.88),
    (["reuters.com", "bloomberg.com", "ft.com", "wsj.com", "apnews.com",
      "bbc.com", "nytimes.com", "economist.com", "cnbc.com", "theguardian.com",
      "washingtonpost.com", "forbes.com", "hbr.org", "technologyreview.com",
      "wired.com", "arstechnica.com", "techcrunch.com", "venturebeat.com"], "news", 0.85),
    (["cloud.google.com", "aws.amazon.com", "azure.microsoft.com", "openai.com",
      "microsoft.com", "google.com", "ibm.com", "oracle.com", "salesforce.com",
      "nvidia.com", "anthropic.com", "deepmind.google", "meta.com"], "enterprise", 0.82),
    (["merriam-webster.com", "dictionary.cambridge.org", "dictionary.com",
      "wiktionary.org", "britannica.com", "investopedia.com"], "reference_dictionary", 0.30),
    (["stackoverflow.com", "stackexchange.com", "reddit.com", "quora.com",
      "medium.com", "substack.com", "dev.to", "hackernews.com"], "community_forum", 0.25),
    (["facebook.com", "twitter.com", "x.com", "instagram.com", "linkedin.com",
      "tiktok.com", "youtube.com", "pinterest.com", "threads.net"], "social_media", 0.15),
]


def classify_domain(url: str) -> Tuple[str, float]:
    """Classify URL into source type and domain quality score."""
    if not url:
        return "general_web", 0.70
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return "general_web", 0.70

    for patterns, source_type, quality in _DOMAIN_RULES:
        for pat in patterns:
            if pat.startswith("."):
                if domain.endswith(pat) or f"{pat}." in domain:
                    return source_type, quality
            else:
                if pat in domain:
                    return source_type, quality

    if "github.com" in domain:
        return "community_forum", 0.30
    if "wikipedia.org" in domain:
        return "reference_dictionary", 0.35
    if "scholar.google" in domain:
        return "academic", 0.92

    return "general_web", 0.70


def classify_source_role(source_type: str, domain_quality: float, relevance_score: float) -> str:
    """Classify source role for confidence calibration."""
    if domain_quality < 0.40 or source_type in ("community_forum", "social_media", "reference_dictionary", "reference"):
        return "DISCOVERY_ONLY"
    if domain_quality >= 0.85 and relevance_score >= 0.40:
        return "PRIMARY"
    if domain_quality >= 0.70 and relevance_score >= 0.25:
        return "SECONDARY"
    return "SUPPORTING"


# ─── Key Concept Extraction ─────────────────────────────────────────────────

def extract_key_concepts(text: str, max_concepts: int = 10) -> List[str]:
    """
    Extract domain-agnostic key concepts from text.
    Used for concept-overlap scoring between queries and search results.
    """
    if not text:
        return []

    concepts: List[str] = []
    seen: Set[str] = set()

    # Capitalized multi-word phrases (e.g., "Data Center", "Reserve Bank")
    for phrase in re.findall(r"\b[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)+\b", text):
        p = phrase.strip().lower()
        if p not in seen and len(p) > 3:
            seen.add(p)
            concepts.append(p)

    # Acronyms (e.g., "AI", "GPU", "TSMC")
    for acr in re.findall(r"\b[A-Z]{2,6}\b", text):
        a = acr.lower()
        if a not in seen and a not in STOP_WORDS:
            seen.add(a)
            concepts.append(a)

    # Hyphenated compounds (e.g., "data-center", "water-energy")
    for hyp in re.findall(r"\b[a-zA-Z0-9]+-[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*\b", text):
        h = hyp.lower()
        if h not in seen:
            seen.add(h)
            concepts.append(h)

    # Content words
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    content_words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    for w in content_words:
        if w not in seen:
            seen.add(w)
            concepts.append(w)

    return concepts[:max_concepts]


# ─── Source Relevance Result ─────────────────────────────────────────────────

class SourceScore(BaseModel):
    """Composite relevance score for a search candidate."""
    relevance_score: float = Field(..., description="Composite score 0.0-1.0")
    title_match: float = 0.0
    snippet_match: float = 0.0
    concept_match: float = 0.0
    domain_quality: float = 0.0
    source_type: str = "general_web"
    source_role: str = "SUPPORTING"
    is_hard_excluded: bool = False
    exclusion_reason: str = ""
    rejection_reason: str = ""
    is_relevant: bool = True
    matched_concepts: List[str] = Field(default_factory=list)
    reasoning: str = ""


# Backward-compatible model alias
SourceRelevanceResult = SourceScore


# ─── Core Scoring Function ──────────────────────────────────────────────────

def score_source(
    title: str,
    snippet: str,
    url: str,
    query: str,
    sub_question: str = "",
    min_score: float = 0.0,
) -> SourceScore:
    """
    Score a search result candidate. Returns a composite relevance score.
    The pipeline ranks all candidates by this score and selects top-N.
    """
    excluded, reason = is_hard_excluded(url)
    source_type, domain_quality = classify_domain(url)

    if excluded:
        audit_reason = REJECTION_REASON_AUDIT_LABELS.get(reason, reason.upper())
        return SourceScore(
            relevance_score=0.0,
            domain_quality=domain_quality,
            source_type=source_type,
            source_role="DISCOVERY_ONLY",
            is_hard_excluded=True,
            is_relevant=False,
            exclusion_reason=reason,
            rejection_reason=audit_reason,
            reasoning=f"Hard excluded by policy: {reason}",
        )

    # Build token sets
    query_tokens = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOP_WORDS and len(w) > 2}
    title_tokens = {w for w in re.findall(r"[a-z0-9]+", (title or "").lower()) if w not in STOP_WORDS and len(w) > 1}
    snippet_tokens = {w for w in re.findall(r"[a-z0-9]+", (snippet or "").lower()) if w not in STOP_WORDS and len(w) > 1}

    # Title match
    if query_tokens and title_tokens:
        title_match = min(1.0, len(query_tokens & title_tokens) / len(query_tokens) * 1.2)
    else:
        title_match = 0.0

    # Snippet match
    if query_tokens and snippet_tokens:
        snippet_match = min(1.0, len(query_tokens & snippet_tokens) / len(query_tokens) * 1.1)
    else:
        snippet_match = 0.0

    # Concept match
    target_concepts = extract_key_concepts(f"{query} {sub_question}")
    doc_text = f"{(title or '').lower()} {(snippet or '').lower()}"
    matched = [c for c in target_concepts if c in doc_text] if target_concepts else []
    concept_match = len(matched) / len(target_concepts) if target_concepts else 0.0

    # Composite score
    score = (
        WEIGHT_TITLE * title_match
        + WEIGHT_SNIPPET * snippet_match
        + WEIGHT_CONCEPT * concept_match
        + WEIGHT_DOMAIN * domain_quality
    )
    score = round(min(1.0, max(0.0, score)), 4)
    role = classify_source_role(source_type, domain_quality, score)
    is_rel = score >= min_score

    reasoning = (
        f"title={title_match:.2f} snippet={snippet_match:.2f} "
        f"concept={concept_match:.2f} domain={domain_quality:.2f} "
        f"-> composite={score:.3f} [{role}]"
    )

    return SourceScore(
        relevance_score=score,
        title_match=round(title_match, 4),
        snippet_match=round(snippet_match, 4),
        concept_match=round(concept_match, 4),
        domain_quality=round(domain_quality, 4),
        source_type=source_type,
        source_role=role,
        is_relevant=is_rel,
        rejection_reason="" if is_rel else f"insufficient_relevance ({score:.3f} < {min_score:.2f})",
        matched_concepts=matched,
        reasoning=reasoning,
    )


def evaluate_source_relevance(
    title: str,
    snippet: str,
    url: str,
    query: str,
    sub_question: str = "",
    research_question: str = "",
    min_score: float = 0.15,
) -> SourceScore:
    """Backward-compatible wrapper for evaluate_source_relevance."""
    return score_source(
        title=title,
        snippet=snippet,
        url=url,
        query=query,
        sub_question=sub_question or research_question,
        min_score=min_score,
    )


# Canonical URL backward-compatible alias
canonicalize_url = normalize_url


# ─── Domain Diversity Enforcement ───────────────────────────────────────────

def apply_domain_diversity(
    ranked_candidates: List[dict],
    max_per_domain: int = 2,
    max_total: int = 12,
) -> List[dict]:
    """
    From a list of candidates sorted by score descending, select top-N
    while enforcing a per-domain cap. Returns the selected subset.
    """
    domain_counts: Dict[str, int] = {}
    selected: List[dict] = []

    for item in ranked_candidates:
        if len(selected) >= max_total:
            break

        url = item.get("url", "")
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            domain = "unknown"

        if domain_counts.get(domain, 0) >= max_per_domain:
            continue

        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        selected.append(item)

    return selected


def apply_domain_diversity_filter(
    candidate_sources: List[dict],
    max_per_domain: int = 2,
) -> Tuple[List[dict], List[dict]]:
    """Backward-compatible wrapper for apply_domain_diversity_filter."""
    domain_counts: Dict[str, int] = {}
    accepted: List[dict] = []
    rejected: List[dict] = []

    for item in candidate_sources:
        url = item.get("url", "")
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            domain = "unknown"

        if domain_counts.get(domain, 0) < max_per_domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            accepted.append(item)
        else:
            rejected.append({**item, "rejection_reason": "DOMAIN_DIVERSITY_CAP"})

    return accepted, rejected
