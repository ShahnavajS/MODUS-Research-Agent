"""
Strengthened URL normalization with tracking parameter stripping,
fragment removal, and near-duplicate detection.
"""
import re
import urllib.parse
from difflib import SequenceMatcher
from typing import Set


# Common tracking / analytics URL parameters to strip
_TRACKING_PARAMS: Set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "s", "fbclid", "gclid", "gclsrc", "dclid", "msclkid",
    "mc_cid", "mc_eid", "yclid", "twclid",
    "_ga", "_gl", "source", "campaign",
    "share", "action", "context", "si",
}


def normalize_url(url: str) -> str:
    """
    Normalizes a URL to prevent duplicate source acquisition within a research run.
    - Lowercases scheme and netloc
    - Strips trailing slashes
    - Strips fragment (#...)
    - Strips tracking query parameters (utm_*, fbclid, gclid, etc.)
    - Preserves meaningful query parameters
    """
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")

        # Filter query parameters: keep only non-tracking params
        if parsed.query:
            params = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
            filtered = {
                k: v for k, v in params.items()
                if k.lower() not in _TRACKING_PARAMS
            }
            clean_query = urllib.parse.urlencode(filtered, doseq=True) if filtered else ""
        else:
            clean_query = ""

        # Reconstruct without fragment
        normalized = urllib.parse.urlunparse((scheme, netloc, path, parsed.params, clean_query, ""))
        return normalized
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
        return False  # Different domains — not duplicates
    
    # Same domain: compare titles
    ratio = SequenceMatcher(None, title_a.lower().strip(), title_b.lower().strip()).ratio()
    return ratio >= threshold
