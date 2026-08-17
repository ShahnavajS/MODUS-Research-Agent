from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    status: str = Field(..., description="Database status e.g. ok or error")
    dialect: str = Field(..., description="Database engine dialect e.g. sqlite or postgresql")


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Application health status")
    version: str = Field("0.1.0", description="API version")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Current server ISO timestamp")
    database: DatabaseHealth = Field(..., description="Database connectivity status")
