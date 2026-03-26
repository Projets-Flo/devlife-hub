"""
DevLife Hub — API FastAPI
Point d'entrée principal.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.common.config import settings
from src.common.database import create_all_tables
from src.common.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage, nettoyage à l'arrêt."""
    logger.info(f"Démarrage DevLife Hub API — env: {settings.app_env}")
    create_all_tables()
    yield
    logger.info("Arrêt de l'API")


app = FastAPI(
    title="DevLife Hub API",
    description="Job search, sport tracking & ML pipeline",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


@app.get("/")
async def root() -> dict:
    return {
        "message": "DevLife Hub API",
        "docs": "/docs",
        "modules": ["jobs", "sport", "coach", "ml"],
    }


# Les routers seront ajoutés ici au fur et à mesure :
# from src.api.routes import jobs, sport, coach, ml
# app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
# app.include_router(sport.router, prefix="/sport", tags=["Sport"])
# app.include_router(coach.router, prefix="/coach", tags=["Coach"])
# app.include_router(ml.router, prefix="/ml", tags=["ML"])
