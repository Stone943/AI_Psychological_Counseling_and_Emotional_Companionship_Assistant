"""Strict validation of the active content review record used for crisis signing."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
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
EXPECTED_CONTENT_TUPLES = frozenset(
    {
        *(
            ("knowledge", content_id, "v1")
            for content_id in (
                "emotion_basics",
                "anxiety_self_help",
                "stress_management",
                "sleep_and_emotions",
                "when_to_seek_help",
                "how_counseling_works",
                "crisis_support_guide",
                "mindfulness_cbt_basics",
            )
        ),
        *(
            ("exercise", content_id, "v1")
            for content_id in (
                "breathing_awareness",
                "body_scan",
                "five_senses_grounding",
                "three_minute_mindfulness",
                "cbt_emotion_record",
                "cbt_automatic_thought",
                "cbt_evidence_review",
                "cbt_alternative_thought",
                "cbt_small_step_plan",
                "stress_relief",
                "sleep_relaxation",
                "emotion_stabilization",
            )
        ),
        ("assessment", "PHQ9", "v1"),
        ("assessment", "GAD7", "v1"),
        ("crisis_resource", "china-mainland", "v1"),
        ("safety_ui", "ui-manifest", "v1"),
    }
)
SOURCE_REGISTER_PATH = Path("sources/source-register.json")
AUTHOR_HANDOFF_PATH = Path("reviews/content-author-handoff.v1.json")
A_HANDOFF_PATH = Path("reviews/a-content-safety-review.v1.json")
INDEPENDENT_HANDOFF_PATH = Path("reviews/independent-domain-review.v1.json")
HANDOFF_FIELDS = {"schema_version", "confirmation_ref", "confirmation_checksum", "items"}
CONTENT_KEY_FIELDS = {"content_type", "content_id", "content_version"}
AUTHOR_ITEM_FIELDS = CONTENT_KEY_FIELDS | {"author_id", "draft_checksum", "source_refs", "authored_at"}
REVIEW_ITEM_FIELDS = CONTENT_KEY_FIELDS | {
    "reviewer_id",
    "reviewed_at",
    "decision",
    "input_checksum",
    "output_checksum",
}
INDEPENDENT_ITEM_FIELDS = REVIEW_ITEM_FIELDS | {"qualification_ref", "qualification_checksum"}
SOURCE_FIELDS = {
    "source_id",
    "authority",
    "title",
    "locator",
    "license_basis",
    "region",
    "retrieved_at",
    "version",
    "checksum",
}


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


def validate_register(review_register: list[dict[str, Any]], *, evidence_root: str | Path = Path("content")) -> None:
    if len(review_register) != 24 or any(
        not isinstance(row, dict) or set(row) != RECORD_FIELDS for row in review_register
    ):
        raise ValueError("active review register must contain 24 strict records")
    review_ids = [row["review_record_id"] for row in review_register]
    tuples = [(row["content_type"], row["content_id"], row["content_version"]) for row in review_register]
    if len(set(review_ids)) != 24 or len(set(tuples)) != 24:
        raise ValueError("active review register contains duplicate identities")
    if set(tuples) != EXPECTED_CONTENT_TUPLES:
        raise ValueError("active review register does not contain the frozen 24 content tuples")
    for row in review_register:
        validate_review_record(row)
    _validate_external_evidence(review_register, Path(evidence_root))


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


def _validate_external_evidence(review_register: list[dict[str, Any]], root: Path) -> None:
    register_by_key = {_content_key(row): row for row in review_register}
    source_register = _load_json_object(root, SOURCE_REGISTER_PATH)
    if set(source_register) != {"schema_version", "sources"} or source_register.get("schema_version") != "v1":
        raise ValueError("source register schema is invalid")
    sources = source_register.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("source register is empty")
    source_ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != SOURCE_FIELDS:
            raise ValueError("source record shape is invalid")
        source_id = source.get("source_id")
        locator = source.get("locator")
        if (
            not isinstance(source_id, str)
            or not source_id
            or source_id in source_ids
            or not all(isinstance(source.get(field), str) and source[field].strip() for field in SOURCE_FIELDS)
            or CHECKSUM_PATTERN.fullmatch(str(source.get("checksum"))) is None
            or not isinstance(locator, str)
            or "example.com" in locator.lower()
            or "todo" in locator.lower()
            or _parse_utc(source.get("retrieved_at"), "retrieved_at") > datetime.now(UTC)
        ):
            raise ValueError("source record is not releasable")
        source_ids.add(source_id)
    referenced_sources = {source for row in review_register for source in row["source_refs"]}
    if not referenced_sources.issubset(source_ids):
        raise ValueError("review register contains unresolved source references")

    author_handoff = _load_handoff(root, AUTHOR_HANDOFF_PATH, "content-author-handoff.v1")
    a_handoff = _load_handoff(root, A_HANDOFF_PATH, "a-content-safety-review.v1")
    independent_handoff = _load_handoff(root, INDEPENDENT_HANDOFF_PATH, "independent-domain-review.v1")
    _validate_author_items(author_handoff["items"], register_by_key)
    _validate_review_items(a_handoff["items"], register_by_key, stage_index=0, root=root)
    _validate_review_items(independent_handoff["items"], register_by_key, stage_index=1, root=root, independent=True)


def _load_handoff(root: Path, relative_path: Path, schema_version: str) -> dict[str, Any]:
    handoff = _load_json_object(root, relative_path)
    if set(handoff) != HANDOFF_FIELDS or handoff.get("schema_version") != schema_version:
        raise ValueError(f"{schema_version} handoff schema is invalid")
    items = handoff.get("items")
    if not isinstance(items, list) or len(items) != 24:
        raise ValueError(f"{schema_version} must cover the frozen 24 content tuples")
    _verify_referenced_file(
        root,
        handoff.get("confirmation_ref"),
        handoff.get("confirmation_checksum"),
        f"{schema_version} confirmation",
    )
    return handoff


def _validate_author_items(items: list[object], register: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    mapped = _strict_item_map(items, AUTHOR_ITEM_FIELDS, "author")
    if set(mapped) != EXPECTED_CONTENT_TUPLES:
        raise ValueError("author handoff does not cover the frozen 24 content tuples")
    for key, item in mapped.items():
        record = register[key]
        if (
            item.get("author_id") != record["draft_author_id"]
            or item.get("draft_checksum") != record["content_checksum"]
            or item.get("source_refs") != record["source_refs"]
            or _parse_utc(item.get("authored_at"), "authored_at") > datetime.now(UTC)
        ):
            raise ValueError("author handoff does not match the active review record")


def _validate_review_items(
    items: list[object],
    register: dict[tuple[str, str, str], dict[str, Any]],
    *,
    stage_index: int,
    root: Path,
    independent: bool = False,
) -> None:
    fields = INDEPENDENT_ITEM_FIELDS if independent else REVIEW_ITEM_FIELDS
    mapped = _strict_item_map(items, fields, "independent" if independent else "content-safety")
    if set(mapped) != EXPECTED_CONTENT_TUPLES:
        raise ValueError("review handoff does not cover the frozen 24 content tuples")
    for key, item in mapped.items():
        record = register[key]
        stage = record["review_chain"][stage_index]
        if (
            item.get("reviewer_id") != stage["reviewer_id"]
            or item.get("reviewed_at") != stage["reviewed_at"]
            or item.get("decision") != "approved"
            or item.get("input_checksum") != record["content_checksum"]
            or item.get("output_checksum") != record["content_checksum"]
        ):
            raise ValueError("review handoff does not match the active review chain")
        if independent:
            if item.get("qualification_ref") != stage["qualification_ref"]:
                raise ValueError("independent qualification reference does not match the review chain")
            qualification_ref = item.get("qualification_ref")
            qualification_checksum = item.get("qualification_checksum")
            if qualification_ref is None and qualification_checksum is None:
                if record["content_type"] in HIGH_RISK_CONTENT_TYPES:
                    raise ValueError("high-risk content lacks qualification evidence")
            else:
                _verify_referenced_file(
                    root,
                    qualification_ref,
                    qualification_checksum,
                    "independent reviewer qualification",
                )


def _strict_item_map(items: list[object], fields: set[str], label: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    mapped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != fields:
            raise ValueError(f"{label} handoff item shape is invalid")
        key = _content_key(item)
        if key in mapped:
            raise ValueError(f"{label} handoff contains duplicate content tuples")
        mapped[key] = item
    return mapped


def _content_key(value: dict[str, Any]) -> tuple[str, str, str]:
    fields = (value.get("content_type"), value.get("content_id"), value.get("content_version"))
    if not all(isinstance(item, str) and item for item in fields):
        raise ValueError("content tuple is invalid")
    return fields  # type: ignore[return-value]


def _load_json_object(root: Path, relative_path: Path) -> dict[str, Any]:
    path = _resolve_evidence_path(root, relative_path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"required review evidence is unavailable: {relative_path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"required review evidence is not an object: {relative_path}")
    return value


def _verify_referenced_file(root: Path, reference: object, checksum: object, label: str) -> None:
    if (
        not isinstance(reference, str)
        or not reference
        or not isinstance(checksum, str)
        or CHECKSUM_PATTERN.fullmatch(checksum) is None
    ):
        raise ValueError(f"{label} reference is invalid")
    path = _resolve_evidence_path(root, Path(reference))
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError(f"{label} evidence is unavailable") from exc
    if actual != checksum:
        raise ValueError(f"{label} checksum mismatch")


def _resolve_evidence_path(root: Path, relative_path: Path) -> Path:
    if relative_path.is_absolute():
        raise ValueError("review evidence paths must be relative to the content root")
    resolved_root = root.resolve()
    resolved = (resolved_root / relative_path).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("review evidence path escapes the content root")
    return resolved
