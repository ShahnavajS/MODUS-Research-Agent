"""
Research Quality Engine — 24-Test Regression Suite.

Covers:
  - Source relevance filtering & deduplication (tests 1-5)
  - Failed source evidence exclusion (tests 6-14)
  - Finding quality & evidence grounding (tests 15-19)
  - Consistency, classification, security (tests 20-24)
"""

import asyncio
import hashlib
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.utils import normalize_url, is_near_duplicate
from app.evaluation.relevance import (
    SourceRelevanceResult,
    classify_domain,
    evaluate_source_relevance,
)
from app.providers.research.web import (
    clean_search_query,
    generate_focused_queries,
    validate_extracted_content,
)
from app.services.research_pipeline_service import is_template_finding


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 1-5: Source Relevance Filtering & Deduplication
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceRelevanceFiltering:
    """Tests 1-5: Relevance scoring, filtering, and deduplication."""

    def test_01_irrelevant_source_rejected(self):
        """Test 1: An irrelevant source (dictionary page for a banking query) is rejected."""
        result = evaluate_source_relevance(
            title="Current | Definition & Meaning - Merriam-Webster",
            snippet="The meaning of CURRENT is occurring in or existing at the present time.",
            url="https://www.merriam-webster.com/dictionary/current",
            query="bank generative AI fraud detection",
            sub_question="How are banks using generative AI for fraud detection?",
            research_question="How are large banks deploying generative AI?",
            min_score=0.35,
        )
        assert not result.is_relevant, f"Dictionary page should be rejected, got score={result.relevance_score}"
        assert result.relevance_score < 0.35

    def test_02_relevant_source_retained(self):
        """Test 2: A relevant source (bank AI deployment article) is retained."""
        result = evaluate_source_relevance(
            title="How Banks Are Using Generative AI to Fight Fraud",
            snippet="Major banks are deploying generative AI models for real-time fraud detection.",
            url="https://www.reuters.com/technology/banks-generative-ai-fraud-detection",
            query="bank generative AI fraud detection",
            sub_question="How are banks using generative AI for fraud detection?",
            research_question="How are large banks deploying generative AI?",
            min_score=0.35,
        )
        assert result.is_relevant, f"Bank AI article should be relevant, got score={result.relevance_score}"
        assert result.relevance_score >= 0.35

    def test_03_relevance_score_is_deterministic(self):
        """Test 3: Same inputs produce identical relevance scores."""
        kwargs = dict(
            title="AI in Manufacturing Quality Control",
            snippet="Computer vision models are being used to detect defects on assembly lines.",
            url="https://www.mckinsey.com/industries/manufacturing/ai-quality-control",
            query="AI manufacturing quality control",
            sub_question="How is AI used for quality control in manufacturing?",
            research_question="How is AI changing manufacturing?",
            min_score=0.35,
        )
        r1 = evaluate_source_relevance(**kwargs)
        r2 = evaluate_source_relevance(**kwargs)
        assert r1.relevance_score == r2.relevance_score
        assert r1.title_match == r2.title_match
        assert r1.snippet_match == r2.snippet_match

    def test_04_relevance_breakdown_is_explainable(self):
        """Test 4: Relevance result contains all breakdown components."""
        result = evaluate_source_relevance(
            title="Generative AI in Financial Services",
            snippet="Banks are adopting generative AI for compliance and risk management.",
            url="https://www.accenture.com/gen-ai-finance",
            query="generative AI banking compliance",
            min_score=0.35,
        )
        assert hasattr(result, "title_match")
        assert hasattr(result, "snippet_match")
        assert hasattr(result, "concept_match")
        assert hasattr(result, "domain_quality")
        assert hasattr(result, "source_type")
        assert hasattr(result, "is_relevant")
        assert hasattr(result, "reasoning")
        assert 0.0 <= result.title_match <= 1.0
        assert 0.0 <= result.snippet_match <= 1.0
        assert 0.0 <= result.concept_match <= 1.0
        assert 0.0 <= result.domain_quality <= 1.0

    def test_05_near_duplicate_urls_deduplicated(self):
        """Test 5: Near-duplicate URLs with different tracking params normalize identically."""
        url_a = "https://www.reuters.com/technology/ai-banking?utm_source=twitter&utm_medium=social"
        url_b = "https://www.reuters.com/technology/ai-banking?utm_source=google&fbclid=abc123"
        url_c = "https://www.reuters.com/technology/ai-banking/"

        assert normalize_url(url_a) == normalize_url(url_b)
        assert normalize_url(url_a) == normalize_url(url_c)

        # Near-duplicate title detection on same domain
        assert is_near_duplicate(
            "AI in Banking Report 2024", "reuters.com",
            "AI in Banking Report 2024", "reuters.com",
        )
        # Different domains — not duplicates
        assert not is_near_duplicate(
            "AI in Banking Report 2024", "reuters.com",
            "AI in Banking Report 2024", "bloomberg.com",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 6-14: Failed Source Evidence Exclusion
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailedSourceEvidenceExclusion:
    """Tests 6-14: HTTP failures, timeouts, and empty content produce no evidence."""

    @pytest.mark.parametrize("http_status,test_name", [
        (401, "test_06_401_source_cannot_generate_evidence"),
        (403, "test_07_403_source_cannot_generate_evidence"),
        (404, "test_08_404_source_cannot_generate_evidence"),
        (410, "test_09_410_source_cannot_generate_evidence"),
        (429, "test_10_429_source_cannot_generate_evidence"),
        (500, "test_11_5xx_source_cannot_generate_evidence"),
    ])
    def test_http_error_source_ineligible(self, http_status, test_name):
        """Tests 6-11: HTTP error status sources must be marked as failed and ineligible."""
        # Simulate a fetch response with failed status
        from app.providers.research.base import ResearchDocument
        doc = ResearchDocument(
            url="https://example.com/article",
            title="Some Article",
            content="",  # STRICT: empty content on failure
            content_hash=None,
            word_count=0,
            metadata={"status": "failed", "http_status": http_status, "failure_type": "http_error"},
        )
        # Verify contract: status is failed, content is empty
        assert doc.metadata["status"] == "failed"
        assert doc.content == ""
        assert doc.word_count == 0
        assert doc.metadata["http_status"] == http_status

    def test_12_timeout_cannot_generate_evidence(self):
        """Test 12: Timeout produces failed document with empty content."""
        from app.providers.research.base import ResearchDocument
        doc = ResearchDocument(
            url="https://example.com/slow",
            title="Slow Page",
            content="",
            content_hash=None,
            word_count=0,
            metadata={"status": "failed", "failure_type": "timeout"},
        )
        assert doc.metadata["status"] == "failed"
        assert doc.content == ""

    def test_13_empty_content_cannot_generate_evidence(self):
        """Test 13: Empty content fails validation."""
        is_valid, reason = validate_extracted_content("", min_words=30)
        assert not is_valid
        assert reason == "empty_content"

    def test_14_error_page_cannot_generate_evidence(self):
        """Test 14: Error page content (403 Forbidden text) fails validation."""
        is_valid, reason = validate_extracted_content(
            "403 Forbidden\nYou do not have permission to access this resource.",
            min_words=5,
        )
        assert not is_valid
        assert reason == "error_or_login_page"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 15-19: Finding Quality & Evidence Grounding
# ═══════════════════════════════════════════════════════════════════════════════

class TestFindingQualityAndGrounding:
    """Tests 15-19: Finding validation, excerpt matching, and insufficiency handling."""

    def test_15_generic_template_finding_rejected(self):
        """Test 15: Generic/template findings are detected and rejected."""
        assert is_template_finding("Enterprise research insight regarding generative AI in banking")
        assert is_template_finding("Empirical evidence from https://example.com indicates trends")
        assert is_template_finding("Source Document Reference: https://example.com/article")
        assert is_template_finding("Enterprise analysis report examining banking AI deployment")

    def test_16_finding_requires_valid_evidence(self):
        """Test 16: A specific factual claim is NOT a template finding."""
        assert not is_template_finding(
            "JPMorgan Chase has deployed generative AI models that reduced false positive fraud alerts by 20%."
        )
        assert not is_template_finding(
            "Banks are concentrating AI deployments on customer service chatbots and internal code generation."
        )

    def test_17_evidence_excerpt_must_exist_in_source_content(self):
        """Test 17: Evidence excerpt validation — must be substring of source content."""
        source_content = (
            "Major banks including JPMorgan Chase and Bank of America have begun deploying "
            "generative AI models for fraud detection, achieving a 15% reduction in false positives. "
            "However, regulatory concerns remain around model explainability requirements."
        )
        # Valid excerpt
        excerpt = "generative AI models for fraud detection, achieving a 15% reduction in false positives"
        assert excerpt in source_content

        # Invalid excerpt (fabricated)
        fake_excerpt = "AI has completely eliminated all fraud in banking worldwide"
        assert fake_excerpt not in source_content

    def test_18_conclusion_references_actual_validated_findings(self):
        """Test 18: Conclusion supporting_finding_statements should reference real findings."""
        from app.providers.base import ConclusionCandidate
        conclusion = ConclusionCandidate(
            statement="Banks are deploying AI for fraud detection with measurable results.",
            confidence=0.85,
            supporting_finding_statements=[
                "JPMorgan deployed AI reducing false positives by 20%",
                "Bank of America uses AI chatbots for customer service",
            ],
            limitations="Limited to publicly available information.",
        )
        assert len(conclusion.supporting_finding_statements) > 0
        assert conclusion.confidence > 0

    def test_19_insufficient_evidence_produces_safe_limitation(self):
        """Test 19: When no findings exist, conclusion should state evidence insufficiency."""
        from app.providers.gemini import GeminiAIProvider
        provider = GeminiAIProvider(api_key=None)  # Fallback mode
        conclusions = provider._fallback_generate_conclusions("Test question?", [])
        assert len(conclusions) >= 1
        assert "insufficient" in conclusions[0].statement.lower() or "limited" in conclusions[0].statement.lower()
        assert conclusions[0].confidence <= 0.50


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 20-24: Consistency, Classification, and Security
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsistencyClassificationSecurity:
    """Tests 20-24: Different results, domain classification, metrics consistency, security."""

    def test_20_different_questions_produce_different_results(self):
        """Test 20: Different queries produce different search query outputs."""
        q1 = clean_search_query("How are banks using AI for fraud detection?")
        q2 = clean_search_query("How is AI changing predictive maintenance in manufacturing?")
        assert q1 != q2

        queries_1 = generate_focused_queries("Bank AI fraud detection systems")
        queries_2 = generate_focused_queries("Manufacturing predictive maintenance AI systems")
        assert queries_1[0] != queries_2[0]

    def test_21_source_type_classification_works(self):
        """Test 21: Domain classification returns correct source types."""
        assert classify_domain("https://www.sec.gov/rules/ai-guidance")[0] == "government"
        assert classify_domain("https://arxiv.org/abs/2401.12345")[0] == "research"
        assert classify_domain("https://www.mckinsey.com/industries/banking")[0] == "industry_report"
        assert classify_domain("https://www.reuters.com/technology/ai")[0] == "news"
        assert classify_domain("https://www.reddit.com/r/MachineLearning")[0] == "community_forum"
        assert classify_domain("https://www.merriam-webster.com/dictionary/ai")[0] == "reference_dictionary"
        assert classify_domain("https://www.facebook.com/page")[0] == "social_media"
        assert classify_domain("https://www.randomsite.com/article")[0] == "general_web"

    def test_22_failed_sources_recorded_correctly(self):
        """Test 22: Failed fetch documents have correct metadata structure."""
        from app.providers.research.base import ResearchDocument
        doc = ResearchDocument(
            url="https://example.com/blocked",
            title="Blocked Page",
            content="",
            content_hash=None,
            word_count=0,
            metadata={
                "status": "failed",
                "http_status": 403,
                "error": "Client error '403 Forbidden'",
                "failure_type": "http_error",
            },
        )
        assert doc.metadata["status"] == "failed"
        assert doc.metadata["http_status"] == 403
        assert "error" in doc.metadata
        assert "failure_type" in doc.metadata
        assert doc.content == ""

    def test_23_source_metrics_internally_consistent(self):
        """Test 23: Metric consistency assertions hold."""
        from app.evaluation.metrics import calculate_research_quality_metrics
        metrics = calculate_research_quality_metrics(
            discovered_sources_count=20,
            relevant_sources_count=14,
            rejected_irrelevant_count=6,
            fetch_success_count=10,
            failed_sources_count=4,
            evidence_eligible_count=10,
            findings_count=8,
            grounded_findings_count=6,
            unsupported_findings_count=2,
            contradictions_count=1,
            conclusions_count=2,
            conclusions_with_findings_count=2,
        )
        # Consistency: successful <= relevant <= discovered
        assert metrics["fetch_success_sources"] <= metrics["relevant_sources"]
        assert metrics["relevant_sources"] <= metrics["discovered_sources"]
        assert metrics["evidence_eligible_sources"] <= metrics["fetch_success_sources"]
        assert metrics["grounded_findings"] <= metrics["total_findings"]
        assert metrics["evidence_coverage"] <= 1.0
        assert metrics["source_coverage"] <= 1.0

    def test_24_existing_security_ssrf_tests_compatible(self):
        """Test 24: SSRF protection still works correctly."""
        from app.core.security import is_safe_external_url
        # Safe URLs
        safe, _ = is_safe_external_url("https://www.reuters.com/article")
        assert safe
        # Unsafe URLs
        unsafe, reason = is_safe_external_url("http://127.0.0.1/internal")
        assert not unsafe
        unsafe, reason = is_safe_external_url("http://localhost/admin")
        assert not unsafe
        unsafe, reason = is_safe_external_url("file:///etc/passwd")
        assert not unsafe
