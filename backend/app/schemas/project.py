from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Project name")
    description: str | None = Field(None, max_length=2000, description="Detailed project description")
    research_topic: str = Field(..., min_length=2, max_length=255, description="Core research topic")
    industry: str | None = Field(None, max_length=100, description="Industry sector")
    status: str = Field("draft", description="Status: draft, active, completed, failed")


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)
    research_topic: str | None = Field(None, min_length=2, max_length=255)
    industry: str | None = Field(None, max_length=100)
    status: str | None = Field(None)


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    research_topic: str
    industry: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
