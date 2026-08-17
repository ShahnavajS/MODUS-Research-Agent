from fastapi import APIRouter
from app.api import health, projects, questions, runs

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(projects.router)
api_router.include_router(questions.router)
api_router.include_router(runs.router)
