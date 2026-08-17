from typing import Sequence
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import ResearchProject
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.repo = ProjectRepository(session)

    async def create_project(self, data: ProjectCreate) -> ResearchProject:
        project = ResearchProject(
            name=data.name,
            description=data.description,
            research_topic=data.research_topic,
            industry=data.industry,
            status=data.status,
        )
        return await self.repo.create(project)

    async def get_project(self, project_id: UUID) -> ResearchProject:
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ResearchProject with id '{project_id}' not found.",
            )
        return project

    async def list_projects(self, limit: int = 50, offset: int = 0) -> Sequence[ResearchProject]:
        return await self.repo.list_projects(limit=limit, offset=offset)

    async def update_project(self, project_id: UUID, data: ProjectUpdate) -> ResearchProject:
        project = await self.get_project(project_id)
        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description
        if data.research_topic is not None:
            project.research_topic = data.research_topic
        if data.industry is not None:
            project.industry = data.industry
        if data.status is not None:
            project.status = data.status
        return await self.repo.update(project)

    async def delete_project(self, project_id: UUID) -> None:
        project = await self.get_project(project_id)
        await self.repo.delete(project)
