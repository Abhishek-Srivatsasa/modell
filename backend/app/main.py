from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, sessions, verification, websocket as ws_router, audio_websocket as audio_ws_router
from db.database import Base, check_db_connection, engine


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title="Pratyaksha API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(verification.router, prefix="/api/v1/verify", tags=["verification"])
    app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
    app.include_router(ws_router.router, tags=["websocket"])

    @app.on_event("startup")
    async def on_startup() -> None:
        """Initialize database schema on startup."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, Any]:
        """Return detailed health status of core dependencies."""
        settings_local = get_settings()

        db_ok = await check_db_connection()
        db_status = "connected" if db_ok else "error"

        redis_status = "error"
        try:
            redis_client = aioredis.from_url(settings_local.redis_url)
            if await redis_client.ping():
                redis_status = "connected"
        except Exception:
            redis_status = "error"

        overall_status = "ok" if db_status == "connected" and redis_status == "connected" else "degraded"

        return {
            "status": overall_status,
            "db": db_status,
            "redis": redis_status,
            "environment": settings_local.environment,
            "mock_models": settings_local.use_mock_models,
        }

    return app


app = create_app()

