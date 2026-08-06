"""
SENTINEL AI X — FastAPI Application Factory.

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


# ═══════════════════════════════════════════════════════════════════
# Application Lifecycle
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle manager."""
    logger.info("🚀 Starting SENTINEL AI X", env=settings.app_env.value)

    # ── Startup ────────────────────────────────────────────────
    # Import here to avoid circular imports at module level
    from app.models.database import engine, Base
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.rag import RAGService

    # Create tables (in dev; use Alembic migrations in production)
    if settings.debug:
        # Import all models so Base.metadata is fully populated
        from app.models import github_event  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created")

    # Initialize Neo4j knowledge graph
    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        app.state.knowledge_graph = kg
        logger.info("✅ Neo4j Knowledge Graph connected")
    except Exception as e:
        logger.warning("⚠️ Neo4j unavailable, running without knowledge graph", error=str(e))
        app.state.knowledge_graph = None

    # Initialize Qdrant RAG
    try:
        rag = RAGService()
        await rag.initialize()
        app.state.rag = rag
        logger.info("✅ Qdrant RAG service connected")
    except Exception as e:
        logger.warning("⚠️ Qdrant unavailable, running without RAG", error=str(e))
        app.state.rag = None

    logger.info("✅ SENTINEL AI X ready", port=8000)
    yield

    # ── Shutdown ───────────────────────────────────────────────
    logger.info("🛑 Shutting down SENTINEL AI X")
    if app.state.knowledge_graph:
        await app.state.knowledge_graph.close()
    await engine.dispose()
    logger.info("✅ Shutdown complete")


# ═══════════════════════════════════════════════════════════════════
# Application Factory
# ═══════════════════════════════════════════════════════════════════

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    application = FastAPI(
        title="SENTINEL AI X",
        description=(
            "Autonomous AI Security Engineering Organization "
            "for the Secure Software Development Lifecycle."
        ),
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request Timing Middleware ──────────────────────────────
    @application.middleware("http")
    async def add_timing_header(request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response

    # ── Routers ────────────────────────────────────────────────
    from app.api.router import api_router
    from app.api.auth import router as auth_router
    from app.api.onboarding import router as onboarding_router
    from app.api.webhooks import router as webhooks_router
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(onboarding_router, prefix="/api/v1")
    application.include_router(webhooks_router, prefix="/api/v1")
    application.include_router(api_router, prefix="/api/v1")

    # ── Health Check ───────────────────────────────────────────
    @application.get("/health", tags=["health"])
    async def health_check():
        return {
            "status": "healthy",
            "version": "1.0.0",
            "app": "SENTINEL AI X",
        }

    return application


# ── Module-level app instance for uvicorn ──────────────────────────
app = create_app()
