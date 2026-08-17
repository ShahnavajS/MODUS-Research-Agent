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
from app.providers.gemini import GeminiAIProvider
from app.providers.research.web import WebResearchProvider
from app.services.research_pipeline_service import ResearchPipelineService
from sqlalchemy import select


async def run_live_test():
    test_question = (
        "How are sovereign wealth funds and private equity firms deploying capital into AI infrastructure, "
        "energy assets, and custom semiconductor ventures through 2030, and what are the primary geopolitical, "
        "regulatory, and return-on-investment risks comparing North America, the Gulf Cooperation Council (GCC), and East Asia?"
    )

    print("=" * 80)
    print("STARTING LIVE MICRO-FIX RESEARCH VALIDATION TEST")
    print(f"Question: {test_question}")
    print("=" * 80)

    t_start = time.time()

    async with AsyncSessionLocal() as session:
        # Create Project
        project = ResearchProject(
            name="Sovereign AI Infrastructure Investment 2030",
            description="Live micro-fix validation run",
            research_topic="Sovereign AI and PE Capital Deployment 2030",
            industry="Finance / Infrastructure",
            status="active",
        )
        session.add(project)
        await session.flush()

        # Create Question
        question_obj = ResearchQuestion(
            project_id=project.id,
            question=test_question,
            status="pending",
        )
        session.add(question_obj)
        await session.flush()

        # Create Run
        run = ResearchRun(
            question_id=question_obj.id,
            status="pending",
        )
        session.add(run)
        await session.commit()

        run_id = run.id

    # Providers
    ai_provider = GeminiAIProvider()
    research_provider = WebResearchProvider()

    async with AsyncSessionLocal() as session:
        service = ResearchPipelineService(
            session=session,
            ai_provider=ai_provider,
            research_provider=research_provider,
        )
        completed_run = await service.execute_run(run_id)

    total_duration = round(time.time() - t_start, 2)

    # Fetch all details from DB
    async with AsyncSessionLocal() as session:
        sub_qs = (await session.scalars(
            select(ResearchSubQuestion).where(ResearchSubQuestion.research_run_id == run_id)
        )).all()

        sources = (await session.scalars(
            select(ResearchSource).where(ResearchSource.research_run_id == run_id)
        )).all()

        contents = (await session.scalars(
            select(SourceContent).join(ResearchSource, SourceContent.source_id == ResearchSource.id).where(ResearchSource.research_run_id == run_id)
        )).all()

        findings = (await session.scalars(
            select(Finding).where(Finding.research_run_id == run_id)
        )).all()

        evidences = (await session.scalars(
            select(Evidence).join(Finding, Evidence.finding_id == Finding.id).where(Finding.research_run_id == run_id)
        )).all()

        contradictions = (await session.scalars(
            select(Contradiction).where(Contradiction.research_run_id == run_id)
        )).all()

        conclusions = (await session.scalars(
            select(Conclusion).where(Conclusion.research_run_id == run_id)
        )).all()

        r_obj = await session.get(ResearchRun, run_id)
        meta = r_obj.metadata_json or {}

        # Source status counts
        status_counts = {
            "DISCOVERED": len(sources),
            "REJECTED": 0,
            "FETCH_FAILED": 0,
            "EVIDENCE_ELIGIBLE": 0,
        }
        reasons_count = {}

        for s in sources:
            smeta = s.metadata_json or {}
            lstate = smeta.get("lifecycle_state", "DISCOVERED")
            if lstate in ["REJECTED", "HARD_EXCLUDED", "REJECTED_IRRELEVANT"]:
                status_counts["REJECTED"] += 1
                r = smeta.get("rejection_reason", "INSUFFICIENT_RELEVANCE")
                reasons_count[r] = reasons_count.get(r, 0) + 1
            elif lstate == "FETCH_FAILED":
                status_counts["FETCH_FAILED"] += 1
                r = smeta.get("rejection_reason", "FETCH_FAILED")
                reasons_count[r] = reasons_count.get(r, 0) + 1
            elif lstate == "EVIDENCE_ELIGIBLE":
                status_counts["EVIDENCE_ELIGIBLE"] += 1

        contradiction_categories = {}
        for c in contradictions:
            cat = c.contradiction_category or "DIRECT_CONTRADICTION"
            contradiction_categories[cat] = contradiction_categories.get(cat, 0) + 1

        print("\n" + "=" * 80)
        print("LIVE RESEARCH TEST RESULTS")
        print("=" * 80)
        print(f"Status:                      {completed_run.status}")
        print(f"Total Runtime:               {total_duration}s")
        print(f"Sub-Questions:               {len(sub_qs)}")
        for sq in sub_qs:
            print(f"  - {sq.question}")
        print(f"\nSource Status Counts:")
        print(f"  - Discovered Sources:      {status_counts['DISCOVERED']}")
        print(f"  - Rejected Sources:        {status_counts['REJECTED']}")
        print(f"  - Fetch Failed Sources:    {status_counts['FETCH_FAILED']}")
        print(f"  - Evidence Eligible:       {status_counts['EVIDENCE_ELIGIBLE']}")
        print(f"Rejection Reasons Breakdown:")
        for r, count in reasons_count.items():
            print(f"  - {r}: {count}")

        print(f"\nFindings & Grounding:")
        print(f"  - Canonical Findings:      {len(findings)}")
        print(f"  - Grounded Evidence Links: {len(evidences)}")

        print(f"\nContradictions Detected:    {len(contradictions)}")
        print(f"Contradiction Categories Breakdown:")
        for cat, count in contradiction_categories.items():
            print(f"  - {cat}: {count}")
        for c in contradictions:
            print(f"    * [{c.contradiction_category}] {c.description[:140]}...")

        print(f"\nConclusions Synthesized:    {len(conclusions)}")
        for cl in conclusions:
            print(f"  - Confidence: {cl.confidence}")
            print(f"  - Statement:  {cl.statement}")

        print("=" * 80)

        # Save summary JSON
        result_summary = {
            "runtime_seconds": total_duration,
            "status": completed_run.status,
            "sub_questions_count": len(sub_qs),
            "source_status_counts": status_counts,
            "rejection_reasons": reasons_count,
            "evidence_eligible_source_count": status_counts["EVIDENCE_ELIGIBLE"],
            "findings_count": len(findings),
            "evidence_count": len(evidences),
            "contradictions_count": len(contradictions),
            "contradiction_categories": contradiction_categories,
            "conclusions": [
                {
                    "statement": cl.statement,
                    "confidence": cl.confidence,
                }
                for cl in conclusions
            ],
            "timings": meta.get("timing", {}),
        }

    with open("live_microfix_summary.json", "w") as f:
        json.dump(result_summary, f, indent=2)
    print("Saved live_microfix_summary.json")


if __name__ == "__main__":
    asyncio.run(run_live_test())
