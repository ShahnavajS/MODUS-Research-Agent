from typing import Sequence
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.question import ResearchQuestion
from app.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[ResearchQuestion]):
    def __init__(self, session: AsyncSession):
        super().__init__(ResearchQuestion, session)

    async def list_by_project_id(self, project_id: UUID, limit: int = 100, offset: int = 0) -> Sequence[ResearchQuestion]:
        stmt = (
            select(ResearchQuestion)
            .where(ResearchQuestion.project_id == project_id)
            .order_by(ResearchQuestion.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
