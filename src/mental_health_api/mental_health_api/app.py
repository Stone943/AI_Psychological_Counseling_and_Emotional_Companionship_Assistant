"""FastAPI application factory for mental_health_api.

Creates the ASGI application with all middlewares, routes, and exception handlers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mental_health_api.config import Settings
from mental_health_api.errors import AppError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown hooks."""
    # Startup: validate settings, connect pools
    _ = app.state.settings  # eagerly validate
    yield
    # Shutdown: disconnect pools
    pass


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Args:
        settings: Application settings. If None, loads from environment.

    Returns:
        Configured FastAPI application.
    """
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Mental Health API",
        description="AI Psychological Counseling and Emotional Companionship Assistant — Backend API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    app.state.settings = settings

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register exception handlers
    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "request_id": request.headers.get("X-Request-ID", ""),
                "retryable": exc.retryable,
                "client_action": exc.client_action,
            },
        )

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "version": "0.1.0"}

    return app
