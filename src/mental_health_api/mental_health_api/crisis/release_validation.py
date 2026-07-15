"""Strict validation of the active content review record used for crisis signing."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

from mental_health_api.crisis.jcs import canonicalize

RECORD_FIELDS = {
    "review_record_id",
    "content_type",
    "content_id",
    "content_version",
    "draft_author_id",
    "review_chain",
    "release_decision",
    "source_refs",
    "content_checksum",
    "next_review_at",
}
EXPECTED_REVIEWER_ROLES = (
    "member_a_content_safety_reviewer",
    "independent_domain_reviewer",
    "member_b_release_validator",
)
STAGE_FIELDS = {
    "reviewer_id",
    "reviewer_role",
    "qualification_ref",
    "reviewed_at",
    "decision",
    "input_checksum",
}
HIGH_RISK_CONTENT_TYPES = frozenset({"assessment", "crisis_resource", "safety_ui"})
CHECKSUM_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def validate_release(source: dict[str, Any], review_register: list[dict[str, Any]]) -> None:
    review_id = source.get("review_record_id")
    claimed_checksum = source.get("checksum")
    if not isinstance(review_id, str) or not isinstance(claimed_checksum, str):
        raise ValueError("crisis source lacks release proof")
    unsigned_source = {key: value for key, value in source.items() if key != "checksum"}
    if claimed_checksum != hashlib.sha256(canonicalize(unsigned_source)).hexdigest():
        raise ValueError("crisis source checksum mismatch")
    matches = [row for row in review_register if row.get("review_record_id") == review_id]
    if len(matches) != 1:
        raise ValueError("crisis source needs one active review record")
    record = matches[0]
    validate_review_record(record)
    chain = record.get("review_chain")
    if (
        set(record) != RECORD_FIELDS
        or record.get("content_type") != "crisis_resource"
        or record.get("release_decision") != "approved"
        or record.get("content_id") != source.get("content_id")
        or record.get("content_version") != source.get("version")
        or record.get("content_checksum") != claimed_checksum
        or record.get("source_refs") != source.get("source_refs")
        or not isinstance(record.get("source_refs"), list)
        or not record["source_refs"]
        or not isinstance(chain, list)
        or len(chain) != 3
    ):
        raise ValueError("crisis review record is not an approved release")
    if any(stage["input_checksum"] != claimed_checksum for stage in chain):
        raise ValueError("crisis review checksum continuity failed")


def validate_register(review_register: list[dict[str, Any]]) -> None:
    if len(review_register) != 24 or any(
        not isinstance(row, dict) or set(row) != RECORD_FIELDS for row in review_register
    ):
        raise ValueError("active review register must contain 24 strict records")
    review_ids = [row["review_record_id"] for row in review_register]
    tuples = [(row["content_type"], row["content_id"], row["content_version"]) for row in review_register]
    if len(set(review_ids)) != 24 or len(set(tuples)) != 24:
        raise ValueError("active review register contains duplicate identities")
    expected_counts = {
        "knowledge": 8,
        "exercise": 12,
        "assessment": 2,
        "crisis_resource": 1,
        "safety_ui": 1,
    }
    actual_counts = {content_type: 0 for content_type in expected_counts}
    for row in review_register:
        if row["content_type"] not in actual_counts:
            raise ValueError("active review register contains an unknown content type")
        validate_review_record(row)
        actual_counts[row["content_type"]] += 1
    if actual_counts != expected_counts:
        raise ValueError("active review register content counts are invalid")


def validate_review_record(record: dict[str, Any]) -> None:
    chain = record.get("review_chain")
    checksum = record.get("content_checksum")
    source_refs = record.get("source_refs")
    if (
        set(record) != RECORD_FIELDS
        or record.get("release_decision") != "approved"
        or not isinstance(record.get("review_record_id"), str)
        or not record["review_record_id"]
        or not isinstance(record.get("content_id"), str)
        or not record["content_id"]
        or not isinstance(record.get("content_version"), str)
        or not record["content_version"]
        or not isinstance(record.get("draft_author_id"), str)
        or not record["draft_author_id"]
        or not isinstance(source_refs, list)
        or not source_refs
        or not all(isinstance(item, str) and item for item in source_refs)
        or not isinstance(checksum, str)
        or CHECKSUM_PATTERN.fullmatch(checksum) is None
        or not isinstance(chain, list)
        or len(chain) != 3
    ):
        raise ValueError("active review record shape or status is invalid")
    if any(not isinstance(stage, dict) or set(stage) != STAGE_FIELDS for stage in chain):
        raise ValueError("active review chain shape is invalid")
    if any(stage.get("decision") != "approved" or stage.get("input_checksum") != checksum for stage in chain):
        raise ValueError("active review chain decision/checksum continuity is invalid")
    reviewers = [stage["reviewer_id"] for stage in chain]
    if (
        not all(isinstance(reviewer, str) and reviewer for reviewer in reviewers)
        or len(set(reviewers)) != 3
        or record["draft_author_id"] in reviewers
    ):
        raise ValueError("active review identities are not independent")
    if tuple(stage["reviewer_role"] for stage in chain) != EXPECTED_REVIEWER_ROLES:
        raise ValueError("active review role order is invalid")
    qualification = chain[1]["qualification_ref"]
    if record["content_type"] in HIGH_RISK_CONTENT_TYPES and (
        not isinstance(qualification, str) or not qualification.strip()
    ):
        raise ValueError("high-risk independent review qualification is required")
    if qualification is not None and (not isinstance(qualification, str) or not qualification.strip()):
        raise ValueError("independent review qualification is malformed")
    reviewed_times = [_parse_utc(stage["reviewed_at"], "reviewed_at") for stage in chain]
    now = datetime.now(UTC)
    next_review_at = _parse_utc(record.get("next_review_at"), "next_review_at")
    if (
        reviewed_times != sorted(reviewed_times)
        or any(value > now for value in reviewed_times)
        or next_review_at <= now
        or reviewed_times[-1] >= next_review_at
    ):
        raise ValueError("active review timestamps are invalid")


def _parse_utc(value: object, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"{field_name} must be a UTC timestamp")
    return parsed.astimezone(UTC)
