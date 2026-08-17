from typing import Sequence
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.run import ResearchRun
from app.repositories.base import BaseRepository


class RunRepository(BaseRepository[ResearchRun]):
    def __init__(self, session: AsyncSession):
        super().__init__(ResearchRun, session)

    async def list_by_question_id(self, question_id: UUID, limit: int = 50, offset: int = 0) -> Sequence[ResearchRun]:
        stmt = (
            select(ResearchRun)
            .where(ResearchRun.question_id == question_id)
            .order_by(ResearchRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
