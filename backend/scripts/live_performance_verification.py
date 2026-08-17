"""
Live Verification Script for Performance and Quality Verification.
Executes Question 1 (Manufacturing Predictive Maintenance) and Question 2 (Pharma Supply Chain AI)
with live DDGS web search and Gemini 2.5 Flash structured output.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import ResearchProject, ResearchQuestion, ResearchRun, Finding, Evidence, Contradiction, Conclusion, ResearchSource
from app.providers.gemini import GeminiAIProvider
from app.providers.research.web import WebResearchProvider
from app.services.research_pipeline_service import ResearchPipelineService
from sqlalchemy import select


async def run_live_test(topic_name: str, industry: str, question_text: str):
    print("\n" + "=" * 80)
    print(f"STARTING LIVE RUN: {topic_name} [{industry}]")
    print(f"QUESTION: {question_text}")
    print("=" * 80)

    # Force real providers for this live test
    gemini_api_key = settings.GEMINI_API_KEY
    if not gemini_api_key:
        print("ERROR: GEMINI_API_KEY is not set.")
        return None

    ai_provider = GeminiAIProvider(api_key=gemini_api_key, model_name="gemini-2.5-flash")
    research_provider = WebResearchProvider()

    async with AsyncSessionLocal() as session:
        # Create Project
        project = ResearchProject(
            name=f"Live Verification - {topic_name}",
            research_topic=topic_name,
            industry=industry,
        )
        session.add(project)
        await session.flush()

        # Create Question
        question = ResearchQuestion(
            project_id=project.id,
            question=question_text,
        )
        session.add(question)
        await session.flush()

        # Create Research Run
        run = ResearchRun(
            question_id=question.id,
            status="queued",
        )
        session.add(run)
        await session.commit()
        run_id = run.id

    t_start = time.time()

    async with AsyncSessionLocal() as session:
        service = ResearchPipelineService(
            session=session,
            ai_provider=ai_provider,
            research_provider=research_provider,
        )
        completed_run = await service.execute_run(run_id)

    wall_clock_time = time.time() - t_start

    async with AsyncSessionLocal() as session:
        run_obj = await session.get(ResearchRun, run_id)
        meta = run_obj.metadata_json or {}

        # Fetch entities
        findings = (await session.scalars(select(Finding).where(Finding.research_run_id == run_id))).all()
        evidences = (await session.scalars(
            select(Evidence).join(Finding, Evidence.finding_id == Finding.id).where(Finding.research_run_id == run_id)
        )).all()
        contradictions = (await session.scalars(select(Contradiction).where(Contradiction.research_run_id == run_id))).all()
        conclusions = (await session.scalars(select(Conclusion).where(Conclusion.research_run_id == run_id))).all()
        sources = (await session.scalars(select(ResearchSource).where(ResearchSource.research_run_id == run_id))).all()

    print("\n" + "-" * 80)
    print(f"LIVE RUN RESULTS: {topic_name}")
    print(f"Status: {run_obj.status}")
    print(f"Wall Clock Time: {wall_clock_time:.2f}s (Internal: {meta.get('duration_seconds')}s)")
    print(f"Search Time: {meta.get('search_duration_seconds')}s (Queries: {meta.get('search_query_count')})")
    print(f"Fetch Time: {meta.get('quality_metrics', {}).get('timing_breakdown', {}).get('fetch_seconds')}s (Eligible Sources: {meta.get('evidence_eligible_count')})")
    print(f"Extraction Time: {meta.get('extraction_duration_seconds')}s (Batches: {meta.get('extraction_batch_count')})")
    print(f"Contradiction Time: {meta.get('quality_metrics', {}).get('timing_breakdown', {}).get('contradiction_seconds')}s (Count: {len(contradictions)})")
    print(f"Synthesis Time: {meta.get('quality_metrics', {}).get('timing_breakdown', {}).get('synthesis_seconds')}s (Count: {len(conclusions)})")
    print(f"Findings Before Deduplication: {meta.get('findings_before_deduplication')}")
    print(f"Canonical Findings After Deduplication: {meta.get('findings_after_deduplication')}")
    print(f"Duplicate Findings Merged: {meta.get('duplicate_findings_merged')}")
    print(f"Total Evidence Links: {len(evidences)}")

    if conclusions:
        print("\n--- EXECUTIVE CONCLUSION ---")
        print(f"Conclusion Statement: {conclusions[0].statement}")
        print(f"Confidence: {conclusions[0].confidence}")

    if findings:
        print("\n--- SAMPLE CANONICAL FINDINGS ---")
        for f in findings[:4]:
            print(f"[{f.finding_type.upper()}] (conf: {f.confidence:.2f}) {f.statement[:120]}...")

    if contradictions:
        print("\n--- CONTRADICTIONS DETECTED ---")
        for c in contradictions:
            print(f"[{c.severity.upper()}] {c.description[:140]}...")

    return {
        "topic": topic_name,
        "total_runtime": meta.get("duration_seconds", wall_clock_time),
        "search_time": meta.get("search_duration_seconds", 0.0),
        "fetch_time": meta.get("quality_metrics", {}).get("timing_breakdown", {}).get("fetch_seconds", 0.0),
        "extraction_time": meta.get("extraction_duration_seconds", 0.0),
        "contradiction_time": meta.get("quality_metrics", {}).get("timing_breakdown", {}).get("contradiction_seconds", 0.0),
        "synthesis_time": meta.get("quality_metrics", {}).get("timing_breakdown", {}).get("synthesis_seconds", 0.0),
        "gemini_calls": 1 + meta.get("extraction_batch_count", 0) + (1 if contradictions else 1) + len(conclusions),
        "queries_count": meta.get("search_query_count", 0),
        "eligible_sources": meta.get("evidence_eligible_count", 0),
        "findings_before": meta.get("findings_before_deduplication", 0),
        "findings_after": meta.get("findings_after_deduplication", 0),
        "merged_count": meta.get("duplicate_findings_merged", 0),
        "evidence_count": len(evidences),
        "contradiction_count": len(contradictions),
    }


async def main():
    # 1. Run Manufacturing Live Test
    mfg_res = await run_live_test(
        topic_name="Predictive Maintenance in Manufacturing",
        industry="Manufacturing",
        question_text=(
            "How is AI changing predictive maintenance in manufacturing, and what evidence exists regarding "
            "cost savings, downtime reduction, implementation challenges, workforce impact, and operational risks?"
        ),
    )

    # 2. Run Pharma Live Test
    pharma_res = await run_live_test(
        topic_name="AI in Pharmaceutical Supply Chains",
        industry="Pharmaceuticals",
        question_text=(
            "What are the major applications, measurable benefits, implementation challenges, and governance risks of AI in pharmaceutical supply chain operations?"
        ),
    )

    print("\n" + "=" * 80)
    print("FINAL BEFORE / AFTER SUMMARY DATA")
    print("=" * 80)
    print("MANUFACTURING RUN:", json.dumps(mfg_res, indent=2))
    print("PHARMA RUN:", json.dumps(pharma_res, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
