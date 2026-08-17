from typing import List
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
from app.repositories import QuestionRepository, RunRepository
from app.schemas.conclusion import ConclusionResponse
from app.schemas.contradiction import ContradictionResponse
from app.schemas.finding import EvidenceResponse, FindingResponse
from app.schemas.run import (
    ResearchRunCreate,
    ResearchRunDetailResponse,
    ResearchRunResponse,
    RunCountsSchema,
    RunTraceabilityResponse,
    TraceabilityNodeSchema,
)
from app.schemas.source import ContentResponse, SourceResponse
from app.schemas.sub_question import SubQuestionResponse


class RunService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.question_repo = QuestionRepository(session)
        self.run_repo = RunRepository(session)

    async def create_run(self, question_id: UUID, data: ResearchRunCreate) -> ResearchRunResponse:
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot trigger research run: ResearchQuestion '{question_id}' not found.",
            )
        run = ResearchRun(
            question_id=question_id,
            status="queued",
            metadata_json=data.metadata_json or {},
        )
        created_run = await self.run_repo.create(run)
        return await self._to_response(created_run)

    async def get_run(self, run_id: UUID) -> ResearchRunResponse:
        run = await self.run_repo.get_by_id(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ResearchRun '{run_id}' not found.",
            )
        return await self._to_response(run)

    async def list_runs_by_question(
        self, question_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[ResearchRunResponse]:
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ResearchQuestion '{question_id}' not found.",
            )
        runs = await self.run_repo.list_by_question_id(question_id, limit=limit, offset=offset)
        return [await self._to_response(r) for r in runs]

    async def get_run_details(self, run_id: UUID) -> ResearchRunDetailResponse:
        run = await self.run_repo.get_by_id(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ResearchRun '{run_id}' not found.",
            )

        question = await self.question_repo.get_by_id(run.question_id)
        question_text = question.question if question else "Unknown Question"
        project_id = question.project_id if question else UUID("00000000-0000-0000-0000-000000000000")

        project_res = await self.session.execute(select(ResearchProject).where(ResearchProject.id == project_id))
        project = project_res.scalar_one_or_none()
        project_name = project.name if project else "Unknown Project"

        # 1. Sub-questions
        sub_qs_res = await self.session.execute(
            select(ResearchSubQuestion)
            .where(ResearchSubQuestion.research_run_id == run.id)
            .order_by(ResearchSubQuestion.sequence_number.asc())
        )
        sub_qs = [SubQuestionResponse.model_validate(sq) for sq in sub_qs_res.scalars().all()]

        # 2. Sources & contents
        sources_res = await self.session.execute(
            select(ResearchSource)
            .where(ResearchSource.research_run_id == run.id)
            .options(selectinload(ResearchSource.contents))
        )
        raw_sources = sources_res.scalars().all()
        source_responses: List[SourceResponse] = []
        source_map = {}

        for s in raw_sources:
            source_map[s.id] = s
            cnt_resp = None
            if s.contents:
                first_cnt = s.contents[0]
                cnt_resp = ContentResponse.model_validate(first_cnt)
            s_resp = SourceResponse(
                id=s.id,
                research_run_id=s.research_run_id,
                title=s.title,
                url=s.url,
                publisher=s.publisher,
                author=s.author,
                published_at=s.published_at,
                retrieved_at=s.retrieved_at,
                source_type=s.source_type,
                credibility_score=s.credibility_score,
                metadata_json=s.metadata_json,
                created_at=s.created_at,
                content=cnt_resp,
            )
            source_responses.append(s_resp)

        # 3. Findings & Evidence
        findings_res = await self.session.execute(
            select(Finding)
            .where(Finding.research_run_id == run.id)
            .options(selectinload(Finding.evidences))
        )
        raw_findings = findings_res.scalars().all()
        finding_responses: List[FindingResponse] = []
        finding_map = {}

        for f in raw_findings:
            finding_map[f.id] = f
            ev_responses = []
            for ev in f.evidences:
                src = source_map.get(ev.source_id)
                ev_resp = EvidenceResponse(
                    id=ev.id,
                    finding_id=ev.finding_id,
                    source_id=ev.source_id,
                    source_content_id=ev.source_content_id,
                    excerpt=ev.excerpt,
                    relevance_score=ev.relevance_score,
                    evidence_type=ev.evidence_type,
                    created_at=ev.created_at,
                    source_title=src.title if src else None,
                    source_url=src.url if src else None,
                )
                ev_responses.append(ev_resp)

            f_resp = FindingResponse(
                id=f.id,
                research_run_id=f.research_run_id,
                statement=f.statement,
                finding_type=f.finding_type,
                confidence=f.confidence,
                importance=f.importance,
                created_at=f.created_at,
                updated_at=f.updated_at,
                evidences=ev_responses,
            )
            finding_responses.append(f_resp)

        # 4. Contradictions
        contradictions_res = await self.session.execute(
            select(Contradiction).where(Contradiction.research_run_id == run.id)
        )
        raw_contradictions = contradictions_res.scalars().all()
        contradiction_responses: List[ContradictionResponse] = []

        for c in raw_contradictions:
            fa = finding_map.get(c.finding_a_id)
            fb = finding_map.get(c.finding_b_id)
            c_resp = ContradictionResponse(
                id=c.id,
                research_run_id=c.research_run_id,
                finding_a_id=c.finding_a_id,
                finding_b_id=c.finding_b_id,
                finding_a_statement=fa.statement if fa else None,
                finding_b_statement=fb.statement if fb else None,
                description=c.description,
                severity=c.severity,
                resolution_status=c.resolution_status,
                resolution_notes=c.resolution_notes,
                created_at=c.created_at,
            )
            contradiction_responses.append(c_resp)

        # 5. Conclusions
        conclusions_res = await self.session.execute(
            select(Conclusion)
            .where(Conclusion.research_run_id == run.id)
            .options(selectinload(Conclusion.findings))
        )
        raw_conclusions = conclusions_res.scalars().all()
        conclusion_responses: List[ConclusionResponse] = []

        for conc in raw_conclusions:
            f_ids = [f.id for f in conc.findings]
            conc_resp = ConclusionResponse(
                id=conc.id,
                research_run_id=conc.research_run_id,
                statement=conc.statement,
                confidence=conc.confidence,
                created_at=conc.created_at,
                updated_at=conc.updated_at,
                finding_ids=f_ids,
            )
            conclusion_responses.append(conc_resp)

        total_ev_count = sum(len(f.evidences) for f in raw_findings)
        counts = RunCountsSchema(
            sub_questions=len(sub_qs),
            sources=len(source_responses),
            findings=len(finding_responses),
            evidence=total_ev_count,
            contradictions=len(contradiction_responses),
            conclusions=len(conclusion_responses),
        )

        return ResearchRunDetailResponse(
            id=run.id,
            question_id=run.question_id,
            question_text=question_text,
            project_id=project_id,
            project_name=project_name,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
            metadata_json=run.metadata_json,
            created_at=run.created_at,
            counts=counts,
            sub_questions=sub_qs,
            sources=source_responses,
            findings=finding_responses,
            contradictions=contradiction_responses,
            conclusions=conclusion_responses,
        )

    async def get_run_traceability(self, run_id: UUID) -> RunTraceabilityResponse:
        """Returns structured evidence graph mapping Conclusion -> Findings -> Evidence -> Source -> Content."""
        detail = await self.get_run_details(run_id)
        
        # Build node schemas per conclusion
        provenance_nodes: List[TraceabilityNodeSchema] = []
        finding_by_id = {f.id: f for f in detail.findings}

        for conc in detail.conclusions:
            member_findings = [finding_by_id[fid] for fid in conc.finding_ids if fid in finding_by_id]
            node = TraceabilityNodeSchema(
                conclusion_id=conc.id,
                conclusion_statement=conc.statement,
                conclusion_confidence=conc.confidence,
                findings=member_findings,
            )
            provenance_nodes.append(node)

        return RunTraceabilityResponse(
            run_id=detail.id,
            question_id=detail.question_id,
            question_text=detail.question_text,
            status=detail.status,
            execution_metadata=detail.metadata_json,
            provenance_graph=provenance_nodes,
        )

    async def _to_response(self, run: ResearchRun) -> ResearchRunResponse:
        sub_q_count = (
            await self.session.scalar(
                select(func.count(ResearchSubQuestion.id)).where(ResearchSubQuestion.research_run_id == run.id)
            )
        ) or 0

        source_count = (
            await self.session.scalar(
                select(func.count(ResearchSource.id)).where(ResearchSource.research_run_id == run.id)
            )
        ) or 0

        finding_count = (
            await self.session.scalar(
                select(func.count(Finding.id)).where(Finding.research_run_id == run.id)
            )
        ) or 0

        evidence_count = (
            await self.session.scalar(
                select(func.count(Evidence.id))
                .join(Finding, Evidence.finding_id == Finding.id)
                .where(Finding.research_run_id == run.id)
            )
        ) or 0

        contradiction_count = (
            await self.session.scalar(
                select(func.count(Contradiction.id)).where(Contradiction.research_run_id == run.id)
            )
        ) or 0

        conclusion_count = (
            await self.session.scalar(
                select(func.count(Conclusion.id)).where(Conclusion.research_run_id == run.id)
            )
        ) or 0

        counts = RunCountsSchema(
            sub_questions=sub_q_count,
            sources=source_count,
            findings=finding_count,
            evidence=evidence_count,
            contradictions=contradiction_count,
            conclusions=conclusion_count,
        )

        return ResearchRunResponse(
            id=run.id,
            question_id=run.question_id,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
            metadata_json=run.metadata_json,
            created_at=run.created_at,
            counts=counts,
        )

    async def delete_run(self, run_id: UUID) -> None:
        run = await self.run_repo.get_by_id(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ResearchRun '{run_id}' not found.",
            )
        await self.run_repo.delete(run)
