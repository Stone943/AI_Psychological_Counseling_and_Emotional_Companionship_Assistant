"""# ruff: noqa: E501
Crisis resource routes — anonymous access, region-based resources, offline bundle.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request

from mental_health_api.crisis.signing import verify_trusted_bundle

router = APIRouter(prefix="/v1/crisis-resources", tags=["crisis"])
SUPPORTED_REGION = "CN-mainland"
SUPPORTED_LANGUAGE = "zh-CN"


@router.get("")
async def get_crisis_resources(
    request: Request, region: str = "CN-mainland", language: str = "zh-CN"
) -> dict[str, object]:
    """Get crisis resources for a region. Anonymous access allowed."""
    supported_request = region == SUPPORTED_REGION and language == SUPPORTED_LANGUAGE
    content_dir = request.app.state.settings.content_dir
    bundle_path = content_dir / "crisis" / "offline-bundle.zh-CN.v1.json"
    keys_path = content_dir / "crisis" / "trusted-keys.json"
    try:
        if not supported_request:
            raise FileNotFoundError("no reviewed bundle exists for the requested locale")
        bundle: Any = json.loads(bundle_path.read_text(encoding="utf-8"))
        registry: Any = json.loads(keys_path.read_text(encoding="utf-8"))
        if not isinstance(bundle, dict) or not isinstance(registry, dict):
            raise TypeError("crisis artifact root must be an object")
        valid, reason = verify_trusted_bundle(bundle, registry)
        if valid:
            return {"region": SUPPORTED_REGION, "language": SUPPORTED_LANGUAGE, **bundle}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        reason = (
            "bundle_missing"
            if not supported_request or not bundle_path.exists() or not keys_path.exists()
            else "checksum_failed"
        )
    return {
        "region": SUPPORTED_REGION,
        "language": SUPPORTED_LANGUAGE,
        "bundle_version": "builtin-v1",
        "resource_status": "degraded",
        "degraded_reason": reason or "checksum_failed",
        "signature_alg": "Ed25519",
        "canonicalization": "RFC8785-JCS",
        "key_id": None,
        "verified_at": None,
        "expires_at": None,
        "sha256": None,
        "signature": None,
        "resources": [
            {"type": "phone", "label": "Police", "number": "110"},
            {"type": "phone", "label": "Ambulance", "number": "120"},
            {"type": "phone", "label": "Mental Health Hotline", "number": "12356"},
        ],
    }
