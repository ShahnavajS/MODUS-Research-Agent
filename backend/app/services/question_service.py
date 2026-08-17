from typing import Sequence
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.question import ResearchQuestion
from app.repositories.project_repository import ProjectRepository
from app.repositories.question_repository import QuestionRepository
from app.schemas.question import QuestionCreate, QuestionUpdate


class QuestionService:
    def __init__(self, session: AsyncSession):
        self.project_repo = ProjectRepository(session)
        self.question_repo = QuestionRepository(session)

    async def create_question(self, project_id: UUID, data: QuestionCreate) -> ResearchQuestion:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot add question: ResearchProject '{project_id}' not found.",
            )
        question = ResearchQuestion(
            project_id=project_id,
            question=data.question,
            status=data.status,
        )
        return await self.question_repo.create(question)

    async def get_question(self, question_id: UUID) -> ResearchQuestion:
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ResearchQuestion with id '{question_id}' not found.",
            )
        return question

    async def list_questions(self, project_id: UUID, limit: int = 100, offset: int = 0) -> Sequence[ResearchQuestion]:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ResearchProject '{project_id}' not found.",
            )
        return await self.question_repo.list_by_project_id(project_id, limit=limit, offset=offset)

    async def update_question(self, question_id: UUID, data: QuestionUpdate) -> ResearchQuestion:
        question = await self.get_question(question_id)
        if data.question is not None:
            question.question = data.question
        if data.status is not None:
            question.status = data.status
        return await self.question_repo.update(question)

    async def delete_question(self, question_id: UUID) -> None:
        question = await self.get_question(question_id)
        await self.question_repo.delete(question)
