"""
Deterministic Source Relevance Evaluator Engine.

Scores search results using explainable, deterministic signals:
  - title_match:   Token overlap between search query keywords and document title
  - snippet_match: Term frequency intersection between search query and snippet
  - concept_match: Important concept coverage (entities, technologies, domains)
  - domain_quality: Category weight based on domain classification

Composite formula (configurable weights):
  relevance_score = W_title * title_match + W_snippet * snippet_match
                  + W_concept * concept_match + W_domain * domain_quality

This score represents RETRIEVAL RELEVANCE only — it does not claim factual correctness.
"""

import re
import logging
from typing import List, Optional, Set
from urllib.parse import urlparse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── Configurable Scoring Weights ───────────────────────────────────────────

WEIGHT_TITLE = 0.35
WEIGHT_SNIPPET = 0.35
WEIGHT_CONCEPT = 0.20
WEIGHT_DOMAIN = 0.10

# ─── English Stop Words (lightweight, no external deps) ─────────────────────

_STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "it", "its", "this",
    "that", "these", "those", "i", "you", "he", "she", "we", "they", "my",
    "your", "his", "her", "our", "their", "me", "him", "us", "them",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "not", "no", "nor", "so", "if", "then", "than", "too", "very",
    "just", "about", "also", "more", "most", "some", "any", "each",
    "all", "both", "few", "other", "such", "only", "own",
    "up", "out", "off", "over", "under", "again", "further",
    "there", "here", "as", "into", "through", "during", "before", "after",
    "above", "below", "between", "same", "because",
}


# ─── Hard Exclusion Patterns (Deterministic Policy) ─────────────────────────

_HARD_EXCLUDED_DOMAINS: dict[str, str] = {
    # Social media platforms
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
    # Community / User-generated forums
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
    # Dictionary / Generic definition & reference sites
    "merriam-webster.com": "hard_excluded_dictionary_reference",
    "dictionary.cambridge.org": "hard_excluded_dictionary_reference",
    "wiktionary.org": "hard_excluded_dictionary_reference",
    "britannica.com": "hard_excluded_dictionary_reference",
    "dictionary.com": "hard_excluded_dictionary_reference",
    "thesaurus.com": "hard_excluded_dictionary_reference",
    "collinsdictionary.com": "hard_excluded_dictionary_reference",
    "urbandictionary.com": "hard_excluded_dictionary_reference",
    "vocabulary.com": "hard_excluded_dictionary_reference",
    # Low-value utility / calculator / debug sites
    "calculator.net": "hard_excluded_utility",
    "calculators.org": "hard_excluded_utility",
    "calculator.com": "hard_excluded_utility",
    "rapidtables.com": "hard_excluded_utility",
    "easycalculation.com": "hard_excluded_utility",
}

REJECTION_REASON_AUDIT_LABELS: dict[str, str] = {
    "hard_excluded_social_media": "SOCIAL_MEDIA_DOMAIN",
    "hard_excluded_community_forum": "COMMUNITY_FORUM_DOMAIN",
    "hard_excluded_dictionary_reference": "DICTIONARY_REFERENCE_DOMAIN",
    "hard_excluded_utility": "GENERIC_UTILITY_DOMAIN",
    "hard_excluded_github_issue_or_pull": "GITHUB_ISSUE_PR",
    "hard_excluded_github_user_profile": "GITHUB_USER_PROFILE",
    "insufficient_relevance": "INSUFFICIENT_RELEVANCE",
    "empty_url": "INVALID_URL",
    "invalid_url": "INVALID_URL",
}

_HARD_EXCLUDED_PATH_PATTERNS = [
    (re.compile(r"^https?://(?:www\.)?github\.com/[^/]+/[^/]+/(?:issues|pull|commit|blob|discussions|actions)", re.IGNORECASE), "hard_excluded_github_issue_or_pull"),
    (re.compile(r"^https?://(?:www\.)?github\.com/[^/]+/?$", re.IGNORECASE), "hard_excluded_github_user_profile"),
    (re.compile(r"^https?://(?:www\.)?investopedia\.com/terms/", re.IGNORECASE), "hard_excluded_dictionary_reference"),
]


def is_hard_excluded_source(url: str) -> tuple[bool, str]:
    """
    Deterministically check if a URL belongs to a hard-excluded domain or category.
    Hard-excluded sources must NOT be fetched, enter finding extraction, or produce evidence.
    Returns (is_excluded, reason).
    """
    if not url:
        return True, "empty_url"

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
    except Exception:
        return True, "invalid_url"

    # 1. Exact or suffix match on hard-excluded domains
    for blocked_domain, reason in _HARD_EXCLUDED_DOMAINS.items():
        if domain == blocked_domain or domain.endswith(f".{blocked_domain}"):
            return True, reason

    # 2. Path-based hard exclusion patterns
    for pattern, reason in _HARD_EXCLUDED_PATH_PATTERNS:
        if pattern.search(url):
            return True, reason

    return False, "allowed"


