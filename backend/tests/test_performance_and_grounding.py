"""
Unit and Integration Tests for Performance, Search Parallelism,
Source Batching, Finding Deduplication, Numeric Guard, and Confidence Calibration.
"""

import pytest
from uuid import uuid4

from app.evaluation.confidence import calculate_calibrated_finding_confidence
from app.evaluation.deduplication import are_findings_duplicate, deduplicate_findings
from app.evaluation.numeric_guard import validate_numeric_preservation, extract_numeric_claims
from app.evaluation.relevance import classify_source_role, evaluate_source_relevance
from app.providers.base import FindingCandidate, SourceDocumentInput
from app.providers.mock import MockAIProvider
from app.providers.research.mock import MockResearchProvider
from app.services.research_pipeline_service import ResearchPipelineService


# ─── 1. Finding Deduplication Tests ──────────────────────────────────────────

class TestFindingDeduplication:
    def test_semantic_near_duplicates_identified(self):
        stmt1 = "AI predictive maintenance reduces downtime by 30-50%."
        stmt2 = "Predictive maintenance can reduce unplanned downtime by 30-50%."
        assert are_findings_duplicate(stmt1, stmt2) is True

    def test_varied_formulations_merged(self):
        stmt1 = "AI-driven predictive maintenance reduces unplanned downtime by 30-50%."
        stmt2 = "AI predictive maintenance reduces downtime by 30-50%."
        assert are_findings_duplicate(stmt1, stmt2) is True

    def test_different_numbers_not_merged(self):
        stmt1 = "Predictive maintenance reduces maintenance costs by 10%."
        stmt2 = "Predictive maintenance reduces maintenance costs by 50%."
        assert are_findings_duplicate(stmt1, stmt2) is False

    def test_unrelated_claims_not_merged(self):
        stmt1 = "Vibration sensors monitor bearing temperatures in industrial pumps."
        stmt2 = "Workforce reskilling requires extensive data engineering training programs."
        assert are_findings_duplicate(stmt1, stmt2) is False

    def test_deduplicate_findings_preserves_evidence_and_provenance(self):
        f_id1 = uuid4()
        f_id2 = uuid4()
        f_id3 = uuid4()

        raw_findings = [
            {
                "id": f_id1,
                "statement": "AI predictive maintenance reduces downtime by 30-50%.",
                "finding_type": "benefit",
                "importance": "high",
                "confidence": 0.85,
                "source_id": "source-1",
                "evidence": [{"excerpt": "reduces downtime by 30-50%", "source_id": "source-1", "content_obj": type("Obj", (), {"id": "c1"})(), "evidence_relevance": 0.9, "evidence_type": "supporting"}],
            },
            {
                "id": f_id2,
                "statement": "Predictive maintenance can reduce unplanned downtime by 30-50%.",
                "finding_type": "benefit",
                "importance": "high",
                "confidence": 0.90,
                "source_id": "source-2",
                "evidence": [{"excerpt": "unplanned downtime by 30-50%", "source_id": "source-2", "content_obj": type("Obj", (), {"id": "c2"})(), "evidence_relevance": 0.95, "evidence_type": "supporting"}],
            },
            {
                "id": f_id3,
                "statement": "Data quality issues cause 70% of deployment delays in manufacturing plants.",
                "finding_type": "risk",
                "importance": "medium",
                "confidence": 0.80,
                "source_id": "source-1",
                "evidence": [{"excerpt": "Data quality issues cause 70% of delays", "source_id": "source-1", "content_obj": type("Obj", (), {"id": "c1"})(), "evidence_relevance": 0.85, "evidence_type": "supporting"}],
            },
        ]

        canonical, merged_count = deduplicate_findings(raw_findings, similarity_threshold=0.70)

        # 3 raw findings should become 2 canonical findings
        assert len(canonical) == 2
        assert merged_count == 1

        # The first canonical finding should aggregate evidence from both source-1 and source-2
        downtime_finding = next(f for f in canonical if "30-50%" in f["statement"])
        assert len(downtime_finding["evidence"]) == 2
        assert downtime_finding["merged_count"] == 2
        assert len(downtime_finding["merged_statements"]) == 2


# ─── 2. Numeric Claim Protection Tests ───────────────────────────────────────

