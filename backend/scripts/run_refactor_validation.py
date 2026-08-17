"""
Live Refactor Validation Script.

Executes:
1. Question A: India AI Infrastructure
2. Question B: Personalized mRNA Oncology Vaccines (Different Domain)

Collects detailed metrics for comparing before vs after.
"""

import asyncio
import os
import sys
import time
import json
from uuid import uuid4

# Ensure backend root is on pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import (
    ResearchProject,
    ResearchQuestion,
    ResearchRun,
    ResearchSource,
    SourceContent,
    Finding,
    Evidence,
    Contradiction,
    Conclusion,
)
from app.providers.gemini import GeminiAIProvider
from app.providers.research.web import WebResearchProvider
from app.services.research_pipeline_service import ResearchPipelineService
from sqlalchemy import select


# Instrument Gemini Provider to count LLM calls
class CountingGeminiProvider(GeminiAIProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_count = 0
        self.calls_by_method = {}

    async def decompose_question(self, question: str):
        self.call_count += 1
        self.calls_by_method["decompose_question"] = self.calls_by_method.get("decompose_question", 0) + 1
        return await super().decompose_question(question)

    async def extract_findings_from_source_batch(self, sources, research_question: str):
        self.call_count += 1
        self.calls_by_method["extract_findings_from_source_batch"] = self.calls_by_method.get("extract_findings_from_source_batch", 0) + 1
        return await super().extract_findings_from_source_batch(sources, research_question)

    async def detect_contradictions_from_findings(self, findings):
        self.call_count += 1
        self.calls_by_method["detect_contradictions"] = self.calls_by_method.get("detect_contradictions", 0) + 1
        return await super().detect_contradictions_from_findings(findings)

    async def generate_conclusions_from_findings(self, question: str, findings):
        self.call_count += 1
        self.calls_by_method["generate_conclusions"] = self.calls_by_method.get("generate_conclusions", 0) + 1
        return await super().generate_conclusions_from_findings(question, findings)


async def execute_validation_run(test_name: str, topic: str, question_text: str):
    print(f"\n{'='*80}")
    print(f"STARTING VALIDATION RUN: {test_name}")
    print(f"Topic: {topic}")
    print(f"Question: {question_text[:100]}...")
    print(f"{'='*80}")

    async with AsyncSessionLocal() as session:
        # 1. Create project & question
        project = ResearchProject(
            name=f"Validation: {test_name}",
            research_topic=topic,
            description="Live post-refactor validation run",
        )
        session.add(project)
        await session.flush()

        question = ResearchQuestion(
            project_id=project.id,
            question=question_text,
            status="active",
        )
        session.add(question)
        await session.flush()

        run = ResearchRun(
            question_id=question.id,
            status="pending",
        )
        session.add(run)
        await session.commit()

        # 2. Setup providers
        ai_provider = CountingGeminiProvider()
        research_provider = WebResearchProvider()
        pipeline = ResearchPipelineService(session, ai_provider=ai_provider, research_provider=research_provider)

        start_time = time.time()
        completed_run = await pipeline.execute_run(run.id)
        wall_clock = time.time() - start_time

        # 3. Query all outputs from DB
        run_id = completed_run.id
        sources = (await session.scalars(select(ResearchSource).where(ResearchSource.research_run_id == run_id))).all()
        contents = (await session.scalars(select(SourceContent).join(ResearchSource).where(ResearchSource.research_run_id == run_id))).all()
        findings = (await session.scalars(select(Finding).where(Finding.research_run_id == run_id))).all()
        evidences = (await session.scalars(select(Evidence).join(Finding).where(Finding.research_run_id == run_id))).all()
        contradictions = (await session.scalars(select(Contradiction).where(Contradiction.research_run_id == run_id))).all()
        conclusions = (await session.scalars(select(Conclusion).where(Conclusion.research_run_id == run_id))).all()

        meta = completed_run.metadata_json or {}

        # 4. Compile detailed stats
        successful_contents = [c for c in contents if c.extraction_status == "success"]
        failed_contents = [c for c in contents if c.extraction_status == "failed"]

        result = {
            "test_name": test_name,
            "run_id": str(run_id),
            "status": completed_run.status,
            "wall_clock_runtime_seconds": round(wall_clock, 2),
            "pipeline_total_seconds": meta.get("total_runtime", round(wall_clock, 2)),
            "gemini_total_calls": ai_provider.call_count,
            "gemini_calls_by_method": ai_provider.calls_by_method,
            "sources_discovered": meta.get("discovered_sources", len(sources)),
            "sources_selected": meta.get("selected_sources", 0),
            "sources_successfully_fetched": len(successful_contents),
            "sources_failed": len(failed_contents),
            "failed_sources_details": meta.get("failed_sources", []),
            "raw_findings_before_dedup": meta.get("findings_before_deduplication", len(findings)),
            "deduplicated_findings_count": len(findings),
            "unsupported_findings_rejected": meta.get("unsupported_findings_count", 0),
            "evidence_count": len(evidences),
            "contradiction_count": len(contradictions),
            "conclusions_count": len(conclusions),
            "conclusion_confidence": conclusions[0].confidence if conclusions else 0.0,
            "conclusion_text": conclusions[0].statement if conclusions else "",
            "sample_findings": [f.statement for f in findings[:5]],
            "sample_evidence": [e.excerpt[:120] for e in evidences[:3]],
        }

        print(f"\n--- RESULTS FOR {test_name} ---")
        print(f"Status: {result['status']}")
        print(f"Total Runtime: {result['wall_clock_runtime_seconds']}s")
        print(f"Gemini Calls: {result['gemini_total_calls']} (Breakdown: {result['gemini_calls_by_method']})")
        print(f"Sources Discovered: {result['sources_discovered']}")
        print(f"Sources Selected: {result['sources_selected']}")
        print(f"Sources Successfully Fetched: {result['sources_successfully_fetched']}")
        print(f"Sources Failed: {result['sources_failed']}")
        print(f"Raw Findings (before dedup): {result['raw_findings_before_dedup']}")
        print(f"Deduplicated Findings: {result['deduplicated_findings_count']}")
        print(f"Evidence Excerpts: {result['evidence_count']}")
        print(f"Contradictions: {result['contradiction_count']}")
        print(f"Conclusion Confidence: {result['conclusion_confidence']:.2f}")
        print(f"Conclusion: {result['conclusion_text'][:150]}...")

        return result


async def main():
    q_india = (
        "How will India's emergence as a major AI data-center and semiconductor hub through 2030 "
        "reshape global AI infrastructure supply chains, electricity and water demand, chip and advanced-packaging dependencies, "
        "and national energy security—and can India capture enough economic value from AI infrastructure investment to justify "
        "the fiscal, environmental, geopolitical, cybersecurity, and strategic risks?"
    )

    q_healthcare = (
        "What are the primary clinical efficacy, safety endpoints, genomic targeting mechanisms, "
        "and regulatory approval pathways for personalized neoantigen mRNA cancer vaccines in solid tumors, "
        "and how do their manufacturing turnaround times, cold-chain logistics, and cost-effectiveness compare to immune checkpoint inhibitors?"
    )

    res_india = await execute_validation_run(
        "Run A: India AI Infrastructure",
        "India AI & Semiconductor Infrastructure 2030",
        q_india,
    )

    res_healthcare = await execute_validation_run(
        "Run B: mRNA Cancer Vaccines",
        "Personalized Neoantigen mRNA Oncology Vaccines",
        q_healthcare,
    )

    summary = {
        "run_a_india": res_india,
        "run_b_healthcare": res_healthcare,
    }

    with open("live_refactor_validation_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\nSaved full validation summary to live_refactor_validation_summary.json")


if __name__ == "__main__":
    asyncio.run(main())
