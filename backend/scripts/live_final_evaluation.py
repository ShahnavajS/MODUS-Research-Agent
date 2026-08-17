import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models import (
    Conclusion,
    Contradiction,
    Evidence,
    Finding,
    ResearchProject,
    ResearchQuestion,
    ResearchRun,
    ResearchSource,
    ResearchSubQuestion,
    SourceContent,
)
from app.services.research_pipeline_service import ResearchPipelineService
from sqlalchemy import select

TEST_A_QUESTION = (
    "How will the rapid expansion of AI data centers reshape global electricity demand, "
    "water consumption, semiconductor supply chains, and national energy security through 2030, "
    "and does the expected economic value of AI justify the infrastructure, environmental, geopolitical, "
    "and regulatory risks? Compare evidence across the United States, European Union, China, and India."
)

TEST_B_QUESTION = (
    "How significantly is AI accelerating pharmaceutical drug discovery from early-stage target identification "
    "through clinical development, and how do the economics, success rates, and regulatory challenges differ "
    "between large pharmaceutical companies and smaller biotechnology firms?"
)


async def run_live_test(test_name: str, topic: str, industry: str, question_text: str):
    print(f"\n{'='*80}\nSTARTING {test_name}\nQUESTION: {question_text}\n{'='*80}")
    t_start = time.time()

    async with AsyncSessionLocal() as session:
        project = ResearchProject(
            name=f"Live Validation {test_name}",
            research_topic=topic,
            industry=industry,
        )
        session.add(project)
        await session.flush()

        question = ResearchQuestion(
            project_id=project.id,
            question=question_text,
        )
        session.add(question)
        await session.flush()

        run = ResearchRun(
            question_id=question.id,
            status="queued",
        )
        session.add(run)
        await session.commit()

        service = ResearchPipelineService(session=session)
        completed_run = await service.execute_run(run.id)

        duration = round(time.time() - t_start, 2)
        print(f"\n{test_name} COMPLETED IN {duration}s | Status: {completed_run.status}")

        # Fetch detailed entities
        sub_qs = (await session.scalars(select(ResearchSubQuestion).where(ResearchSubQuestion.research_run_id == completed_run.id))).all()
        sources = (await session.scalars(select(ResearchSource).where(ResearchSource.research_run_id == completed_run.id))).all()
        contents = (await session.scalars(
            select(SourceContent).join(ResearchSource, SourceContent.source_id == ResearchSource.id).where(ResearchSource.research_run_id == completed_run.id)
        )).all()
        findings = (await session.scalars(select(Finding).where(Finding.research_run_id == completed_run.id))).all()
        evidence = (await session.scalars(
            select(Evidence).join(Finding, Evidence.finding_id == Finding.id).where(Finding.research_run_id == completed_run.id)
        )).all()
        contradictions = (await session.scalars(select(Contradiction).where(Contradiction.research_run_id == completed_run.id))).all()
        conclusions = (await session.scalars(select(Conclusion).where(Conclusion.research_run_id == completed_run.id))).all()

        meta = completed_run.metadata_json or {}
        timing = meta.get("quality_metrics", {}).get("timing_breakdown", {})

        print(f"\n--- EXECUTION TIMING ---")
        print(f"Total Duration: {duration}s")
        print(f"Decomposition: {timing.get('decomposition_seconds')}s")
        print(f"Search: {timing.get('search_seconds')}s")
        print(f"Fetch: {timing.get('fetch_seconds')}s")
        print(f"Extraction: {timing.get('extraction_seconds')}s")
        print(f"Contradiction: {timing.get('contradiction_seconds')}s")
        print(f"Synthesis: {timing.get('synthesis_seconds')}s")

        print(f"\n--- SOURCE & FINDING STATS ---")
        print(f"Sub-questions: {len(sub_qs)}")
        for idx, sq in enumerate(sub_qs):
            print(f"  SQ{idx+1}: {sq.question}")
        print(f"Discovered Sources: {meta.get('discovered_sources_count')}")
        print(f"Rejected Sources: {meta.get('rejected_irrelevant_count')}")
        print(f"Relevant Sources: {meta.get('relevant_sources_count')}")
        print(f"Successful Fetches: {meta.get('successful_sources_count')}")
        print(f"Failed Sources: {meta.get('failed_sources_count')}")
        print(f"Evidence Eligible: {meta.get('evidence_eligible_count')}")
        print(f"Findings Before Deduplication: {meta.get('findings_before_deduplication')}")
        print(f"Canonical Findings: {len(findings)}")
        print(f"Duplicates Merged: {meta.get('duplicate_findings_merged')}")
        print(f"Evidence Links: {len(evidence)}")
        print(f"Contradictions: {len(contradictions)} (by category: {meta.get('contradictions_by_category')})")
        for c in contradictions:
            print(f"  - [{c.contradiction_category}] {c.description[:120]}... (Severity: {c.severity})")
        print(f"Conclusions: {len(conclusions)}")
        for conc in conclusions:
            print(f"  - (Confidence {conc.confidence:.2f}): {conc.statement}")

        return {
            "test_name": test_name,
            "duration": duration,
            "status": completed_run.status,
            "sub_questions_count": len(sub_qs),
            "discovered_sources": meta.get("discovered_sources_count"),
            "rejected_irrelevant": meta.get("rejected_irrelevant_count"),
            "relevant_sources": meta.get("relevant_sources_count"),
            "successful_sources": meta.get("successful_sources_count"),
            "failed_sources": meta.get("failed_sources_count"),
            "evidence_eligible": meta.get("evidence_eligible_count"),
            "findings_count": len(findings),
            "evidence_count": len(evidence),
            "contradictions_count": len(contradictions),
            "contradictions_by_category": meta.get("contradictions_by_category"),
            "conclusions_count": len(conclusions),
            "timing": timing,
        }


async def main():
    res_a = await run_live_test(
        test_name="TEST A (AI Data Center Energy & Infrastructure)",
        topic="AI Data Center Global Energy & Geopolitics",
        industry="Technology & Infrastructure",
        question_text=TEST_A_QUESTION,
    )

    res_b = await run_live_test(
        test_name="TEST B (AI Drug Discovery Economics)",
        topic="AI in Drug Discovery Economics & Development",
        industry="Pharmaceuticals & Biotechnology",
        question_text=TEST_B_QUESTION,
    )

    print("\n" + "="*80)
    print("FINAL SUMMARY REPORT")
    print("="*80)
    print(json.dumps({"Test_A": res_a, "Test_B": res_b}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
