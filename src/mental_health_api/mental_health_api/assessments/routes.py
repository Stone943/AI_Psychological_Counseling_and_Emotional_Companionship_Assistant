"""# ruff: noqa: E501
Assessment REST routes — PHQ-9/GAD-7 definitions, submissions, results, history, export, delete.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from mental_health_api.errors import AppError

router = APIRouter(tags=["assessments"])


@router.get("/v1/assessments/{scale}/definitions/{version}")
async def get_definition(scale: str, version: str, request: Request):
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Assessments not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.post("/v1/assessments/{scale}/submissions", status_code=202)
async def submit_assessment(scale: str, request: Request):
    raise AppError(
        code="SERVICE_UNAVAILABLE",
        message="Assessments not yet implemented",
        http_status=503,
        retryable=True,
        client_action="retry",
    )


@router.get("/v1/assessment-results/{assessment_result_id}")
async def get_result(assessment_result_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.get("/v1/assessment-results")
async def list_results(request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.get("/v1/assessment-results/{assessment_result_id}/export")
async def export_result(assessment_result_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )


@router.delete("/v1/assessment-results/{assessment_result_id}", status_code=204)
async def delete_result(assessment_result_id: str, request: Request):
    raise AppError(
        code="AUTH_REQUIRED",
        message="Authentication required",
        http_status=401,
        retryable=False,
        client_action="authenticate",
    )