# ─── Domain Classification ──────────────────────────────────────────────────

_DOMAIN_RULES: list[tuple[list[str], str, float]] = [
    # Government / Regulator
    ([".gov", ".gov.", ".mil", ".europa.eu"], "government", 0.95),
    # Academic
    ([".edu", ".ac.uk", ".ac.", "scholar.google"], "academic", 0.92),
    # Research publishers
    (["sciencedirect.com", "nature.com", "ieee.org", "arxiv.org", "ncbi.nlm.nih.gov",
      "pubmed.", "springer.com", "wiley.com", "jstor.org", "researchgate.net", "cell.com", "biorxiv.org", "medrxiv.org"], "research", 0.90),
    # Financial institutions / regulators
    (["federalreserve.gov", "bis.org", "imf.org", "worldbank.org", "sec.gov",
      "eba.europa.eu", "bankofengland.co.uk", "ecb.europa.eu", "jpmorgan.com",
      "goldmansachs.com", "morganstanley.com", "citigroup.com", "bankofamerica.com"], "financial_institution", 0.90),
    # Industry research / consulting
    (["mckinsey.com", "gartner.com", "forrester.com", "deloitte.com", "pwc.com",
      "accenture.com", "bcg.com", "bain.com", "capgemini.com", "idc.com",
      "statista.com", "grandviewresearch.com", "iea.org", "epri.com", "trendforce.com"], "industry_report", 0.88),
    # Reputable news
    (["reuters.com", "bloomberg.com", "ft.com", "wsj.com", "apnews.com",
      "bbc.com", "nytimes.com", "economist.com", "cnbc.com", "theguardian.com",
      "washingtonpost.com", "forbes.com", "hbr.org", "technologyreview.com",
      "wired.com", "arstechnica.com", "techcrunch.com", "venturebeat.com"], "news", 0.85),
    # Enterprise / company technical research
    (["cloud.google.com", "aws.amazon.com", "azure.microsoft.com", "openai.com",
      "microsoft.com", "google.com", "ibm.com", "oracle.com", "salesforce.com",
      "nvidia.com", "anthropic.com", "deepmind.google", "meta.com"], "enterprise", 0.82),
    # Reference / dictionary
    (["merriam-webster.com", "dictionary.cambridge.org", "dictionary.com",
      "wiktionary.org", "britannica.com", "investopedia.com"], "reference_dictionary", 0.30),
    # Community / forums
    (["stackoverflow.com", "stackexchange.com", "reddit.com", "quora.com",
      "medium.com", "dev.to", "hackernews.com"], "community_forum", 0.25),
    # Social media
    (["facebook.com", "twitter.com", "x.com", "instagram.com", "linkedin.com",
      "tiktok.com", "youtube.com", "pinterest.com", "threads.net"], "social_media", 0.15),
]


def classify_domain(url: str) -> tuple[str, float]:
    """
    Deterministically classify a URL's source type and domain quality score.
    Returns (source_type, domain_quality_score).
    """
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

    return "general_web", 0.70


