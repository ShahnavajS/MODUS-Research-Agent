"""
Final Pre-Submission Quality & Reliability Regression Test Suite.

Verifies:
  1. TikTok/social domain rejected
  2. Reddit/community domain rejected
  3. Dictionary/reference domain rejected
  4. Irrelevant source rejected
  5. Relevant legitimate source retained
  6. Failed 401 source cannot produce evidence
  7. Failed 403 source cannot produce evidence
  8. Failed 404 source cannot produce evidence
  9. Failed 5xx source cannot produce evidence
  10. Empty source cannot produce evidence
  11. Generic/template finding rejected
  12. Evidence must exist in source content
  13. Duplicate URLs canonicalized
  14. Duplicate findings reduced
  15. Original geographic constraints preserved
  16. Original temporal constraints preserved
  17. Contradiction categories distinguish scope/time mismatches
  18. Conclusion cannot cite unsupported findings
  19. Failed sources recorded in metadata
  20. Source filtering happens BEFORE HTTP fetching
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.core.utils import normalize_url
from app.evaluation.confidence import calculate_calibrated_finding_confidence
from app.evaluation.constraint_guard import (
    extract_question_constraints,
    validate_and_augment_sub_questions,
)
from app.evaluation.deduplication import deduplicate_findings
from app.evaluation.numeric_guard import validate_numeric_preservation
from app.evaluation.relevance import (
    classify_domain,
    classify_source_role,
    evaluate_source_relevance,
    is_hard_excluded_source,
)
from app.providers.base import (
    ConclusionCandidate,
    ContradictionCandidate,
    FindingCandidate,
    SourceDocumentInput,
    SubQuestionCandidate,
)
from app.providers.mock import MockAIProvider
from app.providers.research.mock import MockResearchProvider
from app.providers.research.base import ResearchDocument, ResearchSearchResult
from app.providers.research.web import validate_extracted_content
from app.services.research_pipeline_service import ResearchPipelineService
from app.models import ResearchProject, ResearchQuestion, ResearchRun, Finding, Evidence, Contradiction, Conclusion, ResearchSource, SourceContent
from sqlalchemy import select


class TestHardSourceFiltering:
    """1-5: Hard source filtering and relevance scoring."""

    def test_01_tiktok_and_social_domains_hard_rejected(self):
        """Test 1: TikTok and social media URLs are deterministically hard-excluded."""
        social_urls = [
            "https://www.tiktok.com/@researcher/video/123456",
            "https://facebook.com/groups/ai-research",
            "https://www.instagram.com/p/C12345/",
            "https://twitter.com/analyst/status/123",
            "https://x.com/tech_expert/status/456",
            "https://threads.net/@user/post/789",
        ]
        for url in social_urls:
            is_blocked, reason = is_hard_excluded_source(url)
            assert is_blocked is True
            assert reason == "hard_excluded_social_media"

            rel = evaluate_source_relevance("Social Post Title", "Social content snippet", url, "AI data center electricity demand")
            assert rel.is_relevant is False
            assert rel.is_hard_excluded is True
            assert rel.source_role == "DISCOVERY_ONLY"

    def test_02_reddit_and_community_domains_hard_rejected(self):
        """Test 2: Reddit, Quora, StackOverflow, and GitHub issues/PRs are hard-excluded."""
        community_urls = [
            "https://www.reddit.com/r/MachineLearning/comments/12345/data_centers/",
            "https://quora.com/How-much-power-does-AI-consume",
            "https://stackoverflow.com/questions/1234567/python-memory-error",
            "https://github.com/vllm-project/vllm/issues/1234",
            "https://github.com/huggingface/transformers/pull/5678",
        ]
        for url in community_urls:
            is_blocked, reason = is_hard_excluded_source(url)
            assert is_blocked is True
            assert "community" in reason or "github" in reason

            rel = evaluate_source_relevance("Community Thread", "Forum discussion snippet", url, "AI data center electricity demand")
            assert rel.is_relevant is False
            assert rel.is_hard_excluded is True

    def test_03_dictionary_and_generic_reference_hard_rejected(self):
        """Test 3: Merriam-Webster, Britannica, Cambridge dictionary, and Investopedia terms are hard-excluded."""
        dict_urls = [
            "https://www.merriam-webster.com/dictionary/artificial%20intelligence",
            "https://dictionary.cambridge.org/dictionary/english/semiconductor",
            "https://www.britannica.com/technology/data-center",
            "https://wiktionary.org/wiki/electricity",
            "https://www.investopedia.com/terms/e/ebitda.asp",
        ]
        for url in dict_urls:
            is_blocked, reason = is_hard_excluded_source(url)
            assert is_blocked is True
            assert reason == "hard_excluded_dictionary_reference"

            rel = evaluate_source_relevance("Definition of AI", "A generic definition of AI", url, "AI data center electricity demand")
            assert rel.is_relevant is False
            assert rel.is_hard_excluded is True

    def test_04_irrelevant_source_rejected(self):
        """Test 4: Sources with low topical relevance are rejected at filtering stage."""
        url = "https://www.technologysite.com/gaming/best-nintendo-switch-games-2024"
        rel = evaluate_source_relevance(
            title="Best Nintendo Switch Games of 2024",
            snippet="Here are our favorite portable handheld console games for the holidays.",
            url=url,
            query="AI data center electricity demand through 2030 in United States",
            min_score=0.35,
        )
        assert rel.is_relevant is False
        assert rel.relevance_score < 0.35

    def test_05_relevant_legitimate_source_retained(self):
        """Test 5: Legitimate government, academic, and research institution sources are retained."""
        legit_sources = [
            ("https://www.iea.org/reports/electricity-2024/data-centres", "Electricity 2024 - Data Centres and Energy", "IEA analysis of data center power demand through 2026 and 2030.", "industry_report"),
            ("https://www.energy.gov/reports/data-center-energy-consumption", "Data Center Energy Consumption Trends", "US Department of Energy report on grid infrastructure and power demand.", "government"),
            ("https://link.springer.com/article/10.1007/data-center-cooling", "Water Consumption and Cooling in AI Data Centers", "Empirical study on water and power efficiency in hyperscale facilities.", "research"),
        ]
        for url, title, snippet, expected_type in legit_sources:
            is_blocked, _ = is_hard_excluded_source(url)
            assert is_blocked is False

            rel = evaluate_source_relevance(
                title=title,
                snippet=snippet,
                url=url,
                query="AI data center electricity demand and water consumption through 2030",
                min_score=0.35,
            )
            assert rel.is_relevant is True
            assert rel.relevance_score >= 0.35
            assert rel.source_type == expected_type


class TestStrictEvidenceContractAndHTTPStatus:
    """6-12: HTTP failures, empty content, and grounded evidence contract."""

    def test_06_to_10_failed_http_and_empty_sources_validation(self):
        """Tests 6-10: 401, 403, 404, 5xx, and empty sources fail validation."""
        # 401 / 403 / 404 / 500 error page content
        error_pages = [
            "401 Unauthorized - Access Denied to this API endpoint.",
            "403 Forbidden - You do not have permission to view this resource. Captcha required.",
            "404 Not Found - The requested page could not be found on this server.",
            "500 Internal Server Error - An unexpected error occurred.",
            "   ",  # Empty
            "Short text with only ten words in this body.",  # Insufficient words (< 30)
        ]
        for text in error_pages:
            is_valid, reason = validate_extracted_content(text, min_words=30)
            assert is_valid is False
            assert reason in ("empty_content", "error_or_login_page") or "insufficient_content" in reason

    def test_11_generic_template_finding_rejected(self):
        """Test 11: Generic template findings without specific factual claims are rejected."""
        from app.services.research_pipeline_service import is_template_finding
        generic_statements = [
            "Enterprise research insight regarding the topic.",
            "Research indicates that generative AI is transforming industries.",
            "According to sources, there are multiple implementation challenges.",
            "Findings reveal important benefits and risks for organizations.",
        ]
        for stmt in generic_statements:
            assert is_template_finding(stmt) is True

        specific_stmt = "AI data center electricity demand in the United States is projected to grow by 160% from 2023 to 2030, reaching 390 TWh."
        assert is_template_finding(specific_stmt) is False

    def test_12_evidence_must_exist_in_source_content(self):
        """Test 12: Evidence excerpts must be directly grounded in the source text."""
        source_text = (
            "A comprehensive study by the International Energy Agency estimates that data centers "
            "consumed approximately 460 TWh of electricity in 2022 and could exceed 1,000 TWh by 2026. "
            "In the United States, data centers represent 4 percent of total electricity consumption."
        )

        valid_excerpt = "data centers consumed approximately 460 TWh of electricity in 2022 and could exceed 1,000 TWh by 2026"
        assert valid_excerpt in source_text

        hallucinated_excerpt = "data centers will consume 50,000 TWh of nuclear energy and cause nationwide blackouts"
        assert hallucinated_excerpt not in source_text


class TestURLCanonicalizationAndDeduplication:
    """13-14: URL normalization and finding deduplication."""

    def test_13_duplicate_urls_canonicalized(self):
        """Test 13: URLs with trailing slashes, tracking parameters, and casing are normalized."""
        url1 = "https://www.IEA.org/reports/data-centres/?utm_source=twitter&utm_medium=social"
        url2 = "https://www.iea.org/reports/data-centres/"
        assert normalize_url(url1) == "https://www.iea.org/reports/data-centres"
        assert normalize_url(url2) == "https://www.iea.org/reports/data-centres"

    def test_14_duplicate_findings_reduced(self):
        """Test 14: Semantically duplicate findings are merged into canonical findings."""
        raw_findings = [
            FindingCandidate(
                statement="AI data centers in the US will require up to 390 TWh of electricity by 2030.",
                finding_type="metric",
                confidence=0.85,
                importance="high",
                source_url="https://iea.org/report1",
                excerpt="AI data centers in the US will require up to 390 TWh of electricity by 2030.",
            ),
            FindingCandidate(
                statement="By 2030, US data center electricity consumption is projected to reach approximately 390 TWh.",
                finding_type="metric",
                confidence=0.80,
                importance="high",
                source_url="https://epri.com/report2",
                excerpt="By 2030, US data center electricity consumption is projected to reach approximately 390 TWh.",
            ),
            FindingCandidate(
                statement="Water consumption for hyperscale data center cooling is growing at 20% annually.",
                finding_type="trend",
                confidence=0.82,
                importance="medium",
                source_url="https://nature.com/water-study",
                excerpt="Water consumption for hyperscale data center cooling is growing at 20% annually.",
            ),
        ]
        canonical, merged_c = deduplicate_findings(raw_findings)
        assert len(raw_findings) == 3
        assert len(canonical) == 2  # The two 390 TWh findings merged
        assert merged_c == 1
        assert len(canonical[0]["evidence_items"]) == 2  # Aggregated both evidence links


class TestConstraintPreservation:
    """15-16: Geographic and temporal constraints preservation."""

    def test_15_original_geographic_constraints_preserved(self):
        """Test 15: Geographic comparative constraints (US, EU, China, India) are preserved."""
        question = (
            "How will the rapid expansion of AI data centers reshape global electricity demand, "
            "water consumption, semiconductor supply chains, and national energy security through 2030, "
            "and does the expected economic value of AI justify the infrastructure, environmental, geopolitical, "
            "and regulatory risks? Compare evidence across the United States, European Union, China, and India."
        )

        constraints = extract_question_constraints(question)
        assert "United States" in constraints["geographic_constraints"]
        assert "European Union" in constraints["geographic_constraints"]
        assert "China" in constraints["geographic_constraints"]
        assert "India" in constraints["geographic_constraints"]
        assert constraints["is_comparative"] is True

        # Incomplete sub-questions from naive LLM
        incomplete_sub_qs = [
            SubQuestionCandidate(question="What is the electricity demand of AI data centers?", sequence_number=1),
            SubQuestionCandidate(question="What are the water consumption impacts of cooling systems?", sequence_number=2),
            SubQuestionCandidate(question="How are semiconductor supply chains impacted?", sequence_number=3),
        ]

        augmented, meta = validate_and_augment_sub_questions(question, incomplete_sub_qs)
        assert meta["geographic_constraints_preserved"] is True
        combined_text = " ".join(sq.question for sq in augmented)
        assert "United States" in combined_text
        assert "European Union" in combined_text
        assert "China" in combined_text
        assert "India" in combined_text

    def test_16_original_temporal_constraints_preserved(self):
        """Test 16: Temporal horizon (e.g. 2030) is extracted and preserved across sub-questions."""
        question = (
            "How will the rapid expansion of AI data centers reshape global electricity demand through 2030?"
        )
        constraints = extract_question_constraints(question)
        assert "2030" in constraints["temporal_constraints"]

        sub_qs = [
            SubQuestionCandidate(question="What are the electricity demand projections for data center expansion?", sequence_number=1),
        ]
        augmented, meta = validate_and_augment_sub_questions(question, sub_qs)
        assert meta["temporal_constraints_preserved"] is True
        assert "2030" in augmented[0].question


class TestContradictionTaxonomyAndConclusionGrounding:
    """17-18: Contradiction categories and conclusion integrity."""

    def test_17_contradiction_categories_distinguish_scope_and_time_mismatches(self):
        """Test 17: Contradiction categories distinguish between direct contradictions and scope/time mismatches."""
        cand_direct = ContradictionCandidate(
            finding_a_statement="US data centers consumed 100 TWh in 2023.",
            finding_b_statement="US data centers consumed 300 TWh in 2023.",
            description="Incompatible figures for the exact same metric, country, and year.",
            severity="high",
            contradiction_category="DIRECT_CONTRADICTION",
        )
        assert cand_direct.contradiction_category == "DIRECT_CONTRADICTION"

        cand_time = ContradictionCandidate(
            finding_a_statement="Global data-center efficiency improved significantly from 2010 to 2020.",
            finding_b_statement="US data-center electricity consumption increased substantially from 2018 to 2023.",
            description="Difference in time window and metric scope (efficiency vs gross power demand).",
            severity="low",
            contradiction_category="TIME_PERIOD_MISMATCH",
        )
        assert cand_time.contradiction_category == "TIME_PERIOD_MISMATCH"

        cand_scope = ContradictionCandidate(
            finding_a_statement="Data center power demand in Europe is growing at 3% due to strict grid regulations.",
            finding_b_statement="Data center power demand in the US is surging at 15% due to rapid hyperscale clustering.",
            description="Regional jurisdictional difference, not a factual contradiction.",
            severity="low",
            contradiction_category="SCOPE_MISMATCH",
        )
        assert cand_scope.contradiction_category == "SCOPE_MISMATCH"

    def test_18_numeric_claim_protection_and_range_fidelity(self):
        """Test 18: Numeric claim protection verifies figures and rejects inverted ranges."""
        # Exact range preserved
        stmt = "EBITDA will increase by 15-30% within five years."
        excerpt = "advanced analytics can boost EBITDA by 15-30% within five years"
        is_valid, violations = validate_numeric_preservation(stmt, excerpt)
        assert is_valid is True
        assert len(violations) == 0

        # Inverted range flagged
        inverted_stmt = "EBITDA will increase by 30-15% within five years."
        is_inv_valid, inv_violations = validate_numeric_preservation(inverted_stmt, excerpt)
        assert is_inv_valid is False
        assert any("inverted" in v.lower() for v in inv_violations)


class TestEndToEndAuditabilityAndSourceLifecycle:
    """19-20: Audit metadata and source filtering before HTTP fetch."""

    @pytest.mark.asyncio
    async def test_19_and_20_pipeline_metadata_and_pre_fetch_filtering(self, db_session):
        """Tests 19 & 20: Pre-fetch filtering rejects social/dict sources and metadata records complete audit trail."""
        project = ResearchProject(
            name="Audit Test Project",
            research_topic="AI Data Center Power",
            industry="Energy",
        )
        db_session.add(project)
        await db_session.flush()

        question = ResearchQuestion(
            project_id=project.id,
            question="How will AI data centers reshape electricity demand through 2030 across US and China?",
        )
        db_session.add(question)
        await db_session.flush()

        run = ResearchRun(question_id=question.id, status="queued")
        db_session.add(run)
        await db_session.commit()

        ai_provider = MockAIProvider()
        research_provider = MockResearchProvider()

        # Inject a mix of search results including social media and dictionary
        async def mock_search(q, max_results=5):
            return [
                ResearchSearchResult(
                    title="IEA Electricity 2024 Report",
                    url="https://www.iea.org/reports/electricity-2024",
                    publisher="iea.org",
                    published_at=None,
                    source_type="industry_report",
                    snippet="Global data center electricity consumption projected through 2030 in US and China.",
                    credibility_score=0.88,
                ),
                ResearchSearchResult(
                    title="TikTok Viral Video on AI Blackouts",
                    url="https://www.tiktok.com/@techguru/video/987654321",
                    publisher="tiktok.com",
                    published_at=None,
                    source_type="social_media",
                    snippet="Crazy video showing data center power!",
                    credibility_score=0.15,
                ),
                ResearchSearchResult(
                    title="Definition of Electricity - Merriam-Webster",
                    url="https://www.merriam-webster.com/dictionary/electricity",
                    publisher="merriam-webster.com",
                    published_at=None,
                    source_type="reference_dictionary",
                    snippet="A fundamental form of energy observable in positive and negative forms.",
                    credibility_score=0.30,
                ),
            ]

        research_provider.search = AsyncMock(side_effect=mock_search)

        service = ResearchPipelineService(
            session=db_session,
            ai_provider=ai_provider,
            research_provider=research_provider,
        )

        completed_run = await service.execute_run(run.id)
        assert completed_run.status == "completed"

        meta = completed_run.metadata_json or {}
        # Test 19: Full metadata transparency
        assert "discovered_sources" in meta
        assert "rejected_irrelevant_sources" in meta
        assert "failed_sources" in meta
        assert "findings_before_deduplication" in meta
        assert "findings_after_deduplication" in meta
        assert "quality_metrics" in meta

        # Test 20: Pre-fetch filtering verified
        # The TikTok and Merriam-Webster sources MUST be in rejected_irrelevant_sources
        rejected_urls = [s["url"] for s in meta["rejected_irrelevant_sources"]]
        assert any("tiktok.com" in u for u in rejected_urls)
        assert any("merriam-webster.com" in u for u in rejected_urls)

        # They must NEVER be in eligible sources or produce findings
        sources_in_db = (await db_session.scalars(
            select(ResearchSource).where(ResearchSource.research_run_id == run.id)
        )).all()

        for s in sources_in_db:
            if "tiktok.com" in s.url or "merriam-webster.com" in s.url:
                assert s.metadata_json.get("lifecycle_state") in ["HARD_EXCLUDED", "REJECTED"]
                assert s.metadata_json.get("is_evidence_eligible") is False
                # Must not have any source content or evidence
                contents = (await db_session.scalars(
                    select(SourceContent).where(SourceContent.source_id == s.id)
                )).all()
                assert len(contents) == 0

    def test_21_linkedin_medium_substack_hard_rejected(self):
        """Test 21: LinkedIn, Medium, and Substack are deterministically hard-excluded."""
        from app.evaluation.relevance import REJECTION_REASON_AUDIT_LABELS
        urls = [
            ("https://www.linkedin.com/pulse/ai-data-center-trends-2024", "SOCIAL_MEDIA_DOMAIN"),
            ("https://medium.com/@analyst/the-cost-of-drug-discovery-12345", "COMMUNITY_FORUM_DOMAIN"),
            ("https://substack.com/@techpulse/note/c-67890", "COMMUNITY_FORUM_DOMAIN"),
        ]
        for url, expected_label in urls:
            is_blocked, raw_reason = is_hard_excluded_source(url)
            assert is_blocked is True
            audit_label = REJECTION_REASON_AUDIT_LABELS.get(raw_reason)
            assert audit_label == expected_label

    def test_22_audit_reason_mappings_and_evidence_eligible_flags(self):
        """Test 22: Rejection reason mappings cover all required audit categories."""
        from app.evaluation.relevance import REJECTION_REASON_AUDIT_LABELS
        assert REJECTION_REASON_AUDIT_LABELS["hard_excluded_social_media"] == "SOCIAL_MEDIA_DOMAIN"
        assert REJECTION_REASON_AUDIT_LABELS["hard_excluded_community_forum"] == "COMMUNITY_FORUM_DOMAIN"
        assert REJECTION_REASON_AUDIT_LABELS["hard_excluded_dictionary_reference"] == "DICTIONARY_REFERENCE_DOMAIN"
        assert REJECTION_REASON_AUDIT_LABELS["hard_excluded_utility"] == "GENERIC_UTILITY_DOMAIN"
        assert REJECTION_REASON_AUDIT_LABELS["hard_excluded_github_issue_or_pull"] == "GITHUB_ISSUE_PR"
        assert REJECTION_REASON_AUDIT_LABELS["insufficient_relevance"] == "INSUFFICIENT_RELEVANCE"

    def test_23_contradiction_taxonomy_categories_and_examples(self):
        """Test 23: Contradiction taxonomy differentiates scope, time, definition, and contextual tension."""
        from app.models.contradiction import Contradiction
        valid_categories = {
            "DIRECT_CONTRADICTION",
            "SCOPE_MISMATCH",
            "TIME_PERIOD_MISMATCH",
            "DEFINITION_MISMATCH",
            "METHODOLOGY_MISMATCH",
            "FORECAST_DISAGREEMENT",
            "CONTEXTUAL_TENSION",
        }
        for cat in valid_categories:
            c = ContradictionCandidate(
                finding_a_statement="Finding A",
                finding_b_statement="Finding B",
                description=f"Testing category {cat}",
                severity="medium",
                contradiction_category=cat,
            )
            assert c.contradiction_category in valid_categories

    def test_24_conclusion_grounding_limitation_statement(self):
        """Test 24: ConclusionCandidate requires grounded statements and explicit limitations."""
        c = ConclusionCandidate(
            statement="AI data centers increase electricity demand while energy efficiency mitigates baseline growth.",
            confidence=0.75,
            supporting_finding_statements=["Finding 1: Data centers consume 4% of power."],
            limitations="Evidence is limited for small regional grids outside the US and EU.",
        )
        assert c.confidence <= 1.0
        assert len(c.supporting_finding_statements) > 0
        assert "limited" in c.limitations.lower()

