"""Content artifact, handoff identity, and release-chain mutation tests."""

from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from mental_health_api.crisis.jcs import canonicalize
from mental_health_api.crisis.release_validation import (
    ARTIFACT_PATHS,
    EXPECTED_CONTENT_TUPLES,
    _validate_artifact_semantics,
    _validate_qualification,
    validate_register,
    validate_release,
)
from mental_health_api.crisis.signing import public_key_b64

if TYPE_CHECKING:
    from pathlib import Path


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


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
    root = tmp_path / "content"
    now = datetime.now(UTC).replace(microsecond=0)
    reviewed = [(now - timedelta(days=days)).isoformat() for days in (4, 3, 2)]
    authored_at = (now - timedelta(days=5)).isoformat()
    qualification_ref = "reviews/proofs/qualification.proof"
    proof = root / qualification_ref
    proof.parent.mkdir(parents=True)
    proof.write_text(
        json.dumps(
            {
                "schema_version": "qualification.v1",
                "holder_id": "independent-reviewer",
                "issuer": "Independent professional review board",
                "qualification_type": "mental-health-content-review",
                "issued_at": (now - timedelta(days=365)).isoformat(),
                "expires_at": (now + timedelta(days=365)).isoformat(),
                "evidence_id": "qualification-evidence-001",
            }
        ),
        encoding="utf-8",
    )

    rows: list[dict] = []
    artifacts: dict[tuple[str, str, str], dict] = {}
    for content_type, content_id, version in sorted(EXPECTED_CONTENT_TUPLES):
        review_id = "review-crisis" if content_type == "crisis_resource" else f"review-{content_type}-{content_id}"
        id_field = {
            "knowledge": "article_id",
            "exercise": "exercise_id",
            "assessment": "scale",
            "crisis_resource": "content_id",
            "safety_ui": "content_id",
        }[content_type]
        artifact: dict = {
            id_field: content_id,
            "version": version,
            "status": "published",
            "review_record_id": review_id,
            "source_refs": ["official-cn-source"],
            "forbidden_claims": ["不得将该内容表述为诊断、治疗或紧急服务替代品"],
        }
        if content_type == "knowledge":
            artifact.update(
                {
                    "title": f"经审核的心理健康知识：{content_id}",
                    "body_markdown": (
                        "这是一段用于验证发布结构的充分长度正文。"
                        "它说明适用边界、信息来源、何时应寻求专业帮助，并明确不能替代诊断或紧急服务。"
                    )
                    * 2,
                    "topics": ["心理健康", "自助支持"],
                    "claims": [{"text": "该材料只提供一般性支持信息。", "source_refs": ["official-cn-source"]}],
                    "applicable_scenarios": ["一般心理健康科普和自助了解"],
                    "contraindications": [
                        {"text": "处于紧急危险时不能只依赖本文。", "source_refs": ["official-cn-source"]}
                    ],
                    "author_or_institution": "Independent content institution",
                    "region": "CN-mainland",
                    "reviewed_at": reviewed[1],
                    "expires_at": (now + timedelta(days=30)).isoformat(),
                }
            )
        elif content_type == "exercise":
            artifact.update(
                {
                    "title": f"经审核练习：{content_id}",
                    "category": "self_support",
                    "purpose": "在安全范围内提供可随时退出的短时自助练习。",
                    "applicable_scenarios": ["用户主动选择的一般自助场景"],
                    "contraindications": [
                        {"text": "明显不适或危险升级时应立即退出。", "source_refs": ["official-cn-source"]}
                    ],
                    "estimated_minutes": 3,
                    "steps": [
                        {
                            "step_id": "prepare",
                            "instruction": "先确认环境安全，并允许自己随时停止。",
                            "source_refs": ["official-cn-source"],
                        },
                        {
                            "step_id": "practice",
                            "instruction": "按舒适节奏完成练习，不追求固定表现。",
                            "source_refs": ["official-cn-source"],
                        },
                    ],
                    "exit_copy": "你可以随时结束，这不代表失败，也不会造成损失。",
                    "completion_feedback": "练习已结束，请留意当前感受并选择是否继续。",
                    "reviewed_at": reviewed[1],
                }
            )
        elif content_type == "assessment":
            item_count = 9 if content_id == "PHQ9" else 7
            artifact.update(
                {
                    "title": f"{content_id} 简体中文审核定义",
                    "review_period_days": 14,
                    "license_basis": "Documented authorized assessment use basis",
                    "items": [
                        {
                            "item_id": f"{content_id}_Q{index}",
                            "prompt": f"过去两周第 {index} 项审核题目",
                            "options": [{"score": score, "text": f"审核选项 {score}"} for score in range(4)],
                            "source_refs": ["official-cn-source"],
                        }
                        for index in range(1, item_count + 1)
                    ],
                    "display": {
                        "title": f"{content_id} 结果说明",
                        "summary": "结果用于帮助理解近期感受。",
                        "non_diagnostic_notice": "本结果不是医学诊断，也不能替代专业评估。",
                        "recommended_actions": ["如持续困扰，请考虑寻求专业支持"],
                        "resource_refs": ["official-cn-source"],
                        "content_version": version,
                    },
                }
            )
        elif content_type == "crisis_resource":
            artifact.update(
                {
                    "region": "CN-mainland",
                    "language": "zh-CN",
                    "verified_at": (now - timedelta(days=1)).isoformat(),
                    "expires_at": (now + timedelta(days=30)).isoformat(),
                    "resources": [
                        {
                            "name": f"紧急资源 {number}",
                            "number": number,
                            "instructions": "如当前存在紧急危险，请在确保安全的前提下联系此资源。",
                            "source_refs": ["official-cn-source"],
                        }
                        for number in ("110", "120", "12356")
                    ],
                }
            )
        else:
            artifact.update(
                {
                    "region": "CN-mainland",
                    "language": "zh-CN",
                    "reviewed_at": reviewed[1],
                    "prompt": {"text": "你现在处于安全吗？", "source_refs": ["official-cn-source"]},
                    "answers": [
                        {
                            "id": answer_id,
                            "text": text,
                            "kind": "safety_answer",
                            "source_refs": ["official-cn-source"],
                        }
                        for answer_id, text in (
                            ("safe_now", "目前安全"),
                            ("not_safe", "目前不安全"),
                            ("unsure", "我不确定"),
                        )
                    ],
                    "actions": [
                        {
                            "id": action_id,
                            "text": f"审核动作：{action_id}",
                            "kind": "safety_action",
                            "source_refs": ["official-cn-source"],
                        }
                        for action_id in (
                            "call_110",
                            "call_120",
                            "call_12356",
                            "contact_trusted_person",
                            "open_nearest_emergency",
                            "recheck_safety",
                        )
                    ],
                }
            )
        checksum = hashlib.sha256(canonicalize(artifact)).hexdigest()
        artifact["checksum"] = checksum
        artifacts[(content_type, content_id, version)] = artifact
        rows.append(
            {
                "review_record_id": review_id,
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
                        qualification_ref,
                    ),
                    _stage("member_b_release_validator", "member-b-validator", checksum, reviewed[2]),
                ],
                "release_decision": "approved",
                "source_refs": ["official-cn-source"],
                "content_checksum": checksum,
                "next_review_at": (now + timedelta(days=30)).isoformat(),
            }
        )

    _write_artifacts(root, artifacts)
    _write_source_register(root, now)
    _write_signed_handoffs(root, rows, authored_at, reviewed, now, qualification_ref, proof)
    return artifacts[("crisis_resource", "china-mainland", "v1")], rows, root


