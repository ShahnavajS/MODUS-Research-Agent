"""
Production Web Research Provider.

Powered by DuckDuckGo Search (DDGS) with:
  - Dynamic focused query generation from sub-question concepts
  - SSRF-guarded HTTP content extraction
  - Strict fetch contract: no synthetic/fallback content injection
  - Content quality validation before AI processing
"""

import asyncio
import hashlib
import logging
import re
import time
from urllib.parse import urlparse
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from app.core.config import settings
from app.core.security import is_safe_external_url
from app.core.utils import normalize_url
from app.providers.research.base import ResearchDocument, ResearchProvider, ResearchSearchResult
from app.evaluation.relevance import classify_domain

logger = logging.getLogger(__name__)


# ─── Query Generation ────────────────────────────────────────────────────────

def clean_search_query(query: str) -> str:
    """
    Clean conversational question prefixes so search engines target core subject matter.
    Strips preamble phrases like 'What are the current...', 'How are large banks...',
    'What evidence exists that...', etc.
    """
    # Strip common conversational question prefixes (order matters — longer first)
    prefixes = [
        r"what evidence exists that",
        r"what quantifiable evidence",
        r"what specific evidence",
        r"what are the current",
        r"what are the key",
        r"what are the main",
        r"what are the major",
        r"what operational",
        r"what specific",
        r"what are the",
        r"what is the",
        r"how are large",
        r"how is the",
        r"how are",
        r"how is",
        r"in what ways",
        r"to what extent",
        r"and what evidence exists",
    ]
    clean = query
    for prefix in prefixes:
        clean = re.sub(rf"^{prefix}\s+", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(rf",?\s*{prefix}\s+", " ", clean, flags=re.IGNORECASE).strip()

    # Remove trailing question marks and excessive punctuation
    clean = re.sub(r"[?!]+$", "", clean).strip()
    # Remove special characters but keep hyphens and apostrophes
    clean = re.sub(r"[^\w\s\-']", " ", clean).strip()
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()

    if len(clean) > 90:
        clean = clean[:90].rsplit(" ", 1)[0]

    return clean if len(clean) >= 5 else query[:90]


def generate_focused_queries(sub_question: str, max_queries: int = 2) -> List[str]:
    """
    Generate focused search queries from a sub-question by extracting key concepts.
    Avoids generic repetition of the original question.
    """
    base_query = clean_search_query(sub_question)
    queries = [base_query]

    if max_queries <= 1:
        return queries

    # Extract content words for a variant query
    words = re.findall(r"[a-z0-9]+(?:[-][a-z0-9]+)*", base_query.lower())
    from app.core.utils import STOP_WORDS
    key_terms = [w for w in words if w not in STOP_WORDS and len(w) > 2]

    if len(key_terms) >= 4:
        # Create a variant query using a subset of key terms + "analysis" or "report"
        variant = " ".join(key_terms[:6]) + " analysis"
        if variant != base_query:
            queries.append(variant)

    return queries[:max_queries]


# ─── Content Validation ──────────────────────────────────────────────────────

# Patterns indicating error/login pages rather than useful content
_ERROR_PAGE_PATTERNS = [
    r"access denied",
    r"403 forbidden",
    r"404 not found",
    r"page not found",
    r"sign in to continue",
    r"log in to continue",
    r"please log in",
    r"please sign in",
    r"create an account",
    r"subscribe to continue",
    r"you need to enable javascript",
    r"enable cookies",
    r"captcha",
    r"are you a robot",
    r"verify you are human",
]
_ERROR_PAGE_RE = re.compile("|".join(_ERROR_PAGE_PATTERNS), re.IGNORECASE)


def validate_extracted_content(text: str, min_words: int = 30) -> tuple[bool, str]:
    """
    Validate that extracted text is meaningful content, not an error page,
    login wall, or empty/useless text.
    Returns (is_valid, reason).
    """
    if not text or not text.strip():
        return False, "empty_content"

    word_count = len(text.split())
    if word_count < min_words:
        return False, f"insufficient_content ({word_count} words < {min_words})"

    # Check for error / login page patterns in first 500 chars
    head = text[:500].lower()
    if _ERROR_PAGE_RE.search(head):
        return False, "error_or_login_page"

    return True, "valid"


# ─── Web Research Provider ────────────────────────────────────────────────────

class WebResearchProvider(ResearchProvider):
    """
    Production Web Research Provider with:
    - Dynamic focused query generation
    - Domain classification
    - SSRF protection
    - Strict fetch contract (no synthetic content injection)
    - Content quality validation
    """

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MODUS-ResearchAgent/1.0"
        )

    async def search(self, query: str, max_results: int = 5) -> List[ResearchSearchResult]:
        """
        Perform web search using DuckDuckGo with query cleaning and SSRF checks.
        No synthetic fallback sources are injected.
        """
        results: List[ResearchSearchResult] = []
        clean_q = clean_search_query(query)

        try:
            logger.info(f"[search] query='{clean_q}' (original='{query[:60]}...')")

            def _do_ddgs_query(q_str: str, n_res: int):
                for attempt in range(3):
                    try:
                        with DDGS() as ddgs:
                            res = list(ddgs.text(q_str, max_results=n_res))
                            if res:
                                return res
                    except Exception:
                        time.sleep(0.4 * (attempt + 1))
                return []

            ddg_results = await asyncio.to_thread(_do_ddgs_query, clean_q, max_results)

            seen_urls: set[str] = set()
            for item in ddg_results:
                raw_url = item.get("href", "")
                norm_url = normalize_url(raw_url)

                # SSRF Protection Check
                is_safe, reason = is_safe_external_url(norm_url)
                if not is_safe:
                    logger.warning(f"[search] SSRF blocked '{norm_url}': {reason}")
                    continue

                if norm_url in seen_urls:
                    continue
                seen_urls.add(norm_url)

                title = item.get("title", "Untitled Source")
                snippet = item.get("body", "")
                domain = urlparse(norm_url).netloc
                source_type, credibility = classify_domain(norm_url)

                results.append(
                    ResearchSearchResult(
                        title=title,
                        url=norm_url,
                        publisher=domain,
                        published_at=None,
                        source_type=source_type,
                        snippet=snippet,
                        credibility_score=credibility,
                        metadata={"raw_url": raw_url, "query": clean_q, "provider": "ddgs"},
                    )
                )

        except Exception as e:
            logger.warning(f"[search] exception for '{clean_q}': {e}")

        # No synthetic fallback sources — return whatever the search engine provides.
        # If zero results, the pipeline handles it via insufficient-evidence policy.
        return results

    async def fetch_content(self, url: str) -> ResearchDocument:
        """
        Fetch webpage HTML via HTTP client with SSRF checks and strict failure reporting.
        
        STRICT CONTRACT:
        - On success: returns content with metadata={"status": "success", "http_status": 200}
        - On failure: returns content="" with metadata={"status": "failed", "http_status": code, "error": ...}
        - NEVER injects synthetic or fallback text content.
        """
        norm_url = normalize_url(url)

        # SSRF Security Check
        is_safe, reason = is_safe_external_url(norm_url)
        if not is_safe:
            logger.warning(f"[fetch] SSRF block '{norm_url}': {reason}")
            return ResearchDocument(
                url=norm_url,
                title=norm_url,
                content="",
                content_hash=None,
                word_count=0,
                metadata={"status": "failed", "error": f"SSRF Block: {reason}", "failure_type": "ssrf_blocked"},
            )

        # Reject binary extensions
        if norm_url.lower().endswith((".pdf", ".zip", ".tar", ".gz", ".exe", ".bin", ".mp4", ".mp3", ".jpg", ".png", ".webp", ".xlsx", ".docx")):
            logger.info(f"[fetch] binary extension skipped: '{norm_url}'")
            return ResearchDocument(
                url=norm_url,
                title=norm_url,
                content="",
                content_hash=None,
                word_count=0,
                metadata={"status": "failed", "failure_type": "binary_file_skipped"},
            )

        headers = {"User-Agent": self.user_agent}
        timeout = httpx.Timeout(settings.CONTENT_EXTRACTION_TIMEOUT_SECONDS)

        last_exception = None
        http_status = None

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
                    response = await client.get(norm_url)
                    http_status = response.status_code
                    response.raise_for_status()

                    # Verify text/html content type
                    ctype = response.headers.get("content-type", "").lower()
                    if ctype and not any(t in ctype for t in ("text/html", "text/plain", "application/xhtml", "application/xml")):
                        logger.info(f"[fetch] non-html content-type '{ctype}': '{norm_url}'")
                        return ResearchDocument(
                            url=norm_url,
                            title=norm_url,
                            content="",
                            content_hash=None,
                            word_count=0,
                            metadata={"status": "failed", "http_status": http_status, "failure_type": "unsupported_content_type"},
                        )

                    # Enforce max document size
                    content_bytes = response.content
                    if len(content_bytes) > settings.MAX_DOCUMENT_SIZE_BYTES:
                        content_bytes = content_bytes[: settings.MAX_DOCUMENT_SIZE_BYTES]

                    html_text = content_bytes.decode("utf-8", errors="ignore")

                    # Parse HTML and strip non-content elements
                    soup = BeautifulSoup(html_text, "html.parser")
                    for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
                        element.decompose()

                    title = soup.title.string.strip() if soup.title and soup.title.string else norm_url
                    text = soup.get_text(separator="\n")

                    # Clean whitespace
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    clean_text = "\n".join(chunk for chunk in chunks if chunk)

                    # Content quality validation
                    is_valid, validation_reason = validate_extracted_content(
                        clean_text, min_words=settings.MIN_CONTENT_WORD_COUNT
                    )

                    if not is_valid:
                        logger.info(f"[fetch] content_invalid url='{norm_url}' reason={validation_reason}")
                        return ResearchDocument(
                            url=norm_url,
                            title=title,
                            content="",
                            content_hash=None,
                            word_count=len(clean_text.split()) if clean_text else 0,
                            metadata={
                                "status": "failed",
                                "http_status": http_status,
                                "failure_type": "content_validation_failed",
                                "validation_reason": validation_reason,
                            },
                        )

                    content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
                    word_count = len(clean_text.split())

                    return ResearchDocument(
                        url=norm_url,
                        title=title,
                        content=clean_text,
                        content_hash=content_hash,
                        word_count=word_count,
                        metadata={"status": "success", "http_status": http_status},
                    )

            except httpx.HTTPStatusError as exc:
                last_exception = exc
                http_status = exc.response.status_code
                # Non-retryable HTTP errors — break immediately
                if http_status in (401, 403, 404, 410, 429):
                    break
                logger.debug(f"[fetch] attempt {attempt+1} HTTP {http_status} for '{norm_url}'")

            except httpx.TimeoutException as exc:
                last_exception = exc
                http_status = None
                logger.debug(f"[fetch] attempt {attempt+1} timeout for '{norm_url}'")

            except Exception as exc:
                last_exception = exc
                logger.debug(f"[fetch] attempt {attempt+1} failed for '{norm_url}': {exc}")

        # ALL attempts failed — return strict failure with NO synthetic content
        failure_type = "http_error"
        if isinstance(last_exception, httpx.TimeoutException):
            failure_type = "timeout"
        elif isinstance(last_exception, httpx.ConnectError):
            failure_type = "connection_error"

        logger.warning(f"[fetch] FAILED url='{norm_url}' http={http_status} error='{last_exception}'")
        return ResearchDocument(
            url=norm_url,
            title=norm_url,
            content="",
            content_hash=None,
            word_count=0,
            metadata={
                "status": "failed",
                "http_status": http_status,
                "error": str(last_exception),
                "failure_type": failure_type,
            },
        )
