import hashlib
import re
from datetime import datetime, timezone
from typing import List
from app.providers.research.base import ResearchDocument, ResearchProvider, ResearchSearchResult


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")


class MockResearchProvider(ResearchProvider):
    """
    Development Mock Research Provider.
    Generates deterministic, input-dependent search results and source content based on input queries.
    NOTE: Used for local testing/development prior to live web search integration.
    """

    async def search(self, query: str, max_results: int = 5) -> List[ResearchSearchResult]:
        slug = slugify(query)
        now = datetime.now(timezone.utc)

        # Generate topic-derived search results
        results = [
            ResearchSearchResult(
                title=f"Global Industry Analysis: {query.capitalize()}",
                url=f"https://research-mock.org/reports/global-analysis-{slug}",
                publisher="Enterprise Intelligence Research Institute",
                published_at=now,
                source_type="report",
                snippet=f"Detailed empirical investigation analyzing the economic impact, key benchmarks, and operational implications of '{query}'.",
                credibility_score=0.92,
                metadata={"mock": True, "query": query, "rank": 1},
            ),
            ResearchSearchResult(
                title=f"Technical Benchmark & Implementation Case Study on {query.capitalize()}",
                url=f"https://tech-insights-mock.com/articles/case-study-{slug}",
                publisher="Applied Enterprise Technology Journal",
                published_at=now,
                source_type="paper",
                snippet=f"Systematic technical analysis examining architecture patterns, deployment hurdles, and ROI metrics for '{query}'.",
                credibility_score=0.87,
                metadata={"mock": True, "query": query, "rank": 2},
            ),
        ]
        return results[:max_results]

    async def fetch_content(self, url: str) -> ResearchDocument:
        now = datetime.now(timezone.utc)

        # Extract title hint from URL
        parts = url.rstrip("/").split("/")
        slug = parts[-1] if parts else "report"
        title_words = [w.capitalize() for w in slug.replace("-", " ").split()]
        title = " ".join(title_words)

        content = (
            f"EXECUTIVE SUMMARY & ANALYSIS: {title.upper()}\n\n"
            f"1. Core Operational Findings:\n"
            f"Recent empirical data demonstrates that implementing advanced strategies around '{title}' "
            f"yields an average operational performance improvement of 28% to 42% across enterprise deployments. "
            f"Key metrics indicate significant reductions in latency and error rates.\n\n"
            f"2. Risk Factors & Payback Bottlenecks:\n"
            f"Despite strong top-line efficiency gains, high initial capital expenditures and integration friction "
            f"with legacy architecture remain major challenges. Payback periods often extend between 18 and 36 months.\n\n"
            f"3. Strategic Recommendation:\n"
            f"Enterprises adopting '{title}' should prioritize phased rollouts, modular API gateways, "
            f"and continuous monitoring to mitigate risk during transition."
        )

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        words = len(content.split())

        return ResearchDocument(
            url=url,
            title=f"Source Analysis: {title}",
            content=content,
            content_hash=content_hash,
            word_count=words,
            metadata={"mock": True, "status": "success", "retrieved_at": now.isoformat()},
        )
