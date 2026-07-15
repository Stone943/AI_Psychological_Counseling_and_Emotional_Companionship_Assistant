# Member B delivery evidence

Last verified: 2026-07-15 (Asia/Shanghai)

## Verdict

Member B is **not release-complete**.  The earlier claim that B-01 through B-20
were complete was based largely on route skeletons and tests that accepted HTTP
503 as GREEN.  This document now follows the stricter completion definition in
`member_b_backend_delivery_plan.md`.

Current local result: `uv run pytest -q` reports **213 passed** under managed
CPython 3.11.15.  This is a useful unit/contract baseline, not proof of the
required MySQL, Android, real-AI, content-review, performance, recovery or ECS
release gates.

## Work completed in the 2026-07-15 audit

- Restored the shared baseline to Python 3.11 and regenerated `uv.lock`.
- Kept TensorRT Python bindings behind the Linux x86_64 optional extra; the
  standard `ai + onnx` sync does not select or import TensorRT.  This WSL host
  can execute a PyTorch CUDA tensor on an RTX 4060, and the TensorRT extra
  resolves, but importing its bindings fails because the external
  `libnvonnxparser.so.10` runtime is absent.  The TensorRT runtime gate therefore
  remains unverified rather than PASS.
- Replaced per-request SQLAlchemy engine creation with one application-owned
  async engine/session factory, bounded MySQL pool settings, rollback-on-error
  and shutdown disposal.
- Replaced the safety gateway's unconditional L0 allow stub with an injectable
  Member A adapter.  Missing A code, invalid context, malformed A output or A
  failure now returns a fail-closed result and never fabricates a decision ID.
- Replaced the AI turn adapter's fake counseling response with an in-process
  `run_screened_turn` boundary.  It rejects missing A, non-contiguous reviewed
  chunks and any A-owned `sequence` field.
- Added persistent guest session service logic (256-bit token, HMAC lookup,
  expiry and revocation).  MySQL execution remains unverified in this host.
- Added RFC 8785 JCS + Ed25519 signing/verification, one-time demo key generation,
  deterministic bundle build/check and mobile asset verification. The validator
  has synthetic mutation coverage for the frozen 24 tuples, type-specific
  semantic structure, knowledge/source checksums, structured qualification
  identity and signed handoff continuity. Trusted review keys must be provisioned
  outside the content tree and match a separately pinned SHA-256. These tests do
  not constitute real content or reviewer evidence; no bundle is published
  because the external package and C mobile project are absent.
- Added an idempotent retention worker for guest/ephemeral/outbox/risk/audit/
  tombstone/idempotency deadlines, including a same-connection MySQL advisory
  lock boundary.  It is deliberately not scheduled by the demo Compose stack
  until the missing full-schema Alembic migration is supplied.
- Added TOTP enrollment, encrypted seed storage, time-window validation, replay
  prevention and single-use recovery codes.
- Added focused unit/adversarial tests for all new safety, AI, signing and MFA
  boundaries.

## Strict task status

| Task | Status | Current evidence / missing gate |
| --- | --- | --- |
| B-01 | PARTIAL | Python 3.11 lock/sync passes; Docker services unavailable |
| B-02 | PARTIAL | Existing public schemas pass local tests; required A schemas absent |
| B-03 | PARTIAL | ORM/encryption/pool implemented; the sole Alembic migration is known incomplete and the MySQL gate is unverified |
| B-04 | PARTIAL | Guest persistence and default-disabled policy boundary implemented; MySQL/consent lifecycle incomplete |
| B-05 | INCOMPLETE | Auth/recovery routes remain substantially skeletal |
| B-06 | INCOMPLETE | Models exist; repository/idempotency/outbox transaction services missing |
| B-07 | INCOMPLETE | Realtime route remains a 503/error skeleton |
| B-08 | PARTIAL | Registry/context/fail-closed A adapter implemented; SafetyContext transactions/answers incomplete and A-04 absent |
| B-09 | INCOMPLETE | Guest migration remains a 503 skeleton |
| B-10 | PARTIAL | Safe A turn boundary implemented; real A runner/repository/WS bridge absent |
| B-11 | INCOMPLETE | Emotion/memory routes are mostly skeletons; A emotion contract absent |
| B-12 | BLOCKED EXTERNAL | No immutable author package or review handoffs; active registry must stay empty |
| B-13 | BLOCKED/PARTIAL | Depends on B-12 Stage 2; route is skeletal |
| B-14 | BLOCKED/PARTIAL | Depends on reviewed assessment content and A-11 trigger; route is skeletal |
| B-15 | PARTIAL | Artifact-bound signing/handoff validators pass synthetic mutation tests; approved external package and C asset target absent |
| B-16 | PARTIAL | Retention worker added but not scheduled before full migrations; export/deletion/provider legal-review lifecycle incomplete |
| B-17 | PARTIAL | TOTP core added; admin repository/RBAC/reauth/CLI/final freeze incomplete |
| B-18 | PARTIAL | Gate requires exact matrix/JUnit plus run/git/Compose/image/migration/MySQL-bound application instrumentation; missing matrix/environment correctly fails |
| B-19 | UNVERIFIED | Static config requires secret files and image digests; Docker/performance/backup/restore gates unavailable |
| B-20 | BLOCKED/PARTIAL | Orchestrator isolates every run, rejects stale/conflicting producer JSON, requires exact case matrix and A/C/B-19 evidence, and fails closed because those inputs/environment are absent |

## Commands executed successfully

```text
uv lock
uv sync --frozen
uv sync --frozen --extra ai --extra onnx
uv run pytest -q
uv run python scripts/export_openapi.py --check
uv run python scripts/export_ws_contracts.py --check
uv run python scripts/build_crisis_bundle.py --check-vectors
uv run mypy scripts/run_backend_adversarial_gate.py scripts/run_live_stack_e2e.py scripts/verify_release_evidence.py alembic/env.py src/mental_health_api/mental_health_api/config.py src/mental_health_api/mental_health_api/consents/contracts.py src/mental_health_api/mental_health_api/provider_policy/contracts.py src/mental_health_api/mental_health_api/safety/gateway.py src/mental_health_api/mental_health_api/crisis/release_validation.py src/mental_health_api/mental_health_api/contracts/models.py
uv run ruff check .
uv run ruff format --check .
git diff --check
```

The repository-wide Ruff baseline is now clean.  A broader `uv run mypy
src/mental_health_api scripts` audit still reports 67 pre-existing errors in
skeletal routes and older untyped modules; the eight functionally changed audit
ten functionally changed audit modules above pass mypy. The full-repository mypy debt is not reported as a
passing gate.

Six context-free sub-agent reviews returned `CHANGES_REQUESTED`; their
deployment prefix/runtime-command, strict safety-output/context
ownership/timeout, retention-child/lock-order, crisis
degraded/signature/review-chain, reviewed-turn terminal/timeout,
device-binding, key-path, exact content tuples/artifact-bound signed handoffs,
immutable deployment inputs, optimized-mode consent/policy invariants,
fail-closed B-18/B-20 gates, public DTO, external trust-root and stale-evidence
findings have been implemented and locally retested. A fresh seventh review is
still pending; no approval is claimed. Docker/MySQL
commands were not executable because Docker is not exposed inside this WSL
distribution.

## External blockers

See `project_docs/05_progress/member_b_missing_dependencies.md`.  Every missing
external gate is recorded as `BLOCKED`, `UNVERIFIED` or `INCOMPLETE`; none is
reported as PASS.
