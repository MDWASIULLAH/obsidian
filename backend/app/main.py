"""
OBSIDIAN — FastAPI Application Factory.

This is the main entry point for the backend API server.
It configures middleware, mounts routers, and manages the
lifecycle of all external connections (DB, Redis, Neo4j, Qdrant).
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle manager."""
    logger.info("Starting OBSIDIAN", env=settings.app_env.value)

    from app.models.database import Base, engine
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.rag import RAGService
    from app.models import github_event  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        app.state.knowledge_graph = kg
        logger.info("Neo4j Knowledge Graph connected")
    except Exception as exc:
        logger.warning("Neo4j unavailable, running without knowledge graph", error=str(exc))
        app.state.knowledge_graph = None

    try:
        rag = RAGService()
        await rag.initialize()
        app.state.rag = rag
        logger.info("Qdrant RAG service connected")
    except Exception as exc:
        logger.warning("Qdrant unavailable, running without RAG", error=str(exc))
        app.state.rag = None

    logger.info("OBSIDIAN ready", port=8000)
    yield

    logger.info("Shutting down OBSIDIAN")
    if getattr(app.state, "knowledge_graph", None):
        try:
            await app.state.knowledge_graph.close()
        except Exception as exc:
            logger.warning("Error closing Neo4j connection", error=str(exc))
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="OBSIDIAN",
        description="Autonomous AI Security Engineering Organization for the Secure Software Development Lifecycle.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "https://obsidian-rwnd.vercel.app",
    ]
    if settings.frontend_url and settings.frontend_url not in allowed_origins:
        allowed_origins.append(settings.frontend_url)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def add_timing_header(request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
        return response

    from app.api.router import api_router
    from app.api.auth import router as auth_router
    from app.api.onboarding import router as onboarding_router
    from app.api.live_scan import router as live_scan_router

    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(onboarding_router, prefix="/api/v1")
    application.include_router(api_router, prefix="/api/v1")
    application.include_router(live_scan_router, prefix="/api/v1")

    @application.get("/health", tags=["health"])
    async def health_check():
        return {"status": "healthy", "version": "1.0.0", "app": "OBSIDIAN"}

    return application


app = create_app()