def _write_artifacts(root: Path, artifacts: dict[tuple[str, str, str], dict]) -> None:
    exercises: list[dict] = []
    knowledge: list[dict] = []
    for key, artifact in artifacts.items():
        path = root / ARTIFACT_PATHS[key]
        if key[0] == "exercise":
            exercises.append(artifact)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact), encoding="utf-8")
        if key[0] == "knowledge":
            knowledge.append(
                {"article_id": key[1], "path": ARTIFACT_PATHS[key].as_posix(), "checksum": artifact["checksum"]}
            )
    manifest = root / "exercises/manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"schema_version": "v1", "items": exercises}), encoding="utf-8")
    knowledge_manifest = root / "knowledge/manifest.json"
    knowledge_manifest.parent.mkdir(parents=True, exist_ok=True)
    knowledge_manifest.write_text(json.dumps({"schema_version": "v1", "items": knowledge}), encoding="utf-8")


def _write_source_register(root: Path, now: datetime) -> None:
    path = root / "sources/source-register.json"
    path.parent.mkdir(parents=True)
    source = {
        "source_id": "official-cn-source",
        "authority": "Official authority",
        "title": "Official source title",
        "locator": "https://www.gov.cn/official-source",
        "license_basis": "reviewed internal demonstration use",
        "region": "CN-mainland",
        "retrieved_at": (now - timedelta(days=10)).isoformat(),
        "version": "v1",
    }
    source["checksum"] = hashlib.sha256(canonicalize(source)).hexdigest()
    path.write_text(json.dumps({"schema_version": "v1", "sources": [source]}), encoding="utf-8")


