# Member B missing dependency register

Last verified: 2026-07-15 (Asia/Shanghai)

This register records prerequisites owned outside Member B before continuing the
remaining B-owned work.  A missing prerequisite never authorizes a fabricated
implementation, review signature, release claim, or passing evidence.

## Confirmed missing Member A deliverables

- `contracts/ai/` is absent.  In particular, the A-04/A-05 free-text safety,
  safety-answer, emotion and crisis schemas/canonical rows required by B-02 and
  B-08 are unavailable.
- A-09 `ReviewedStreamChunk`, A-11 assessment trigger/content-safety handoff,
  A-12 screened-turn contracts and A-13/A-15 release/runtime evidence are absent.
- `src/mental_health_ai/mental_health_ai/` contains only an empty package marker;
  there is no callable `screen_text()` or `run_screened_turn()` implementation.

Impact: B can implement fail-closed ports/adapters and test doubles, but cannot
claim the real AI bridge, emotion/crisis semantics, provider smoke, or AI release
gates are complete.

## Confirmed missing Member C deliverables

- The `mobile/` React Native project is absent, including the generated contract
  types, SQLCipher client, signed crisis assets, Detox configuration, Android AVD
  harness, `mobile/e2e/liveStack20Turn.e2e.ts`, and C-17 harness-ready evidence.

Impact: B-15 mobile asset copying and B-20 Android/full-stack orchestration cannot
be accepted as complete.  B may keep validation/orchestration code fail closed
until the C-owned paths exist.

## Confirmed missing external content and review deliverables

- No `content/` author package exists: source register, eight knowledge articles,
  twelve exercises, PHQ-9, GAD-7, the China-mainland crisis resource and safety
  UI draft are all absent.
- The designated-author handoff, A content-safety handoff, and independent-domain
  reviewer handoff are absent.  No verifiable qualification/legal/privacy review
  signature is present.

Impact: B-12 must remain at an unpublished/fail-closed boundary; B must not invent
content, signatures, qualifications or an active 24-record review registry.
B-13 through B-16 may implement generic services but cannot publish content or
claim the formal content/privacy release gates pass.

## Confirmed environment/external evidence gaps

- `uv` was initially absent and was installed locally during this audit; the
  managed CPython 3.11 environment and frozen lock checks are now available.
- Docker Desktop is installed on the Windows host, but Docker is unavailable in
  this WSL distribution because WSL integration is disabled.
- The WSL host exposes an NVIDIA GeForce RTX 4060 Laptop GPU and PyTorch CUDA is
  functional.  The conditional TensorRT extra installs, but the host lacks the
  pinned TensorRT runtime library `libnvonnxparser.so.10`; A-owned model engines,
  manifests and equivalence benchmarks are also absent.  TensorRT cannot be
  imported or accepted as a passing runtime gate here.
- No Android/KVM toolchain or pre-provisioned Alibaba Cloud ECS HTTPS/WSS endpoint
  has been supplied.

Impact: MySQL/Docker, Android Detox, performance, backup/restore and remote ECS
evidence cannot be freshly executed here.  Static checks and Python checks that
do not require these facilities remain in scope; unavailable gates must be marked
`UNVERIFIED`, never `PASS`.

## Continuation rule

Member B work continues on all independent, fail-closed infrastructure and
business logic.  Each unavailable cross-member boundary must return a stable
service/safety-unavailable result and must not produce ordinary business writes.
When an external deliverable later appears, its checksum, schema and ownership
must be validated before enabling the corresponding release path.
