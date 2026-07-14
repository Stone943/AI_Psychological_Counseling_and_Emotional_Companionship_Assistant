# ruff: noqa: E501
"""Knowledge REST routes — search, categories, detail."""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])


@router.get("/categories")
async def list_categories(request: Request):
    """List knowledge categories with article counts."""
    return {"categories": []}


@router.get("/articles/{article_id}")
async def get_article(article_id: str, request: Request):
    """Get a published knowledge article by ID."""
    raise AppError(
        code="CONTENT_WITHDRAWN",
        message="Content not yet published",
        http_status=410,
        retryable=False,
        client_action="remove_local_copy",
    )


@router.post("/search", status_code=200)
async def search_knowledge(request: Request):
    """Search knowledge base. query in JSON body, not URL."""
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Knowledge search not yet available",
        http_status=503,
        retryable=True,
        client_action="retry",
    )
