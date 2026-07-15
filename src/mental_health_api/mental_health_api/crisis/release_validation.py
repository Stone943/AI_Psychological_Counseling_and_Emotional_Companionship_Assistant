"""Fail-closed validation for the 24-item reviewed content release."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

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
KNOWLEDGE_IDS = (
    "emotion_basics",
    "anxiety_self_help",
    "stress_management",
    "sleep_and_emotions",
    "when_to_seek_help",
    "how_counseling_works",
    "crisis_support_guide",
    "mindfulness_cbt_basics",
)
EXERCISE_IDS = (
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
EXPECTED_CONTENT_TUPLES = frozenset(
    {
        *(("knowledge", content_id, "v1") for content_id in KNOWLEDGE_IDS),
        *(("exercise", content_id, "v1") for content_id in EXERCISE_IDS),
        ("assessment", "PHQ9", "v1"),
        ("assessment", "GAD7", "v1"),
        ("crisis_resource", "china-mainland", "v1"),
        ("safety_ui", "ui-manifest", "v1"),
    }
)
ARTIFACT_PATHS: dict[tuple[str, str, str], Path] = {
    **{
        ("knowledge", content_id, "v1"): Path(f"knowledge/articles/{content_id}.zh-CN.v1.json")
        for content_id in KNOWLEDGE_IDS
    },
    **{("exercise", content_id, "v1"): Path("exercises/manifest.json") for content_id in EXERCISE_IDS},
    ("assessment", "PHQ9", "v1"): Path("assessments/phq9.zh-CN.v1.json"),
    ("assessment", "GAD7", "v1"): Path("assessments/gad7.zh-CN.v1.json"),
    ("crisis_resource", "china-mainland", "v1"): Path("crisis/china-mainland.zh-CN.v1.json"),
    ("safety_ui", "ui-manifest", "v1"): Path("safety/ui-manifest.zh-CN.v1.json"),
}
SOURCE_REGISTER_PATH = Path("sources/source-register.json")
AUTHOR_HANDOFF_PATH = Path("reviews/handoffs/content-author-handoff.v1.json")
A_HANDOFF_PATH = Path("reviews/handoffs/a-content-safety-review.v1.json")
INDEPENDENT_HANDOFF_PATH = Path("reviews/handoffs/independent-domain-review.v1.json")
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
CONFIRMATION_FIELDS = {
    "schema_version",
    "handoff_sha256",
    "signer_id",
    "signer_role",
    "key_id",
    "signed_at",
    "signature",
}
REVIEW_KEY_FIELDS = {
    "key_id",
    "signer_id",
    "signer_role",
    "public_key",
    "not_before",
    "not_after",
    "status",
}
EXPECTED_SIGNER_ROLES = {
    "content-author-handoff.v1": "designated_content_author",
    "a-content-safety-review.v1": "member_a_content_safety_reviewer",
    "independent-domain-review.v1": "independent_domain_reviewer",
}
KNOWLEDGE_MANIFEST_FIELDS = {"schema_version", "items"}
KNOWLEDGE_MANIFEST_ITEM_FIELDS = {"article_id", "path", "checksum"}
QUALIFICATION_FIELDS = {
    "schema_version",
    "holder_id",
    "issuer",
    "qualification_type",
    "issued_at",
    "expires_at",
    "evidence_id",
    "issuer_key_id",
    "signature",
}
SAFETY_ANSWER_IDS = {"safe_now", "not_safe", "unsure"}
SAFETY_ACTION_IDS = {
    "call_110",
    "call_120",
    "call_12356",
    "contact_trusted_person",
    "open_nearest_emergency",
    "recheck_safety",
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
    if (
        record.get("content_type") != "crisis_resource"
        or record.get("release_decision") != "approved"
        or record.get("content_id") != source.get("content_id")
        or record.get("content_version") != source.get("version")
        or record.get("content_checksum") != claimed_checksum
        or record.get("source_refs") != source.get("source_refs")
    ):
        raise ValueError("crisis review record is not an approved release")


def validate_register(
    review_register: list[dict[str, Any]],
    *,
    evidence_root: str | Path = Path("content"),
    trusted_review_keys_path: str | Path | None = None,
    trusted_review_keys_sha256: str | None = None,
) -> None:
    if len(review_register) != 24 or any(
        not isinstance(row, dict) or set(row) != RECORD_FIELDS for row in review_register
    ):
        raise ValueError("active review register must contain 24 strict records")
    review_ids = [row["review_record_id"] for row in review_register]
    tuples = [_content_key(row) for row in review_register]
    if len(set(review_ids)) != 24 or len(set(tuples)) != 24:
        raise ValueError("active review register contains duplicate identities")
    if set(tuples) != EXPECTED_CONTENT_TUPLES:
        raise ValueError("active review register does not contain the frozen 24 content tuples")
    for row in review_register:
        validate_review_record(row)
    root = Path(evidence_root)
    trusted_keys = _load_trusted_review_keys(
        root,
        trusted_review_keys_path=trusted_review_keys_path,
        trusted_review_keys_sha256=trusted_review_keys_sha256,
    )
    _validate_external_evidence(review_register, root, trusted_keys)


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
        any(earlier >= later for earlier, later in zip(reviewed_times, reviewed_times[1:], strict=False))
        or any(value > now for value in reviewed_times)
        or next_review_at <= now
        or reviewed_times[-1] >= next_review_at
    ):
        raise ValueError("active review timestamps are invalid")


def _validate_external_evidence(
    review_register: list[dict[str, Any]], root: Path, trusted_keys: dict[str, Any]
) -> None:
    register = {_content_key(row): row for row in review_register}
    _validate_artifacts(root, register)
    _validate_source_register(root, review_register)

    author_handoff, author_signer = _load_handoff(root, AUTHOR_HANDOFF_PATH, "content-author-handoff.v1", trusted_keys)
    a_handoff, a_signer = _load_handoff(root, A_HANDOFF_PATH, "a-content-safety-review.v1", trusted_keys)
    independent_handoff, independent_signer = _load_handoff(
        root, INDEPENDENT_HANDOFF_PATH, "independent-domain-review.v1", trusted_keys
    )
    authored = _validate_author_items(author_handoff["items"], register, author_signer)
    reviewed_by_a = _validate_review_items(
        a_handoff["items"],
        register,
        stage_index=0,
        root=root,
        signer_id=a_signer,
        after=authored,
        trusted_keys=trusted_keys,
    )
    independently_reviewed = _validate_review_items(
        independent_handoff["items"],
        register,
        stage_index=1,
        root=root,
        signer_id=independent_signer,
        after=reviewed_by_a,
        trusted_keys=trusted_keys,
        independent=True,
    )
    for key, record in register.items():
        release_time = _parse_utc(record["review_chain"][2]["reviewed_at"], "reviewed_at")
        if release_time <= independently_reviewed[key]:
            raise ValueError("release validation must follow independent review")


def _validate_artifacts(root: Path, register: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    exercise_manifest = _load_json_object(root, Path("exercises/manifest.json"))
    if set(exercise_manifest) != {"schema_version", "items"} or exercise_manifest.get("schema_version") != "v1":
        raise ValueError("exercise manifest schema is invalid")
    exercise_items = exercise_manifest.get("items")
    if not isinstance(exercise_items, list) or len(exercise_items) != len(EXERCISE_IDS):
        raise ValueError("exercise manifest lacks item records")
    exercise_ids = [item.get("exercise_id") for item in exercise_items if isinstance(item, dict)]
    if len(exercise_ids) != len(EXERCISE_IDS) or set(exercise_ids) != set(EXERCISE_IDS):
        raise ValueError("exercise manifest does not contain the frozen exercise IDs")

    knowledge_manifest = _load_json_object(root, Path("knowledge/manifest.json"))
    if (
        set(knowledge_manifest) != KNOWLEDGE_MANIFEST_FIELDS
        or knowledge_manifest.get("schema_version") != "v1"
        or not isinstance(knowledge_manifest.get("items"), list)
        or len(knowledge_manifest["items"]) != len(KNOWLEDGE_IDS)
    ):
        raise ValueError("knowledge manifest schema is invalid")
    knowledge_items: dict[str, dict[str, Any]] = {}
    for item in knowledge_manifest["items"]:
        if (
            not isinstance(item, dict)
            or set(item) != KNOWLEDGE_MANIFEST_ITEM_FIELDS
            or not isinstance(item.get("article_id"), str)
            or item["article_id"] in knowledge_items
        ):
            raise ValueError("knowledge manifest item is invalid")
        knowledge_items[item["article_id"]] = item
    if set(knowledge_items) != set(KNOWLEDGE_IDS):
        raise ValueError("knowledge manifest does not contain the frozen article IDs")

    for key, record in register.items():
        if key[0] == "exercise":
            matches = [item for item in exercise_items if isinstance(item, dict) and item.get("exercise_id") == key[1]]
            if len(matches) != 1:
                raise ValueError("exercise manifest does not map one item per frozen exercise")
            artifact = matches[0]
        else:
            artifact = _load_json_object(root, ARTIFACT_PATHS[key])
        _validate_artifact_semantics(key, artifact)
        id_field = {
            "knowledge": "article_id",
            "assessment": "scale",
            "crisis_resource": "content_id",
            "safety_ui": "content_id",
            "exercise": "exercise_id",
        }[key[0]]
        checksum = artifact.get("checksum")
        unsigned = {field: value for field, value in artifact.items() if field != "checksum"}
        actual_checksum = hashlib.sha256(canonicalize(unsigned)).hexdigest()
        if (
            artifact.get(id_field) != key[1]
            or artifact.get("version") != key[2]
            or artifact.get("status") != "published"
            or artifact.get("review_record_id") != record["review_record_id"]
            or artifact.get("source_refs") != record["source_refs"]
            or checksum != actual_checksum
            or checksum != record["content_checksum"]
        ):
            raise ValueError("review record checksum is not bound to its real content artifact")
        if key[0] == "knowledge":
            manifest_item = knowledge_items[key[1]]
            if manifest_item["path"] != ARTIFACT_PATHS[key].as_posix() or manifest_item["checksum"] != checksum:
                raise ValueError("knowledge manifest is not bound to its reviewed article")


def _validate_source_register(root: Path, review_register: list[dict[str, Any]]) -> None:
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
        unsigned_source = {field: value for field, value in source.items() if field != "checksum"}
        if source["checksum"] != hashlib.sha256(canonicalize(unsigned_source)).hexdigest():
            raise ValueError("source record checksum mismatch")
        source_ids.add(source_id)
    referenced = {source for row in review_register for source in row["source_refs"]}
    if not referenced.issubset(source_ids):
        raise ValueError("review register contains unresolved source references")


def _validate_artifact_semantics(key: tuple[str, str, str], artifact: dict[str, Any]) -> None:
    """Reject structurally valid placeholders that cannot satisfy the frozen content contract."""
    content_type = key[0]
    source_refs = artifact.get("source_refs")
    if not _nonempty_strings(source_refs) or not _nonempty_strings(artifact.get("forbidden_claims")):
        raise ValueError("content artifact lacks source or forbidden-claim boundaries")
    if content_type == "knowledge":
        required = {
            "article_id",
            "title",
            "body_markdown",
            "topics",
            "claims",
            "applicable_scenarios",
            "contraindications",
            "forbidden_claims",
            "source_refs",
            "author_or_institution",
            "review_record_id",
            "version",
            "region",
            "status",
            "reviewed_at",
            "expires_at",
            "checksum",
        }
        if set(artifact) != required:
            raise ValueError("knowledge article schema is invalid")
        if (
            not _meaningful_text(artifact.get("title"), 4)
            or not _meaningful_text(artifact.get("body_markdown"), 80)
            or not _nonempty_strings(artifact.get("topics"))
            or not _nonempty_strings(artifact.get("applicable_scenarios"))
            or not _source_bound_texts(artifact.get("contraindications"), source_refs)
            or not _source_bound_texts(artifact.get("claims"), source_refs)
            or not _meaningful_text(artifact.get("author_or_institution"), 3)
            or artifact.get("region") != "CN-mainland"
        ):
            raise ValueError("knowledge article semantics are incomplete")
        _validate_review_window(artifact)
    elif content_type == "exercise":
        required = {
            "exercise_id",
            "title",
            "category",
            "purpose",
            "applicable_scenarios",
            "contraindications",
            "estimated_minutes",
            "steps",
            "exit_copy",
            "completion_feedback",
            "forbidden_claims",
            "source_refs",
            "review_record_id",
            "reviewed_at",
            "version",
            "status",
            "checksum",
        }
        steps = artifact.get("steps")
        if set(artifact) != required or not isinstance(steps, list) or len(steps) < 2:
            raise ValueError("exercise schema or step count is invalid")
        if (
            not all(
                isinstance(step, dict)
                and set(step) == {"step_id", "instruction", "source_refs"}
                and _meaningful_text(step.get("step_id"), 2)
                and _meaningful_text(step.get("instruction"), 8)
                and _valid_source_subset(step.get("source_refs"), source_refs)
                for step in steps
            )
            or not _source_bound_texts(artifact.get("contraindications"), source_refs)
            or not _nonempty_strings(artifact.get("applicable_scenarios"))
            or not isinstance(artifact.get("estimated_minutes"), int)
            or isinstance(artifact.get("estimated_minutes"), bool)
            or not 1 <= artifact["estimated_minutes"] <= 60
            or not _meaningful_text(artifact.get("purpose"), 8)
            or not _meaningful_text(artifact.get("exit_copy"), 8)
            or not _meaningful_text(artifact.get("completion_feedback"), 8)
        ):
            raise ValueError("exercise semantics are incomplete")
        _parse_utc(artifact.get("reviewed_at"), "reviewed_at")
    elif content_type == "assessment":
        expected_items = 9 if key[1] == "PHQ9" else 7
        items = artifact.get("items")
        display = artifact.get("display")
        if (
            not isinstance(items, list)
            or len(items) != expected_items
            or artifact.get("review_period_days") != 14
            or not _meaningful_text(artifact.get("license_basis"), 8)
            or not isinstance(display, dict)
            or set(display)
            != {
                "title",
                "summary",
                "non_diagnostic_notice",
                "recommended_actions",
                "resource_refs",
                "content_version",
            }
            or display.get("content_version") != key[2]
            or not _meaningful_text(display.get("non_diagnostic_notice"), 8)
            or not _nonempty_strings(display.get("recommended_actions"))
            or not _nonempty_strings(display.get("resource_refs"))
        ):
            raise ValueError("assessment semantics are incomplete")
        if not all(
            isinstance(item, dict)
            and set(item) == {"item_id", "prompt", "options", "source_refs"}
            and _meaningful_text(item.get("item_id"), 2)
            and _meaningful_text(item.get("prompt"), 4)
            and isinstance(item.get("options"), list)
            and [option.get("score") for option in item["options"] if isinstance(option, dict)] == [0, 1, 2, 3]
            and all(
                isinstance(option, dict)
                and set(option) == {"score", "text"}
                and _meaningful_text(option.get("text"), 2)
                for option in item["options"]
            )
            and _valid_source_subset(item.get("source_refs"), source_refs)
            for item in items
        ):
            raise ValueError("assessment items are invalid")
    elif content_type == "crisis_resource":
        resources = artifact.get("resources")
        if (
            artifact.get("region") != "CN-mainland"
            or artifact.get("language") != "zh-CN"
            or not isinstance(resources, list)
            or {item.get("number") for item in resources if isinstance(item, dict)} != {"110", "120", "12356"}
            or not all(
                isinstance(item, dict)
                and set(item) == {"name", "number", "instructions", "source_refs"}
                and _meaningful_text(item.get("name"), 2)
                and _meaningful_text(item.get("instructions"), 6)
                and _valid_source_subset(item.get("source_refs"), source_refs)
                for item in resources
            )
        ):
            raise ValueError("crisis resource semantics are incomplete")
        _validate_review_window(artifact, start="verified_at")
    else:
        prompt = artifact.get("prompt")
        answers = artifact.get("answers")
        actions = artifact.get("actions")
        if (
            artifact.get("region") != "CN-mainland"
            or artifact.get("language") != "zh-CN"
            or not _source_bound_text(prompt, source_refs)
            or not isinstance(answers, list)
            or {item.get("id") for item in answers if isinstance(item, dict)} != SAFETY_ANSWER_IDS
            or not isinstance(actions, list)
            or {item.get("id") for item in actions if isinstance(item, dict)} != SAFETY_ACTION_IDS
            or not all(_ui_item(item, source_refs) for item in [*answers, *actions])
        ):
            raise ValueError("safety UI semantics are incomplete")
        _parse_utc(artifact.get("reviewed_at"), "reviewed_at")


def _nonempty_strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(_meaningful_text(item, 2) for item in value)


def _meaningful_text(value: object, minimum: int) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum and "todo" not in value.lower()


def _valid_source_subset(value: object, allowed: object) -> bool:
    return (
        isinstance(value, list)
        and _nonempty_strings(value)
        and isinstance(allowed, list)
        and set(value).issubset(allowed)
    )


def _source_bound_text(value: object, allowed: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"text", "source_refs"}
        and _meaningful_text(value.get("text"), 6)
        and _valid_source_subset(value.get("source_refs"), allowed)
    )


def _source_bound_texts(value: object, allowed: object) -> bool:
    return isinstance(value, list) and bool(value) and all(_source_bound_text(item, allowed) for item in value)


def _ui_item(value: object, allowed: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"id", "text", "kind", "source_refs"}
        and _meaningful_text(value.get("id"), 3)
        and _meaningful_text(value.get("text"), 2)
        and _meaningful_text(value.get("kind"), 3)
        and _valid_source_subset(value.get("source_refs"), allowed)
    )


def _validate_review_window(artifact: dict[str, Any], *, start: str = "reviewed_at") -> None:
    reviewed_at = _parse_utc(artifact.get(start), start)
    expires_at = _parse_utc(artifact.get("expires_at"), "expires_at")
    now = datetime.now(UTC)
    if reviewed_at > now or expires_at <= now or reviewed_at >= expires_at:
        raise ValueError("content review validity window is invalid")


def _load_handoff(
    root: Path, path: Path, schema_version: str, trusted_keys: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    handoff = _load_json_object(root, path)
    if set(handoff) != HANDOFF_FIELDS or handoff.get("schema_version") != schema_version:
        raise ValueError(f"{schema_version} handoff schema is invalid")
    items = handoff.get("items")
    if not isinstance(items, list) or len(items) != 24:
        raise ValueError(f"{schema_version} must cover the frozen 24 content tuples")
    signer_id, signed_at = _verify_handoff_confirmation(root, handoff, schema_version, trusted_keys)
    timestamp_field = "authored_at" if schema_version == "content-author-handoff.v1" else "reviewed_at"
    if any(
        _parse_utc(item.get(timestamp_field), timestamp_field) > signed_at for item in items if isinstance(item, dict)
    ):
        raise ValueError("handoff was signed before its item decisions")
    return handoff, signer_id


def _verify_handoff_confirmation(
    root: Path,
    handoff: dict[str, Any],
    schema_version: str,
    trusted_keys: dict[str, Any],
) -> tuple[str, datetime]:
    reference = handoff.get("confirmation_ref")
    checksum = handoff.get("confirmation_checksum")
    _verify_referenced_file(root, reference, checksum, f"{schema_version} confirmation")
    if not isinstance(reference, str):
        raise ValueError("confirmation reference is invalid")
    confirmation = _load_json_object(root, Path(reference))
    if set(confirmation) != CONFIRMATION_FIELDS or confirmation.get("schema_version") != "review-confirmation.v1":
        raise ValueError("review confirmation schema is invalid")
    handoff_payload = {key: value for key, value in handoff.items() if key != "confirmation_checksum"}
    if confirmation.get("handoff_sha256") != hashlib.sha256(canonicalize(handoff_payload)).hexdigest():
        raise ValueError("review confirmation is not bound to the canonical handoff")
    expected_role = EXPECTED_SIGNER_ROLES[schema_version]
    if confirmation.get("signer_role") != expected_role:
        raise ValueError("review confirmation signer role is invalid")
    keys = trusted_keys["keys"]
    matches = [key for key in keys if isinstance(key, dict) and key.get("key_id") == confirmation.get("key_id")]
    if len(matches) != 1 or set(matches[0]) != REVIEW_KEY_FIELDS:
        raise ValueError("review confirmation key is not uniquely trusted")
    key = matches[0]
    signed_at = _parse_utc(confirmation.get("signed_at"), "signed_at")
    if (
        key.get("status") != "active"
        or key.get("signer_id") != confirmation.get("signer_id")
        or key.get("signer_role") != expected_role
        or not (
            _parse_utc(key.get("not_before"), "not_before") <= signed_at < _parse_utc(key.get("not_after"), "not_after")
        )
        or signed_at > datetime.now(UTC)
    ):
        raise ValueError("review confirmation signer identity or validity is invalid")
    signed_payload = {field: value for field, value in confirmation.items() if field != "signature"}
    try:
        public_key = Ed25519PublicKey.from_public_bytes(_decode_b64url(key["public_key"]))
        public_key.verify(_decode_b64url(confirmation["signature"]), canonicalize(signed_payload))
    except (InvalidSignature, KeyError, TypeError, ValueError) as exc:
        raise ValueError("review confirmation signature is invalid") from exc
    return str(confirmation["signer_id"]), signed_at


def _validate_author_items(
    items: list[object], register: dict[tuple[str, str, str], dict[str, Any]], signer_id: str
) -> dict[tuple[str, str, str], datetime]:
    mapped = _strict_item_map(items, AUTHOR_ITEM_FIELDS, "author")
    if set(mapped) != EXPECTED_CONTENT_TUPLES:
        raise ValueError("author handoff does not cover the frozen 24 content tuples")
    timestamps: dict[tuple[str, str, str], datetime] = {}
    for key, item in mapped.items():
        record = register[key]
        authored_at = _parse_utc(item.get("authored_at"), "authored_at")
        if (
            item.get("author_id") != signer_id
            or item.get("author_id") != record["draft_author_id"]
            or item.get("draft_checksum") != record["content_checksum"]
            or item.get("source_refs") != record["source_refs"]
            or authored_at > datetime.now(UTC)
        ):
            raise ValueError("author handoff does not match the active review record")
        timestamps[key] = authored_at
    return timestamps


def _validate_review_items(
    items: list[object],
    register: dict[tuple[str, str, str], dict[str, Any]],
    *,
    stage_index: int,
    root: Path,
    signer_id: str,
    after: dict[tuple[str, str, str], datetime],
    trusted_keys: dict[str, Any],
    independent: bool = False,
) -> dict[tuple[str, str, str], datetime]:
    fields = INDEPENDENT_ITEM_FIELDS if independent else REVIEW_ITEM_FIELDS
    mapped = _strict_item_map(items, fields, "independent" if independent else "content-safety")
    if set(mapped) != EXPECTED_CONTENT_TUPLES:
        raise ValueError("review handoff does not cover the frozen 24 content tuples")
    timestamps: dict[tuple[str, str, str], datetime] = {}
    for key, item in mapped.items():
        record = register[key]
        stage = record["review_chain"][stage_index]
        reviewed_at = _parse_utc(item.get("reviewed_at"), "reviewed_at")
        if (
            item.get("reviewer_id") != signer_id
            or item.get("reviewer_id") != stage["reviewer_id"]
            or item.get("reviewed_at") != stage["reviewed_at"]
            or item.get("decision") != "approved"
            or item.get("input_checksum") != record["content_checksum"]
            or item.get("output_checksum") != record["content_checksum"]
            or reviewed_at <= after[key]
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
                _verify_referenced_file(root, qualification_ref, qualification_checksum, "reviewer qualification")
                _validate_qualification(root, qualification_ref, signer_id, trusted_keys)
        timestamps[key] = reviewed_at
    return timestamps


def _validate_qualification(root: Path, reference: object, signer_id: str, trusted_keys: dict[str, Any]) -> None:
    if not isinstance(reference, str):
        raise ValueError("reviewer qualification reference is invalid")
    qualification = _load_json_object(root, Path(reference))
    if set(qualification) != QUALIFICATION_FIELDS or qualification.get("schema_version") != "qualification.v1":
        raise ValueError("reviewer qualification schema is invalid")
    issued_at = _parse_utc(qualification.get("issued_at"), "issued_at")
    expires_at = _parse_utc(qualification.get("expires_at"), "expires_at")
    issuer_matches = [
        key
        for key in trusted_keys["keys"]
        if key.get("key_id") == qualification.get("issuer_key_id")
        and key.get("signer_id") == qualification.get("issuer")
        and key.get("signer_role") == "qualification_issuer"
    ]
    if (
        qualification.get("holder_id") != signer_id
        or not _meaningful_text(qualification.get("issuer"), 3)
        or not _meaningful_text(qualification.get("qualification_type"), 3)
        or not _meaningful_text(qualification.get("evidence_id"), 3)
        or issued_at > datetime.now(UTC)
        or expires_at <= datetime.now(UTC)
        or issued_at >= expires_at
        or len(issuer_matches) != 1
    ):
        raise ValueError("reviewer qualification identity or validity is invalid")
    issuer_key = issuer_matches[0]
    if issuer_key.get("status") != "active" or not (
        _parse_utc(issuer_key.get("not_before"), "not_before")
        <= issued_at
        < _parse_utc(issuer_key.get("not_after"), "not_after")
    ):
        raise ValueError("reviewer qualification issuer key is not valid at issuance")
    signed_payload = {field: value for field, value in qualification.items() if field != "signature"}
    try:
        public_key = Ed25519PublicKey.from_public_bytes(_decode_b64url(issuer_key["public_key"]))
        public_key.verify(_decode_b64url(qualification["signature"]), canonicalize(signed_payload))
    except (InvalidSignature, KeyError, TypeError, ValueError) as exc:
        raise ValueError("reviewer qualification issuer signature is invalid") from exc


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
    values = (value.get("content_type"), value.get("content_id"), value.get("content_version"))
    if not all(isinstance(item, str) and item for item in values):
        raise ValueError("content tuple is invalid")
    return str(values[0]), str(values[1]), str(values[2])


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


def _load_json_object(root: Path, relative_path: Path) -> dict[str, Any]:
    path = _resolve_evidence_path(root, relative_path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"required review evidence is unavailable: {relative_path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"required review evidence is not an object: {relative_path}")
    return value


def _load_trusted_review_keys(
    evidence_root: Path,
    *,
    trusted_review_keys_path: str | Path | None,
    trusted_review_keys_sha256: str | None,
) -> dict[str, Any]:
    configured_path = trusted_review_keys_path or os.environ.get("MENTAL_HEALTH_REVIEW_KEYS_FILE")
    pinned_checksum = trusted_review_keys_sha256 or os.environ.get("MENTAL_HEALTH_REVIEW_KEYS_SHA256")
    if not configured_path or not pinned_checksum or CHECKSUM_PATTERN.fullmatch(pinned_checksum) is None:
        raise ValueError("external trusted review key path and pinned SHA-256 are required")
    path = Path(configured_path)
    if not path.is_absolute():
        raise ValueError("trusted review key path must be absolute")
    resolved_path = path.resolve()
    resolved_root = evidence_root.resolve()
    if resolved_path == resolved_root or resolved_root in resolved_path.parents:
        raise ValueError("trusted review keys must be provisioned outside the content evidence root")
    try:
        raw = resolved_path.read_bytes()
        registry = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("trusted review key registry is unavailable") from exc
    if hashlib.sha256(raw).hexdigest() != pinned_checksum:
        raise ValueError("trusted review key registry does not match its pinned SHA-256")
    if not isinstance(registry, dict):
        raise ValueError("trusted review key registry is invalid")
    keys = registry.get("keys")
    if (
        set(registry) != {"schema_version", "keys"}
        or registry.get("schema_version") != "v1"
        or not isinstance(keys, list)
        or not keys
        or any(not isinstance(key, dict) or set(key) != REVIEW_KEY_FIELDS for key in keys)
    ):
        raise ValueError("trusted review key registry is invalid")
    return registry


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


def _decode_b64url(value: object) -> bytes:
    if not isinstance(value, str) or "=" in value:
        raise ValueError("base64url value is invalid")
    padding = "=" * (-len(value) % 4)
    return base64.b64decode((value + padding).encode("ascii"), altchars=b"-_", validate=True)
