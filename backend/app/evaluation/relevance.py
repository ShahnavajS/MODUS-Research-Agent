"""
Deterministic Source Relevance Evaluator & Candidate Engine.

Implements Stage 2A of the Two-Stage Retrieval Pipeline:
  - Canonicalizes URLs and strips tracking parameters
  - Enforces Hard-Exclusion Policy (Social Media, User Forums, Calculators, Dictionaries)
  - Scores search candidates via:
      * title_match: Token overlap between search query/concepts and document title
      * snippet_match: Term frequency and concept overlap in snippet
      * concept_match: Dynamic entity and domain phrase overlap from sub-question
      * domain_quality: Category weight based on domain classification
  - Enforces Domain Diversity Constraints (Max N sources per domain)

This score represents RETRIEVAL CANDIDATE ELIGIBILITY — semantic validation occurs in Stage 2B.
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── Configurable Candidate Scoring Weights ─────────────────────────────────

WEIGHT_TITLE = 0.35
WEIGHT_SNIPPET = 0.30
WEIGHT_CONCEPT = 0.20
WEIGHT_DOMAIN = 0.15

# ─── URL Canonicalization & Parameter Cleansing ─────────────────────────────

_TRACKING_PARAM_PREFIXES = ("utm_", "ga_", "mc_", "_hs", "pk_")
_TRACKING_PARAM_EXACT = {
    "ref", "ref_src", "fbclid", "gclid", "msclkid", "twclid", "igshid",
    "spm", "from_source", "feature", "source", "share", "ncid", "ocid",
    "session_id", "client_id", "s_kwcid", "dclid", "zanpid",
}


def canonicalize_url(url: str) -> str:
    """
    Deterministically canonicalize a URL:
      - Lowercase scheme and domain
      - Strip tracking/analytics parameters
      - Strip URL fragments (#...)
      - Strip trailing slash for consistency
    """
    if not url or not isinstance(url, str):
        return ""

    url_str = url.strip()
    try:
        parsed = urlparse(url_str)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()

        # Remove default port
        if netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif netloc.endswith(":443"):
            netloc = netloc[:-4]

        # Strip tracking query parameters
        clean_params = {}
        if parsed.query:
            query_dict = parse_qs(parsed.query, keep_blank_values=False)
            for k, v in query_dict.items():
                k_lower = k.lower()
                if k_lower in _TRACKING_PARAM_EXACT or any(k_lower.startswith(p) for p in _TRACKING_PARAM_PREFIXES):
                    continue
                clean_params[k] = v[0] if len(v) == 1 else v

        clean_query = urlencode(clean_params, doseq=True) if clean_params else ""

        # Normalize path
        path = parsed.path or "/"
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        canonical = urlunparse((scheme, netloc, path, parsed.params, clean_query, ""))
        return canonical
    except Exception:
        return url_str


# ─── English Stop Words ─────────────────────────────────────────────────────

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


# ─── Dynamic Concept & Entity Extraction (Generic / No Hardcoding) ──────────

def extract_key_concepts(text: str, max_concepts: int = 10) -> List[str]:
    """
    Dynamically extract domain-agnostic key concepts, acronyms, and entity phrases.
    Works for any subject (AI infrastructure, clinical medicine, monetary policy, etc.)
    without hardcoding.
    """
    if not text:
        return []

    concepts: List[str] = []
    seen: Set[str] = set()

    # 1. Capitalized multi-word named entities & phrases (e.g. "Data Center", "Reserve Bank")
    cap_phrases = re.findall(r"\b[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)+\b", text)
    for phrase in cap_phrases:
        p_clean = phrase.strip().lower()
        if p_clean not in seen and len(p_clean) > 3:
            seen.add(p_clean)
            concepts.append(p_clean)

    # 2. Acronyms & technical abbreviations (e.g. "AI", "HBM", "GPU", "GDP", "LLM", "TSMC")
    acronyms = re.findall(r"\b[A-Z]{2,6}\b", text)
    for acr in acronyms:
        a_lower = acr.lower()
        if a_lower not in seen and a_lower not in _STOP_WORDS:
            seen.add(a_lower)
            concepts.append(a_lower)

    # 3. Hyphenated technical compound terms (e.g. "data-center", "water-energy")
    hyphenated = re.findall(r"\b[a-zA-Z0-9]+-[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*\b", text)
    for hyp in hyphenated:
        h_lower = hyp.lower()
        if h_lower not in seen:
            seen.add(h_lower)
            concepts.append(h_lower)

    # 4. Content words & bigrams
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    content_words = [w for w in words if w not in _STOP_WORDS and len(w) > 2]

    for i in range(len(content_words) - 1):
        bigram = f"{content_words[i]} {content_words[i+1]}"
        if bigram not in seen:
            seen.add(bigram)
            concepts.append(bigram)

    for w in content_words:
        if w not in seen:
            seen.add(w)
            concepts.append(w)

    return concepts[:max_concepts]


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
    "domain_diversity_cap": "DOMAIN_DIVERSITY_CAP",
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


# ─── Source Role Classification ─────────────────────────────────────────────

def classify_source_role(source_type: str, domain_quality: float, relevance_score: float) -> str:
    """
    Classify source into one of four roles:
    - PRIMARY: High quality domain (>= 0.85) + strong relevance (>= 0.40)
    - SECONDARY: Good domain (>= 0.70) + good relevance (>= 0.25)
    - SUPPORTING: Valid source with moderate relevance
    - DISCOVERY_ONLY: Forums, social media, reference dictionaries (domain quality < 0.40)
    """
    if domain_quality < 0.40 or source_type in ("community_forum", "social_media", "reference_dictionary"):
        return "DISCOVERY_ONLY"
    if domain_quality >= 0.85 and relevance_score >= 0.40:
        return "PRIMARY"
    if domain_quality >= 0.70 and relevance_score >= 0.25:
        return "SECONDARY"
    return "SUPPORTING"


# ─── Relevance Result Model ─────────────────────────────────────────────────

class SourceRelevanceResult(BaseModel):
    """Explainable candidate relevance evaluation result for a search result."""
    relevance_score: float = Field(..., description="Composite relevance score 0.0-1.0")
    title_match: float = Field(..., description="Title/query token overlap score")
    snippet_match: float = Field(..., description="Snippet/query concept overlap score")
    concept_match: float = Field(..., description="Important concept coverage score")
    domain_quality: float = Field(..., description="Domain type quality signal")
    source_type: str = Field(..., description="Classified source type")
    source_role: str = Field("SUPPORTING", description="Classified source role: PRIMARY | SECONDARY | SUPPORTING | DISCOVERY_ONLY")
    is_relevant: bool = Field(..., description="Whether source meets minimum candidate threshold")
    is_hard_excluded: bool = Field(False, description="Whether source is deterministically hard-blocked")
    rejection_reason: str = Field("", description="Specific rejection reason if not relevant or hard excluded")
    matched_concepts: List[str] = Field(default_factory=list, description="Dynamic concepts matched in document")
    reasoning: str = Field("", description="Human-readable relevance explanation")


# ─── Core Evaluator Function (Stage 2A: Candidate Filter) ───────────────────

def evaluate_source_relevance(
    title: str,
    snippet: str,
    url: str,
    query: str,
    sub_question: str = "",
    research_question: str = "",
    min_score: float = 0.15,
) -> SourceRelevanceResult:
    """
    Deterministic broad candidate relevance evaluation (Stage 2A).
    Evaluates hard exclusion policy, title match, snippet match, dynamic concept match, and domain quality.
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

    # Extract dynamic key concepts from query and sub-question
    target_concepts = extract_key_concepts(f"{query} {sub_question}")
    query_content_tokens = set([w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in _STOP_WORDS and len(w) > 2])

    title_lower = (title or "").lower()
    snippet_lower = (snippet or "").lower()
    doc_text = f"{title_lower} {snippet_lower}"

    title_tokens = set([w for w in re.findall(r"[a-z0-9]+", title_lower) if w not in _STOP_WORDS and len(w) > 1])
    snippet_tokens = set([w for w in re.findall(r"[a-z0-9]+", snippet_lower) if w not in _STOP_WORDS and len(w) > 1])

    # 1. Title Match
    if query_content_tokens and title_tokens:
        overlap_q_in_title = len(query_content_tokens & title_tokens) / len(query_content_tokens)
        title_match = round(min(1.0, overlap_q_in_title * 1.2), 4)
    else:
        title_match = 0.0

    # 2. Snippet Match
    if query_content_tokens and snippet_tokens:
        overlap_q_in_snippet = len(query_content_tokens & snippet_tokens) / len(query_content_tokens)
        snippet_match = round(min(1.0, overlap_q_in_snippet * 1.1), 4)
    else:
        snippet_match = 0.0

    # 3. Dynamic Concept & Entity Match
    matched_concepts: List[str] = []
    if target_concepts:
        for c in target_concepts:
            if c in doc_text:
                matched_concepts.append(c)
        concept_match = round(len(matched_concepts) / len(target_concepts), 4)
    else:
        concept_match = 0.0

    # Composite Candidate Score
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
        f"-> composite={relevance_score:.3f} [{source_role}] ({'CANDIDATE' if is_relevant else 'REJECTED'})"
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
        matched_concepts=matched_concepts,
        reasoning=reasoning,
    )


# ─── Retrieval Diversity Filter ─────────────────────────────────────────────

def apply_domain_diversity_filter(
    candidate_sources: List[dict],
    max_per_domain: int = 2,
) -> Tuple[List[dict], List[dict]]:
    """
    Enforces domain diversity constraints across candidate sources.
    Prevents a single domain from dominating the candidate set while preserving
    a balanced distribution across diverse categories (gov, academic, news, industry).

    Returns (accepted_candidates, rejected_candidates).
    """
    domain_counts: Dict[str, int] = {}
    accepted: List[dict] = []
    rejected: List[dict] = []

    for item in candidate_sources:
        src = item.get("source")
        url = src.url if hasattr(src, "url") else item.get("url", "")
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            domain = "unknown"

        count = domain_counts.get(domain, 0)
        if count < max_per_domain:
            domain_counts[domain] = count + 1
            accepted.append(item)
        else:
            rejected.append({
                **item,
                "rejection_reason": f"DOMAIN_DIVERSITY_CAP (max {max_per_domain} per domain '{domain}')",
            })

    return accepted, rejected
