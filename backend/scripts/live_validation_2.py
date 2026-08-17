import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath("."))

from app.core.database import AsyncSessionLocal
from app.models import ResearchProject, ResearchQuestion, ResearchRun
from app.services.research_pipeline_service import ResearchPipelineService
from app.services.run_service import RunService

async def main():
    print("======================================================================")
    print("LIVE VALIDATION TEST 2: GENERIC MANUFACTURING PREDICTIVE MAINTENANCE")
    print("======================================================================")
    t0 = time.time()
    
    question_text = (
        "How is AI changing predictive maintenance in manufacturing, and what evidence "
        "exists regarding cost savings, downtime reduction, implementation challenges, "
        "workforce impact, and operational risks?"
    )

    async with AsyncSessionLocal() as session:
        p = ResearchProject(name="Industrial AI Manufacturing", research_topic="Predictive Maintenance")
        session.add(p)
        await session.flush()

        q = ResearchQuestion(project_id=p.id, question=question_text)
        session.add(q)
        await session.flush()

        run = ResearchRun(question_id=q.id, status="queued", metadata_json={})
        session.add(run)
        await session.commit()

        print(f"Starting live research run {run.id}...")
        pipeline = ResearchPipelineService(session)
        completed_run = await pipeline.execute_run(run.id)

        run_svc = RunService(session)
        traceability = await run_svc.get_run_traceability(completed_run.id)
        meta = completed_run.metadata_json or {}
        metrics = meta.get("quality_metrics", {})

        print("\n=== LIVE TEST 2 RESULTS ===")
        print(f"Run Status: {completed_run.status}")
        print(f"Execution Mode: {meta.get('execution_mode')}")
        print(f"Total Duration: {round(time.time() - t0, 2)}s (pipeline internal: {meta.get('duration_seconds')}s)")
        print(f"Discovered Sources: {meta.get('discovered_sources_count')}")
        print(f"Relevant Sources: {meta.get('relevant_sources_count')}")
        print(f"Rejected Irrelevant Sources: {meta.get('rejected_irrelevant_count')}")
        print(f"Fetch Success Sources: {meta.get('fetch_success_count')}")
        print(f"Failed Sources: {meta.get('failed_sources_count')}")
        print(f"Evidence Eligible Sources: {meta.get('evidence_eligible_count')}")
        print(f"Source Type Distribution: {metrics.get('source_type_distribution')}")
        print(f"Grounded Findings: {meta.get('grounded_findings_count')}")
        print(f"Unsupported Findings Rejected: {meta.get('unsupported_findings_count')}")
        print(f"Evidence Excerpts: {meta.get('evidence_count')}")
        print(f"Contradictions: {meta.get('contradictions_count')}")
        print(f"Conclusions: {meta.get('conclusions_count')}")
        print(f"Timing Breakdown: {metrics.get('timing_breakdown')}")

        print("\n--- SAMPLE GROUNDED FINDINGS ---")
        for idx, node in enumerate(traceability.provenance_graph[:2]):
            print(f"\nConclusion #{idx+1}: {node.conclusion_statement[:120]}...")
            for f in node.findings[:3]:
                print(f"  - [{f.finding_type.upper()}] {f.statement[:100]}...")
                for ev in f.evidences[:1]:
                    print(f"    * Excerpt: \"{ev.excerpt[:80]}...\"")
                    print(f"    * Source URL: {ev.source_url}")

if __name__ == "__main__":
    asyncio.run(main())
