from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.question import QuestionCreate, QuestionResponse, QuestionUpdate
from app.services.question_service import QuestionService

router = APIRouter(tags=["Questions"])


@router.post("/projects/{project_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    project_id: UUID,
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
):
    service = QuestionService(db)
    return await service.create_question(project_id, data)


@router.get("/projects/{project_id}/questions", response_model=List[QuestionResponse])
async def list_questions(
    project_id: UUID,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = QuestionService(db)
    return await service.list_questions(project_id, limit=limit, offset=offset)


@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: UUID, db: AsyncSession = Depends(get_db)):
    service = QuestionService(db)
    return await service.get_question(question_id)


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = QuestionService(db)
    return await service.update_question(question_id, data)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(question_id: UUID, db: AsyncSession = Depends(get_db)):
    service = QuestionService(db)
    await service.delete_question(question_id)


@router.delete("/projects/{project_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_question(project_id: UUID, question_id: UUID, db: AsyncSession = Depends(get_db)):
    service = QuestionService(db)
    await service.delete_question(question_id)