def _write_signed_handoffs(
    root: Path,
    rows: list[dict],
    authored_at: str,
    reviewed: list[str],
    now: datetime,
    qualification_ref: str,
    qualification_path: Path,
) -> None:
    issuer_private_key = Ed25519PrivateKey.generate()
    issuer_key_id = "key-independent-professional-review-board"
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    qualification["issuer_key_id"] = issuer_key_id
    qualification["signature"] = _b64url(issuer_private_key.sign(canonicalize(qualification)))
    qualification_path.write_text(json.dumps(qualification), encoding="utf-8")

    def key_fields(row: dict) -> dict:
        return {field: row[field] for field in ("content_type", "content_id", "content_version")}

    author_items = [
        {
            **key_fields(row),
            "author_id": row["draft_author_id"],
            "draft_checksum": row["content_checksum"],
            "source_refs": row["source_refs"],
            "authored_at": authored_at,
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
    independent_items = [
        {
            **key_fields(row),
            "reviewer_id": row["review_chain"][1]["reviewer_id"],
            "reviewed_at": reviewed[1],
            "decision": "approved",
            "input_checksum": row["content_checksum"],
            "output_checksum": row["content_checksum"],
            "qualification_ref": qualification_ref,
            "qualification_checksum": hashlib.sha256(qualification_path.read_bytes()).hexdigest(),
        }
        for row in rows
    ]
    definitions = (
        (
            "content-author-handoff.v1.json",
            "content-author-handoff.v1",
            "external-author",
            "designated_content_author",
            author_items,
            now - timedelta(days=4, hours=12),
        ),
        (
            "a-content-safety-review.v1.json",
            "a-content-safety-review.v1",
            "member-a-reviewer",
            "member_a_content_safety_reviewer",
            a_items,
            now - timedelta(days=3, hours=12),
        ),
        (
            "independent-domain-review.v1.json",
            "independent-domain-review.v1",
            "independent-reviewer",
            "independent_domain_reviewer",
            independent_items,
            now - timedelta(days=2, hours=12),
        ),
    )
    handoff_dir = root / "reviews/handoffs"
    handoff_dir.mkdir(parents=True)
    keys = [
        {
            "key_id": issuer_key_id,
            "signer_id": "Independent professional review board",
            "signer_role": "qualification_issuer",
            "public_key": public_key_b64(issuer_private_key.public_key()),
            "not_before": (now - timedelta(days=730)).isoformat(),
            "not_after": (now + timedelta(days=730)).isoformat(),
            "status": "active",
        }
    ]
    for filename, schema_version, signer_id, signer_role, items, signed_at in definitions:
        private_key = Ed25519PrivateKey.generate()
        key_id = f"key-{signer_id}"
        confirmation_ref = f"reviews/handoffs/{filename}.confirmation.json"
        handoff = {
            "schema_version": schema_version,
            "confirmation_ref": confirmation_ref,
            "confirmation_checksum": "0" * 64,
            "items": items,
        }
        handoff_payload = {key: value for key, value in handoff.items() if key != "confirmation_checksum"}
        confirmation = {
            "schema_version": "review-confirmation.v1",
            "handoff_sha256": hashlib.sha256(canonicalize(handoff_payload)).hexdigest(),
            "signer_id": signer_id,
            "signer_role": signer_role,
            "key_id": key_id,
            "signed_at": signed_at.isoformat(),
        }
        confirmation["signature"] = _b64url(private_key.sign(canonicalize(confirmation)))
        confirmation_bytes = json.dumps(confirmation, sort_keys=True).encode("utf-8")
        (root / confirmation_ref).write_bytes(confirmation_bytes)
        handoff["confirmation_checksum"] = hashlib.sha256(confirmation_bytes).hexdigest()
        (handoff_dir / filename).write_text(json.dumps(handoff), encoding="utf-8")
        keys.append(
            {
                "key_id": key_id,
                "signer_id": signer_id,
                "signer_role": signer_role,
                "public_key": public_key_b64(private_key.public_key()),
                "not_before": (now - timedelta(days=30)).isoformat(),
                "not_after": (now + timedelta(days=30)).isoformat(),
                "status": "active",
            }
        )
    (root.parent / "trusted-review-keys.json").write_text(
        json.dumps({"schema_version": "v1", "keys": keys}), encoding="utf-8"
    )


def _validate(rows: list[dict], evidence_root: Path) -> None:
    trust_path = evidence_root.parent / "trusted-review-keys.json"
    validate_register(
        rows,
        evidence_root=evidence_root,
        trusted_review_keys_path=trust_path.resolve(),
        trusted_review_keys_sha256=hashlib.sha256(trust_path.read_bytes()).hexdigest(),
    )


def test_valid_crisis_release_chain(tmp_path: Path) -> None:
    source, rows, evidence_root = _fixture(tmp_path)
    _validate(rows, evidence_root)
    validate_release(source, rows)


def test_review_trust_must_be_external_and_checksum_pinned(tmp_path: Path) -> None:
    _, rows, evidence_root = _fixture(tmp_path)
    trust_path = evidence_root.parent / "trusted-review-keys.json"
    with pytest.raises(ValueError, match="external trusted review key"):
        validate_register(rows, evidence_root=evidence_root)
    with pytest.raises(ValueError, match="pinned SHA-256"):
        validate_register(
            rows,
            evidence_root=evidence_root,
            trusted_review_keys_path=trust_path.resolve(),
            trusted_review_keys_sha256="0" * 64,
        )
    in_tree = evidence_root / "reviews/handoffs/trusted-review-keys.json"
    in_tree.write_bytes(trust_path.read_bytes())
    with pytest.raises(ValueError, match="outside"):
        validate_register(
            rows,
            evidence_root=evidence_root,
            trusted_review_keys_path=in_tree.resolve(),
            trusted_review_keys_sha256=hashlib.sha256(in_tree.read_bytes()).hexdigest(),
        )


def test_semantically_empty_content_and_unbound_qualification_are_rejected(tmp_path: Path) -> None:
    _, _, evidence_root = _fixture(tmp_path)
    article_path = evidence_root / ARTIFACT_PATHS[("knowledge", "emotion_basics", "v1")]
    article = json.loads(article_path.read_text(encoding="utf-8"))
    article["body_markdown"] = ""
    with pytest.raises(ValueError, match="semantics"):
        _validate_artifact_semantics(("knowledge", "emotion_basics", "v1"), article)

    qualification_path = evidence_root / "reviews/proofs/qualification.proof"
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    qualification["holder_id"] = "different-reviewer"
    qualification_path.write_text(json.dumps(qualification), encoding="utf-8")
    trusted_keys = json.loads((evidence_root.parent / "trusted-review-keys.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="identity"):
        _validate_qualification(
            evidence_root,
            "reviews/proofs/qualification.proof",
            "independent-reviewer",
            trusted_keys,
        )


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
        _validate(candidate, evidence_root)


@pytest.mark.parametrize(
    "mutation",
    ["wrong_id", "missing_handoff", "qualification", "source_ref", "handoff_checksum", "artifact", "signature"],
)
def test_external_release_evidence_mutations_fail_closed(mutation: str, tmp_path: Path) -> None:
    _, rows, evidence_root = _fixture(tmp_path)
    candidate = deepcopy(rows)
    handoff_dir = evidence_root / "reviews/handoffs"
    if mutation == "wrong_id":
        candidate[0]["content_id"] = "invented-content"
    elif mutation == "missing_handoff":
        (handoff_dir / "a-content-safety-review.v1.json").unlink()
    elif mutation == "qualification":
        (evidence_root / "reviews/proofs/qualification.proof").unlink()
    elif mutation == "source_ref":
        candidate[0]["source_refs"] = ["unregistered-source"]
    elif mutation == "handoff_checksum":
        path = handoff_dir / "content-author-handoff.v1.json"
        handoff = json.loads(path.read_text(encoding="utf-8"))
        handoff["items"][0]["draft_checksum"] = "0" * 64
        path.write_text(json.dumps(handoff), encoding="utf-8")
    elif mutation == "artifact":
        row = next(row for row in candidate if row["content_type"] == "knowledge")
        path = evidence_root / ARTIFACT_PATHS[(row["content_type"], row["content_id"], row["content_version"])]
        artifact = json.loads(path.read_text(encoding="utf-8"))
        artifact["title"] = "tampered after review"
        path.write_text(json.dumps(artifact), encoding="utf-8")
    else:
        handoff_path = handoff_dir / "content-author-handoff.v1.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        confirmation_path = evidence_root / handoff["confirmation_ref"]
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
        confirmation["signature"] = _b64url(b"invalid-signature")
        confirmation_bytes = json.dumps(confirmation, sort_keys=True).encode("utf-8")
        confirmation_path.write_bytes(confirmation_bytes)
        handoff["confirmation_checksum"] = hashlib.sha256(confirmation_bytes).hexdigest()
        handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
    with pytest.raises(ValueError):
        _validate(candidate, evidence_root)
