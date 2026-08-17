from typing import Sequence
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sub_question import ResearchSubQuestion
from app.repositories.base import BaseRepository


class SubQuestionRepository(BaseRepository[ResearchSubQuestion]):
    def __init__(self, session: AsyncSession):
        super().__init__(ResearchSubQuestion, session)

    async def list_by_run_id(self, run_id: UUID) -> Sequence[ResearchSubQuestion]:
        stmt = (
            select(ResearchSubQuestion)
            .where(ResearchSubQuestion.research_run_id == run_id)
            .order_by(ResearchSubQuestion.sequence_number.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
