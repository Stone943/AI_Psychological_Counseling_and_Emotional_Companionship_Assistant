"""Crisis release approval-chain mutation tests."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from mental_health_api.crisis.jcs import canonicalize
from mental_health_api.crisis.release_validation import validate_register, validate_release


def _stage(role: str, reviewer: str, checksum: str, reviewed_at: str, qualification: str | None = None) -> dict:
    return {
        "reviewer_id": reviewer,
        "reviewer_role": role,
        "qualification_ref": qualification,
        "reviewed_at": reviewed_at,
        "decision": "approved",
        "input_checksum": checksum,
    }


def _fixture() -> tuple[dict, list[dict]]:
    now = datetime.now(UTC).replace(microsecond=0)
    source = {
        "content_id": "china-mainland",
        "version": "v1",
        "status": "published",
        "review_record_id": "review-crisis",
        "source_refs": ["official-cn-source"],
        "verified_at": (now - timedelta(days=1)).isoformat(),
        "expires_at": (now + timedelta(days=30)).isoformat(),
        "resources": [{"number": number} for number in ("110", "120", "12356")],
    }
    checksum = hashlib.sha256(canonicalize(source)).hexdigest()
    source["checksum"] = checksum
    reviewed = [(now - timedelta(days=days)).isoformat() for days in (4, 3, 2)]

    def record(content_type: str, index: int) -> dict:
        return {
            "review_record_id": "review-crisis"
            if content_type == "crisis_resource"
            else f"review-{content_type}-{index}",
            "content_type": content_type,
            "content_id": "china-mainland" if content_type == "crisis_resource" else f"{content_type}-{index}",
            "content_version": "v1",
            "draft_author_id": "external-author",
            "review_chain": [
                _stage("member_a_content_safety_reviewer", "member-a-reviewer", checksum, reviewed[0]),
                _stage(
                    "independent_domain_reviewer",
                    "independent-reviewer",
                    checksum,
                    reviewed[1],
                    "qualification:verified",
                ),
                _stage("member_b_release_validator", "member-b-validator", checksum, reviewed[2]),
            ],
            "release_decision": "approved",
            "source_refs": ["official-cn-source"],
            "content_checksum": checksum,
            "next_review_at": (now + timedelta(days=30)).isoformat(),
        }

    rows = [record("knowledge", index) for index in range(8)]
    rows += [record("exercise", index) for index in range(12)]
    rows += [record("assessment", index) for index in range(2)]
    rows += [record("crisis_resource", 0), record("safety_ui", 0)]
    return source, rows


def test_valid_crisis_release_chain() -> None:
    source, rows = _fixture()
    validate_register(rows)
    validate_release(source, rows)


@pytest.mark.parametrize("mutation", ["role", "timestamp", "qualification", "checksum", "author"])
def test_crisis_release_chain_mutations_fail_closed(mutation: str) -> None:
    source, rows = _fixture()
    candidate = deepcopy(rows)
    crisis = next(row for row in candidate if row["content_type"] == "crisis_resource")
    if mutation == "role":
        crisis["review_chain"][1]["reviewer_role"] = "unknown-role"
    elif mutation == "timestamp":
        crisis["review_chain"][1]["reviewed_at"] = "not-a-date"
    elif mutation == "qualification":
        crisis["review_chain"][1]["qualification_ref"] = None
    elif mutation == "checksum":
        crisis["review_chain"][0]["input_checksum"] = "0" * 64
    else:
        crisis["draft_author_id"] = crisis["review_chain"][1]["reviewer_id"]

    with pytest.raises(ValueError):
        validate_release(source, candidate)


@pytest.mark.parametrize("mutation", ["decision", "empty_chain", "expired", "checksum", "empty_author"])
def test_any_invalid_record_rejects_entire_active_register(mutation: str) -> None:
    _, rows = _fixture()
    candidate = deepcopy(rows)
    row = candidate[0]
    if mutation == "decision":
        row["release_decision"] = "rejected"
    elif mutation == "empty_chain":
        row["review_chain"] = []
    elif mutation == "expired":
        row["next_review_at"] = "2020-01-01T00:00:00+00:00"
    elif mutation == "checksum":
        row["content_checksum"] = "not-a-checksum"
    else:
        row["draft_author_id"] = ""

    with pytest.raises(ValueError):
        validate_register(candidate)