class TestNumericClaimProtection:
    def test_valid_numeric_range_passes(self):
        stmt = "Downtime is reduced by 30-50% with predictive maintenance."
        excerpt = "Operating data confirms downtime is reduced by 30-50% across facilities."
        is_valid, violations = validate_numeric_preservation(stmt, excerpt)
        assert is_valid is True
        assert len(violations) == 0

    def test_inverted_numeric_range_detected(self):
        stmt = "Costs are reduced by 50-30% in pilot programs."
        excerpt = "Costs are reduced by 30-50% in pilot programs."
        is_valid, violations = validate_numeric_preservation(stmt, excerpt)
        assert is_valid is False
        assert any("Inverted numeric range" in v for v in violations)

    def test_hallucinated_large_number_flagged(self):
        stmt = "Annual savings reached $450 million in Year 1."
        excerpt = "The company saw modest initial productivity gains in Year 1."
        is_valid, violations = validate_numeric_preservation(stmt, excerpt)
        assert is_valid is False
        assert any("not grounded in evidence excerpt" in v for v in violations)

    def test_numeric_extraction(self):
        text = "Savings of $1.5 million (25-40%) achieved over 12-18 months with 10:1 ROI."
        claims = extract_numeric_claims(text)
        assert len(claims["ranges"]) >= 2
        assert len(claims["currencies"]) >= 1
        assert len(claims["ratios"]) >= 1


# ─── 3. Confidence Calibration & Source Roles ────────────────────────────────

class TestConfidenceCalibration:
    def test_confidence_is_never_100_percent(self):
        res = calculate_calibrated_finding_confidence(
            evidence_match_score=1.0,
            source_relevance=1.0,
            source_credibility=1.0,
            distinct_sources_count=5,
            source_role="PRIMARY",
        )
        assert res["confidence"] <= 0.95
        assert res["confidence"] < 1.0

    def test_discovery_only_source_capped_at_50_percent(self):
        res = calculate_calibrated_finding_confidence(
            evidence_match_score=1.0,
            source_relevance=0.80,
            source_credibility=0.30,
            distinct_sources_count=1,
            source_role="DISCOVERY_ONLY",
        )
        assert res["confidence"] <= 0.50

    def test_corroborated_findings_have_higher_confidence(self):
        res_single = calculate_calibrated_finding_confidence(
            evidence_match_score=1.0,
            source_relevance=0.80,
            source_credibility=0.80,
            distinct_sources_count=1,
            source_role="SECONDARY",
        )
        res_multi = calculate_calibrated_finding_confidence(
            evidence_match_score=1.0,
            source_relevance=0.80,
            source_credibility=0.80,
            distinct_sources_count=3,
            source_role="SECONDARY",
        )
        assert res_multi["confidence"] > res_single["confidence"]

    def test_source_role_classification(self):
        assert classify_source_role("academic_journal", 0.95, 0.70) == "PRIMARY"
        assert classify_source_role("news", 0.85, 0.60) == "PRIMARY"
        assert classify_source_role("general_web", 0.70, 0.45) == "SECONDARY"
        assert classify_source_role("social_media", 0.15, 0.80) == "DISCOVERY_ONLY"
        assert classify_source_role("community_forum", 0.20, 0.75) == "DISCOVERY_ONLY"


# ─── 4. Batched Extraction & Source Boundary Isolation ───────────────────────

class TestBatchedExtraction:
    @pytest.mark.asyncio
    async def test_mock_batch_extraction_preserves_source_id(self):
        provider = MockAIProvider()
        sources = [
            SourceDocumentInput(
                source_id="src-1",
                title="Industrial AI Adoption",
                url="https://example.com/industrial-ai",
                source_type="general_web",
                credibility=0.80,
                content="Predictive maintenance delivers 30-50% downtime reduction in manufacturing plants. Sensor networks monitor motor vibrations continuously.",
            ),
            SourceDocumentInput(
                source_id="src-2",
                title="Manufacturing Cost Study",
                url="https://example.com/costs",
                source_type="industry_report",
                credibility=0.85,
                content="Implementation challenges include legacy equipment integration and high upfront sensor installation costs.",
            ),
        ]

        findings = await provider.extract_findings_from_source_batch(sources, "AI in manufacturing")

        assert len(findings) >= 2
        # Every finding must have a valid source_id matching its originating source
        source_ids = {f.source_id for f in findings}
        assert "src-1" in source_ids
        assert "src-2" in source_ids

        # Verify evidence cannot cross source boundaries
        for f in findings:
            if f.source_id == "src-1":
                assert "predictive" in f.excerpt.lower() or "sensor" in f.excerpt.lower()
            if f.source_id == "src-2":
                assert "implementation" in f.excerpt.lower() or "legacy" in f.excerpt.lower()
