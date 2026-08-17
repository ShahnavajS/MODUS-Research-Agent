"""
Core utilities: URL normalization, near-duplicate detection, and shared constants.

This is the SINGLE canonical URL normalizer for the entire pipeline.
"""
import re
import urllib.parse
from difflib import SequenceMatcher
from typing import Set


# ─── Shared English Stop Words (single canonical definition) ─────────────────

STOP_WORDS: Set[str] = {
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
    "furthermore", "moreover", "however", "often", "typically",
    "primarily", "largely",
}


# ─── Tracking Parameters to Strip ────────────────────────────────────────────

_TRACKING_PARAM_PREFIXES = ("utm_", "ga_", "mc_", "_hs", "pk_")
_TRACKING_PARAM_EXACT: Set[str] = {
    "ref", "ref_src", "fbclid", "gclid", "msclkid", "twclid", "igshid",
    "spm", "from_source", "feature", "source", "share", "ncid", "ocid",
    "session_id", "client_id", "s_kwcid", "dclid", "zanpid", "yclid",
    "s", "campaign", "action", "context", "si",
    "_ga", "_gl",
}


def normalize_url(url: str) -> str:
    """
    Canonical URL normalization for the entire pipeline.
    - Lowercases scheme and netloc
    - Removes default ports (:80, :443)
    - Strips tracking/analytics query parameters
    - Strips URL fragments
    - Strips trailing slash
    """
    if not url or not isinstance(url, str):
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
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
            query_dict = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
            for k, v in query_dict.items():
                k_lower = k.lower()
                if k_lower in _TRACKING_PARAM_EXACT:
                    continue
                if any(k_lower.startswith(p) for p in _TRACKING_PARAM_PREFIXES):
                    continue
                clean_params[k] = v[0] if len(v) == 1 else v

        clean_query = urllib.parse.urlencode(clean_params, doseq=True) if clean_params else ""

        # Normalize path
        path = (parsed.path or "").rstrip("/")

        canonical = urllib.parse.urlunparse((scheme, netloc, path, parsed.params, clean_query, ""))
        return canonical
    except Exception:
        return url.strip().rstrip("/")


def is_near_duplicate(title_a: str, domain_a: str, title_b: str, domain_b: str, threshold: float = 0.85) -> bool:
    """
    Conservative near-duplicate detection using domain match + title similarity.
    Only flags duplicates when BOTH same domain and highly similar titles.
    """
    if not domain_a or not domain_b:
        return False
    if domain_a.lower() != domain_b.lower():
        return False
    ratio = SequenceMatcher(None, title_a.lower().strip(), title_b.lower().strip()).ratio()
    return ratio >= threshold
