"""# ruff: noqa: E501
Crisis resource routes — anonymous access, region-based resources, offline bundle.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/v1/crisis-resources", tags=["crisis"])


@router.get("")
async def get_crisis_resources(request: Request, region: str = "CN-mainland", language: str = "zh-CN"):
    """Get crisis resources for a region. Anonymous access allowed."""
    return {
        "region": region,
        "language": language,
        "bundle_version": "v1",
        "resource_status": "active",
        "resources": [
            {"type": "phone", "label": "Police", "number": "110"},
            {"type": "phone", "label": "Ambulance", "number": "120"},
            {"type": "phone", "label": "Mental Health Hotline", "number": "12356"},
        ],
    }
