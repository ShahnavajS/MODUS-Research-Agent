from typing import Sequence
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import ResearchProject
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[ResearchProject]):
    def __init__(self, session: AsyncSession):
        super().__init__(ResearchProject, session)

    async def list_projects(self, limit: int = 50, offset: int = 0) -> Sequence[ResearchProject]:
        stmt = select(ResearchProject).order_by(ResearchProject.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
