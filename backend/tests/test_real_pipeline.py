import uuid
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.utils import normalize_url
from app.providers.factory import get_ai_provider, get_research_provider
from app.providers.gemini import GeminiAIProvider
from app.providers.research.web import WebResearchProvider
from app.evaluation.relevance import classify_domain


def test_provider_configuration_loading():
    """Verify provider factory respects settings."""
    ai_provider = get_ai_provider()
    research_provider = get_research_provider()

    assert ai_provider is not None
    assert research_provider is not None


def test_url_normalization_and_deduplication():
    """Test URL normalization utility."""
    url1 = "HTTP://Example.com/article/123/?utm_source=twitter#section1/"
    url2 = "http://example.com/article/123"

    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)

    assert norm1 == "http://example.com/article/123"
    assert norm2 == "http://example.com/article/123"
    assert norm1 == norm2


def test_classify_source_type_and_credibility():
    """Test deterministic source classification heuristics."""
    st_gov, cred_gov = classify_domain("https://www.energy.gov/reports/1")
    assert st_gov == "government"
    assert cred_gov == 0.95

    st_edu, cred_edu = classify_domain("https://research.mit.edu/paper")
    assert st_edu == "academic"
    assert cred_edu == 0.92

    st_news, cred_news = classify_domain("https://www.reuters.com/business")
    assert st_news == "news"
    assert cred_news == 0.85


@pytest.mark.asyncio
async def test_content_extraction_invalid_url_handling():
    """Verify web research provider gracefully handles invalid URLs or extraction failures."""
    web_provider = WebResearchProvider()
    doc = await web_provider.fetch_content("https://invalid-domain-that-does-not-exist-12345.com")

    assert doc.url == "https://invalid-domain-that-does-not-exist-12345.com"
    # Strict contract: failed sources have empty content
    assert doc.metadata.get("status") == "failed"
    assert doc.content == ""


@pytest.mark.asyncio
async def test_gemini_fallback_mode_when_no_api_key():
    """Verify GeminiAIProvider falls back safely when GEMINI_API_KEY is not provided."""
    gemini_provider = GeminiAIProvider(api_key="")

    sub_qs = await gemini_provider.decompose_question("What is AI retail forecasting?")
    assert len(sub_qs) >= 1
    assert sub_qs[0].question is not None

    findings = await gemini_provider.extract_findings_and_evidence(
        source_url="https://example.com",
        source_content="Retail AI increases demand accuracy by 35% according to industry benchmarks and deployment studies across multiple retail organizations.",
        research_question="What is AI retail forecasting?"
    )
    # Fallback may return findings or empty list if content is insufficient
    if findings:
        assert findings[0].source_url == "https://example.com"

    conclusions = await gemini_provider.generate_conclusions_from_findings(
        question="What is AI retail forecasting?",
        findings=[{"statement": "Retail AI increases demand accuracy by 35%."}]
    )
    assert len(conclusions) >= 1


@pytest.mark.asyncio
async def test_run_traceability_endpoint(client: AsyncClient):
    """Verify GET /api/v1/runs/{run_id}/traceability endpoint returns complete evidence graph."""
    # 1. Create project & question
    p_res = await client.post("/api/v1/projects", json={"name": "Traceability Test", "research_topic": "AI Traceability"})
    p_id = p_res.json()["id"]

    q_res = await client.post(f"/api/v1/projects/{p_id}/questions", json={"question": "How is evidence traceability verified?"})
    q_id = q_res.json()["id"]

    # 2. Trigger and execute run
    run_res = await client.post(f"/api/v1/questions/{q_id}/runs", json={})
    run_id = run_res.json()["id"]

    exec_res = await client.post(f"/api/v1/runs/{run_id}/execute")
    assert exec_res.status_code == 200

    # 3. Retrieve traceability evidence graph
    trac_res = await client.get(f"/api/v1/runs/{run_id}/traceability")
    assert trac_res.status_code == 200
    trac_data = trac_res.json()

    assert trac_data["run_id"] == run_id
    assert trac_data["question_id"] == q_id
    assert trac_data["status"] == "completed"
    assert "provenance_graph" in trac_data
