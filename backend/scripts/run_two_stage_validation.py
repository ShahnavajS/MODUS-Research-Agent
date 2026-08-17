import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models import ResearchProject, ResearchQuestion, ResearchRun, Finding, Evidence, Conclusion, Contradiction
from app.services.research_pipeline_service import ResearchPipelineService
from sqlalchemy import select


async def run_validation_case(project_name: str, topic: str, question_text: str):
    print(f"\n=======================================================")
    print(f"RUNNING LIVE VALIDATION: {project_name}")
    print(f"Question: {question_text}")
    print(f"=======================================================")
    t_start = time.time()

    async with AsyncSessionLocal() as session:
        # Create Project
        proj = (await session.scalars(select(ResearchProject).where(ResearchProject.name == project_name))).first()
        if not proj:
            proj = ResearchProject(name=project_name, research_topic=topic)
            session.add(proj)
            await session.flush()

        # Add Question
        q = ResearchQuestion(project_id=proj.id, question=question_text, status="active")
        session.add(q)
        await session.flush()

        # Create Run
        run = ResearchRun(question_id=q.id, status="queued", metadata_json={})
        session.add(run)
        await session.commit()

        pipeline = ResearchPipelineService(session)
        executed_run = await pipeline.execute_run(run.id)

        duration = round(time.time() - t_start, 2)
        meta = executed_run.metadata_json or {}

        findings = (await session.scalars(select(Finding).where(Finding.research_run_id == run.id))).all()
        evidences = (await session.scalars(select(Evidence).join(Finding).where(Finding.research_run_id == run.id))).all()
        conclusions = (await session.scalars(select(Conclusion).where(Conclusion.research_run_id == run.id))).all()
        conflicts = (await session.scalars(select(Contradiction).where(Contradiction.research_run_id == run.id))).all()

        print(f"\n[RESULTS] {project_name}")
        print(f"Run ID: {run.id}")
        print(f"Status: {executed_run.status}")
        print(f"Total Runtime: {duration}s (<90s budget)")
        print(f"Stage Timings: {meta.get('timing_breakdown') or meta.get('stage_timings')}")
        print(f"Discovered Sources: {meta.get('discovered_sources')}")
        print(f"Deterministic Candidates (Stage 2A): {meta.get('deterministic_candidates')}")
        print(f"Semantically Relevant Sources (Stage 2B): {meta.get('semantically_relevant_sources')}")
        print(f"Successful Fetches: {meta.get('successful_sources_count')}")
        print(f"Failed Fetches: {meta.get('failed_sources_count')}")
        print(f"Source Diversity: {meta.get('source_diversity')}")
        print(f"Findings Generated: {len(findings)}")
        print(f"Evidence Generated: {len(evidences)}")
        print(f"Contradictions Logged: {len(conflicts)}")
        print(f"Conclusions: {len(conclusions)}")
        if conclusions:
            print(f"Conclusion Statement: {conclusions[0].statement[:200]}...")

        return {
            "project": project_name,
            "runtime": duration,
            "findings": len(findings),
            "evidence": len(evidences),
            "conflicts": len(conflicts),
            "conclusions": len(conclusions),
        }


async def main():
    res1 = await run_validation_case(
        project_name="India AI Data Center & Semiconductor Strategy",
        topic="Sovereign AI Infrastructure 2030",
        question_text="How will India's emergence as a major AI data-center and semiconductor hub through 2030 reshape global AI infrastructure supply chains, electricity and water demand, chip and advanced-packaging dependencies, and national energy security—and can India capture enough economic value from AI infrastructure investment to justify the fiscal, environmental, geopolitical, cybersecurity, and strategic risks?",
    )

    res2 = await run_validation_case(
        project_name="Healthcare AI & Clinical Diagnostics 2030",
        topic="Generative AI in Clinical Oncology & Diagnostics",
        question_text="How are multi-modal foundation models and generative AI transforming clinical oncology workflows, diagnostic turnaround times, and hospital reimbursement models across North America and Europe by 2030?",
    )

    print("\n\n=======================================================")
    print("FINAL SUMMARY OF TWO-STAGE RETRIEVAL VALIDATION RUNS")
    print("=======================================================")
    print(f"Run 1 ({res1['project']}): {res1['findings']} findings, {res1['evidence']} evidence links, {res1['conflicts']} conflicts in {res1['runtime']}s")
    print(f"Run 2 ({res2['project']}): {res2['findings']} findings, {res2['evidence']} evidence links, {res2['conflicts']} conflicts in {res2['runtime']}s")


if __name__ == "__main__":
    asyncio.run(main())
