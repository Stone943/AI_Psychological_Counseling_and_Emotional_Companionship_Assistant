# 成员 B：FastAPI、WebSocket、账户、数据与阿里云 ECS Linux 兼容 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 建成连接成员 A 安全 AI 包与成员 C React Native 客户端的完整服务端，使访客与正式账户都能通过真实 FastAPI、MySQL、事务 outbox 和 WebSocket 完成五项核心功能与隐私权利，并保证最终容器栈可运行在阿里云 ECS x86_64 Linux。本文不提供购买 ECS、配置云控制台或上线操作教程。

**术语：** 本文所有缩写、协议名、风险等级和门禁状态统一引用 [系统 PRD 第 1.1 节](../01_requirements/product_system_prd.md#11-统一术语与缩写表)，不得在本方案中另行改义。

**Architecture:** mental_health_api 采用契约优先的模块化单体：单 replica/单 Uvicorn worker 的 FastAPI 进程负责身份、协议、事务和依赖注入，并在同一进程内加载 `mental_health_ai`；A 独占情绪、危机与 LLM 安全语义，B 提供 repository/consent adapters。进程内 DecisionStore 不跨 worker；可选 `model-runtime` 只能无状态执行本地 logits 推理。MySQL 是服务端事实源，Redis 只承担限流/短期协调，事务 outbox 是所有 ServerEventEnvelope 的唯一来源；B 独占最终会话 sequence。内容先由 Git 制品经过 source/review-chain 校验导入 MySQL，再由同一个 KnowledgeRetrieverPort adapter 同时服务 REST 与 A 的 RAG，不建立第二套索引事实源。

**Tech Stack:** Python 3.11、uv/uv.lock、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic、asyncmy、MySQL 8.4、Redis、Argon2id、AES-GCM、Ed25519、RFC 8785 JCS、JWT + opaque refresh/guest token、WebSocket、Caddy、Mailpit、Docker Compose、pytest、Ruff、mypy、Locust、Git；最终运行目标为阿里云 ECS x86_64、官方 Ubuntu 24.04 LTS Linux。

## Global Constraints

- 最高需求源是 project_docs/01_requirements/product_system_prd.md；本文不得弱化 SRC-F01–SRC-F05 或 SRC-T01–SRC-T12。
- 当前产品是课程、竞赛或内部演示系统；最终运行目标仅为阿里云 ECS x86_64 Linux 容器栈，不编写云控制台操作教程，不设计、不实现、不测试嵌入式、ARM、车载或 CARLA 路径。
- 当前管理形态固定为结构化 FastAPI 管理 API + Git 内容制品 + CLI；不建设 Web 管理端，管理 API 不接受任意正文。
- B-01 是 A/B 共享 `pyproject.toml`、`.python-version` 和 `uv.lock` 的唯一 bootstrap/lock owner；完成 B-01 后，标准 CPU 环境统一执行 `uv sync --frozen --extra ai --extra onnx`，只有具备 NVIDIA Linux/CUDA/TensorRT 能力的专用 job 才执行 `uv sync --frozen --extra ai --extra onnx --extra tensorrt`；结束时执行 `uv lock --check`。
- 生产语义只在 MySQL 验证；SQLite 不能替代锁、唯一约束、事务隔离、outbox 或 retention 集成测试。
- 所有最终用户自由文本都必须进入同一个 FreeTextSafetyGateway；未知入口、context_ref 不匹配或安全依赖失败一律 fail closed。
- 所有自由文本 REST 请求必须携带 Idempotency-Key；WebSocket 使用 ClientCommandEnvelope.idempotency_key。
- B 维护 client_commands.schema.json 与 server_events.schema.json 两个独立 WS schema；客户端命令没有 sequence。
- B 是 ServerEventEnvelope.sequence 唯一分配者；messages.message_ordinal 与 WS sequence 永远分离。
- L2/L3、unsure/not_safe 和安全服务故障不得调用普通 LLM、CBT、正念或知识回答，也不得产生原业务写入。
- A 独占 tests/contract/test_emotion_result_contract.py；B 只运行/消费该测试和 A schema，不复制同路径或重写情绪语义。
- 首发内容必须是 24 个真实制品及 24 条一一对应的 active release approval record；每条含三阶段 review chain，空正文、占位来源、自创量表或链断裂不能通过。
- 危机离线包使用 Ed25519 + RFC 8785 JCS；私钥只来自仓库外 secret，客户端公钥事实源是 content/crisis/trusted-keys.json。
- 每个新增或修改 route 的任务都必须重新生成 OpenAPI，再用生成器自身的临时文件 byte compare 模式验证无漂移。
- 初次生成尚未跟踪的制品不能只执行 git diff：先运行生成器 --check 做临时文件 byte compare，再执行 git add -N 对目标建立 intent-to-add，最后审查 git diff。
- 当前工作树可能含成员 A 的未提交 RED 修复以及用户 .vscode/、03-Agent_graph.py；任何 B 任务不得 reset、checkout、覆盖或暂存这些文件。
- 每个任务只提交其 Commit boundary 列出的文件；提交前 git diff --check 必须通过。

---

## 1. 第三者上手与唯一命令约定

### 1.1 必读顺序

1. project_docs/01_requirements/product_system_prd.md。
2. 本文件。
3. contracts/ai 下成员 A 的 schema 与 canonical rows。
4. project_docs/05_progress/member_a_implementation_status.md，确认 A 当前可用边界。
5. project_docs/02_planning/three_person_task_division.md。

### 1.2 Working directory 与环境

本文所有 Working directory: repository root 都表示包含 pyproject.toml 的仓库根目录。Linux/CI 使用正斜杠命令；Windows 开发机可在 PowerShell 原样运行 uv 与 docker compose 命令。

首次执行先判断 B-01 是否完成：若 `.python-version`、`uv.lock`、`deploy/compose.test.yml` 或 `project_docs/05_progress/python_bootstrap_evidence.md` 任一不存在，直接进入 B-01 的 bootstrap 步骤；此时不要先运行 `uv sync --frozen`。只有四项均存在后才执行通用入口：

~~~bash
git status --short
git diff -- src/mental_health_ai tests/unit/domain
uv sync --frozen --extra ai --extra onnx
uv lock --check
docker compose -f deploy/compose.test.yml up -d --wait mysql redis mailpit
~~~

预期：保留并记录已有工作树；B-01 evidence 对应当前 lock hash；uv 无锁漂移；三个基础服务 healthy。不能用旧 `.venv`、本机临时数据库或手工 requirements 替代 B-01。

### 1.3 每个 route task 的固定契约循环

1. 先写目标 route 的失败测试与 OpenAPI 路径/Idempotency-Key/x-input-kind 断言。
2. 运行 RED 命令并确认因 route/handler/schema 未实现而失败。
3. 实现最小 route、service、repository 与事务。
4. 运行 uv run python scripts/export_openapi.py --write。
5. 运行 uv run python scripts/export_openapi.py --check；该命令必须写入临时文件并逐字节比较，不能依赖 git 是否跟踪目标。
6. 若是首次生成文件，运行 git add -N contracts/openapi/openapi.json 后再审查 git diff。
7. 运行目标 MySQL/契约测试、任务 Full gate 和 git diff --check。

## 2. 冻结公共协议

### 2.1 Subject、guest 与账户

- POST /v1/guest-sessions 创建服务端 guest_subject_id 与 256 bit opaque token；数据库只存 token HMAC 摘要、device_key_hash、scopes、expires_at、revoked_at，TTL 最长 24 小时。
- guest token 只允许 onboarding、注册、统一安全门、realtime ticket 和五项演示功能，只能访问自己的临时对象。
- POST /v1/realtime/tickets 同时支持正式账户与 guest，ticket 绑定 subject、session、device key 和目标 conversation，60 秒、单次使用。
- POST /v1/auth/register 必须证明 active guest/pre-auth subject；服务端不信任客户端 user_id 或 guest_id。
- POST /v1/auth/recovery-requests 永远返回 202；recovery token 为 256 bit、只存 HMAC、15 分钟、单次使用。POST /v1/auth/recovery-confirmations 成功返回 204 并撤销全部 refresh family。
- guest 服务端临时数据与账户 ephemeral 会话最长 24 小时；账户 saved 会话保留至用户删除。

### 2.2 十个自由文本入口与 context_ref grammar

| entry_point | method/route | field | B 构造的 context_ref |
| --- | --- | --- | --- |
| chat.message | message.send on WS /v1/realtime | payload.text | conversation:{conversation_id} |
| conversation.title | POST /v1/conversations | title | subject:{subject_id}:new-conversation |
| conversation.title | PATCH /v1/conversations/{id} | title | conversation:{id} |
| feedback.comment | POST /v1/feedback | comment | response:{id}、knowledge:{id} 或 crisis-event:{id} |
| feedback.comment | POST /v1/exercise-sessions/{exercise_session_id}/feedback | comment | exercise-session:{exercise_session_id} |
| exercise.reflection | POST /v1/exercise-sessions/{exercise_session_id}/entries | text | exercise-session:{exercise_session_id}:entry:new |
| exercise.reflection | PATCH /v1/exercise-sessions/{exercise_session_id}/entries/{entry_id} | text | exercise-session:{exercise_session_id}:entry:{entry_id} |
| emotion.correction_note | POST /v1/emotions/{id}/corrections | correction_note | emotion-result:{id} |
| memory.value | POST /v1/memories | value | subject:{subject_id}:new-memory |
| memory.value | PATCH /v1/memories/{id} | value | memory:{id} |
| knowledge.search | POST /v1/knowledge/search | query | subject:{subject_id}:knowledge-search |
| assessment.optional_note | POST /v1/assessments/{scale}/submissions | optional_note | assessment:{PHQ9|GAD7}:{version} |
| profile.nickname | POST /v1/auth/register | nickname | subject:{subject_id}:registration |
| profile.nickname | PATCH /v1/profile | nickname | profile:{subject_id} |
| guest_migration.label | POST /v1/guest-migrations | items[*].label | guest-migration:{batch_id}:item:{item_id} |

route、field、entry point 或 grammar 不一致固定返回 TEXT_ENTRY_CONTEXT_MISMATCH。context_ref 只由 B 从鉴权对象构造；客户端值没有授权意义。所有表中 REST route 必须要求 Idempotency-Key。

v1 的 `entry_point` 集合**精确**为上表十种；新增入口必须提升安全契约版本，不能只在某个 route 临时调用过滤器。B 构造给 A 的 `FreeTextSafetyRequest` 必须恰好包含 `request_id`、`subject_id`、可空 `conversation_id`、`entry_point`、`field_name`、`context_ref`、仅驻留进程内存的 `text`、`idempotency_key`、UTC `occurred_at` 九个字段。A 返回的 `FreeTextSafetyResult` 固定含 `decision=allow|block|error`、allow 时非空 `screening_decision_id`、`risk_decision`、`pii_result`、可空 `safe_template_id`、`safety_action_ids`、`evidence_codes`、`rule_version` 和可空 `model_version`；B 不重新计算风险或 PII。`text` 不得进入 URL、ORM、repr、日志、trace、指标标签、异常、outbox 或幂等请求快照；幂等摘要只覆盖规范化后的非正文元数据和正文 HMAC。管理端不存在任意正文 authoring route：正文由 Git 内容制品进入审核/导入链路，管理 API 只接受结构化 ID、版本、状态和枚举决定，因此不形成第十一个运行时自由文本入口。

### 2.3 SafetyContext 与安全回答

SafetyRequiredResponse 是以 `safety_context_kind` 为 discriminator、拒绝未知字段的 oneOf。base 固定含 status=safety_required、safety_event_id、非空 conversation_id、risk_level、safety_context_kind、safety_context_id、prompt_template_id、action_ids、resource_bundle_version。`free_text` 分支额外必填十入口之一的 entry_point 并禁止 assessment 字段；`assessment` 分支禁止 entry_point，固定 risk_level=L1，并必填 assessment_result_id、scale=PHQ9、item_id=PHQ9_Q9、safety_required=true、result_release_state=held_for_safety、result_visible=false、result=null，且 context ID 等于 result ID。

无现有会话的 L1–L3 请求由 B 在同一 MySQL 事务创建 `mode=free_text_safety` 的会话；已有会话必须先验证 subject ownership。L1 的 `safety_event_id` 精确等于 `safety.question.event_id`；L2/L3 精确等于该 bundle 第一个 `risk.status.event_id`。REST HTTP 202、WS `message.accepted` 的 safety 分支和断线重放必须复用同一个 ID、conversation 与 response body。相同 `(subject_id, entry_point, idempotency_key)` 重试返回原安全会话和事件；事务失败时 SafetyContext、Conversation、CrisisEvent、outbox 与原业务写入全部为零。

| answer_id | SafetyContext 下一状态 | 必发事件 | assessment | generic free text |
| --- | --- | --- | --- | --- |
| safe_now | confirmed_safe，risk=L0 | risk.status | 同一事务 released，再发 assessment.result.available | 不重放旧正文；客户端用新业务幂等键重新提交并再次筛查 |
| unsure | escalated，risk=L2 | risk.status 后 safety.resources | 保持 held | 原业务写入为零 |
| not_safe | escalated，risk=L3 | risk.status 后 safety.resources | 保持 held | 原业务写入为零 |

POST /v1/safety-contexts/{safety_context_id}/rechecks 创建新 server-owned safety.question。相同 command 幂等键返回同一结果；同键不同答案返回 IDEMPOTENCY_CONFLICT；已回答 question 不可突变。旧 generic 业务幂等键永远重放原 SafetyRequiredResponse。

`safety.question` payload 精确为 `{safety_context_kind,safety_context_id,safety_state:'confirmation_required',prompt_template_id,action_ids,resource_bundle_version}`；`safety.answer` command payload 精确为 `{safety_event_id,safety_context_kind,safety_context_id,answer_id}`，其中 answer_id 仅 `safe_now|not_safe|unsure`，幂等键只位于 ClientCommandEnvelope。generic `safe_now` 后不得由服务端恢复已阻断正文；客户端若仍在 RAM 保有 draft，必须提示用户以**新业务幂等键**重提并重新筛查。

### 2.4 WebSocket 双向协议

ClientCommandEnvelope 字段：protocol_version、command_id、conversation_id、idempotency_key、sent_at、type、typed payload；没有 sequence。类型仅 message.send、generation.cancel、session.resume、session.ack、safety.answer。

ServerEventEnvelope 字段：protocol_version、event_id、conversation_id、可空 message_id、sequence、idempotency_key、occurred_at、type、typed payload。sequence 在同一 conversation 从 0 连续递增，只由 B 在 outbox 事务分配。

客户端 payload 精确为：

- `message.send={client_message_id,text,mode}`，mode 仅 `null|support|clarify|exercise|knowledge`；
- `generation.cancel={response_id}`；
- `session.resume={last_ack}`，last_ack>=-1；
- `session.ack={acked_sequence}`，acked_sequence>=0；
- `safety.answer` 使用第 2.3 节精确结构。

服务端 event type 精确为 `message.accepted|risk.status|emotion.result|response.delta|response.completed|response.blocked|safety.question|safety.resources|assessment.result.available|memory.mode.changed|error`。`message.accepted` 是 normal/safety_required 判别联合并保留 command/message 关联；`response.delta={response_id,chunk_index,text}`；`response.completed={response_id,total_chunks,response_source,outcome,feedback_target_id}`；`response.blocked={response_id,outcome,template_id,public_error_code}`；`error` 只封装第 2.5 节 PublicError。`feedback.submit` 不属于 WS：AI/知识/危机反馈走 REST `/v1/feedback`，练习完成反馈只走 B-13 的 `/v1/exercise-sessions/{id}/feedback`；两者的可选 `comment` 共用同一个 `feedback.comment` 安全入口。

- session.resume payload 为 last_ack，最小 -1；重放 sequence > last_ack。
- session.ack payload 为 acked_sequence，最小 0；B 用 CAS 只允许最高连续 ACK 前进，拒绝倒退、越过缺口或其他会话。
- C 只有在 schema 校验、reducer 应用与本地必要提交成功后才 ACK。
- A 只提供 ReviewedStreamChunk(response_id, chunk_index, type, payload)，绝不提供或预留 sequence。
- Message 使用 message_ordinal 表达会话消息顺序，不得出现 message.sequence。

### 2.5 PublicError

B 的唯一错误事实源为 contracts/errors/public_errors.schema.json 与 canonical_rows.json。v1 canonical rows 精确如下；增加/删除/改义必须提升 error-contract version：

| code | HTTP | retryable | client_action |
| --- | ---: | --- | --- |
| VALIDATION_FAILED | 422 | false | fix_input |
| AUTH_REQUIRED | 401 | false | authenticate |
| AUTH_INVALID | 401 | false | reauthenticate |
| FORBIDDEN | 403 | false | none |
| NOT_FOUND | 404 | false | none |
| CONFLICT | 409 | false | refresh |
| IDEMPOTENCY_CONFLICT | 409 | false | use_new_idempotency_key |
| RATE_LIMITED | 429 | true | retry_after |
| SERVICE_UNAVAILABLE | 503 | true | retry |
| SAFETY_GATE_UNAVAILABLE | 503 | true | retry |
| TEXT_ENTRY_NOT_REGISTERED | 500 | false | contact_support |
| TEXT_ENTRY_CONTEXT_MISMATCH | 400 | false | fix_input |
| WS_COMMAND_INVALID | 400 | false | reconnect |
| WS_ACK_INVALID | 409 | false | resume |
| WS_RESUME_INVALID | 409 | false | reconnect |
| WS_TICKET_INVALID | 401 | false | obtain_new_ticket |
| OUTPUT_BLOCKED | 422 | false | show_safe_template |
| ASSESSMENT_VERSION_CONFLICT | 409 | false | refetch_definition |
| SAFETY_CONFIRMATION_REQUIRED | 423 | false | open_safety_confirmation |
| ASSESSMENT_RESULT_DELETED | 410 | false | remove_local_copy |
| RECOVERY_TOKEN_INVALID | 400 | false | restart_recovery |
| GUEST_SESSION_INVALID | 401 | false | create_guest_session |
| GUEST_SESSION_EXPIRED | 401 | false | create_guest_session |
| CONTENT_WITHDRAWN | 410 | false | remove_local_copy |
| DELETION_IN_PROGRESS | 202 | false | show_pending |
| INTERNAL_ERROR | 500 | true | retry |

PublicError 只返回 code、request_id、retryable、client_action 和按 code 允许的 retry_after_seconds；不返回 Pydantic input/ctx/msg、堆栈、内部 reason、原文或供应商信息。

### 2.6 Retention

| 数据 | 保存规则 |
| --- | --- |
| guest 服务端业务/outbox | 最长 24 小时；撤销、过期或迁移完成后按选择清理 |
| account ephemeral conversation | 最长 24 小时；不得进入长期记忆 |
| account saved conversation/memory | 保存至用户删除或注销 |
| 已 ACK 普通 outbox | 7 天 |
| 最小风险事件/安全 outbox | 30 天，无自由文本 |
| AuditLog | 90 天，无心理正文 |
| 加密备份 | 7 天滚动 |
| 删除墓碑 | 30 天，无被删除正文 |

在线删除 24 小时内完成；备份窗口内由 tombstone 阻止复活。

## 3. 契约优先实施 DAG

| Task | depends_on | 主要 produces |
| --- | --- | --- |
| B-01 | 仓库现状 | uv 锁、FastAPI 基线、早期 Docker/Compose |
| B-02 | B-01、A-04、A-05 已提交基础 schema | PublicError、OpenAPI、双向 WS、B-owned skeleton，以及仅针对 A-04/A-05 的首轮 round-trip |
| B-03 | B-01、B-02 | MySQL schema、加密类型、事务/retention 基础 |
| B-04 | B-02、B-03 | guest session、pre-auth、consent |
| B-05 | B-02–B-04 | 账户、token、设备、密码找回/Mailpit |
| B-06 | B-02–B-05 | conversation、message_ordinal、幂等、outbox |
| B-07 | B-02、B-04–B-06 | WS ticket、ACK/CAS、resume、cancel |
| B-08 | B-02、B-03、B-06、B-07、A-04 free-text/answer contracts | 通用 SafetyContext、FreeTextSafetyGateway、answer/recheck；不依赖 A-11 assessment trigger |
| B-09 | B-04、B-05、B-08 | guest migration 原子闭环 |
| B-10 | B-04、B-06–B-08、A-09 reviewed chunks、A-12 turn/consent contracts | 进程内 AI bridge、cloud-consent gate、chat/summary、emotion、feedback；在本任务注册并 byte-compare后置 AI 契约 |
| B-11 | B-06、B-08、B-10 | memory capability、CRUD、context proof |
| B-12 Stage 1 | B-03、B-08 | source/review schema、24 个草稿、pending registry、只拒绝未发布内容的知识 adapter skeleton |
| B-12 Stage 2 | B-12 Stage 1、A-11 content-safety handoff、独立领域审核 handoff | 三阶段 active review registry、发布校验、MySQL import、知识/RAG adapter |
| B-13 | B-03、B-08、B-12 Stage 2 | 练习目录、状态、历史、反馈 |
| B-14 | B-03、B-06、B-08、B-12 Stage 2、A-11 assessment trigger | PHQ/GAD、optional_note、安全 held/release，并注册/byte-compare assessment trigger |
| B-15 | B-03、B-08、B-12 Stage 2 | Ed25519/JCS 危机资源与风险审计 |
| B-16 | B-03–B-15 | 隐私、retention worker、导出/删除/注销 |
| B-17 | B-02–B-16 | TOTP 管理 API + CLI、工具治理、最终 OpenAPI/WS freeze，无 Web UI |
| B-18 | B-08–B-17 | 十入口旁路、安全/日志/依赖故障总门禁 |
| B-19 | B-01、B-03、B-07、B-16–B-18 | 阿里云 ECS Linux runtime contract、Caddy、恢复、性能、唯一 CARLA 扫描 |
| B-20 | B-19、A release profile、C Detox 工程 | Linux/Android/MySQL 本地全栈证据 + 预置阿里云 ECS endpoint remote smoke |

## 4. 实施任务

### Task B-01：uv 锁、FastAPI 基线与早期可运行 Compose

**Working directory:** repository root

**depends_on:** 当前仓库与成员 A 现有 `pyproject.toml` 依赖清单；不得修改成员 A 的未提交领域文件。

**produces:** `.python-version`、A/B 单一 uv workspace/lock、可安装的 `mental_health_ai` 与 `mental_health_api`、`ai`/`onnx`/Linux 条件 `tensorrt` optional extras、bootstrap evidence、create_app(settings)、严格 Settings、最小 Dockerfile、可立即运行的 compose.dev/test、统一 Python 质量命令。

**Files:**
- Modify: pyproject.toml
- Create: .python-version
- Create: uv.lock
- Create: src/mental_health_api/__init__.py
- Create: src/mental_health_api/app.py
- Create: src/mental_health_api/config.py
- Create: src/mental_health_api/errors.py
- Create: scripts/quality.py
- Create: deploy/Dockerfile.api
- Create: deploy/compose.dev.yml
- Create: deploy/compose.test.yml
- Create: deploy/env.example
- Create: project_docs/05_progress/python_bootstrap_evidence.md
- Test: tests/api/test_app.py
- Test: tests/api/test_config.py
- Test: tests/integration/test_early_compose_contract.py
- Test: tests/tooling/test_optional_tensorrt_extra.py

**RED**

- [ ] **Bootstrap 例外（先于业务 RED，只做可运行测试环境）：** 将根 `pyproject.toml` 变为唯一 uv workspace，保留当前 A 依赖并加入 B 依赖；显式定义 `ai`、`onnx` 和带 `sys_platform == 'linux' and platform_machine == 'x86_64'` marker 的 `tensorrt` optional extras，禁止第二份 requirements/lock。执行 `uv lock && uv sync --extra ai --extra onnx && uv lock --check`，记录 Python/uv 版本、lock SHA-256、包可导入结果到 `python_bootstrap_evidence.md`；CPU bootstrap 必须证明 `import mental_health_ai, mental_health_api` 不触发 TensorRT/CUDA import。另在具备 NVIDIA Linux 能力的专用 job 执行 `uv sync --frozen --extra ai --extra onnx --extra tensorrt` 并记录 capability evidence。`uv.lock` 解析全部 extras，但标准 CPU/Windows clean clone 不安装 TensorRT extra。此步骤不实现 FastAPI 业务，因此不以 feature RED 约束；任何依赖解析失败必须先解决，不能跳到 A-01/B-02。
- [ ] 随后写测试，要求缺 DATABASE_URL/ENCRYPTION_KEY_REF 启动失败，production 拒绝 SQLite/http，ValidationError 不泄漏 input，health endpoint 存在，compose 精确声明 mysql/redis/mailpit/api-test。
- [ ] Run: uv run pytest tests/api/test_app.py tests/api/test_config.py tests/integration/test_early_compose_contract.py -q
- [ ] Expected: FAIL，首个失败为 ModuleNotFoundError: mental_health_api 或缺少 deploy/compose.test.yml。

**Implementation**

- [ ] `.python-version` 固定 3.11；bootstrap 后任何新增 Python 依赖都先修改该唯一 workspace 并由 B 重新生成/复核 lock。A 的 ONNX/危机/情绪脚本与 Linux 条件 TensorRT 包必须能从同一 lock 解析，Windows 只跳过平台 marker，不维护另一份锁。
- [ ] 实现 create_app 与 Settings；测试环境允许 SQLite，demo/production 只允许 MySQL、https/wss 和外部 secret 引用。
- [ ] scripts/quality.py 提供 python 与 all 子命令；python 顺序执行 uv lock --check、Ruff、format check、mypy 与 pytest。
- [ ] Dockerfile 使用 Python 3.11、`uv sync --frozen --extra ai --extra onnx`、非 root 用户；仅 NVIDIA image/job 显式追加 `--extra tensorrt`。compose.test 从本任务起提供 MySQL 8.4、Redis、Mailpit 与 api-test，均有 healthcheck。

**GREEN**

- [ ] Run (standard CPU): uv lock --check && uv sync --frozen --extra ai --extra onnx && uv run python -c "import mental_health_ai, mental_health_api" && uv run pytest tests/api/test_app.py tests/api/test_config.py tests/integration/test_early_compose_contract.py tests/tooling/test_optional_tensorrt_extra.py -q
- [ ] Run (NVIDIA Linux only): uv sync --frozen --extra ai --extra onnx --extra tensorrt && uv run pytest tests/tooling/test_optional_tensorrt_extra.py tests/unit/inference/test_backend_selection.py -q
- [ ] Expected: PASS，且收集到的错误正文不含测试 canary。
- [ ] Run: docker compose -f deploy/compose.test.yml up -d --wait mysql redis mailpit
- [ ] Expected: exit 0，三个服务均 healthy。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api tests/api tests/integration/test_early_compose_contract.py tests/tooling/test_optional_tensorrt_extra.py scripts/quality.py && uv run ruff format --check src/mental_health_api tests/api tests/integration/test_early_compose_contract.py tests/tooling/test_optional_tensorrt_extra.py scripts/quality.py && uv run mypy src/mental_health_api scripts/quality.py && git diff --check
- [ ] Expected: 全部 exit 0；不要求尚处于成员 A RED 的全仓 pytest 通过。

**Commit boundary**

- [ ] Stage only: pyproject.toml .python-version uv.lock src/mental_health_api/__init__.py src/mental_health_api/app.py src/mental_health_api/config.py src/mental_health_api/errors.py scripts/quality.py deploy/Dockerfile.api deploy/compose.dev.yml deploy/compose.test.yml deploy/env.example project_docs/05_progress/python_bootstrap_evidence.md tests/api/test_app.py tests/api/test_config.py tests/integration/test_early_compose_contract.py tests/tooling/test_optional_tensorrt_extra.py
- [ ] Commit: chore(api): establish uv and runnable service baseline

### Task B-02：PublicError、OpenAPI、双向 WebSocket 与安全公共契约

**Working directory:** repository root

**depends_on:** B-01，以及 A-04 已提交的 `free_text_safety`/answer 契约和 A-05 已提交的 emotion/crisis 契约。B-02 只消费这批当时存在的 `contracts/ai` 基础 schema；A-09 reviewed-chunk、A-11 assessment-trigger 和 A-12 turn contract 由后续 B-10/B-14 领域任务注册并校验。

**produces:** public error 唯一事实源、全部 REST route/request/response skeleton、client_commands/server_events 两份 WS schema、guest/safety/memory/feedback/量表 B-owned schema、确定性生成器和 byte-compare 门禁，以及仅覆盖 A-04/A-05 的首轮 AI→B round-trip；后续领域任务实现 skeleton，并对其届时才存在的 A-owned schema 执行显式注册、canonical 补充和 byte-compare。

**Files:**
- Create: src/mental_health_api/contracts/models.py
- Create: src/mental_health_api/contracts/public_errors.py
- Create: scripts/export_openapi.py
- Create: scripts/export_ws_contracts.py
- Create: contracts/openapi/openapi.json
- Create: contracts/errors/public_errors.schema.json
- Create: contracts/errors/canonical_rows.json
- Create: contracts/ws/client_commands.schema.json
- Create: contracts/ws/server_events.schema.json
- Create: contracts/ws/canonical_rows.json
- Create: contracts/safety/safety_required_response.schema.json
- Create: contracts/safety/safety_question.schema.json
- Create: contracts/safety/safety_answer.schema.json
- Create: contracts/safety/canonical_rows.json
- Create: contracts/guests/guest_session.schema.json
- Create: contracts/guests/guest_migration.schema.json
- Create: contracts/guests/canonical_rows.json
- Create: contracts/memory/memory_capability.schema.json
- Create: contracts/memory/context_proof.schema.json
- Create: contracts/memory/canonical_rows.json
- Create: contracts/feedback/feedback.schema.json
- Create: contracts/feedback/canonical_rows.json
- Create: contracts/auth/recovery.schema.json
- Create: contracts/auth/admin_mfa.schema.json
- Create: contracts/auth/canonical_rows.json
- Create: contracts/assessments/assessment_submission_response.schema.json
- Create: contracts/assessments/assessment_result.schema.json
- Create: contracts/assessments/assessment_result_available.schema.json
- Create: contracts/assessments/canonical_rows.json
- Test: tests/contract/test_public_errors.py
- Test: tests/contract/test_ws_contracts.py
- Test: tests/contract/test_contract_generation.py
- Test: tests/contract/test_ai_backend_roundtrip.py

**RED**

- [ ] 写 mutation tests：ClientCommandEnvelope 出现 sequence、ServerEventEnvelope 缺 sequence、首事件非 0、unknown field、错误泄漏 msg/input、SafetyRequiredResponse 缺 conversation_id 均失败；free_text 缺 entry_point 或带 assessment 字段失败，assessment 带 entry_point/缺 scale-item-result/泄漏 answer 或 score 失败。断言第 2.5 节 PublicError 精确集合/字段/HTTP/action；guest/memory/feedback/recovery/admin MFA skeleton 均能从 OpenAPI 定位且没有任意管理正文参数。
- [ ] Run: uv run pytest tests/contract/test_public_errors.py tests/contract/test_ws_contracts.py tests/contract/test_contract_generation.py tests/contract/test_ai_backend_roundtrip.py -q
- [ ] Expected: FAIL，原因是 B-owned schema/生成器不存在；不得因重新定义 A EmotionResult 失败。

**Implementation**

- [ ] 按第 2 节实现 strict Pydantic 判别联合；SafetyRequiredResponse 的 assessment/free_text 两分支不可互相填充字段，assessment 分支领域校验强制 `safety_context_id == assessment_result_id`，client command 无 sequence，server event sequence>=0。
- [ ] 在 FastAPI 注册本方案 B-04 至 B-18 的全部 route request/response skeleton：未实现 handler 只能返回显式 `SERVICE_UNAVAILABLE`，不得返回假成功；skeleton 从第一天即可生成 OpenAPI，之后每个领域任务替换 handler 并 byte compare。
- [ ] export_openapi.py 与 export_ws_contracts.py 同时支持 --write 和 --check；--check 写临时文件、逐字节比较并清理临时文件。
- [ ] 第一次 --write 后先运行 --check，再运行 git add -N 对全部新 contracts 文件建立 intent-to-add，最后审查 git diff；不能用空 git diff 冒充稳定生成。
- [ ] tests/contract/test_ai_backend_roundtrip.py 在 B-02 只验证 A-04 free-text/answer 与 A-05 emotion/crisis JSON schema → B adapter → JSON 不丢字段；A-09 reviewed-chunk、A-11 assessment-trigger、A-12 turn 的 round-trip 分别由 B-10/B-14 后置追加。tests/contract/test_emotion_result_contract.py 始终由 A 独占。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_ws_contracts.py --write
- [ ] Expected: 生成上述全部制品。
- [ ] Run: uv run python scripts/export_openapi.py --check && uv run python scripts/export_ws_contracts.py --check
- [ ] Expected: PASS，临时输出与工作树文件逐字节一致。
- [ ] Run: uv run pytest tests/contract/test_public_errors.py tests/contract/test_ws_contracts.py tests/contract/test_contract_generation.py tests/contract/test_ai_backend_roundtrip.py -q
- [ ] Expected: PASS。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/contracts scripts/export_openapi.py scripts/export_ws_contracts.py tests/contract && uv run ruff format --check src/mental_health_api/contracts scripts/export_openapi.py scripts/export_ws_contracts.py tests/contract && uv run mypy src/mental_health_api/contracts scripts/export_openapi.py scripts/export_ws_contracts.py && git diff --check
- [ ] Expected: 全部 exit 0；rg -n "events.schema|SafeStreamEvent" contracts src/mental_health_api tests/contract 无命中。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/contracts scripts/export_openapi.py scripts/export_ws_contracts.py contracts/openapi contracts/errors contracts/ws contracts/safety contracts/guests contracts/memory contracts/feedback contracts/auth contracts/assessments tests/contract/test_public_errors.py tests/contract/test_ws_contracts.py tests/contract/test_contract_generation.py tests/contract/test_ai_backend_roundtrip.py
- [ ] Commit: feat(contracts): freeze public http websocket and safety schemas

### Task B-03：MySQL schema、加密类型、message_ordinal 与 retention 基础

**Working directory:** repository root

**depends_on:** B-01、B-02。

**produces:** async MySQL session factory、AES-GCM envelope、初始 Alembic schema、所有核心表/约束、数据库时钟和 retention policy primitives。

**Files:**
- Create: src/mental_health_api/database/base.py
- Create: src/mental_health_api/database/engine.py
- Create: src/mental_health_api/database/encryption.py
- Create: src/mental_health_api/database/models.py
- Create: src/mental_health_api/database/clock.py
- Create: src/mental_health_api/database/retention.py
- Create: alembic.ini
- Create: alembic/env.py
- Create: alembic/versions/0001_initial.py
- Test: tests/integration/test_mysql_schema.py
- Test: tests/integration/test_mysql_constraints.py
- Test: tests/security/test_encrypted_columns.py
- Test: tests/unit/database/test_retention_policy.py

**RED**

- [ ] 写测试锁定 GuestSession、Consent(subject/type/policy_version/consent_version/status/granted_at/withdrawn_at)、Conversation.persistence_mode/next_event_sequence、Message.message_ordinal、SafetyContext、outbox、recovery token、memory、内容、assessment、crisis、privacy job 与 audit 表；同一主体/同意类型的版本单调且 current 唯一，明确断言 Message 不存在 sequence 列。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/integration/test_mysql_schema.py tests/integration/test_mysql_constraints.py tests/security/test_encrypted_columns.py tests/unit/database/test_retention_policy.py -q
- [ ] Expected: FAIL，原因是 Alembic/schema/encryption 模块不存在。

**Implementation**

- [ ] AES-GCM 每值随机 nonce，以 object_type/object_id/field/key_version 为 AAD；数据库与 dump 均不出现明文 canary。
- [ ] messages 唯一顺序列命名 message_ordinal；outbox_events 才有 conversation_id+sequence unique。
- [ ] retention.py 精确表达第 2.6 节期限，使用注入 Clock，不能依赖本机时区。
- [ ] 在 MySQL 执行 upgrade → 空库 downgrade → upgrade；SQLite 只跑纯 policy 单元测试。

**GREEN**

- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test sh -lc "uv run alembic upgrade head && uv run pytest tests/integration/test_mysql_schema.py tests/integration/test_mysql_constraints.py tests/security/test_encrypted_columns.py tests/unit/database/test_retention_policy.py -q"
- [ ] Expected: PASS；数据库 schema 无 message.sequence，明文 canary 零命中。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/database alembic tests/integration/test_mysql_schema.py tests/integration/test_mysql_constraints.py tests/security/test_encrypted_columns.py tests/unit/database/test_retention_policy.py && uv run ruff format --check src/mental_health_api/database alembic tests/integration/test_mysql_schema.py tests/integration/test_mysql_constraints.py tests/security/test_encrypted_columns.py tests/unit/database/test_retention_policy.py && uv run mypy src/mental_health_api/database && git diff --check
- [ ] Expected: 全部 exit 0。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/database alembic.ini alembic tests/integration/test_mysql_schema.py tests/integration/test_mysql_constraints.py tests/security/test_encrypted_columns.py tests/unit/database/test_retention_policy.py
- [ ] Commit: feat(data): add encrypted mysql schema and retention primitives

### Task B-04：Guest session、pre-auth 主体与分项同意

**Working directory:** repository root

**depends_on:** B-02、B-03。

**produces:** POST/GET/DELETE /v1/guest-sessions、guest bearer authentication、24 小时清理、guest scopes、版本化 ConsentSnapshot 与 A `ConsentSnapshotPort` adapter，以及组织级、默认关闭的 `ProviderProcessingPolicyPort` adapter skeleton。

**Files:**
- Create: src/mental_health_api/guests/contracts.py
- Create: src/mental_health_api/guests/service.py
- Create: src/mental_health_api/guests/routes.py
- Create: src/mental_health_api/guests/cleanup.py
- Create: src/mental_health_api/auth/subjects.py
- Create: src/mental_health_api/consents/contracts.py
- Create: src/mental_health_api/consents/service.py
- Create: src/mental_health_api/consents/routes.py
- Create: src/mental_health_api/consents/ai_adapter.py
- Create: src/mental_health_api/provider_policy/contracts.py
- Create: src/mental_health_api/provider_policy/adapter.py
- Create: contracts/privacy/provider_processing_policy.schema.json
- Create: contracts/privacy/provider_processing_policy.canonical.json
- Test: tests/api/test_guest_sessions.py
- Test: tests/integration/test_guest_session_ttl.py
- Test: tests/security/test_guest_scope_isolation.py
- Test: tests/api/test_consents.py
- Test: tests/integration/test_cloud_consent_snapshot.py
- Test: tests/integration/test_provider_processing_policy_snapshot.py

**RED**

- [ ] 写测试：token 256 bit、明文不落库、HMAC lookup、24h 过期、撤销、跨 guest 对象 404、危机静态资源匿名可读、AI/WS 需 guest token、同意类型独立；ConsentSnapshot 精确字段、主体隔离、版本单调、撤回后的即时读取和数据库故障 fail closed。canonical/mutation rows 覆盖 missing→version0/两时间 null、granted→version≥1/granted_at 非空/withdrawn_at null、withdrawn→version≥1/两时间有序；missing 由当前 policy version 合成，不伪造 Consent 数据库行。另按 PRD 10.4 冻结 `ProviderProcessingPolicySnapshot` schema/canonical/mutation rows；缺配置、解析失败或 B-16 尚未批准时只能返回 `disabled`，不得由 B-04 自行构造 approved。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/api/test_guest_sessions.py tests/integration/test_guest_session_ttl.py tests/security/test_guest_scope_isolation.py tests/api/test_consents.py tests/integration/test_cloud_consent_snapshot.py tests/integration/test_provider_processing_policy_snapshot.py -q
- [ ] Expected: FAIL，首个失败为 /v1/guest-sessions 404 或 guests 模块不存在。

**Implementation**

- [ ] guest_subject_id 与 token 都由服务端生成；客户端 guest_id/device id 不参与授权。token 只返回一次，Keychain 保存责任交给 C。
- [ ] DELETE current 先撤销 token，再创建清理 job；清理失败保持 revoked 且可重试，不能恢复访问。
- [ ] 核心、云模型、记忆、趋势、训练同意独立；guest 不允许长期记忆 scope。A adapter 的 `ConsentSnapshot` 精确含 subject_id、consent_type=cloud_model_processing、policy_version、consent_version、status=granted|withdrawn|missing、可空 granted_at、可空 withdrawn_at、loaded_at；missing 固定 version=0/两时间 null，granted 固定 version>=1/granted_at 非空/withdrawn_at null，withdrawn 固定 version>=1/两时间非空且撤回时间不早于授权。canonical/mutation tests 拒绝全部非法组合；每次读取查询当前主体最新版本，不缓存跨 turn，不返回正文或其他同意。
- [ ] `ProviderProcessingPolicyPort` 与用户 ConsentSnapshot 完全分离。B-04 仅提供严格 DTO、canonical schema 和 default-disabled adapter：所有批准引用为 null、`cross_border_status=blocked`；配置缺失、非法、未知 provider、时钟/matrix hash 错误均合成为 disabled。只有 B-16 在独立法律/隐私复核与工程矩阵均有效后才可提供 approved adapter；用户同意不能提升组织 policy。
- [ ] 按第 1.3 节重新生成 OpenAPI；所有 route 的 subject 来源与 401/404 行为写入 schema。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_openapi.py --check
- [ ] Expected: PASS，OpenAPI 含 guest/consent routes 和 bearer scopes。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/api/test_guest_sessions.py tests/integration/test_guest_session_ttl.py tests/security/test_guest_scope_isolation.py tests/api/test_consents.py tests/integration/test_cloud_consent_snapshot.py tests/integration/test_provider_processing_policy_snapshot.py -q
- [ ] Expected: PASS，数据库 token 明文零命中。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/guests src/mental_health_api/auth/subjects.py src/mental_health_api/consents src/mental_health_api/provider_policy tests/api/test_guest_sessions.py tests/api/test_consents.py tests/integration/test_guest_session_ttl.py tests/integration/test_cloud_consent_snapshot.py tests/integration/test_provider_processing_policy_snapshot.py tests/security/test_guest_scope_isolation.py && uv run ruff format --check src/mental_health_api/guests src/mental_health_api/auth/subjects.py src/mental_health_api/consents src/mental_health_api/provider_policy tests/api/test_guest_sessions.py tests/api/test_consents.py tests/integration/test_guest_session_ttl.py tests/integration/test_cloud_consent_snapshot.py tests/integration/test_provider_processing_policy_snapshot.py tests/security/test_guest_scope_isolation.py && uv run mypy src/mental_health_api/guests src/mental_health_api/auth/subjects.py src/mental_health_api/consents src/mental_health_api/provider_policy && git diff --check
- [ ] Expected: 全部 exit 0。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/guests src/mental_health_api/auth/subjects.py src/mental_health_api/consents src/mental_health_api/provider_policy contracts/privacy/provider_processing_policy.schema.json contracts/privacy/provider_processing_policy.canonical.json tests/api/test_guest_sessions.py tests/api/test_consents.py tests/integration/test_guest_session_ttl.py tests/integration/test_cloud_consent_snapshot.py tests/integration/test_provider_processing_policy_snapshot.py tests/security/test_guest_scope_isolation.py contracts/openapi/openapi.json
- [ ] Commit: feat(guest): add scoped temporary identities and consent

### Task B-05：正式账户、设备、token 旋转与 Mailpit 密码找回

**Working directory:** repository root

**depends_on:** B-02、B-03、B-04。

**produces:** 注册/登录/刷新/退出/设备撤销、RecoveryMailer port、Mailpit adapter、15 分钟 recovery token、authenticated_subject_id。

**Files:**
- Create: src/mental_health_api/auth/passwords.py
- Create: src/mental_health_api/auth/tokens.py
- Create: src/mental_health_api/auth/service.py
- Create: src/mental_health_api/auth/routes.py
- Create: src/mental_health_api/accounts/contracts.py
- Create: src/mental_health_api/accounts/service.py
- Create: src/mental_health_api/accounts/routes.py
- Create: src/mental_health_api/recovery/ports.py
- Create: src/mental_health_api/recovery/service.py
- Create: src/mental_health_api/recovery/mailpit.py
- Test: tests/api/test_auth.py
- Test: tests/security/test_auth_attacks.py
- Test: tests/integration/test_password_recovery_mailpit.py
- Test: tests/integration/test_device_revocation.py

**RED**

- [ ] 写邮箱枚举、弱密码、refresh 重放/family revoke、guest proof 缺失、设备撤销、recovery 202 恒等、token 15 分钟/单次使用、邮件无心理正文测试。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/api/test_auth.py tests/security/test_auth_attacks.py tests/integration/test_password_recovery_mailpit.py tests/integration/test_device_revocation.py -q
- [ ] Expected: FAIL，原因是 auth/recovery routes 不存在。

**Implementation**

- [ ] 邮箱 lookup 使用 pepper HMAC，邮箱正文加密，密码使用 Argon2id；access JWT 短期，refresh 为 256 bit opaque token 且只存摘要。
- [ ] 注册必须消费有效 guest/pre-auth subject；昵称先留给 B-08 的 profile.nickname 安全门，未接安全门前 route 必须 fail closed。
- [ ] recovery request 不泄露邮箱是否存在；Mailpit adapter 只发送一次性链接/码和中性文案。
- [ ] 成功恢复撤销全部 refresh family 与 WS session version。
- [ ] 重新生成 OpenAPI 并 byte compare。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_openapi.py --check
- [ ] Expected: PASS，recovery 两个 route 与公开错误已冻结。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/api/test_auth.py tests/security/test_auth_attacks.py tests/integration/test_password_recovery_mailpit.py tests/integration/test_device_revocation.py -q
- [ ] Expected: PASS；Mailpit API 中只有合成测试邮件，恢复后旧 refresh 全失效。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/auth src/mental_health_api/accounts src/mental_health_api/recovery tests/api/test_auth.py tests/security/test_auth_attacks.py tests/integration/test_password_recovery_mailpit.py tests/integration/test_device_revocation.py && uv run ruff format --check src/mental_health_api/auth src/mental_health_api/accounts src/mental_health_api/recovery tests/api/test_auth.py tests/security/test_auth_attacks.py tests/integration/test_password_recovery_mailpit.py tests/integration/test_device_revocation.py && uv run mypy src/mental_health_api/auth src/mental_health_api/accounts src/mental_health_api/recovery && git diff --check
- [ ] Expected: 全部 exit 0。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/auth src/mental_health_api/accounts src/mental_health_api/recovery tests/api/test_auth.py tests/security/test_auth_attacks.py tests/integration/test_password_recovery_mailpit.py tests/integration/test_device_revocation.py contracts/openapi/openapi.json
- [ ] Commit: feat(auth): close account device and recovery lifecycle

### Task B-06：Conversation、message_ordinal、幂等与事务 outbox

**Working directory:** repository root

**depends_on:** B-02、B-03、B-04、B-05。

**produces:** conversation repository、persistence_mode、message_ordinal、Idempotency claim、outbox sequence allocator、基础会话 REST。

**Files:**
- Create: src/mental_health_api/conversations/contracts.py
- Create: src/mental_health_api/conversations/repository.py
- Create: src/mental_health_api/conversations/service.py
- Create: src/mental_health_api/conversations/routes.py
- Create: src/mental_health_api/conversations/idempotency.py
- Create: src/mental_health_api/conversations/outbox.py
- Create: src/mental_health_api/conversations/event_sequence.py
- Test: tests/integration/test_conversation_idempotency.py
- Test: tests/integration/test_outbox_atomicity.py
- Test: tests/integration/test_outbox_sequence.py
- Test: tests/api/test_conversations.py

**RED**

- [ ] 写 MySQL 测试：guest/account owner、ephemeral/saved、同键同请求重放、同键不同 body 冲突、并发 claim、commit rollback、首事件 sequence=0、跨 bundle 连续、message_ordinal 与 event sequence 不相等也不复用。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/integration/test_conversation_idempotency.py tests/integration/test_outbox_atomicity.py tests/integration/test_outbox_sequence.py tests/api/test_conversations.py -q
- [ ] Expected: FAIL，首个失败为 conversations repository/route 不存在。

**Implementation**

- [ ] 使用 MySQL unique constraint 与 SELECT FOR UPDATE 实现 Idempotency claim；进程内锁不能作为正确性条件。
- [ ] conversation.next_event_sequence 初始 0；同一事务锁定 conversation、按逻辑事件顺序写 outbox、推进游标。rollback 不消耗 sequence。
- [ ] message_ordinal 只在消息事务内递增；模型一个 response 的多个 delta 只占一个 assistant message ordinal、多个 event sequence。
- [ ] guest 与 account ephemeral expires_at 最长 24h；saved 只允许正式账户。
- [ ] title create/patch 已标注 conversation.title 与 Idempotency-Key，但在 B-08 接入安全门前，有 title 的请求必须返回 SAFETY_GATE_UNAVAILABLE 且不写入；无 title 可创建。
- [ ] 重新生成 OpenAPI 并 byte compare。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_openapi.py --check
- [ ] Expected: PASS，conversation create/list/detail/patch/delete/export contract 稳定。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/integration/test_conversation_idempotency.py tests/integration/test_outbox_atomicity.py tests/integration/test_outbox_sequence.py tests/api/test_conversations.py -q
- [ ] Expected: PASS，每个测试 conversation 的 event sequence 精确等于 range(event_count)。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/conversations tests/integration/test_conversation_idempotency.py tests/integration/test_outbox_atomicity.py tests/integration/test_outbox_sequence.py tests/api/test_conversations.py && uv run ruff format --check src/mental_health_api/conversations tests/integration/test_conversation_idempotency.py tests/integration/test_outbox_atomicity.py tests/integration/test_outbox_sequence.py tests/api/test_conversations.py && uv run mypy src/mental_health_api/conversations && git diff --check
- [ ] Expected: 全部 exit 0；rg -n "message.*sequence|messages\.sequence" src/mental_health_api/conversations tests 返回零个业务字段命中。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/conversations tests/integration/test_conversation_idempotency.py tests/integration/test_outbox_atomicity.py tests/integration/test_outbox_sequence.py tests/api/test_conversations.py contracts/openapi/openapi.json
- [ ] Commit: feat(conversations): add ordinal messages and atomic event outbox

### Task B-07：WS ticket、双向 command/event、ACK CAS、resume 与 cancel

**Working directory:** repository root

**depends_on:** B-02、B-04、B-05、B-06。

**produces:** POST /v1/realtime/tickets、WS /v1/realtime、严格 command decoder、ServerEvent dispatcher、ACK CAS/resume/cancel。

**Files:**
- Create: src/mental_health_api/realtime/tickets.py
- Create: src/mental_health_api/realtime/contracts.py
- Create: src/mental_health_api/realtime/connection.py
- Create: src/mental_health_api/realtime/dispatcher.py
- Create: src/mental_health_api/realtime/routes.py
- Test: tests/integration/test_websocket_protocol.py
- Test: tests/integration/test_websocket_ack_resume.py
- Test: tests/security/test_websocket_auth.py
- Test: tests/performance/test_websocket_backpressure.py

**RED**

- [ ] 写测试：guest/account ticket、60 秒/单次使用、token 不进 URL、command 有 sequence 拒绝、首 event 0、last_ack=-1、ACK 倒退/越 gap/跨会话拒绝、CAS 并发、断线 resume、跨 bundle 连续、cancel 与安全事件竞态、慢消费者。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/integration/test_websocket_protocol.py tests/integration/test_websocket_ack_resume.py tests/security/test_websocket_auth.py tests/performance/test_websocket_backpressure.py -q
- [ ] Expected: FAIL，原因是 realtime routes/dispatcher 不存在。

**Implementation**

- [ ] ticket 绑定 subject、guest/account session、device_key_hash、conversation_id，消费原子；URL 只含 ticket。
- [ ] decoder 只接受 client_commands.schema.json；dispatcher 只发 server_events.schema.json。
- [ ] ACK 在 MySQL 使用 compare-and-set，只推进最高连续已发 sequence；resume 只读取已提交 outbox 且条件 sequence > last_ack。
- [ ] generation.cancel 只取消未提交普通生成；risk.status、safety.question、safety.resources 与已提交 outbox 不受取消。
- [ ] 重新生成 OpenAPI/WS schema，运行两个生成器 --check。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_ws_contracts.py --write && uv run python scripts/export_openapi.py --check && uv run python scripts/export_ws_contracts.py --check
- [ ] Expected: PASS，client_commands 不含 sequence。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/integration/test_websocket_protocol.py tests/integration/test_websocket_ack_resume.py tests/security/test_websocket_auth.py tests/performance/test_websocket_backpressure.py -q
- [ ] Expected: PASS，断线重放无丢失且逻辑重复数为 0。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/realtime tests/integration/test_websocket_protocol.py tests/integration/test_websocket_ack_resume.py tests/security/test_websocket_auth.py tests/performance/test_websocket_backpressure.py && uv run ruff format --check src/mental_health_api/realtime tests/integration/test_websocket_protocol.py tests/integration/test_websocket_ack_resume.py tests/security/test_websocket_auth.py tests/performance/test_websocket_backpressure.py && uv run mypy src/mental_health_api/realtime && git diff --check
- [ ] Expected: 全部 exit 0；不存在 contracts/ws/events.schema.json。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/realtime tests/integration/test_websocket_protocol.py tests/integration/test_websocket_ack_resume.py tests/security/test_websocket_auth.py tests/performance/test_websocket_backpressure.py contracts/openapi/openapi.json contracts/ws
- [ ] Commit: feat(realtime): add typed commands cas ack and resume

### Task B-08：统一 FreeTextSafetyGateway、SafetyContext、answer/recheck 与 AI 门禁

**Working directory:** repository root

**depends_on:** B-02、B-03、B-06、B-07；外部只依赖 A-04 已发布的 free_text_safety 与 answer decision contracts。A-11 assessment trigger 不属于本任务依赖，由 B-14 在 B-12 Stage 1/A-11 完成后消费。

**produces:** 十入口 registry、context_ref builder、SafetyContext transaction、SafetyRequiredResponse、safety.answer/recheck handler、A safety adapter，以及仅聊天 L0 可消费的 `screening_decision_id` 交接；一个 turn 全链路只筛查一次。

**Files:**
- Create: src/mental_health_api/safety/free_text_registry.py
- Create: src/mental_health_api/safety/context_ref.py
- Create: src/mental_health_api/safety/gateway.py
- Create: src/mental_health_api/safety/contexts.py
- Create: src/mental_health_api/safety/answers.py
- Create: src/mental_health_api/safety/routes.py
- Create: src/mental_health_api/ai_bridge/safety_adapter.py
- Test: tests/contract/test_free_text_registry.py
- Test: tests/contract/test_safety_contracts.py
- Test: tests/integration/test_free_text_safety_transaction.py
- Test: tests/integration/test_safety_answer_recheck.py
- Test: tests/security/test_free_text_context_authorization.py

**RED**

- [ ] 写十入口精确集合与 grammar mutation tests；伪造 context_ref、route/field 错配、缺 Idempotency-Key、安全依赖超时都应 fail closed。
- [ ] 写 safe_now/unsure/not_safe 状态表测试、同键同答案重放、同键不同答案冲突、已回答不可突变、recheck 新 question、assessment release/held 与 generic 不重放旧正文。
- [ ] 写聊天单筛查测试：gateway+turn 合计 `screen_text` 调用次数精确为 1，B 将 allow 的 `screening_decision_id` 交给 `run_screened_turn`；过期、进程重启模拟、主体/会话/幂等错配必须 fail closed 且原业务写入为零。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_free_text_registry.py tests/contract/test_safety_contracts.py tests/integration/test_free_text_safety_transaction.py tests/integration/test_safety_answer_recheck.py tests/security/test_free_text_context_authorization.py -q
- [ ] Expected: FAIL，首个失败为 safety registry/context 模块不存在。

**Implementation**

- [ ] B 从鉴权 route/object 构造 FreeTextSafetyRequest 九字段；request.text 只驻留内存，不进入 repr/log/trace/error/outbox。
- [ ] L0 才调用 on_l0_write；聊天 L0 不把 redacted text 跨服务持久化，而是把 A 返回的短 TTL、一次性、主体/会话/幂等绑定 `screening_decision_id` 交给 `run_screened_turn`。B 不再次调用 `screen_text`；proof 过期/丢失时用原业务幂等键重新进入 gateway。
- [ ] L1 在安全事务创建/复用 conversation、SafetyContext 和 safety.question；L2/L3 另写最小 CrisisEvent、risk.status、safety.resources。L1 response event 指向 question；L2/L3 指向首个 risk.status；REST/WS/event replay 精确同 ID。任一失败全回滚。
- [ ] 无 conversation 时创建 mode=free_text_safety；已有 conversation 必须通过 subject 授权。
- [ ] 实现第 2.3 节 answer 状态表。assessment safe_now 与 released/available 同事务；unsure/not_safe 保持 held。
- [ ] POST /v1/safety-contexts/{safety_context_id}/rechecks 只接受可 recheck 状态，并产生新的 server-owned question_event_id。
- [ ] 将 B-05 register nickname 与 B-06 title create/patch 接入 gateway；安全分支普通写入为零。
- [ ] 重新生成 OpenAPI/WS schema 并 byte compare。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_ws_contracts.py --write && uv run python scripts/export_openapi.py --check && uv run python scripts/export_ws_contracts.py --check
- [ ] Expected: PASS，SafetyRequiredResponse 与 answer/recheck route 可由 C 生成类型。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_free_text_registry.py tests/contract/test_safety_contracts.py tests/integration/test_free_text_safety_transaction.py tests/integration/test_safety_answer_recheck.py tests/security/test_free_text_context_authorization.py -q
- [ ] Expected: PASS，三种回答分支和事务回滚全部符合第 2.3 节。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/safety src/mental_health_api/ai_bridge/safety_adapter.py tests/contract/test_free_text_registry.py tests/contract/test_safety_contracts.py tests/integration/test_free_text_safety_transaction.py tests/integration/test_safety_answer_recheck.py tests/security/test_free_text_context_authorization.py && uv run ruff format --check src/mental_health_api/safety src/mental_health_api/ai_bridge/safety_adapter.py tests/contract/test_free_text_registry.py tests/contract/test_safety_contracts.py tests/integration/test_free_text_safety_transaction.py tests/integration/test_safety_answer_recheck.py tests/security/test_free_text_context_authorization.py && uv run mypy src/mental_health_api/safety src/mental_health_api/ai_bridge/safety_adapter.py && git diff --check
- [ ] Expected: 全部 exit 0。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/safety src/mental_health_api/ai_bridge/safety_adapter.py tests/contract/test_free_text_registry.py tests/contract/test_safety_contracts.py tests/integration/test_free_text_safety_transaction.py tests/integration/test_safety_answer_recheck.py tests/security/test_free_text_context_authorization.py contracts/openapi/openapi.json contracts/ws contracts/safety
- [ ] Commit: feat(safety): centralize text screening contexts and answers

### Task B-09：Guest migration 的逐项筛查、去重与全批原子提交

**Working directory:** repository root

**depends_on:** B-04、B-05、B-08。

**produces:** /v1/guest-migrations preview/create/status、active guest proof、稳定 item 去重、迁移 commit proof。

**Files:**
- Create: src/mental_health_api/guest_migrations/contracts.py
- Create: src/mental_health_api/guest_migrations/service.py
- Create: src/mental_health_api/guest_migrations/routes.py
- Create: src/mental_health_api/guest_migrations/repository.py
- Test: tests/contract/test_guest_migration_contract.py
- Test: tests/integration/test_guest_migration.py
- Test: tests/integration/test_guest_migration_safety.py
- Test: tests/security/test_guest_migration_subject_merge.py

**RED**

- [ ] 写 active guest proof、batch/item 稳定 ID、server temp 与 SQLite 上传去重、选择类型、标签排序筛查、首个非 L0 整批零写入、重复 batch 同 commit proof、跨 user/设备合并拒绝、清理仅在 commit proof 后测试。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_guest_migration_contract.py tests/integration/test_guest_migration.py tests/integration/test_guest_migration_safety.py tests/security/test_guest_migration_subject_merge.py -q
- [ ] Expected: FAIL，原因是 guest_migrations 模块/routes 不存在。

**Implementation**

- [ ] request 固定含 batch_id、选择的 record_types 和按 item_id 稳定排序的 items；客户端 ID 只做批内去重，不决定 subject ownership。
- [ ] 服务端从 guest token 解析 source subject，从新账户 token 解析 target；禁止 device ID、email 或客户端 guest_id 合并。
- [ ] 所有 label 使用派生 item idempotency key 和 guest-migration:{batch_id}:item:{item_id} context_ref 逐项筛查；全部 L0 后才在一个 MySQL 事务导入。
- [ ] 第一个非 L0 创建一个 SafetyContext 并返回可重放 SafetyRequiredResponse，迁移表增量为零。
- [ ] commit proof 含 batch_id、迁移 item IDs、server commit timestamp 与 digest；C 收到后才清本地。
- [ ] 重新生成 OpenAPI 并 byte compare。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_openapi.py --check
- [ ] Expected: PASS。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_guest_migration_contract.py tests/integration/test_guest_migration.py tests/integration/test_guest_migration_safety.py tests/security/test_guest_migration_subject_merge.py -q
- [ ] Expected: PASS，重复/并发批次只产生一个 commit proof。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/guest_migrations tests/contract/test_guest_migration_contract.py tests/integration/test_guest_migration.py tests/integration/test_guest_migration_safety.py tests/security/test_guest_migration_subject_merge.py && uv run ruff format --check src/mental_health_api/guest_migrations tests/contract/test_guest_migration_contract.py tests/integration/test_guest_migration.py tests/integration/test_guest_migration_safety.py tests/security/test_guest_migration_subject_merge.py && uv run mypy src/mental_health_api/guest_migrations && git diff --check
- [ ] Expected: 全部 exit 0。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/guest_migrations tests/contract/test_guest_migration_contract.py tests/integration/test_guest_migration.py tests/integration/test_guest_migration_safety.py tests/security/test_guest_migration_subject_merge.py contracts/openapi/openapi.json
- [ ] Commit: feat(guest): migrate selected records atomically

### Task B-10：AI turn bridge、实时聊天、会话总结与通用反馈

**Working directory:** repository root

**depends_on:** B-04、B-06、B-07、B-08；外部依赖 A-09 已提交的 ReviewedStreamChunk，以及 A-12 已提交的 AiTurnRequest/Response、ConsentSnapshot 和 ProviderProcessingPolicy contracts。

**produces:** message.send 安全纵向链路、A TurnRepository adapter、ReviewedStreamChunk → ServerEventEnvelope、会话总结、POST/GET feedback。

**Files:**
- Create: src/mental_health_api/ai_bridge/turn_adapter.py
- Create: src/mental_health_api/ai_bridge/repository.py
- Create: src/mental_health_api/ai_bridge/service.py
- Create: src/mental_health_api/conversations/summary.py
- Create: src/mental_health_api/feedback/contracts.py
- Create: src/mental_health_api/feedback/service.py
- Create: src/mental_health_api/feedback/routes.py
- Test: tests/integration/test_ai_turn_bridge.py
- Test: tests/integration/test_reviewed_chunk_outbox.py
- Test: tests/integration/test_ai_cloud_consent_gate.py
- Test: tests/integration/test_ai_provider_policy_gate.py
- Test: tests/api/test_conversation_summary.py
- Test: tests/api/test_feedback.py
- Test: tests/integration/test_feedback_safety.py

**RED**

- [ ] 写 message.send → chat.message gateway → A run_turn → MySQL message/response/outbox → WS 的真实适配测试；断言 B 只按 chunk_index 排序并独占 sequence。对当前输入/历史/授权记忆/知识/最终 payload 的 PII canary、NER unavailable/OOD/offset 错误、CloudSafePayloadProof hash/TTL 错配、provider policy disabled/expired/invalid/read-failure，以及 cloud consent granted/missing/withdrawn/读取失败/请求中途撤回逐项使用真实 adapter 和 provider spy；断言唯一顺序为 proof consume=1 → policy read=1 → approved 时 consent read=1 → granted 时 dispatch=1，其他分支 dispatch=0。
- [ ] 写 summary 输出复核、不会自动创建 memory、反馈 target/category 判别联合、owner 校验、comment 安全门、重复 Idempotency-Key 测试。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/integration/test_ai_turn_bridge.py tests/integration/test_reviewed_chunk_outbox.py tests/integration/test_ai_cloud_consent_gate.py tests/integration/test_ai_provider_policy_gate.py tests/api/test_conversation_summary.py tests/api/test_feedback.py tests/integration/test_feedback_safety.py -q
- [ ] Expected: FAIL，首个失败为 turn adapter/feedback route 不存在。

**Implementation**

- [ ] message.send 先走 B-08；L0 只把 `screening_decision_id` 与已鉴权 request metadata 传给 A 的 `run_screened_turn`，不得传持久化明文/脱敏正文，也不得二次调用 `screen_text`；非 L0 直接返回同一个 SafetyRequiredResponse 分支。
- [ ] 在实现 handler 前把 A-09 reviewed-stream 与 A-12 turn/consent schema 注册到 B adapter/canonical round-trip；重新生成 OpenAPI/WS 后 byte-compare，证明 B-02 的基础 skeleton 没有被静默改义。
- [ ] `mental_health_ai`、FreeTextSafetyGateway、DecisionStore、TurnOrchestrator、ProviderProcessingPolicy/ConsentSnapshot adapters 与 TurnRepository adapter 在同一单 worker FastAPI 进程；不得通过独立 AI service/RPC 传递 proof。A 在 provider dispatch 前先调用 B-04 policy adapter，再在 approved 分支即时加载当前主体 consent snapshot；B 不把旧 snapshot 放入 message/outbox/Redis。B-10 只用 default-disabled 与合成 approved fake 验证顺序，真实 approved 配置在 B-16 集成门禁验证。
- [ ] TurnRepository commit 在一个事务写 user message、assistant response、emotion reference 与 outbox；按 ReviewedStreamChunk.chunk_index 生成 response.delta/completed，分配最终 sequence。
- [ ] 禁止 SafeStreamEvent 类型或 A sequence 字段。
- [ ] POST /v1/conversations/{id}/summary 只返回已输出复核 summary；用户必须另行调用 memory API 才能保存。
- [ ] feedback 判别联合精确为：`ai_response -> helpful|not_helpful|inaccurate|uncomfortable`、`knowledge_article -> inaccurate|outdated|unclear`、`crisis_event -> false_positive`；完成练习的 1–5 评分仍归 B-13 exercise session，不混入通用 union。POST `/v1/feedback` 创建，GET `/v1/feedback/{id}` 只读本人状态；target ownership 先授权，optional comment 使用 feedback.comment gateway，危机误报只进入复核队列、绝不解除风险或撤回安全事件。
- [ ] 重新生成 OpenAPI/WS schema 并 byte compare。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_ws_contracts.py --write && uv run python scripts/export_openapi.py --check && uv run python scripts/export_ws_contracts.py --check
- [ ] Expected: PASS。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/integration/test_ai_turn_bridge.py tests/integration/test_reviewed_chunk_outbox.py tests/integration/test_ai_cloud_consent_gate.py tests/integration/test_ai_provider_policy_gate.py tests/api/test_conversation_summary.py tests/api/test_feedback.py tests/integration/test_feedback_safety.py -q
- [ ] Expected: PASS，gateway+turn 每个 message 的 `screen_text` 调用数=1、未审核 token 数=0、重复逻辑 event 数=0。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/ai_bridge src/mental_health_api/conversations/summary.py src/mental_health_api/feedback tests/integration/test_ai_turn_bridge.py tests/integration/test_reviewed_chunk_outbox.py tests/integration/test_ai_cloud_consent_gate.py tests/integration/test_ai_provider_policy_gate.py tests/api/test_conversation_summary.py tests/api/test_feedback.py tests/integration/test_feedback_safety.py && uv run ruff format --check src/mental_health_api/ai_bridge src/mental_health_api/conversations/summary.py src/mental_health_api/feedback tests/integration/test_ai_turn_bridge.py tests/integration/test_reviewed_chunk_outbox.py tests/integration/test_ai_cloud_consent_gate.py tests/integration/test_ai_provider_policy_gate.py tests/api/test_conversation_summary.py tests/api/test_feedback.py tests/integration/test_feedback_safety.py && uv run mypy src/mental_health_api/ai_bridge src/mental_health_api/conversations/summary.py src/mental_health_api/feedback && git diff --check
- [ ] Expected: 全部 exit 0；rg -n "SafeStreamEvent" src/mental_health_api tests 返回零命中。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/ai_bridge/turn_adapter.py src/mental_health_api/ai_bridge/repository.py src/mental_health_api/ai_bridge/service.py src/mental_health_api/conversations/summary.py src/mental_health_api/feedback tests/integration/test_ai_turn_bridge.py tests/integration/test_reviewed_chunk_outbox.py tests/integration/test_ai_cloud_consent_gate.py tests/integration/test_ai_provider_policy_gate.py tests/api/test_conversation_summary.py tests/api/test_feedback.py tests/integration/test_feedback_safety.py contracts/openapi/openapi.json contracts/ws
- [ ] Commit: feat(chat): connect reviewed ai turns summaries and feedback

### Task B-11：Emotion 持久化/纠正/趋势与 Memory capability/context proof

**Working directory:** repository root

**depends_on:** B-06、B-08、B-10；消费 A 的 emotion_result.schema.json 与 canonical rows。

**produces:** 情绪结果无损 MySQL/WS/REST 映射、纠正/趋势 B-owned schemas、长期记忆 CRUD、memory capability、context proof、memory.mode.changed。

**Files:**
- Create: src/mental_health_api/emotions/contracts.py
- Create: src/mental_health_api/emotions/service.py
- Create: src/mental_health_api/emotions/routes.py
- Create: contracts/emotions/emotion_correction.schema.json
- Create: contracts/emotions/emotion_trend.schema.json
- Create: contracts/emotions/canonical_rows.json
- Create: src/mental_health_api/memory/contracts.py
- Create: src/mental_health_api/memory/capability.py
- Create: src/mental_health_api/memory/service.py
- Create: src/mental_health_api/memory/routes.py
- Modify: contracts/memory/memory_capability.schema.json
- Modify: contracts/memory/context_proof.schema.json
- Modify: contracts/memory/canonical_rows.json
- Test: tests/contract/test_emotion_backend_mapping.py
- Test: tests/contract/test_memory_contracts.py
- Test: tests/integration/test_emotion_roundtrip.py
- Test: tests/integration/test_memory_capability_context_proof.py
- Test: tests/security/test_memory_isolation.py

**RED**

- [ ] 写 B-owned tests：A canonical emotion JSON 无损持久化/读回/WS/REST；纠正追加且原值不变；九键趋势；correction_note 安全门。
- [ ] 写 memory 默认关闭、allow/deny、visible/edit/disable/delete、memory_version、history_only、mode changed、context proof 不泄漏 value、跨用户 canary 与 tombstone 测试。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_emotion_backend_mapping.py tests/contract/test_memory_contracts.py tests/integration/test_emotion_roundtrip.py tests/integration/test_memory_capability_context_proof.py tests/security/test_memory_isolation.py -q
- [ ] Expected: FAIL，原因是 emotions/memory 模块或 B-owned schema 不存在；不得创建 tests/contract/test_emotion_result_contract.py。

**Implementation**

- [ ] EmotionResult 的标签/强度/置信/不确定语义只从 A schema 生成；B 只做 schema validation、存储、授权、REST/WS 映射。
- [ ] correction_note 使用 emotion.correction_note context_ref，所有 correction REST 请求要求 Idempotency-Key；趋势只聚合已授权、未删除数据。
- [ ] GET /v1/memory-capability 固定返回 mode、reason、policy_version、effective_at、memory_version；mode 变化写 memory.mode.changed outbox。
- [ ] GET /v1/conversations/{id}/context-proof 返回 mode、included_memory_ids、exclusion_reason_codes、policy_version，不返回记忆值/消息。
- [ ] memory CRUD 只接受 allowlist，危机、量表答案、联系人、推断标签拒绝；memory.value 全部走 B-08。
- [ ] 删除或隔离门禁失败时原子切 history_only，并使旧 memory_version 失效。
- [ ] 重新生成 OpenAPI/WS 与 B-owned emotion/memory schemas；首次生成使用临时 byte compare + git add -N。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_ws_contracts.py --write && uv run python scripts/export_openapi.py --check && uv run python scripts/export_ws_contracts.py --check
- [ ] Expected: PASS。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_emotion_backend_mapping.py tests/contract/test_memory_contracts.py tests/integration/test_emotion_roundtrip.py tests/integration/test_memory_capability_context_proof.py tests/security/test_memory_isolation.py -q
- [ ] Expected: PASS，删除 memory ID 不再出现在任何后续 context proof。
- [ ] Run: uv run pytest tests/contract/test_emotion_result_contract.py -q
- [ ] Expected: PASS；该文件仍由 A 所有，B 不修改、不暂存。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/emotions src/mental_health_api/memory tests/contract/test_emotion_backend_mapping.py tests/contract/test_memory_contracts.py tests/integration/test_emotion_roundtrip.py tests/integration/test_memory_capability_context_proof.py tests/security/test_memory_isolation.py && uv run ruff format --check src/mental_health_api/emotions src/mental_health_api/memory tests/contract/test_emotion_backend_mapping.py tests/contract/test_memory_contracts.py tests/integration/test_emotion_roundtrip.py tests/integration/test_memory_capability_context_proof.py tests/security/test_memory_isolation.py && uv run mypy src/mental_health_api/emotions src/mental_health_api/memory && git diff --check
- [ ] Expected: 全部 exit 0；git diff --name-only 不含 tests/contract/test_emotion_result_contract.py。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/emotions src/mental_health_api/memory contracts/emotions contracts/memory tests/contract/test_emotion_backend_mapping.py tests/contract/test_memory_contracts.py tests/integration/test_emotion_roundtrip.py tests/integration/test_memory_capability_context_proof.py tests/security/test_memory_isolation.py contracts/openapi/openapi.json contracts/ws
- [ ] Commit: feat(personalization): add emotion mapping and provable memory mode

### Task B-12：24 个内容制品、source/review registry、知识 API 与唯一 RAG adapter

**Working directory:** repository root

**depends_on:** Stage 1 depends_on B-03、B-08，以及指定内容作者在工程外一次性交付的不可变作者包：`source-register.json`、精确 24 个草稿和已签署 `content-author-handoff.v1.json`；B 预先只公布本节冻结的 source/review/handoff schema 规范，不要求作者依赖尚未提交的仓库实例。Stage 2 depends_on 已提交的 B-12 Stage 1、A-11 `a-content-safety-review.v1.json` 与独立领域审核人提供的 `independent-domain-review.v1.json`。内容作者不是 A/B/C 工程 owner；独立审核人不得是 draft author、A content-safety reviewer 或 B release validator。任一 handoff 缺失时 Stage 1/Stage 2 必须停在对应未发布状态，active registry 保持为空。

**produces:** Stage 1 产 source/review/handoff schema、24 个有来源的未发布草稿、pending registry 与 fail-closed knowledge adapter skeleton；Stage 2 才产 24 条三阶段 active release approval record、8 知识+12 练习+2 量表+1 危机+1 safety UI 的已批准内容、MySQL import/withdraw、POST knowledge search、KnowledgeRetrieverPort adapter、ETag 与 Recall@3 门禁。

**Files:**
- Create: content/sources/source-register.schema.json
- Integrate/Validate（指定内容作者随不可变作者包提供，B 只校验 schema、来源与许可依据）：content/sources/source-register.json
- Create: content/reviews/review-record.schema.json
- Create: content/reviews/review-register.json
- Create: content/reviews/pending-register.json
- Create: content/reviews/review-stage-handoff.schema.json
- Consume (designated content author owns): content/reviews/handoffs/content-author-handoff.v1.json
- Consume (A-11 owns): content/reviews/handoffs/a-content-safety-review.v1.json
- Consume (independent reviewer owns): content/reviews/handoffs/independent-domain-review.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/knowledge/manifest.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/knowledge/articles/emotion_basics.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/knowledge/articles/anxiety_self_help.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/knowledge/articles/stress_management.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/knowledge/articles/sleep_and_emotions.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/knowledge/articles/when_to_seek_help.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/knowledge/articles/how_counseling_works.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/knowledge/articles/crisis_support_guide.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/knowledge/articles/mindfulness_cbt_basics.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/exercises/manifest.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/assessments/phq9.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/assessments/gad7.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/crisis/china-mainland.zh-CN.v1.json
- Integrate/Validate（指定内容作者拥有正文，B 只拥有 schema、文件路径、序列化与校验）：content/safety/ui-manifest.zh-CN.v1.json
- Create: src/mental_health_api/content/importer.py
- Create: src/mental_health_api/content/validator.py
- Create: src/mental_health_api/knowledge/contracts.py
- Create: src/mental_health_api/knowledge/service.py
- Create: src/mental_health_api/knowledge/routes.py
- Create: src/mental_health_api/knowledge/retriever_adapter.py
- Create: tests/evaluation/data/rag_queries.jsonl
- Test: tests/contract/test_source_register.py
- Test: tests/contract/test_content_draft_handoff.py
- Test: tests/contract/test_review_register.py
- Test: tests/contract/test_content_semantics.py
- Test: tests/contract/test_knowledge_manifest.py
- Test: tests/integration/test_knowledge_lifecycle.py
- Test: tests/evaluation/test_rag_recall.py

**Stage 1 — source、草稿与审核交接骨架（不得发布）**

- [ ] RED：写 `test_content_draft_handoff.py` 和 source/manifest tests，要求 handoff schema、指定 content author、精确 24 个 draft tuple/checksum/source_refs、`pending-register.json` 24 条、`review-register.json` 空数组；任一 draft 标为 published/approved 或知识 adapter 返回正文均失败。
- [ ] Run: `docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_source_register.py tests/contract/test_content_draft_handoff.py tests/contract/test_knowledge_manifest.py -q`
- [ ] Expected: FAIL，首个失败为 source/handoff/pending/content draft 不存在。
- [ ] 实现 source record 与 review/handoff schema；指定内容作者在工程外按冻结 schema 一次性交付 `source-register.json`、精确 24 个草稿和 `content-author-handoff.v1.json`，handoff 逐项含 author_id、content tuple、draft checksum、source refs、authored_at 和签名/确认。B 只验证作者包内部引用、来源、许可、checksum 并落成 Git 草稿，不把自己写成作者或审核人。
- [ ] `pending-register.json` 精确 24 条，状态固定 `pending_content_safety`；`review-register.json` 必须为空。24 个草稿均包含 `review_record_id` 预留、source refs、版本和 checksum，但不能出现 approved/published/临床背书。
- [ ] Knowledge REST/retriever 只建立契约和 fail-closed skeleton；对 pending 内容固定返回 unpublished/not_available，严禁 Stage 1 提前满足 Recall@3 或把草稿导入 MySQL published 集合。
- [ ] GREEN：运行 Stage 1 命令并断言 pending=24、active=0、published/imported=0、orphan=0；`git status --short` 无未归属内容文件。
- [ ] Stage 1 只暂存 B-owned schemas、pending/empty-active registry、knowledge/content fail-closed skeleton 与 Stage 1 tests，以及从不可变作者包集成且 B 不得改写的 author-owned `source-register.json`、24 个草稿和已签署 author handoff；提交 `feat(content): stage sourced drafts and review handoffs`。A-11 必须从包含该 commit 的 clean clone 开始。

**Stage 2 RED — 完整审核链、发布校验与导入**

- [ ] 写精确 24 制品/24 active release approval 一一映射测试：8 knowledge IDs、12 exercise IDs、PHQ9、GAD7、CN crisis、safety UI；缺项、额外、孤儿、重复 key、checksum/source/license/review-chain 不符均失败。
- [ ] 写语义测试：知识 claim、练习步骤/禁忌、量表授权、危机号码与 safety UI action 都映射 source_refs；forbidden_claims 与非诊断/退出文案不是空字符串检查。
- [ ] 写 POST search、Idempotency-Key、knowledge.search 安全门、published/approved/not-expired、ETag、withdraw gone、A adapter 同一 MySQL 事实源与 Recall@3>=0.90 测试。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_source_register.py tests/contract/test_content_draft_handoff.py tests/contract/test_review_register.py tests/contract/test_content_semantics.py tests/contract/test_knowledge_manifest.py tests/integration/test_knowledge_lifecycle.py tests/evaluation/test_rag_recall.py -q
- [ ] Expected: FAIL，首个失败为 A/独立领域 handoff 缺失、未批准，或 active review register 尚为空；不得在测试中自动生成审核签署。

**Stage 2 Implementation**

- [ ] 重新校验 Stage 1 source record 固定权威机构/作者、标题、URL/出版物 ID、许可/使用依据、地区、获取时间、版本、checksum；禁止 example.com、待补来源或无许可说明。Stage 1 commit 后任何正文变化都会改变 checksum，并强制重新取得 A 与独立审核 handoff。
- [ ] 先校验 A-11 handoff 与独立领域 handoff：两者精确覆盖同一 24 content tuple，input/output checksum 连续，decision approved，reviewer 与 author/相邻阶段分离；缺项、拒绝、needs_changes、签名/资格证据不符均保持 active=0 并非零退出。
- [ ] active review register 精确 24 行，review_record_id 与 content tuple 各自唯一；每条记录包含 `draft_author_id` 和精确三阶段 `review_chain`：content_safety_review、independent_domain_review、release_validation。每阶段字段名**精确**为 `reviewer_id`、`reviewer_role`、可空 `qualification_ref`、`reviewed_at`、`decision`、`input_checksum`；mutation tests 拒绝 `reviewer`、`role`、`qualification` 等别名。后一阶段 checksum 等于前一阶段批准版本，作者不得参与审核、相邻角色不得同人。qualification_ref 为空时公共文案只能写“项目内容审核”。
- [ ] 内容工作流固定为：指定内容作者基于 source register 起草并签 author handoff → A 签 content-safety handoff → 与作者/A/B 不同的独立领域/临床审核人签 independent handoff → B 只做 release schema/source/chain/checksum validation。课程演示若拿不到可验证资质，可运行未发布草稿和本地 fixture，但正式内容 release gate 必须 FAIL，不能伪造背书、让作者自审或生成假的 handoff；历史 rejected/superseded 只进入 archive，不计 active 24。
- [ ] review-record schema 的 `content_type` 精确允许 knowledge/exercise/assessment/crisis_resource/safety_ui；每个制品只存 `review_record_id`，禁止在制品内联第二套 reviewer。导入时同时验证 source_refs、最终 checksum、三阶段均 approved、release_decision=approved、next_review_at 与内容状态，额外/孤儿/chain 断裂记录一律拒绝。
- [ ] safety UI manifest 精确包含 prompt、safe_now/not_safe/unsure 和 call_110/call_120/call_12356/contact_trusted_person/open_nearest_emergency/recheck_safety 的审核文案/版本/checksum。
- [ ] PHQ-9/GAD-7 定义内嵌已审核 `display={title,summary,non_diagnostic_notice,recommended_actions,resource_refs,content_version}`；API 原样返回 display，移动端不得按 severity 自创诊断/建议文本。
- [ ] importer 校验通过后把不可变内容版本导入 MySQL；撤回更新状态/ETag，不修改旧正文。
- [ ] KnowledgeRetrieverPort adapter 与 REST search 调同一个 service/repository，只读 MySQL；A 不建立第二套本地数据库或长期 cache。
- [ ] POST /v1/knowledge/search 使用 JSON body 和 Idempotency-Key，query 不进入 URL/log；knowledge.search 非 L0 普通查询为零。
- [ ] RAG 数据至少覆盖八篇内容的主要主题和无命中 hard negative；Recall@3 低于 0.90 非零退出。
- [ ] 重新生成 OpenAPI 并 byte compare。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_openapi.py --check
- [ ] Expected: PASS；OpenAPI 没有 GET knowledge search query。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_source_register.py tests/contract/test_content_draft_handoff.py tests/contract/test_review_register.py tests/contract/test_content_semantics.py tests/contract/test_knowledge_manifest.py tests/integration/test_knowledge_lifecycle.py tests/evaluation/test_rag_recall.py -q
- [ ] Expected: PASS，A 与独立审核 handoff 均来自已提交/外部签署证据，active=24、pending=0，报告 Recall@3>=0.90；撤回后 REST/A adapter 都不再命中。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/content src/mental_health_api/knowledge tests/contract/test_source_register.py tests/contract/test_content_draft_handoff.py tests/contract/test_review_register.py tests/contract/test_content_semantics.py tests/contract/test_knowledge_manifest.py tests/integration/test_knowledge_lifecycle.py tests/evaluation/test_rag_recall.py && uv run ruff format --check src/mental_health_api/content src/mental_health_api/knowledge tests/contract/test_source_register.py tests/contract/test_content_draft_handoff.py tests/contract/test_review_register.py tests/contract/test_content_semantics.py tests/contract/test_knowledge_manifest.py tests/integration/test_knowledge_lifecycle.py tests/evaluation/test_rag_recall.py && uv run mypy src/mental_health_api/content src/mental_health_api/knowledge && git diff --check
- [ ] Expected: 全部 exit 0；review count=24、orphan=0。

**Commit boundary**

- [ ] Stage 2 只暂存 B-owned active/pending register 更新、release-validation/import/search/RAG 实现与测试、OpenAPI，以及独立审核人已签署且 B 不得改写的 handoff；A handoff 必须已由 A-11 commit 提供，B 不重复暂存或改写。不得把测试生成签名作为审核证据。
- [ ] Commit: `feat(content): validate review chain and publish sourced corpus`

### Task B-13：练习目录、状态机、历史、反思与完成反馈

**Working directory:** repository root

**depends_on:** B-03、B-08、B-12 Stage 2。

**produces:** exercise_session_state.schema、12 项目录/API、服务端状态机、history、entry delete、feedback。

**Files:**
- Create: contracts/content/exercise_session_state.schema.json
- Create: contracts/content/canonical_rows.json
- Create: src/mental_health_api/exercises/contracts.py
- Create: src/mental_health_api/exercises/repository.py
- Create: src/mental_health_api/exercises/state_machine.py
- Create: src/mental_health_api/exercises/service.py
- Create: src/mental_health_api/exercises/routes.py
- Test: tests/contract/test_exercise_manifest.py
- Test: tests/contract/test_exercise_session_state.py
- Test: tests/api/test_exercises.py
- Test: tests/integration/test_exercise_history_feedback.py
- Test: tests/integration/test_exercise_safety.py

**RED**

- [ ] 参数化遍历 not_started/in_progress/paused/completed/exited/interrupted 与 start/pause/resume/skip/exit/complete/restart；非法迁移无写入，restart 新 ID。
- [ ] 写 12 IDs 精确集合、版本撤回、进程恢复、history cursor、反思单条删除、rating 1–5、反馈幂等、L1 pending、L2/L3 interrupted 测试。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_exercise_manifest.py tests/contract/test_exercise_session_state.py tests/api/test_exercises.py tests/integration/test_exercise_history_feedback.py tests/integration/test_exercise_safety.py -q
- [ ] Expected: FAIL，原因是 exercise schema/module 不存在。

**Implementation**

- [ ] 状态机只由生成的 schema/transition table 驱动；skip 不能把最后一步当 complete，terminal restart 创建新 session。
- [ ] reflection 使用 exercise.reflection；完成 comment 复用 feedback.comment；所有写 route 要求 Idempotency-Key。
- [ ] L1 不开始/继续，L2/L3 或内容撤回进入 interrupted；风险/outbox 与 session 状态同事务。
- [ ] CBT text 单独 AES-GCM 加密，可单条删除；history 只返回当前主体和 definition version。
- [ ] 重新生成 OpenAPI 与 exercise schema，首次文件用 --check + git add -N。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_openapi.py --check
- [ ] Expected: PASS。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_exercise_manifest.py tests/contract/test_exercise_session_state.py tests/api/test_exercises.py tests/integration/test_exercise_history_feedback.py tests/integration/test_exercise_safety.py -q
- [ ] Expected: PASS，12/12 内容和全部 state×action 组合有确定结果。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/exercises tests/contract/test_exercise_manifest.py tests/contract/test_exercise_session_state.py tests/api/test_exercises.py tests/integration/test_exercise_history_feedback.py tests/integration/test_exercise_safety.py && uv run ruff format --check src/mental_health_api/exercises tests/contract/test_exercise_manifest.py tests/contract/test_exercise_session_state.py tests/api/test_exercises.py tests/integration/test_exercise_history_feedback.py tests/integration/test_exercise_safety.py && uv run mypy src/mental_health_api/exercises && git diff --check
- [ ] Expected: 全部 exit 0。

**Commit boundary**

- [ ] Stage only: contracts/content src/mental_health_api/exercises tests/contract/test_exercise_manifest.py tests/contract/test_exercise_session_state.py tests/api/test_exercises.py tests/integration/test_exercise_history_feedback.py tests/integration/test_exercise_safety.py contracts/openapi/openapi.json
- [ ] Commit: feat(exercises): add reviewed resumable self help sessions

### Task B-14：PHQ-9/GAD-7、optional_note 前置筛查与 assessment held/release

**Working directory:** repository root

**depends_on:** B-03、B-06、B-08、B-12 Stage 2；外部依赖 A-11 已提交的 `assessment_safety_trigger.schema.json` 与 canonical rows。B-14 是首次消费/注册该 trigger 的 B 任务，B-08 不依赖它。

**produces:** versioned assessment definitions、server scoring、result detail、cursor history、single-result JSON export、delete/tombstone、optional note 通用安全分支、PHQ9_Q9 trigger、assessment SafetyContext、held/released；route 精确使用 PRD 18.1 的 definition/submission 与 `/v1/assessment-results` 六类路径。

**Files:**
- Create: src/mental_health_api/assessments/contracts.py
- Create: src/mental_health_api/assessments/scoring.py
- Create: src/mental_health_api/assessments/repository.py
- Create: src/mental_health_api/assessments/service.py
- Create: src/mental_health_api/assessments/routes.py
- Create: src/mental_health_api/assessments/safety_trigger.py
- Create: contracts/assessments/assessment_result_export.schema.json
- Test: tests/contract/test_assessment_manifests.py
- Test: tests/contract/test_assessment_public_contracts.py
- Test: tests/unit/assessments/test_scoring.py
- Test: tests/integration/test_assessment_optional_note_safety.py
- Test: tests/integration/test_assessment_submission.py
- Test: tests/integration/test_assessment_safety_lifecycle.py
- Test: tests/integration/test_assessment_history_export_delete.py

**RED**

- [ ] 写 PHQ 0/27 和 4/5、9/10、14/15、19/20；GAD 0/21 和 4/5、9/10、14/15；漏答、非法选项、版本冲突、伪造 client score，以及 definition/submission/detail/cursor-history/single-export/delete 六类 route 的精确 method/path。
- [ ] 写 history 稳定游标/limit 1–100、export JSON schema/无逐题答案、DELETE 204/重复 204/tombstone 后详情历史导出不可见、guest/account owner 与跨主体 404 测试；held export 423，deleted detail/export 410。
- [ ] optional_note 非 L0 必须在计分前停止：AssessmentResult/trigger 增量 0，只创建 generic SafetyContext。
- [ ] Q9 1–3 在同一事务创建/复用 assessment_safety conversation、Result、Trigger、SafetyContext、safety.question；任一写入失败五类记录均 0。
- [ ] safe_now released/available；unsure L2 与 not_safe L3 保持 held；recheck safe_now 才释放。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_assessment_manifests.py tests/contract/test_assessment_public_contracts.py tests/unit/assessments/test_scoring.py tests/integration/test_assessment_optional_note_safety.py tests/integration/test_assessment_submission.py tests/integration/test_assessment_safety_lifecycle.py tests/integration/test_assessment_history_export_delete.py -q
- [ ] Expected: FAIL，原因是 assessment service/routes 不存在。

**Implementation**

- [ ] optional_note 先以 assessment:{scale}:{version} 调 B-08；只有 L0 才校验答案和计分。
- [ ] 将 A-11 assessment trigger schema/canonical 注册进 B assessment adapter，增加 A→B round-trip/mutation test，并与 OpenAPI/WS/assessment 生成物逐字节比较；B 不重新定义 trigger 语义。
- [ ] 题干/选项/计分/display 全来自 B-12 锁定制品，LLM/客户端无覆盖入口；公开结果不含逐题答案。
- [ ] HTTP 201 使用 released AssessmentSubmissionResponse；HTTP 202 精确使用 `AssessmentSafetyRequiredResponse`，固定 assessment kind/L1/PHQ9/PHQ9_Q9/safety_required=true/result=null/held，禁止 entry_point、answer、score；free-text SafetyRequired 分支反向禁止 assessment 字段。held GET 423，deleted GET 410。
- [ ] HTTP safety_event_id 与 WS question event_id 相同；answer/recheck 复用 B-08 状态表。
- [ ] Idempotency-Key 作用域含 subject、scale_version 和 request digest；同一 submission key 携带不同答卷/optional_note 返回 409。安全确认 command 的同键不同 `answer_id` 由 B-08 返回 IDEMPOTENCY_CONFLICT。
- [ ] 精确实现：`GET /v1/assessments/{scale}/definitions/{version}`、`POST /v1/assessments/{scale}/submissions`、`GET /v1/assessment-results/{assessment_result_id}`、`GET /v1/assessment-results?cursor={opaque}&limit=20&scale={phq9|gad7}`、`GET /v1/assessment-results/{assessment_result_id}/export`、`DELETE /v1/assessment-results/{assessment_result_id}`。path scale 只接收小写 `phq9|gad7`，对象 scale 保持大写枚举；未定义任何别名 route。
- [ ] history 使用 `(completed_at DESC, assessment_result_id DESC)` opaque cursor；详情/history/export/delete 在 repository 查询首条件绑定当前 subject。export 返回 `application/json` 的 `assessment-result.v1` wrapper 并复用 available result，不导出 answers/optional_note/trigger/safety event。held export 423、deleted 410；DELETE 首次与同主体重复均 204，写 tombstone 后同步清除读取面并交给 B-16 传播。
- [ ] 重新生成 OpenAPI/WS/assessment schemas 并 byte compare。

**GREEN**

- [ ] Run: uv run python scripts/export_openapi.py --write && uv run python scripts/export_ws_contracts.py --write && uv run python scripts/export_openapi.py --check && uv run python scripts/export_ws_contracts.py --check
- [ ] Expected: PASS。
- [ ] Run: docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/contract/test_assessment_manifests.py tests/contract/test_assessment_public_contracts.py tests/unit/assessments/test_scoring.py tests/integration/test_assessment_optional_note_safety.py tests/integration/test_assessment_submission.py tests/integration/test_assessment_safety_lifecycle.py tests/integration/test_assessment_history_export_delete.py -q
- [ ] Expected: PASS，三种 answer 分支、断线重放与 definition/submission/detail/history/export/delete 全闭环均通过。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/assessments tests/contract/test_assessment_manifests.py tests/contract/test_assessment_public_contracts.py tests/unit/assessments tests/integration/test_assessment_optional_note_safety.py tests/integration/test_assessment_submission.py tests/integration/test_assessment_safety_lifecycle.py tests/integration/test_assessment_history_export_delete.py && uv run ruff format --check src/mental_health_api/assessments tests/contract/test_assessment_manifests.py tests/contract/test_assessment_public_contracts.py tests/unit/assessments tests/integration/test_assessment_optional_note_safety.py tests/integration/test_assessment_submission.py tests/integration/test_assessment_safety_lifecycle.py tests/integration/test_assessment_history_export_delete.py && uv run mypy src/mental_health_api/assessments && git diff --check
- [ ] Expected: 全部 exit 0。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/assessments tests/contract/test_assessment_manifests.py tests/contract/test_assessment_public_contracts.py tests/unit/assessments tests/integration/test_assessment_optional_note_safety.py tests/integration/test_assessment_submission.py tests/integration/test_assessment_safety_lifecycle.py tests/integration/test_assessment_history_export_delete.py contracts/openapi/openapi.json contracts/ws contracts/assessments
- [ ] Commit: feat(assessments): score and hold phq9 gad7 safely

### Task B-15：Ed25519/JCS 危机包、匿名资源 API 与最小风险审计

**Working directory:** repository root

**depends_on:** B-03、B-08、B-12 Stage 2。

**produces:** trusted key registry、RFC8785 canonical vectors、签名/验证工具、active/degraded 离线包、匿名危机 API、最小 CrisisEvent access。

**Files:**
- Create: content/crisis/trusted-keys.json
- Create: content/crisis/offline-bundle.schema.json
- Create/Generate: content/crisis/offline-bundle.zh-CN.v1.json
- Create: contracts/crisis/canonical_vectors.json
- Create: src/mental_health_api/crisis/contracts.py
- Create: src/mental_health_api/crisis/jcs.py
- Create: src/mental_health_api/crisis/signing.py
- Create: src/mental_health_api/crisis/resources.py
- Create: src/mental_health_api/crisis/events.py
- Create: src/mental_health_api/crisis/routes.py
- Create: scripts/build_crisis_bundle.py
- Create: scripts/build_crisis_mobile_assets.py
- Create: scripts/generate_crisis_demo_key.py
- Create/Generate: mobile/src/assets/crisis/offline-bundle.zh-CN.v1.json
- Create/Generate: mobile/src/assets/crisis/trusted-keys.json
- Test: tests/contract/test_crisis_jcs_vectors.py
- Test: tests/contract/test_crisis_bundle_integrity.py
- Test: tests/contract/test_crisis_mobile_asset_build.py
- Test: tests/contract/test_crisis_demo_key_generation.py
- Test: tests/api/test_crisis_resources.py
- Test: tests/integration/test_crisis_bundle_degraded.py
- Test: tests/security/test_crisis_event_access.py

**RED**

- [ ] 写 unsigned object 不含 sha256/signature、JCS UTF-8 hash、小写 sha256、Ed25519 base64url-no-padding、key_id/有效期/吊销/轮换、篡改/过期/未知 key 的跨语言 vectors；另写 clean-clone demo key 生成测试，证明私钥只写 Git ignored 的 `.local/secrets/`、Linux mode=0600、公钥 registry 可验证且重复执行不覆盖既有私钥。
- [ ] 写 110/120/12356、匿名访问、地区未知、active/degraded 五原因、不可用数据库/模型仍返回 builtin baseline、风险事件无原文与 RBAC 测试。
- [ ] Run: uv run pytest tests/contract/test_crisis_jcs_vectors.py tests/contract/test_crisis_bundle_integrity.py tests/contract/test_crisis_mobile_asset_build.py tests/contract/test_crisis_demo_key_generation.py tests/api/test_crisis_resources.py tests/integration/test_crisis_bundle_degraded.py tests/security/test_crisis_event_access.py -q
- [ ] Expected: FAIL，原因是 trusted keys/schema/signing 模块不存在。

**Implementation**

- [ ] `unsigned_object` 不含 `sha256`/`signature`；对它执行 RFC 8785 JCS 并 UTF-8 编码得到唯一 bytes。`sha256` 是这些 bytes 的小写 SHA-256，`signature` 是 Ed25519 对同一 bytes 的 base64url-no-padding 签名。私钥只从 CRISIS_SIGNING_KEY_FILE secret path 读取，禁止进入 env dump/image/repo。
- [ ] trusted-keys.json 只含公钥、key_id、not_before/not_after、status/revoked_at；轮换期允许明确的两个 active key。
- [ ] `scripts/generate_crisis_demo_key.py` 是课程/竞赛 clean-clone 的一次性 demo 初始化工具：显式接收 `--private-key-file`、`--trusted-keys`、`--key-id`，用 OS CSPRNG 生成 Ed25519 seed/private key，私钥只写 `.local/secrets/` 且 Linux 权限固定 0600，公钥确定性写入 registry；目标私钥已存在即非零退出，任何私钥字节进入 stdout/log/Git/index 立即失败。它不生成或代表生产密钥。
- [ ] 包字段固定 signature_alg=Ed25519、canonicalization=RFC8785-JCS、key_id、resource_status、degraded_reason、bundle_version、verified_at、expires_at、resources、sha256、signature。
- [ ] 校验失败仍返回内置 110/120/12356 且 degraded；绝不显示 complete 或 resource_bundle_status。
- [ ] CrisisEvent 只保存 risk level、signal category、policy/model version、actions、review enum；无自由文本。
- [ ] `scripts/build_crisis_bundle.py` 从已批准 `content/crisis/china-mainland.zh-CN.v1.json` 确定性生成并签署唯一 `content/crisis/offline-bundle.zh-CN.v1.json`；`scripts/build_crisis_mobile_assets.py` 再校验 schema、hash、签名与 trusted key，并只复制为 `mobile/src/assets/crisis/offline-bundle.zh-CN.v1.json` 和 `mobile/src/assets/crisis/trusted-keys.json`。签名无效、未知/撤销 key、额外输出文件或任一输出漂移都非零退出。首次 clean-clone 的精确顺序为：`uv run python scripts/generate_crisis_demo_key.py --private-key-file .local/secrets/crisis-demo-ed25519.key --trusted-keys content/crisis/trusted-keys.json --key-id demo-cn-2026-01` → `$env:CRISIS_SIGNING_KEY_FILE='.local/secrets/crisis-demo-ed25519.key'; uv run python scripts/build_crisis_bundle.py --write --key-id demo-cn-2026-01` → `uv run python scripts/build_crisis_mobile_assets.py --write`；Linux shell 使用同名环境变量，不改变文件路径/参数。
- [ ] 重新生成 OpenAPI 并 byte compare。

**GREEN**

- [ ] Run: uv run python scripts/build_crisis_bundle.py --check-vectors && uv run python scripts/build_crisis_mobile_assets.py --check && uv run python scripts/export_openapi.py --write && uv run python scripts/export_openapi.py --check
- [ ] Expected: PASS；签名 vectors 稳定。
- [ ] Run: uv run pytest tests/contract/test_crisis_jcs_vectors.py tests/contract/test_crisis_bundle_integrity.py tests/contract/test_crisis_mobile_asset_build.py tests/contract/test_crisis_demo_key_generation.py tests/api/test_crisis_resources.py tests/integration/test_crisis_bundle_degraded.py tests/security/test_crisis_event_access.py -q
- [ ] Expected: PASS，任何 degraded 分支仍含三号码。

**Full gate**

- [ ] Run: uv lock --check && uv run ruff check src/mental_health_api/crisis scripts/generate_crisis_demo_key.py scripts/build_crisis_bundle.py scripts/build_crisis_mobile_assets.py tests/contract/test_crisis_jcs_vectors.py tests/contract/test_crisis_bundle_integrity.py tests/contract/test_crisis_mobile_asset_build.py tests/contract/test_crisis_demo_key_generation.py tests/api/test_crisis_resources.py tests/integration/test_crisis_bundle_degraded.py tests/security/test_crisis_event_access.py && uv run ruff format --check src/mental_health_api/crisis scripts/generate_crisis_demo_key.py scripts/build_crisis_bundle.py scripts/build_crisis_mobile_assets.py tests/contract/test_crisis_jcs_vectors.py tests/contract/test_crisis_bundle_integrity.py tests/contract/test_crisis_mobile_asset_build.py tests/contract/test_crisis_demo_key_generation.py tests/api/test_crisis_resources.py tests/integration/test_crisis_bundle_degraded.py tests/security/test_crisis_event_access.py && uv run mypy src/mental_health_api/crisis scripts/generate_crisis_demo_key.py scripts/build_crisis_bundle.py scripts/build_crisis_mobile_assets.py && git diff --check
- [ ] Expected: 全部 exit 0；secret scan 对签名私钥命中为 0。

**Commit boundary**

- [ ] Stage only: content/crisis/trusted-keys.json content/crisis/offline-bundle.schema.json content/crisis/offline-bundle.zh-CN.v1.json contracts/crisis src/mental_health_api/crisis scripts/generate_crisis_demo_key.py scripts/build_crisis_bundle.py scripts/build_crisis_mobile_assets.py mobile/src/assets/crisis/offline-bundle.zh-CN.v1.json mobile/src/assets/crisis/trusted-keys.json tests/contract/test_crisis_jcs_vectors.py tests/contract/test_crisis_bundle_integrity.py tests/contract/test_crisis_mobile_asset_build.py tests/contract/test_crisis_demo_key_generation.py tests/api/test_crisis_resources.py tests/integration/test_crisis_bundle_degraded.py tests/security/test_crisis_event_access.py contracts/openapi/openapi.json；明确不得暂存 `.local/secrets/`、任何私钥或包含私钥的 evidence/log。
- [ ] Commit: feat(crisis): sign and serve verifiable offline resources

### Task B-16：隐私权利、retention worker、导出、删除与注销闭环

**Working directory:** repository root（含 `pyproject.toml`、`deploy/` 与 `src/` 的目录）。

**depends_on:** B-03–B-15；不得在未完成 guest、outbox、内容、assessment、crisis 表之前假设删除面已知。

**produces:** `/v1/privacy` 导出/删除/注销、可观察 PrivacyJob 状态、全数据面 deletion tombstone、注入 Clock 的 retention worker、备份恢复后的墓碑重放证明，以及把适用法规映射到具体工程控制和自动化证据的隐私合规矩阵。矩阵是工程证据索引，不替代法律意见，也不得由 A/B/C 自行签署“已合法合规”。

**Files:**
- Create: src/mental_health_api/privacy/contracts.py
- Create: src/mental_health_api/privacy/routes.py
- Create: src/mental_health_api/privacy/service.py
- Create: src/mental_health_api/privacy/exporter.py
- Create: src/mental_health_api/privacy/deletion.py
- Create: src/mental_health_api/privacy/retention_worker.py
- Create: src/mental_health_api/privacy/tombstones.py
- Create: scripts/run_retention_worker.py
- Create: project_docs/04_technical_design/privacy_compliance_matrix.md
- Create: config/privacy/provider-processing-policy.json
- Create: src/mental_health_api/provider_policy/repository.py
- Modify: src/mental_health_api/provider_policy/adapter.py
- Test: tests/api/test_privacy_routes.py
- Test: tests/integration/test_privacy_export.py
- Test: tests/integration/test_deletion_propagation.py
- Test: tests/integration/test_retention_worker.py
- Test: tests/integration/test_restore_tombstone_replay.py
- Test: tests/security/test_privacy_job_isolation.py
- Test: tests/compliance/test_privacy_control_mapping.py
- Test: tests/integration/test_provider_processing_policy_dispatch_gate.py

**RED**

- [ ] 写导出授权/单次下载/过期、删除阶段状态、重复请求幂等、注销撤销 access/refresh/guest/WS ticket、跨用户 job 404 测试。
- [ ] 用冻结时钟覆盖第 2.6 节每个边界：guest/ephemeral 24h、已 ACK 普通 outbox 7d、最小风险/安全 outbox 30d、audit 90d、backup 7d、tombstone 30d；精确测试 deadline 前一秒保留、deadline 时清理。
- [ ] 写 MySQL、Redis、知识检索派生记录、outbox 副本、memory、assessment、exercise、feedback、conversation 与 guest 对象的删除传播测试；恢复旧备份后 tombstone 必须阻止正文复活。
- [ ] 写合规矩阵结构测试：每项适用法律必须含官方 URL、版本/生效日期、最近复核日、下次复核期限、处理目的/依据、数据类别、控制者/受托处理者、保存期、用户权利、事件响应、跨境/第三方 AI 决策、工程控制、证据路径、owner 和独立复核签署；缺字段、证据路径不存在、外部复核缺失或复核过期均失败。另对 machine-readable provider policy 注入缺配置、坏 JSON/schema、matrix SHA-256 不匹配、未知 provider、合同/独立复核引用缺失、过期与时钟异常，全部必须合成为 disabled。
- [ ] Run: `docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/api/test_privacy_routes.py tests/integration/test_privacy_export.py tests/integration/test_deletion_propagation.py tests/integration/test_retention_worker.py tests/integration/test_restore_tombstone_replay.py tests/integration/test_provider_processing_policy_dispatch_gate.py tests/security/test_privacy_job_isolation.py tests/compliance/test_privacy_control_mapping.py -q`
- [ ] Expected: FAIL；首个失败必须是 privacy route/module/worker 尚不存在，而非用 SQLite 跳过 MySQL 断言。

**Implementation**

- [ ] `POST /v1/privacy/exports`、`POST /v1/privacy/deletions`、`POST /v1/privacy/account-closures` 都要求当前正式账户与 Idempotency-Key；GET job 只返回当前主体的结构化阶段、计数、deadline 和公开错误，不返回其他用户或内部路径。
- [ ] 导出按稳定 manifest 生成加密归档；下载凭证 256 bit、只存 HMAC、单次使用且短 TTL。归档不包含服务密钥、内部 safety evidence、他人内容或已删除数据。
- [ ] 删除请求接受后立即写 tombstone、撤销相关访问并隐藏读取；在线 MySQL/Redis/检索/outbox/派生数据在 24h 内清理，备份只按 7d 窗口淘汰。任一步失败保持 `in_progress` 可重试，不虚报完成。
- [ ] retention worker 使用数据库 advisory lock/lease、批量游标和注入 Clock；每批幂等，崩溃恢复不会越权删除或复活数据。安全/审计留存只含最小枚举/版本/时间/动作，不留自由文本。
- [ ] saved conversation/memory 只由用户删除或注销清理；ephemeral/guest 到期自动清理。删除评估结果后 GET 继续返回 410 tombstone，而非 404 后允许旧副本复活。
- [ ] 建立 `privacy_compliance_matrix.md`：当前中国境内演示基线至少映射《个人信息保护法》《数据安全法》和 2025 年修正、2026-01-01 起施行的《网络安全法》，并使用 PRD NFR-PRIV-004/005 中的官方链接。法律适用性、处理依据、跨境判断和最终结论由独立法律/隐私复核人填写签署；B 只负责把每项结论链接到代码、配置、测试和运行证据。
- [ ] 第三方 LLM/provider 的委托处理或跨境路径默认关闭。B-16 将独立复核后的矩阵结论编译为 Git-reviewed `config/privacy/provider-processing-policy.json`；本演示版本不另设 policy 签名 envelope。repository 校验 schema、provider_id、`matrix_sha256` 与 `privacy_compliance_matrix.md` 实际文件 SHA-256 逐字节一致、合同/独立复核引用存在、data region、cross-border 决策与有效期，再通过 B-04 `ProviderProcessingPolicyPort` 返回 approved/expired/disabled snapshot。只有 machine policy approved、A proof 有效且随后用户 consent granted 才允许 dispatch；任一条件缺失时 provider spy dispatch=0。集成测试精确断言 proof consume=1 → policy read=1 → approved 才 consent read=1 → granted 才 dispatch=1，且撤销/过期后的下一 turn 不能复用旧 snapshot。
- [ ] 重新生成 OpenAPI 并运行临时 byte compare；若 `contracts/openapi/openapi.json` 首次生成，先 `--check` 再 `git add -N`，不能仅检查 git diff。

**GREEN**

- [ ] Run: `uv run python scripts/export_openapi.py --write && uv run python scripts/export_openapi.py --check`
- [ ] Expected: PASS；privacy request/status schema 与公开错误稳定，正文不出现在 schema example。
- [ ] Run: `docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/api/test_privacy_routes.py tests/integration/test_privacy_export.py tests/integration/test_deletion_propagation.py tests/integration/test_retention_worker.py tests/integration/test_restore_tombstone_replay.py tests/integration/test_provider_processing_policy_dispatch_gate.py tests/security/test_privacy_job_isolation.py tests/compliance/test_privacy_control_mapping.py -q`
- [ ] Expected: PASS；删除传播漏项=0、备份恢复复活=0、所有 retention 边界与第 2.6 节一致；矩阵缺失控制/证据/外部复核或超过复核期限时测试稳定 FAIL。

**Full gate**

- [ ] Run: `uv lock --check && uv run ruff check src/mental_health_api/privacy src/mental_health_api/provider_policy scripts/run_retention_worker.py tests/api/test_privacy_routes.py tests/integration/test_privacy_export.py tests/integration/test_deletion_propagation.py tests/integration/test_retention_worker.py tests/integration/test_restore_tombstone_replay.py tests/integration/test_provider_processing_policy_dispatch_gate.py tests/security/test_privacy_job_isolation.py tests/compliance/test_privacy_control_mapping.py && uv run ruff format --check src/mental_health_api/privacy src/mental_health_api/provider_policy scripts/run_retention_worker.py tests/api/test_privacy_routes.py tests/integration/test_privacy_export.py tests/integration/test_deletion_propagation.py tests/integration/test_retention_worker.py tests/integration/test_restore_tombstone_replay.py tests/integration/test_provider_processing_policy_dispatch_gate.py tests/security/test_privacy_job_isolation.py tests/compliance/test_privacy_control_mapping.py && uv run mypy src/mental_health_api/privacy src/mental_health_api/provider_policy scripts/run_retention_worker.py && git diff --check`
- [ ] Expected: 全部 exit 0；`uv lock --check` 无漂移，测试报告显示 online deletion SLA<=24h、backup window=7d。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/privacy src/mental_health_api/provider_policy/repository.py src/mental_health_api/provider_policy/adapter.py config/privacy/provider-processing-policy.json scripts/run_retention_worker.py project_docs/04_technical_design/privacy_compliance_matrix.md tests/api/test_privacy_routes.py tests/integration/test_privacy_export.py tests/integration/test_deletion_propagation.py tests/integration/test_retention_worker.py tests/integration/test_restore_tombstone_replay.py tests/integration/test_provider_processing_policy_dispatch_gate.py tests/security/test_privacy_job_isolation.py tests/compliance/test_privacy_control_mapping.py contracts/openapi/openapi.json
- [ ] Commit: `feat(privacy): close export deletion and retention lifecycle`

### Task B-17：TOTP 管理 API/CLI、工具治理与最终契约冻结

**Working directory:** repository root（所有命令从仓库根执行；PyCharm/VSCode 只能包装这里的相同命令）。

**depends_on:** B-02–B-16；本任务是 B 的最终 route/schema freeze，未完成任一领域 route 时禁止开始 freeze。

**produces:** 独立 `/v1/admin` 鉴权、TOTP enrollment/confirm/recovery、5 分钟 reauth、结构化管理 API+CLI、无 Web UI 的内容/风险/版本管理、审计、最终 OpenAPI/WS/PublicError 制品、IDE/Visio/CARLA/Git 处置证据，以及由 B 独占维护的 tooling 汇总证据骨架。

**Files:**
- Create: src/mental_health_api/admin/auth.py
- Create: src/mental_health_api/admin/mfa.py
- Create: src/mental_health_api/admin/rbac.py
- Create: src/mental_health_api/admin/audit.py
- Create: src/mental_health_api/admin/contracts.py
- Create: src/mental_health_api/admin/routes.py
- Create: src/mental_health_api/admin/cli.py
- Modify: contracts/auth/admin_mfa.schema.json
- Modify: contracts/auth/canonical_rows.json
- Modify: contracts/errors/canonical_rows.json
- Modify: contracts/openapi/openapi.json
- Modify: contracts/ws/client_commands.schema.json
- Modify: contracts/ws/server_events.schema.json
- Create: .editorconfig
- Create: project_docs/04_technical_design/ide_setup.md
- Create: project_docs/04_technical_design/tool_disposition.md
- Create: project_docs/05_progress/tooling_compatibility_evidence.md
- Create: .vscode/settings.example.json
- Create: .vscode/tasks.example.json
- Test: tests/api/test_admin_mfa.py
- Test: tests/api/test_admin_structured_routes.py
- Test: tests/security/test_admin_rbac_reauth.py
- Test: tests/security/test_admin_audit_redaction.py
- Test: tests/contract/test_final_openapi_surface.py
- Test: tests/contract/test_final_ws_surface.py
- Test: tests/tooling/test_ide_command_parity.py
- Test: tests/tooling/test_no_carla_dependency.py

**RED**

- [ ] 写 TOTP seed 加密、enrollment 未确认不可用、时钟窗口、防重放、恢复码单次使用且只存哈希、敏感动作必须密码+TOTP 换 5 分钟 reauth token 测试。
- [ ] 写管理 RBAC/对象级授权/审计测试；内容发布、撤回、风险复核和版本切换只允许结构化 ID/version/status/reason_code，request schema 出现任意正文/自由备注字段即失败。断言不存在 admin Web 页面或前端 bundle。
- [ ] 写 PublicError 精确第 2.5 节、十入口精确集合、REST route 全覆盖、WS command/event 精确 type/payload、未知字段拒绝、OpenAPI 无敏感 example 的 freeze 测试。
- [ ] 写 PyCharm/VSCode 命令等价、配置无绝对路径、Git 为配置事实源、Visio 仅可选绘图、Python/Node/native/Compose/SBOM/runtime 的 CARLA surface=0 测试；不得覆盖已有用户 `.vscode/settings.json`。
- [ ] Run: `docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/api/test_admin_mfa.py tests/api/test_admin_structured_routes.py tests/security/test_admin_rbac_reauth.py tests/security/test_admin_audit_redaction.py tests/contract/test_final_openapi_surface.py tests/contract/test_final_ws_surface.py tests/tooling/test_ide_command_parity.py tests/tooling/test_no_carla_dependency.py -q`
- [ ] Expected: FAIL；首个失败为 admin MFA/CLI 或最终 contract assertions 未实现，不能因缺 CARLA 而错误提前 PASS 全任务。

**Implementation**

- [ ] enrollment seed 以 AES-GCM 加密并绑定 admin ID/AAD；确认后才启用。恢复码随机生成、仅显示一次、Argon2id/HMAC 摘要存储；TOTP/恢复码成功使用均防重放并写无正文 AuditLog。
- [ ] `POST /v1/admin/reauth` 校验密码+TOTP，返回 scope 绑定且 TTL=5 分钟的 token；发布、撤回、风险状态修改、角色变更、密钥元数据变更必须要求 reauth，普通用户/guest 永远 404/403。
- [ ] CLI 调用与 API 相同 application service 和 RBAC，不直连数据库；Git 内容制品才承载正文，CLI/API 只提交结构化审核/发布决定。没有 Web 管理端任务、依赖或路由。
- [ ] `ide_setup.md` 给出 repo-root 与 `mobile/` 两类 cwd 的精确命令；PyCharm/VSCode 调相同 uv/pytest/Ruff/mypy/npm 脚本。示例 VSCode 文件使用 `.example.json`，若已有真实 `.vscode/` 只审查不覆盖。
- [ ] `tool_disposition.md` 记录 Python/C++、TensorRT、FastAPI、WebSocket、React Native、SQLite/MySQL、Git、Linux 的实际位置；Visio 无 runtime 依赖；CARLA 明确不适用且自动扫描为零；不写任何嵌入式待办。
- [ ] 创建 B-owned `tooling_compatibility_evidence.md` 骨架，固定 evidence schema、Python/PyCharm/VSCode/CARLA/Git 汇总字段及 A/C 外部证据引用位置；B-17 只写已完成的 B 工具链结果和 `pending_external_evidence`，不得伪造 A/C 结果。B-20 最终只读 A/C 各自证据并更新此汇总，A/C 均不得暂存该 B-owned 文件。
- [ ] 运行 OpenAPI/WS 生成器 `--write` 后立即 `--check` 临时 byte compare；对任何新 untracked contract 先 `git add -N` 再审查 diff。freeze 后 B-18–B-20 不得新增业务 route/type。

**GREEN**

- [ ] Run: `uv run python scripts/export_openapi.py --write && uv run python scripts/export_ws_contracts.py --write && uv run python scripts/export_openapi.py --check && uv run python scripts/export_ws_contracts.py --check`
- [ ] Expected: PASS；生成器临时文件与仓库制品逐字节一致，OpenAPI 覆盖 B-04–B-17 全部 route，WS type 集合无多无少。
- [ ] Run: `docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/api/test_admin_mfa.py tests/api/test_admin_structured_routes.py tests/security/test_admin_rbac_reauth.py tests/security/test_admin_audit_redaction.py tests/contract/test_final_openapi_surface.py tests/contract/test_final_ws_surface.py tests/tooling/test_ide_command_parity.py tests/tooling/test_no_carla_dependency.py -q`
- [ ] Expected: PASS；TOTP 重放=0、管理自由正文参数=0、CARLA surface=0、PublicError/WS/OpenAPI 漂移=0。

**Full gate**

- [ ] Run: `uv lock --check && uv run ruff check src/mental_health_api/admin tests/api/test_admin_mfa.py tests/api/test_admin_structured_routes.py tests/security/test_admin_rbac_reauth.py tests/security/test_admin_audit_redaction.py tests/contract/test_final_openapi_surface.py tests/contract/test_final_ws_surface.py tests/tooling && uv run ruff format --check src/mental_health_api/admin tests/api/test_admin_mfa.py tests/api/test_admin_structured_routes.py tests/security/test_admin_rbac_reauth.py tests/security/test_admin_audit_redaction.py tests/contract/test_final_openapi_surface.py tests/contract/test_final_ws_surface.py tests/tooling && uv run mypy src/mental_health_api/admin && uv run pytest tests/contract -q && git diff --check`
- [ ] Expected: 全部 exit 0；contract suite 通过且 `rg -n -i "carla" pyproject.toml uv.lock package-lock.json deploy src mobile` 仅允许测试 denylist/处置文档中的解释命中。

**Commit boundary**

- [ ] Stage only: src/mental_health_api/admin contracts/auth contracts/errors/canonical_rows.json contracts/openapi/openapi.json contracts/ws .editorconfig project_docs/04_technical_design/ide_setup.md project_docs/04_technical_design/tool_disposition.md project_docs/05_progress/tooling_compatibility_evidence.md .vscode/settings.example.json .vscode/tasks.example.json tests/api/test_admin_mfa.py tests/api/test_admin_structured_routes.py tests/security/test_admin_rbac_reauth.py tests/security/test_admin_audit_redaction.py tests/contract/test_final_openapi_surface.py tests/contract/test_final_ws_surface.py tests/tooling/test_ide_command_parity.py tests/tooling/test_no_carla_dependency.py
- [ ] Commit: `feat(admin): secure structured operations and freeze contracts`

### Task B-18：十入口旁路、事务回滚、日志与依赖故障总门禁

**Working directory:** repository root。

**depends_on:** B-08–B-17；消费已冻结 OpenAPI/WS/PublicError，不新增 route 或事件类型。

**produces:** 十入口全域参数化安全回归、`context_ref` 授权证明、SafetyContext 三答案/重检总回归、敏感数据零泄漏扫描、依赖故障 fail-closed 证据。

**Files:**
- Create: tests/adversarial/test_all_free_text_entry_points.py
- Create: tests/adversarial/test_context_ref_forgery.py
- Create: tests/adversarial/test_safety_transaction_rollbacks.py
- Create: tests/adversarial/test_safety_answer_replay.py
- Create: tests/adversarial/test_dependency_fail_closed.py
- Create: tests/security/test_plaintext_absence.py
- Create: tests/security/test_log_trace_redaction.py
- Create: tests/security/test_cross_subject_matrix.py
- Create: tests/integration/test_all_free_text_idempotency.py
- Create: scripts/run_backend_adversarial_gate.py

**RED**

- [ ] 对十个 entry point 的每个实际 route/field 参数化 L0/L1/L2/L3/error、缺 key、同 key 重放、同 key 不同正文、伪造 context_ref、跨 subject/object 测试；任一路由旁路或第十一个自由文本字段都失败。
- [ ] 对无会话与有会话的 L1/L2/L3 注入 Conversation/SafetyContext/CrisisEvent/outbox/原业务每个写点失败，断言全回滚；HTTP 202/WS/replay event ID 必须相等。
- [ ] 对 safe_now/unsure/not_safe/recheck/已回答重复/同 key 不同答案/断线重放做全矩阵；assessment release 顺序固定 `risk.status` 后 `assessment.result.available`，generic 永不恢复旧正文。
- [ ] 注入 A safety timeout/crash、MySQL commit failure、Redis unavailable、LLM unavailable、内容撤回和 outbox dispatcher restart；L2/L3/安全依赖失败不得进入普通 LLM/练习/知识或产生原业务写入。
- [ ] Run: `docker compose -f deploy/compose.test.yml run --rm api-test uv run pytest tests/adversarial/test_all_free_text_entry_points.py tests/adversarial/test_context_ref_forgery.py tests/adversarial/test_safety_transaction_rollbacks.py tests/adversarial/test_safety_answer_replay.py tests/adversarial/test_dependency_fail_closed.py tests/security/test_plaintext_absence.py tests/security/test_log_trace_redaction.py tests/security/test_cross_subject_matrix.py tests/integration/test_all_free_text_idempotency.py -q`
- [ ] Expected: FAIL；在测试完成实现前至少一个真实旁路/缺 fixture 失败，不允许把依赖故障测试标记 skip。

**Implementation**

- [ ] 测试从 OpenAPI、WS schema 和 `free_text_registry.py` 自动枚举，不手写另一个可能漂移的 route 清单；精确断言十个 entry point 和第 2.2 节所有 create/patch grammar。
- [ ] 测试工厂只用合成数据；每条敏感 canary 同时扫描响应、日志、trace、metrics、MySQL dump、Redis、outbox、exception 和 pytest artifact。允许的加密 ciphertext 不得包含明文片段。
- [ ] `run_backend_adversarial_gate.py` 顺序启动依赖、迁移、运行矩阵、收集 JSON/Markdown 证据并清理；任一 skip、xfail、timeout 或阈值缺失均非零退出。
- [ ] 修复只回到对应 B-04–B-17 领域实现；不在测试脚本中加入生产旁路，不修改冻结公共 schema，确需改契约时退回 B-17 重新 freeze。

**GREEN**

- [ ] Run: `uv run python scripts/run_backend_adversarial_gate.py --compose deploy/compose.test.yml --evidence artifacts/evidence/backend-adversarial.json`
- [ ] Expected: PASS；十入口×所有安全分支均执行、business_writes_on_non_l0=0、plaintext_hits=0、cross_subject_reads=0、skipped=0。

**Full gate**

- [ ] Run: `uv lock --check && uv run ruff check tests/adversarial/test_all_free_text_entry_points.py tests/adversarial/test_context_ref_forgery.py tests/adversarial/test_safety_transaction_rollbacks.py tests/adversarial/test_safety_answer_replay.py tests/adversarial/test_dependency_fail_closed.py tests/security/test_plaintext_absence.py tests/security/test_log_trace_redaction.py tests/security/test_cross_subject_matrix.py tests/integration/test_all_free_text_idempotency.py scripts/run_backend_adversarial_gate.py && uv run ruff format --check tests/adversarial/test_all_free_text_entry_points.py tests/adversarial/test_context_ref_forgery.py tests/adversarial/test_safety_transaction_rollbacks.py tests/adversarial/test_safety_answer_replay.py tests/adversarial/test_dependency_fail_closed.py tests/security/test_plaintext_absence.py tests/security/test_log_trace_redaction.py tests/security/test_cross_subject_matrix.py tests/integration/test_all_free_text_idempotency.py scripts/run_backend_adversarial_gate.py && uv run mypy scripts/run_backend_adversarial_gate.py && uv run python scripts/export_openapi.py --check && uv run python scripts/export_ws_contracts.py --check && git diff --check`
- [ ] Expected: 全部 exit 0；B-17 freeze 后 OpenAPI/WS byte 漂移=0，evidence 中 `safety_screen_calls_per_chat_turn=1`。

**Commit boundary**

- [ ] Stage only: tests/adversarial/test_all_free_text_entry_points.py tests/adversarial/test_context_ref_forgery.py tests/adversarial/test_safety_transaction_rollbacks.py tests/adversarial/test_safety_answer_replay.py tests/adversarial/test_dependency_fail_closed.py tests/security/test_plaintext_absence.py tests/security/test_log_trace_redaction.py tests/security/test_cross_subject_matrix.py tests/integration/test_all_free_text_idempotency.py scripts/run_backend_adversarial_gate.py；不得暂存任何 A-owned `tests/adversarial/*`。
- [ ] Commit: `test(safety): prove all text routes fail closed`

### Task B-19：阿里云 ECS Linux 运行兼容、TLS、备份恢复、回滚与性能门禁

**Working directory:** repository root；运行验收目标为阿里云 ECS x86_64 官方 Ubuntu 24.04 LTS 或等价 Linux server/CI，Windows 仅可做 `docker compose config` 静态检查。本文只定义运行兼容与证据，不写购买 ECS、控制台配置或发布操作教程。

**depends_on:** B-01、B-03、B-07、B-16–B-18；外部精确消费 A-06 的 ONNX/TensorRT model manifest、A-13 的签名 AI release/performance profile 与 A-15 的 Linux-only compatibility evidence。A 不单独产出服务镜像；B 用 `deploy/Dockerfile.api` 构建包含 A Python package 与已批准模型 artifacts 的 API image，不构建嵌入式 profile。

**produces:** `deploy/compose.demo.yml`、Caddy TLS、migration job、外部 secrets、持久卷、可选 Mailpit profile、备份/恢复/按 digest 回滚脚本、REST/WS 性能证据、阿里云 ECS Linux runtime contract；不产出云资源开通教程。

**Files:**
- Create: deploy/compose.demo.yml
- Create: deploy/compose.e2e.yml
- Create: deploy/Caddyfile
- Create: deploy/Caddyfile.e2e
- Create: deploy/env.demo.example
- Create: deploy/secrets/README.md
- Create: deploy/compatibility-matrix.json
- Create: scripts/healthcheck_demo.py
- Create: scripts/backup_demo.py
- Create: scripts/restore_demo.py
- Create: scripts/rollback_demo.py
- Create: scripts/run_system_performance_gate.py
- Create: tests/performance/locustfile.py
- Create: tests/deployment/test_compose_demo_contract.py
- Create: tests/deployment/test_linux_only_profiles.py
- Create: tests/deployment/test_aliyun_ecs_runtime_contract.py
- Create: tests/deployment/test_e2e_local_listener_isolation.py
- Create: tests/deployment/test_backup_restore.py
- Create: tests/deployment/test_digest_rollback.py
- Create: project_docs/04_technical_design/aliyun_ecs_runtime_contract.md

**RED**

- [ ] 写 runtime/compose contract：基础 `compose.demo.yml` 的服务精确含 caddy/api/mysql/redis/migrate，可选无状态 model-runtime，Mailpit 仅 demo-mail profile；基础/remote 配置只发布 443。`compose.e2e.yml` 只能覆盖同名 `caddy` service，改用 `Caddyfile.e2e` 并额外发布 host `127.0.0.1:8080`，不能新增第二个 caddy service、profile 或把 8080 带入基础/remote config。API 固定单 replica/单 Uvicorn worker并进程内加载 A 包。目标 host 为阿里云 ECS x86_64 Ubuntu 24.04 LTS，建议能力下限 4 vCPU/16 GiB RAM/100 GiB 持久磁盘；只公开 TLS endpoint，MySQL/Redis 无 host public binding；health/readiness、非 root、read-only rootfs where possible、持久卷、resource limit、secret file、image digest、无 host secret/env 明文。任何独立 AI orchestration、embedded/ARM/CARLA profile 失败。
- [ ] 写全新数据→备份→新增数据→恢复→迁移→权限/outbox/content/deletion tombstone 验证，以及上一组 image digest 回滚测试；恢复后被删除 canary 不得复活。
- [ ] 写性能 gate：100 并发 WS + REST 混合、非模型 REST P95<=500ms、已安全复核首 chunk P95<=3s、错误率阈值、预热/持续时间/并发均入 evidence；不能用未审核首 token 计时。
- [ ] Run: `uv run pytest tests/deployment/test_compose_demo_contract.py tests/deployment/test_linux_only_profiles.py tests/deployment/test_aliyun_ecs_runtime_contract.py tests/deployment/test_e2e_local_listener_isolation.py tests/deployment/test_backup_restore.py tests/deployment/test_digest_rollback.py -q`
- [ ] Expected: FAIL；首个失败为 demo compose、runtime contract 或验证脚本不存在。

**Implementation**

- [ ] `compose.demo.yml` 只面向阿里云 ECS Linux 课程/竞赛/内部演示：Caddy 终止 TLS，API 只连 MySQL/Redis 和可选无状态 model-runtime，migrate 成功后 API ready；A 包与 API 同镜像/进程，模型 manifest hash 固定，CPU/ONNX fallback 由 A 包提供，B 不复制 TensorRT/C++ 推理逻辑。
- [ ] 为本地 Android 全栈测试定义唯一 Compose override：`deploy/compose.e2e.yml` 覆盖基础配置里的同名 `caddy` service，挂载 `deploy/Caddyfile.e2e` 并仅在 host `127.0.0.1:8080` 额外提供 HTTP/WS，反代同一 API，使 emulator 通过 `10.0.2.2:8080` 访问；不得创建 `caddy-e2e` service。基础 `compose.demo.yml` 的 caddy 仍只发布 443 HTTPS/WSS，remote 命令永不加载 override。`tests/deployment/test_e2e_local_listener_isolation.py` 必须对基础和合并后的 `docker compose config` 做差分，证明 8080 只存在于显式 local override。
- [ ] secrets 只通过仓库外文件/CI secret 注入；example 只列变量名和生成方法。启动脚本拒绝默认密码、SQLite、HTTP-only public endpoint、浮动 image tag、缺少 encryption/signing key ref。
- [ ] backup/restore 记录 schema/version/content/model/prompt/rule/contract hashes；恢复到隔离 stack 验证后才切换。rollback 只接受 allowlisted previous digest manifest，不能 `latest`。
- [ ] `compatibility-matrix.json` 记录 `cloud_target=Alibaba Cloud ECS`、host OS family/arch、Docker/Compose、Python、FastAPI、MySQL、Redis、OpenAPI/WS、AI model/TensorRT runtime 与 mobile contract version；不绑定 ECS 实例规格型号、区域或购买方式，最终目标没有嵌入式、交叉编译、ARM 或设备固件列。
- [ ] `run_system_performance_gate.py` 产生机器可读 JSON 和 Markdown，阈值超限、样本不足、未解释 skip 或使用 Mock safety/SQLite 均非零退出；把命令、git SHA、image digest、硬件与时间写证据。AI/model 性能由 A 的 `run_ai_performance_gate.py` 独立所有，B-20 只聚合两份报告。

**GREEN**

- [ ] Run: `docker compose -f deploy/compose.demo.yml --profile demo-mail config --quiet && uv run pytest tests/deployment/test_compose_demo_contract.py tests/deployment/test_linux_only_profiles.py tests/deployment/test_aliyun_ecs_runtime_contract.py tests/deployment/test_e2e_local_listener_isolation.py tests/deployment/test_backup_restore.py tests/deployment/test_digest_rollback.py -q`
- [ ] Expected: PASS；阿里云 ECS Linux runtime、services/volumes/secrets/digests 均满足断言，独立 AI orchestration/embedded/CARLA surface=0。
- [ ] Run: `uv run python scripts/run_system_performance_gate.py --compose deploy/compose.demo.yml --ws-clients 100 --output artifacts/evidence/system-performance.json`
- [ ] Expected: PASS；非模型 REST P95<=500ms、reviewed first chunk P95<=3s、错误率在脚本冻结阈值内。

**Full gate**

- [ ] Run: `uv lock --check && uv run ruff check scripts/healthcheck_demo.py scripts/backup_demo.py scripts/restore_demo.py scripts/rollback_demo.py scripts/run_system_performance_gate.py tests/performance/locustfile.py tests/deployment && uv run ruff format --check scripts/healthcheck_demo.py scripts/backup_demo.py scripts/restore_demo.py scripts/rollback_demo.py scripts/run_system_performance_gate.py tests/performance/locustfile.py tests/deployment && uv run mypy scripts/healthcheck_demo.py scripts/backup_demo.py scripts/restore_demo.py scripts/rollback_demo.py scripts/run_system_performance_gate.py && uv run pytest tests/tooling/test_no_carla_dependency.py tests/deployment -q && git diff --check`
- [ ] Expected: 全部 exit 0；backup/restore/rollback evidence 完整，RPO<=24h、RTO<=4h 作为演示目标被脚本验证或显式 FAIL。

**Commit boundary**

- [ ] Stage only: deploy/compose.demo.yml deploy/compose.e2e.yml deploy/Caddyfile deploy/Caddyfile.e2e deploy/env.demo.example deploy/secrets/README.md deploy/compatibility-matrix.json scripts/healthcheck_demo.py scripts/backup_demo.py scripts/restore_demo.py scripts/rollback_demo.py scripts/run_system_performance_gate.py tests/performance/locustfile.py tests/deployment project_docs/04_technical_design/aliyun_ecs_runtime_contract.md；不得暂存 A-owned `tests/performance/model_benchmark.py` 或 `scripts/run_ai_performance_gate.py`。
- [ ] Commit: `feat(runtime): prove aliyun ecs linux compatibility and recovery gates`

### Task B-20：Linux host Android Detox 编排与真实全栈交付证据

**Working directory:** repository root；Compose 命令从 repo-root 执行，Detox build/test 子进程的 cwd 必须显式设为 `mobile/`，Android emulator 在 Linux host/CI KVM 运行。

**depends_on:** B-19；外部依赖 A-13 的 deterministic/real provider release profile，以及 C-17 Stage 1 已通过并写入 `C17_CLIENT_HARNESS_READY` 的 RN 0.84.0、Detox 20.51.3、`.detoxrc.js`、AVD/KVM 脚本和 `mobile/e2e/liveStack20Turn.e2e.ts`。B-20 完成后回交 C-17 Stage 2 运行联合验收；不依赖 C-17 Stage 2，因此无循环。

**produces:** 根级 `run_live_stack_e2e.py`、本地 Linux Compose 的真实 MySQL/Redis/FastAPI（内嵌 A）/Mailpit + host Android 证据、针对预置阿里云 ECS HTTPS/WSS endpoint 的 remote smoke 模式、五项功能/账户/隐私闭环矩阵、统一结果与清理逻辑，并由 B 把 A/C 各自 tooling evidence 的路径/hash/退出码聚合进 B-owned 汇总。脚本不创建或配置云资源。

**Files:**
- Create: scripts/run_live_stack_e2e.py
- Create: tests/e2e/test_live_stack_evidence.py
- Create: tests/e2e/test_live_stack_failure_recovery.py
- Create: tests/e2e/evidence_schema.json
- Create: scripts/verify_release_evidence.py
- Create: project_docs/05_progress/member_b_delivery_evidence.md
- Update (B owns): project_docs/05_progress/tooling_compatibility_evidence.md

**RED**

- [ ] 写 orchestrator 单元/集成测试：本地模式 Linux/KVM/adb/AVD 缺失明确失败；Compose 基础+e2e override 只启动 MySQL/Redis/单 worker FastAPI/可选 model-runtime/Mailpit 和同名 caddy，绝不出现第二个 `caddy-e2e`、独立 AI orchestration、mobile-e2e service 或 `--exit-code-from mobile-e2e`；本地 emulator 使用 `android.emu.e2e` 与仅允许 `10.0.2.2:8080` 的 test-only cleartext config。remote 模式只读取基础 compose/runtime metadata，强制 `android.emu.release` 且只接受 HTTPS/WSS 阿里云 ECS endpoint，不在 ECS 上启动 emulator，也不执行云资源开通；release APK 包含 e2e manifest/network config 时测试必须失败。
- [ ] 写 evidence assertions：guest→账户、guest token/24h、20 轮上下文、单筛查、连续 sequence/ACK/resume、cancel、安全三答案/recheck、emotion、12 exercises、8 knowledge/RAG、PHQ/GAD/Q9、crisis offline/degraded、memory controlled/history_only、feedback、recovery Mailpit、assessment definition/submission/detail/history/single-export/delete、privacy export/delete/account closure。
- [ ] 写失败恢复：API（含内嵌 A 包）进程重启、可选无状态 model-runtime 重启、Redis 重启、WS 连接恢复、网络断开、重复 idempotency、outbox replay、内容撤回、删除墓碑；断言不存在独立 AI orchestration service，且重复逻辑消息=0、未审核 token=0、反馈 MySQL 行=1、跨用户读=0。
- [ ] Run: `uv run pytest tests/e2e/test_live_stack_evidence.py tests/e2e/test_live_stack_failure_recovery.py -q`
- [ ] Expected: FAIL；在 orchestrator/真实 evidence 尚不存在时不得用 fixture 假证据 PASS。

**Implementation**

- [ ] local orchestrator 顺序固定：环境/KVM preflight → 设置 `LOCAL_E2E=1` 并执行 `docker compose -f deploy/compose.demo.yml -f deploy/compose.e2e.yml up -d --wait` → migration/seed → 验证 Caddy `http://127.0.0.1:8080`/WS 与仅加载基础 compose 时不暴露 8080 → 启动或复用 C 的 Linux AVD → 以 cwd=`mobile/`、`APP_PROFILE=e2e_local`、`API_BASE_URL=http://10.0.2.2:8080`、`WS_BASE_URL=ws://10.0.2.2:8080/v1/realtime` 和 `android.emu.e2e` 执行 Detox build/test → cwd=repo-root 执行后端 evidence pytest → 汇总各进程 exit code/evidence hash → finally 用同一双 `-f` 参数清理 AVD 与 Compose。remote 模式跳过 Compose/migration/seed，强制 `android.emu.release`、`DEPLOYMENT_TARGET=aliyun_ecs` 和 HTTPS/WSS，只校验预置 endpoint 的 runtime metadata/health/contract hashes，再从外部 CI/Android runner 执行脱敏 smoke；绝不加载 `compose.e2e.yml`，也不把 KVM 作为 ECS 服务器前提。根脚本按 local/remote 固定配置，调用者不能用参数把 local e2e trust 带入 remote。
- [ ] 所有子命令以参数数组执行，禁止 shell 拼接；日志实时脱敏，超时后先收集 health/outbox/adb artifacts 再清理。任何步骤失败保留结构化失败原因并整体非零退出。
- [ ] 结构链路允许 A 的 DeterministicLocalProvider，但 safety/emotion/output review/MySQL/outbox/WS/mobile reducer 必须是真实实现；另合并 A 的真实 LLM provider smoke/质量门禁证据。缺真实 provider 时写 `LLM_PROVIDER_UNVERIFIED` 并使 SRC-F01/T02 release gate FAIL。
- [ ] `member_b_delivery_evidence.md` 只引用机器证据的路径/hash/命令/环境，不手写“已通过”；Android 是强制项，iOS 无 macOS runner 时明确写“未验证”而非 PASS。
- [ ] 只读 A 的 Linux/AI tooling evidence 与 C-owned `member_c_tooling_evidence.md`，校验文件 hash、命令和退出码后更新 B-owned `tooling_compatibility_evidence.md`；缺任一强制证据时保留 FAIL/pending，不允许复制改写来源证据或让 A/C 提交 B 文件。
- [ ] 第三者复跑入口唯一为下面 GREEN 命令；不得要求理解内部代理上下文、手工点 UI、手工截图或先创建未记录的 secret。所需 secret example、AVD 和网络映射全部在 runtime contract 与 preflight 中列明；不依赖部署 runbook。

**GREEN**

- [ ] Run: `uv run python scripts/run_live_stack_e2e.py --compose deploy/compose.demo.yml --mobile-dir mobile --android-avd MentalHealthApi35 --evidence-dir artifacts/evidence/live-stack`
- [ ] Expected: exit 0；Linux host KVM Android 完成真实全栈，evidence schema valid，五项 SRC 功能、guest/account、安全/隐私矩阵全部有可追踪 case ID。
- [ ] Run: `uv run python scripts/verify_release_evidence.py --dir artifacts/evidence && uv run pytest tests/e2e/test_live_stack_evidence.py tests/e2e/test_live_stack_failure_recovery.py -q`
- [ ] Expected: PASS；20 turns、sequence=0..N、resume `>last_ack`、screen calls/turn=1、unreviewed_tokens=0、duplicate_logical_events=0、feedback_rows=1。
- [ ] Release target command: `uv run python scripts/run_live_stack_e2e.py --remote-base-url $ALIYUN_ECS_BASE_URL --mobile-dir mobile --android-avd MentalHealthApi35 --synthetic-only --evidence-dir artifacts/evidence/aliyun-ecs-smoke`
- [ ] Expected: 对预置阿里云 ECS Linux endpoint 的 TLS、OpenAPI/WS hash、guest/account、20 轮、危机/自测最小 smoke 全部 PASS；命令不包含 ECS 购买、控制台或主机配置步骤。未提供 endpoint 时标记 `ALIYUN_ECS_RUNTIME_UNVERIFIED`，不得宣称最终云目标通过。

**Full gate**

- [ ] Run: `uv lock --check && uv run ruff check scripts/run_live_stack_e2e.py scripts/verify_release_evidence.py tests/e2e && uv run ruff format --check scripts/run_live_stack_e2e.py scripts/verify_release_evidence.py tests/e2e && uv run mypy scripts/run_live_stack_e2e.py scripts/verify_release_evidence.py && uv run python scripts/export_openapi.py --check && uv run python scripts/export_ws_contracts.py --check && uv run pytest tests/contract tests/integration tests/security tests/adversarial tests/deployment tests/tooling -q && git diff --check`
- [ ] Expected: 全部 exit 0；任何**未解释或非条件性允许**的 skip/xfail、SQLite 替代 MySQL、Mock safety、缺 Android/KVM、缺真实 LLM release evidence 或 contract 漂移都使最终 release verdict 非 PASS。唯一条件性 skip 是：无 NVIDIA 时 TensorRT runtime tests 可在 capability report 与 CPU/ONNX 等价门禁通过后 SKIP；无 macOS 时 iOS/VoiceOver 可标记未验证。二者均不得被写成 PASS，也不得跳过 Android、真实 LLM、危机/情绪、MySQL/outbox/WS 或安全门禁。

**Commit boundary**

- [ ] Stage only: scripts/run_live_stack_e2e.py scripts/verify_release_evidence.py tests/e2e/test_live_stack_evidence.py tests/e2e/test_live_stack_failure_recovery.py tests/e2e/evidence_schema.json project_docs/05_progress/member_b_delivery_evidence.md project_docs/05_progress/tooling_compatibility_evidence.md
- [ ] Commit: `test(e2e): prove linux android full stack delivery`

## 5. 交付追踪与第三者停止条件

| 严格要求 | B 的主要实现任务 | 必须由真实证据证明 |
| --- | --- | --- |
| SRC-F01 多轮共情 | B-06、B-07、B-08、B-10、B-20 | 20 轮、单次筛查、ReviewedStreamChunk、连续 sequence、反馈落库 |
| SRC-F02 情绪识别 | B-10、B-11、B-19、B-20 | A schema 无损存储/WS/REST、纠正/趋势、真实模型门禁引用 |
| SRC-F03 正念/CBT | B-12、B-13、B-18、B-20 | 精确 12 项、状态机、L2/L3 阻断、历史/反思/反馈 |
| SRC-F04 科普/自测 | B-12、B-14、B-20 | 8 篇、RAG Recall@3、PHQ/GAD 临界值、Q9 held/release、历史/delete |
| SRC-F05 危机 | B-08、B-12、B-15、B-18、B-20 | L1/L2/L3 事务、三答案/recheck、Ed25519/JCS、离线 degraded |
| SRC-T01 AI 核心 Python | B-01、B-10、B-19 | Python 3.11/uv lock、FastAPI 进程内 A bridge、阿里云 ECS Linux API/model health；A 的 Python AI 证据被 release aggregator 校验 |
| SRC-T02 LLM 高安全与伦理 | B-04、B-08、B-10、B-18、B-20 | 单次输入安全门、每次 dispatch 最新云同意、non-granted 零调用、只接 ReviewedStreamChunk、零未审核 token、L2/L3 无普通 LLM、真实 provider/伦理门禁引用 |
| SRC-T03 情感分析模型 | B-10、B-11、B-19、B-20 | A EmotionResult 无损 MySQL/REST/WS、纠正/趋势、独立模型/version evidence；不得以 LLM 文本冒充分类 |
| SRC-T04 FastAPI | B-01、B-02、B-04–B-17 | 真实 FastAPI routes、生成 OpenAPI、MySQL integration、最终 byte freeze |
| SRC-T05 WebSocket 实时对话 | B-02、B-06、B-07、B-10、B-20 | 双信封、B 唯一 sequence、ACK CAS/resume/cancel/idempotency、20 轮重连证据 |
| SRC-T06 React Native 移动端 | B-02、B-15、B-20 | B 发布 C 可生成契约/签名资源并编排 RN 0.84.0 + Detox 20.51.3 Android host E2E；UI 实现由 C 所有 |
| SRC-T07 SQLite/MySQL 加密存储 | B-03、B-04、B-16、B-20 | 服务端真实 MySQL/AES-GCM/删除传播；端侧 OP-SQLite SQLCipher/Keychain 由 C evidence 接入，SQLite 不替代 MySQL 测试 |
| SRC-T08 Python/C++ | B-01、B-10、B-19 | B 用 Python 实现业务；C++ 只由进程内 A inference adapter 使用 Linux native/TensorRT manifest，不复制安全/业务语义 |
| SRC-T09 TensorRT | B-19、B-20 | 阿里云 ECS Linux runtime 校验 A 的 TensorRT engine/compatibility manifest并验证 CPU/ONNX fallback；无 NVIDIA 时不阻断安全演示但标记 GPU gate 条件结果 |
| SRC-T10 Git/PyCharm/VSCode | B-01、B-17 | Git/lock/commit boundary、`.editorconfig`、两 IDE 相同 uv/pytest/Ruff/mypy 命令、无绝对路径且不覆盖用户 `.vscode/` |
| SRC-T11 Visio/CARLA | B-17、B-19 | Visio 仅可选外部绘图；CARLA 不适用，Python/Node/native/Compose/SBOM/runtime 自动扫描 surface=0 |
| SRC-T12 Linux/嵌入式 | B-17、B-19、B-20 | 唯一阿里云 ECS x86_64 Linux TLS Compose/runtime/恢复/回滚/remote smoke 证据；嵌入式/ARM/交叉编译 profile 与待办均为零 |

第三者只在以下条件同时满足时结束成员 B 工作：B-01–B-20 checkbox 全部有实际 commit/evidence；`uv lock --check`、OpenAPI/WS byte check、MySQL 集成、adversarial、阿里云 ECS Linux runtime compatibility/remote smoke、Android full-stack 均为新鲜 exit 0；24 个内容制品/三阶段审核链无孤儿；PublicError/十入口/WS 类型无漂移；真实 LLM/情绪/危机/RAG 门禁由 A 证据满足；C 的 Android/SQLCipher/离线资产证据已合并；没有 P0/P1、真实密钥、真实用户数据或未解释 skip。若任何外部证据缺失，状态写明具体 `UNVERIFIED`/`FAIL`，不得把“代码已写”当作项目完成。本文不要求实施者编写阿里云资源购买或控制台操作教程。

## 6. 阿里云目标兼容依据（非部署教程）

- 阿里云 ECS 官方 Ubuntu 镜像说明（含 Ubuntu 24.04 LTS）：https://www.alibabacloud.com/help/en/ecs/ubuntu-image
- 阿里云 ECS 安全责任边界：https://www.alibabacloud.com/help/en/ecs/user-guide/security-overview
- 阿里云 ECS Security Group 作为实例网络隔离边界：https://www.alibabacloud.com/help/en/ecs/user-guide/start-using-security-groups
- 阿里云 ECS 快照/恢复能力说明：https://www.alibabacloud.com/help/en/ecs/user-guide/snapshot-overview/

这些链接只用于约束 host OS、网络暴露、加密/备份责任和可恢复性设计；本文不复述云控制台操作步骤。
