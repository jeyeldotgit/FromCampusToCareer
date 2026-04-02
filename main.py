"""FastAPI application entry point for the From Campus to Career API.

Two processes run from this codebase:
- api-service  : this file (uvicorn main:app)
- worker-service: worker.py (python worker.py)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from modules.auth.router import router as auth_router
from modules.gap_and_roadmap.router import router as gap_router
from modules.ingestion.router import router as ingestion_router
from modules.student_profile.router import router as student_router
from modules.taxonomy_admin.router import router as taxonomy_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield


app = FastAPI(
    title="From Campus to Career API",
    version="1.0.0",
    description="Career readiness analysis for Filipino university students",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(student_router)
app.include_router(taxonomy_router)
app.include_router(gap_router)
app.include_router(ingestion_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