# ─── Token Processing Utilities ─────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """Tokenize text to lowercase alphanumeric words, removing stop words."""
    words = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def _jaccard(set_a: Set[str], set_b: Set[str]) -> float:
    """Jaccard similarity coefficient between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


# ─── Source Role Classification ─────────────────────────────────────────────

def classify_source_role(source_type: str, domain_quality: float, relevance_score: float) -> str:
    """
    Classify source into one of four roles:
    - PRIMARY: High quality domain (>= 0.85) + strong relevance (>= 0.50)
    - SECONDARY: Good domain (>= 0.70) + good relevance (>= 0.35)
    - SUPPORTING: Valid source with moderate relevance
    - DISCOVERY_ONLY: Forums, social media, reference dictionaries (domain quality < 0.40)
    """
    if domain_quality < 0.40 or source_type in ("community_forum", "social_media", "reference_dictionary"):
        return "DISCOVERY_ONLY"
    if domain_quality >= 0.85 and relevance_score >= 0.50:
        return "PRIMARY"
    if domain_quality >= 0.70 and relevance_score >= 0.35:
        return "SECONDARY"
    return "SUPPORTING"


# ─── Relevance Result Model ─────────────────────────────────────────────────

class SourceRelevanceResult(BaseModel):
    """Explainable relevance evaluation result for a search result."""
    relevance_score: float = Field(..., description="Composite relevance score 0.0-1.0")
    title_match: float = Field(..., description="Title/query token overlap score")
    snippet_match: float = Field(..., description="Snippet/query concept overlap score")
    concept_match: float = Field(..., description="Important concept coverage score")
    domain_quality: float = Field(..., description="Domain type quality signal")
    source_type: str = Field(..., description="Classified source type")
    source_role: str = Field("SUPPORTING", description="Classified source role: PRIMARY | SECONDARY | SUPPORTING | DISCOVERY_ONLY")
    is_relevant: bool = Field(..., description="Whether source meets minimum relevance threshold")
    is_hard_excluded: bool = Field(False, description="Whether source is deterministically hard-blocked (e.g. social, forums, dictionaries)")
    rejection_reason: str = Field("", description="Specific rejection reason if not relevant or hard excluded")
    reasoning: str = Field("", description="Human-readable relevance explanation")


# ─── Core Evaluator Function ────────────────────────────────────────────────

def evaluate_source_relevance(
    title: str,
    snippet: str,
    url: str,
    query: str,
    sub_question: str = "",
    research_question: str = "",
    min_score: float = 0.35,
) -> SourceRelevanceResult:
    """
    Deterministic source relevance evaluation.
    Evaluates hard exclusion policy, title match, snippet match, concept match, and domain quality against the query.
    """
    # 0. Check Hard Exclusion Policy
    is_blocked, block_reason = is_hard_excluded_source(url)
    source_type, domain_quality = classify_domain(url)

    if is_blocked:
        return SourceRelevanceResult(
            relevance_score=0.0,
            title_match=0.0,
            snippet_match=0.0,
            concept_match=0.0,
            domain_quality=domain_quality,
            source_type=source_type,
            source_role="DISCOVERY_ONLY",
            is_relevant=False,
            is_hard_excluded=True,
            rejection_reason=block_reason,
            reasoning=f"Hard excluded by source policy: {block_reason}",
        )

    # Tokenize the specific search query and sub-question
    query_tokens = set(_tokenize(f"{query} {sub_question}"))
    if not query_tokens:
        query_tokens = set(_tokenize(research_question))

    title_tokens = set(_tokenize(title))
    snippet_tokens = set(_tokenize(snippet))

    # 1. Title Match: compute overlap between query keywords and title
    if query_tokens and title_tokens:
        overlap_query_in_title = len(query_tokens & title_tokens) / len(query_tokens)
        overlap_title_in_query = len(query_tokens & title_tokens) / len(title_tokens)
        jaccard = _jaccard(query_tokens, title_tokens)
        title_match = round(max(overlap_query_in_title, overlap_title_in_query * 0.8, jaccard), 4)
    else:
        title_match = 0.0

    # 2. Snippet Match: what fraction of query keywords appear in snippet
    if query_tokens and snippet_tokens:
        overlap_in_snippet = len(query_tokens & snippet_tokens) / len(query_tokens)
        jaccard_snippet = _jaccard(query_tokens, snippet_tokens)
        snippet_match = round(max(overlap_in_snippet, jaccard_snippet * 1.2), 4)
        snippet_match = min(1.0, snippet_match)
    else:
        snippet_match = 0.0

    # 3. Concept Match: multi-word phrases and domain keywords
    concept_match = _compute_concept_match(query, f"{title} {snippet}")

    # Composite Score
    raw_score = (
        WEIGHT_TITLE * title_match
        + WEIGHT_SNIPPET * snippet_match
        + WEIGHT_CONCEPT * concept_match
        + WEIGHT_DOMAIN * domain_quality
    )
    relevance_score = round(min(1.0, max(0.0, raw_score)), 4)

    is_relevant = relevance_score >= min_score
    source_role = classify_source_role(source_type, domain_quality, relevance_score)
    rejection_reason = "" if is_relevant else f"insufficient_relevance ({relevance_score:.3f} < {min_score:.2f})"

    reasoning = (
        f"title={title_match:.2f} snippet={snippet_match:.2f} "
        f"concept={concept_match:.2f} domain={domain_quality:.2f} "
        f"-> composite={relevance_score:.3f} [{source_role}] ({'RELEVANT' if is_relevant else 'REJECTED'})"
    )

    return SourceRelevanceResult(
        relevance_score=relevance_score,
        title_match=title_match,
        snippet_match=snippet_match,
        concept_match=concept_match,
        domain_quality=domain_quality,
        source_type=source_type,
        source_role=source_role,
        is_relevant=is_relevant,
        is_hard_excluded=False,
        rejection_reason=rejection_reason,
        reasoning=reasoning,
    )


def _compute_concept_match(query_text: str, result_text: str) -> float:
    """
    Extract key multi-word phrases and content terms from query and check presence in result text.
    """
    query_lower = query_text.lower()
    result_lower = result_text.lower()

    words = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", query_lower)
    content_words = [w for w in words if w not in _STOP_WORDS and len(w) > 2]

    if not content_words:
        return 0.0

    # Bigrams
    concepts: List[str] = []
    for i in range(len(content_words) - 1):
        concepts.append(f"{content_words[i]} {content_words[i+1]}")

    # Individual key terms
    concepts.extend(content_words)

    if not concepts:
        return 0.0

    found = sum(1 for c in concepts if c in result_lower)
    return round(min(1.0, found / len(concepts)), 4)
