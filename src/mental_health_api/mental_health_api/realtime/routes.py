# ruff: noqa: E501
"""WebSocket realtime routes — ticket issuance and WS endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from mental_health_api.errors import AppError

router = APIRouter(prefix="/v1/realtime", tags=["realtime"])


@router.post("/tickets", status_code=201)
async def create_ticket(request: Request):
    """Issue a short-lived WebSocket ticket (60s, single-use)."""
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Realtime not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.websocket("")
async def websocket_endpoint(ws: WebSocket):
    """Main WebSocket endpoint for real-time conversation."""
    await ws.accept()
    try:
        while True:
            _ = await ws.receive_text()
            await ws.send_text('{"type":"error","payload":{"code":"SERVICE_UNAVAILABLE"}}')
    except WebSocketDisconnect:
        pass
