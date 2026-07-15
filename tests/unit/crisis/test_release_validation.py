"""Crisis release approval-chain mutation tests."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from mental_health_api.crisis.jcs import canonicalize
from mental_health_api.crisis.release_validation import (
    EXPECTED_CONTENT_TUPLES,
    validate_register,
    validate_release,
)

if TYPE_CHECKING:
    from pathlib import Path


def _stage(role: str, reviewer: str, checksum: str, reviewed_at: str, qualification: str | None = None) -> dict:
    return {
        "reviewer_id": reviewer,
        "reviewer_role": role,
        "qualification_ref": qualification,
        "reviewed_at": reviewed_at,
        "decision": "approved",
        "input_checksum": checksum,
    }


def _fixture(tmp_path: Path) -> tuple[dict, list[dict], Path]:
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

    def record(content_type: str, content_id: str, version: str) -> dict:
        return {
            "review_record_id": "review-crisis"
            if content_type == "crisis_resource"
            else f"review-{content_type}-{content_id}",
            "content_type": content_type,
            "content_id": content_id,
            "content_version": version,
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

    rows = [record(*content_tuple) for content_tuple in sorted(EXPECTED_CONTENT_TUPLES)]
    _write_external_evidence(tmp_path, rows, reviewed, now)
    return source, rows, tmp_path


def _write_external_evidence(root: Path, rows: list[dict], reviewed: list[str], now: datetime) -> None:
    proof_dir = root / "reviews" / "proofs"
    proof_dir.mkdir(parents=True)
    proofs = {
        "author": b"external author confirmation",
        "a": b"member A safety-review confirmation",
        "independent": b"independent domain-review confirmation",
        "qualification": b"independent reviewer qualification evidence",
    }
    for name, value in proofs.items():
        (proof_dir / f"{name}.proof").write_bytes(value)

    sources = root / "sources"
    sources.mkdir()
    (sources / "source-register.json").write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "sources": [
                    {
                        "source_id": "official-cn-source",
                        "authority": "Official authority",
                        "title": "Official source title",
                        "locator": "https://www.gov.cn/official-source",
                        "license_basis": "reviewed internal demonstration use",
                        "region": "CN-mainland",
                        "retrieved_at": (now - timedelta(days=10)).isoformat(),
                        "version": "v1",
                        "checksum": "a" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def key_fields(row: dict) -> dict:
        return {field: row[field] for field in ("content_type", "content_id", "content_version")}

    author_items = [
        {
            **key_fields(row),
            "author_id": row["draft_author_id"],
            "draft_checksum": row["content_checksum"],
            "source_refs": row["source_refs"],
            "authored_at": (now - timedelta(days=5)).isoformat(),
        }
        for row in rows
    ]
    a_items = [
        {
            **key_fields(row),
            "reviewer_id": row["review_chain"][0]["reviewer_id"],
            "reviewed_at": reviewed[0],
            "decision": "approved",
            "input_checksum": row["content_checksum"],
            "output_checksum": row["content_checksum"],
        }
        for row in rows
    ]
    qualification_ref = "reviews/proofs/qualification.proof"
    independent_items = [
        {
            **key_fields(row),
            "reviewer_id": row["review_chain"][1]["reviewer_id"],
            "reviewed_at": reviewed[1],
            "decision": "approved",
            "input_checksum": row["content_checksum"],
            "output_checksum": row["content_checksum"],
            "qualification_ref": qualification_ref,
            "qualification_checksum": hashlib.sha256(proofs["qualification"]).hexdigest(),
        }
        for row in rows
    ]
    for row in rows:
        row["review_chain"][1]["qualification_ref"] = qualification_ref

    handoffs = (
        (
            "content-author-handoff.v1.json",
            "content-author-handoff.v1",
            "author",
            author_items,
        ),
        ("a-content-safety-review.v1.json", "a-content-safety-review.v1", "a", a_items),
        (
            "independent-domain-review.v1.json",
            "independent-domain-review.v1",
            "independent",
            independent_items,
        ),
    )
    for filename, schema_version, proof_name, items in handoffs:
        (root / "reviews" / filename).write_text(
            json.dumps(
                {
                    "schema_version": schema_version,
                    "confirmation_ref": f"reviews/proofs/{proof_name}.proof",
                    "confirmation_checksum": hashlib.sha256(proofs[proof_name]).hexdigest(),
                    "items": items,
                }
            ),
            encoding="utf-8",
        )


def test_valid_crisis_release_chain(tmp_path: Path) -> None:
    source, rows, evidence_root = _fixture(tmp_path)
    validate_register(rows, evidence_root=evidence_root)
    validate_release(source, rows)


@pytest.mark.parametrize("mutation", ["role", "timestamp", "qualification", "checksum", "author"])
def test_crisis_release_chain_mutations_fail_closed(mutation: str, tmp_path: Path) -> None:
    source, rows, _ = _fixture(tmp_path)
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
def test_any_invalid_record_rejects_entire_active_register(mutation: str, tmp_path: Path) -> None:
    _, rows, evidence_root = _fixture(tmp_path)
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
        validate_register(candidate, evidence_root=evidence_root)


@pytest.mark.parametrize("mutation", ["wrong_id", "missing_handoff", "qualification", "source_ref", "handoff_checksum"])
def test_external_release_evidence_mutations_fail_closed(mutation: str, tmp_path: Path) -> None:
    _, rows, evidence_root = _fixture(tmp_path)
    candidate = deepcopy(rows)
    if mutation == "wrong_id":
        candidate[0]["content_id"] = "invented-content"
    elif mutation == "missing_handoff":
        (evidence_root / "reviews" / "a-content-safety-review.v1.json").unlink()
    elif mutation == "qualification":
        (evidence_root / "reviews" / "proofs" / "qualification.proof").unlink()
    elif mutation == "source_ref":
        candidate[0]["source_refs"] = ["unregistered-source"]
    else:
        handoff_path = evidence_root / "reviews" / "content-author-handoff.v1.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        handoff["items"][0]["draft_checksum"] = "0" * 64
        handoff_path.write_text(json.dumps(handoff), encoding="utf-8")

    with pytest.raises(ValueError):
        validate_register(candidate, evidence_root=evidence_root)
