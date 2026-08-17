import asyncio
from datetime import datetime, timezone
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, async_engine
from app.models.base import Base
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


async def seed_sample_data():
    """Deterministic development seed mechanism."""
    print("Starting database seed...")
    
    # Ensure tables exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if project already exists to prevent duplicate seeding
        from sqlalchemy import select
        existing = await session.execute(select(ResearchProject).where(ResearchProject.name == "AI Transformation in Retail"))
        if existing.scalar_one_or_none():
            print("Sample seed project already exists. Skipping seed.")
            return

        now = datetime.now(timezone.utc)

        # 1. Project
        project = ResearchProject(
            id=uuid.uuid4(),
            name="AI Transformation in Retail",
            description="Comprehensive analysis of generative AI, automated inventory, and computer vision deployment in global retail operations.",
            research_topic="Artificial Intelligence in Retail & Supply Chain",
            industry="Retail & Consumer Goods",
            status="active",
        )
        session.add(project)
        await session.flush()

        # 2. Questions
        q1 = ResearchQuestion(
            id=uuid.uuid4(),
            project_id=project.id,
            question="How is AI transforming retail store operations and inventory management?",
            status="active",
        )
        q2 = ResearchQuestion(
            id=uuid.uuid4(),
            project_id=project.id,
            question="What is the ROI and implementation timeline for autonomous checkout systems?",
            status="active",
        )
        session.add_all([q1, q2])
        await session.flush()

        # 3. Research Run
        run = ResearchRun(
            id=uuid.uuid4(),
            question_id=q1.id,
            status="completed",
            started_at=now,
            completed_at=now,
            metadata_json={"seed": True, "depth": "standard", "sources_analyzed": 2},
        )
        session.add(run)
        await session.flush()

        # 4. Sources & Content
        s1 = ResearchSource(
            id=uuid.uuid4(),
            research_run_id=run.id,
            title="McKinsey State of Retail AI 2025 Report",
            url="https://www.mckinsey.com/industries/retail/our-insights/state-of-retail-ai-2025",
            publisher="McKinsey & Company",
            author="Retail Technology Practice Group",
            published_at=now,
            source_type="report",
            credibility_score=0.92,
            metadata_json={"citation": "McKinsey Retail AI 2025"},
        )
        s2 = ResearchSource(
            id=uuid.uuid4(),
            research_run_id=run.id,
            title="National Retail Federation Supply Chain Intelligence Brief",
            url="https://nrf.com/research/supply-chain-ai-trends",
            publisher="NRF Insights",
            author="Sarah Jenkins",
            published_at=now,
            source_type="article",
            credibility_score=0.88,
            metadata_json={"citation": "NRF Brief 2025"},
        )
        session.add_all([s1, s2])
        await session.flush()

        c1 = SourceContent(
            id=uuid.uuid4(),
            source_id=s1.id,
            content="Computer vision and demand-forecasting AI models have reduced out-of-stock incidents by 34% across top 50 global omnichannel retailers while improving demand forecast accuracy to 91%.",
            content_hash="abc123hash",
            word_count=32,
            extraction_status="completed",
        )
        c2 = SourceContent(
            id=uuid.uuid4(),
            source_id=s2.id,
            content="High capital expenditure for camera infrastructure and edge AI sensors remains a significant bottleneck, extending break-even timelines to over 36 months for mid-tier grocers.",
            content_hash="def456hash",
            word_count=28,
            extraction_status="completed",
        )
        session.add_all([c1, c2])
        await session.flush()

        # 5. Findings
        f1 = Finding(
            id=uuid.uuid4(),
            research_run_id=run.id,
            statement="Demand-forecasting AI reduces out-of-stock store events by 34% and increases stock accuracy to 91%.",
            finding_type="fact",
            confidence=0.92,
            importance="high",
        )
        f2 = Finding(
            id=uuid.uuid4(),
            research_run_id=run.id,
            statement="Edge hardware deployment cost for full-store computer vision delays net positive ROI beyond 36 months for mid-market retailers.",
            finding_type="risk",
            confidence=0.85,
            importance="medium",
        )
        session.add_all([f1, f2])
        await session.flush()

        # 6. Evidence
        e1 = Evidence(
            id=uuid.uuid4(),
            finding_id=f1.id,
            source_id=s1.id,
            source_content_id=c1.id,
            excerpt="Computer vision and demand-forecasting AI models have reduced out-of-stock incidents by 34% across top 50 global omnichannel retailers.",
            relevance_score=0.95,
            evidence_type="supporting",
        )
        e2 = Evidence(
            id=uuid.uuid4(),
            finding_id=f2.id,
            source_id=s2.id,
            source_content_id=c2.id,
            excerpt="High capital expenditure for camera infrastructure and edge AI sensors remains a significant bottleneck, extending break-even timelines to over 36 months.",
            relevance_score=0.90,
            evidence_type="supporting",
        )
        session.add_all([e1, e2])
        await session.flush()

        # 7. Contradiction
        contradiction = Contradiction(
            id=uuid.uuid4(),
            research_run_id=run.id,
            finding_a_id=f1.id,
            finding_b_id=f2.id,
            description="Contradiction between immediate operational efficiency claims (34% out-of-stock reduction) versus long capital payback periods (>36 months ROI timeline).",
            severity="medium",
            resolution_status="unresolved",
            resolution_notes="Payback period depends heavily on store footprint density and existing camera infrastructure.",
        )
        session.add(contradiction)
        await session.flush()

        # 8. Conclusion
        conclusion = Conclusion(
            id=uuid.uuid4(),
            research_run_id=run.id,
            statement="Retail AI delivers immediate inventory accuracy gains, but executive investment decisions must account for a multi-year payback period driven by hardware installation costs.",
            confidence=0.89,
        )
        conclusion.findings.append(f1)
        conclusion.findings.append(f2)
        session.add(conclusion)

        await session.commit()
        print("Database seed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_sample_data())
