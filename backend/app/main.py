from contextlib import asynccontextmanager
import sys

# Ensure UTF-8 output encoding for Windows stdout/stderr streams
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.database import async_engine
from app.core.logging import logger, setup_logging
from app.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Initializing MODUS Enterprise Research Intelligence Platform API...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("Shutting down API server...")


app = FastAPI(
    title="MODUS Enterprise Research Intelligence Platform API",
    description="Backend API for automated enterprise research orchestration, evidence extraction, and traceable intelligence generation.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "app": "Enterprise Research Intelligence Platform",
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
    }
