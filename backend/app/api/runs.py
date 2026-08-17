import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.run import (
    ResearchRunCreate,
    ResearchRunDetailResponse,
    ResearchRunResponse,
    RunTraceabilityResponse,
)
from app.services.research_pipeline_service import ResearchPipelineService
from app.services.run_service import RunService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Research Runs"])


@router.post("/questions/{question_id}/runs", response_model=ResearchRunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    question_id: UUID,
    data: ResearchRunCreate,
    db: AsyncSession = Depends(get_db),
):
    service = RunService(db)
    return await service.create_run(question_id, data)


@router.get("/questions/{question_id}/runs", response_model=List[ResearchRunResponse])
async def list_runs_for_question(
    question_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = RunService(db)
    return await service.list_runs_by_question(question_id, limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=ResearchRunResponse)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    service = RunService(db)
    return await service.get_run(run_id)


@router.get("/runs/{run_id}/details", response_model=ResearchRunDetailResponse)
async def get_run_details(run_id: UUID, db: AsyncSession = Depends(get_db)):
    service = RunService(db)
    return await service.get_run_details(run_id)


@router.get("/runs/{run_id}/traceability", response_model=RunTraceabilityResponse)
async def get_run_traceability(run_id: UUID, db: AsyncSession = Depends(get_db)):
    service = RunService(db)
    return await service.get_run_traceability(run_id)


@router.post("/runs/{run_id}/execute", response_model=ResearchRunResponse)
async def execute_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    pipeline_service = ResearchPipelineService(db)
    try:
        executed_run = await pipeline_service.execute_run(run_id)
        run_service = RunService(db)
        return await run_service._to_response(executed_run)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research pipeline execution failed: {str(exc)}",
        )


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    service = RunService(db)
    await service.delete_run(run_id)
