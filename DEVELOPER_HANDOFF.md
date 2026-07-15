# 开发者对接文档

> **项目：** AI 心理咨询与情感陪伴助手  
> **交接人：** Member B（后端）  
> **交接日期：** 2026-07-14  
> **仓库：** https://github.com/Stone943/AI_Psychological_Counseling_and_Emotional_Companionship_Assistant  

---

## 1. 五分钟快速上手

### 1.1 环境准备

```bash
# 1. 创建 conda 环境
conda create -n mental_health python=3.11 -y
conda activate mental_health

# 2. 配置清华源（国内加速）
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 安装 uv 包管理器
pip install uv

# 4. 同步依赖（基础后端包，不含 AI 模型）
cd 项目根目录
uv sync --frozen

# 5. 如需 AI 模型推理能力（torch + transformers，约 3GB）
uv sync --frozen --extra ai --extra onnx

# 6. 运行测试
uv run pytest tests/ -v
```

### 1.2 一句话架构

```
React Native 移动端 → FastAPI 后端 → MySQL + Redis
                         ↑
                    mental_health_ai (AI 安全包，同进程内嵌)
```

---

## 2. 目录结构

```
项目根目录/
├── src/
│   ├── mental_health_api/          # ★ B 负责的后端包
│   │   └── mental_health_api/
│   │       ├── app.py              # FastAPI 工厂 + 路由注册（入口文件）
│   │       ├── config.py           # 严格配置（Settings）
│   │       ├── errors.py           # 结构化错误体系（26 种）
│   │       ├── contracts/          # 公共 Pydantic 模型
│   │       ├── database/           # ORM + 加密 + 留存策略
│   │       ├── guests/             # 访客会话
│   │       ├── auth/               # 认证 + JWT + 密码找回
│   │       ├── consents/           # 同意管理
│   │       ├── provider_policy/    # 云模型组织策略
│   │       ├── conversations/      # 会话 + 消息
│   │       ├── realtime/           # WebSocket
│   │       ├── safety/             # ★ 安全网关（10 入口）
│   │       ├── ai_bridge/          # AI 编排桥接
│   │       ├── guest_migrations/   # 访客升级
│   │       ├── feedback/           # 用户反馈
│   │       ├── emotions/           # 情绪识别
│   │       ├── memory/             # 长期记忆
│   │       ├── knowledge/          # 心理知识库
│   │       ├── exercises/          # 正念/CBT 练习
│   │       ├── assessments/        # PHQ-9/GAD-7 量表
│   │       ├── crisis/             # 危机资源
│   │       ├── privacy/            # 数据权利
│   │       ├── admin/              # 管理 API
│   │       └── content/            # 内容治理
│   └── mental_health_ai/           # A 负责的 AI 包（占位骨架）
├── contracts/                      # JSON Schema + OpenAPI
│   ├── openapi/openapi.json        # OpenAPI 3.1 规范
│   ├── ws/                         # WebSocket 双向协议
│   ├── errors/                     # 26 种错误码
│   ├── safety/                     # 安全响应 schema
│   └── ...
├── deploy/
│   ├── compose.demo.yml            # 阿里云 ECS 演示部署
│   ├── compose.test.yml            # 测试用 Compose
│   ├── compose.dev.yml             # 本地开发 Compose
│   ├── compose.e2e.yml             # E2E 测试覆盖
│   ├── Dockerfile.api              # API 镜像
│   ├── Caddyfile                   # TLS 反代
│   └── compatibility-matrix.json   # 运行时兼容矩阵
├── alembic/                        # 数据库迁移
├── scripts/                        # 工具脚本
├── tests/                          # 本地基线（修订审计时 189 tests）
│   ├── api/                        # REST 接口测试
│   ├── contract/                   # 契约测试
│   ├── integration/                # 集成测试
│   ├── unit/                       # 单元测试
│   ├── adversarial/                # 安全对抗测试
│   ├── security/                   # 安全测试
│   ├── deployment/                 # 部署测试
│   ├── tooling/                    # 工具链测试
│   └── e2e/                        # 端到端测试
├── pyproject.toml                  # uv workspace 根配置
├── uv.lock                         # 依赖锁文件
├── product_system_prd.md           # ★ 最高优先级需求文档
└── member_b_backend_delivery_plan.md  # ★ B 的实施计划
```

---

## 3. 核心架构决策

### 3.1 安全网关（最重要的模块）

**所有用户自由文本**必须经过 `safety/free_text_registry.py` 中注册的 10 个入口之一：

| 入口 | 路由 | 字段 |
|------|------|------|
| `chat.message` | WS /v1/realtime | payload.text |
| `conversation.title` | POST/PATCH /v1/conversations | title |
| `feedback.comment` | POST /v1/feedback | comment |
| `exercise.reflection` | POST /v1/exercise-sessions | text |
| `emotion.correction_note` | POST /v1/emotions/{id}/corrections | correction_note |
| `memory.value` | POST/PATCH /v1/memories | value |
| `knowledge.search` | POST /v1/knowledge/search | query |
| `assessment.optional_note` | POST /v1/assessments | optional_note |
| `profile.nickname` | POST /v1/auth/register | nickname |
| `guest_migration.label` | POST /v1/guest-migrations | label |

**规则：**
- 新增入口 = 必须提升安全契约版本
- 未注册入口的自由文本 = 必须上线前驳回
- 任一入口判定 L2/L3 = 原业务写入必须为零
- 安全服务不可用 = fail closed（阻断普通业务）

### 3.2 数据库关键约束

```sql
-- ★ messages 用 message_ordinal，不是 sequence
-- ★ outbox_events 才用 conversation_id + sequence
-- ★ B 是序列号的唯一分配者
-- ★ A 绝不能读写 sequence

-- 敏感字段全部 AES-256-GCM 加密
-- 每条加密值 = 随机 12 字节 nonce + ciphertext
-- AAD = object_type|object_id|field_name|key_version
```

### 3.3 WebSocket 协议

```
客户端命令: message.send | generation.cancel | session.resume | session.ack | safety.answer
          → ClientCommandEnvelope（没有 sequence 字段！）

服务端事件: message.accepted | risk.status | emotion.result | response.delta | 
           response.completed | response.blocked | safety.question | safety.resources |
           assessment.result.available | memory.mode.changed | error
          → ServerEventEnvelope（sequence ≥ 0，B 独占分配）
```

### 3.4 云端 AI 调用门禁链

```
每次远端 LLM dispatch 前必须按顺序执行：

proof consume=1 → policy read=1 → [approved?] → consent read=1 → [granted?] → dispatch=1

非 approved/granted 分支下 dispatch 必须为 0
```

---

## 4. 已完成 vs 待完成

### 4.1 严格状态（原“B-01 ~ B-20 已完成”声明已撤回）

下表只作快速索引；可复现命令、精确阻塞项和最新计数以
`project_docs/05_progress/member_b_delivery_evidence.md` 与
`member_b_missing_dependencies.md` 为准。路由存在或测试允许 503 不算完成。

| 模块 | 状态 | 说明 |
|------|------|------|
| B-01～B-04 | PARTIAL | Python 3.11、契约、池和 guest 核心已补；MySQL/Docker 门禁未执行 |
| B-05～B-07 | INCOMPLETE | 账户、事务 outbox、WS ticket/ACK 仍有大量 skeleton |
| B-08 | PARTIAL | 严格 fail-closed adapter 已补；A-04 与 SafetyContext 事务闭环缺失 |
| B-09 | INCOMPLETE | guest migration 仍为 skeleton |
| B-10 | PARTIAL | reviewed-turn 边界已补；真实 A runner/repository/WS bridge 缺失 |
| B-11 | INCOMPLETE | emotion/memory 主要业务仍未完成 |
| B-12～B-14 | BLOCKED/PARTIAL | 作者包、A 审核、独立审核和量表 trigger 缺失 |
| B-15～B-18 | PARTIAL | 签名/retention/TOTP/局部对抗门禁已补，正式发布链未闭合 |
| B-19 | UNVERIFIED | 静态部署配置存在，Docker/恢复/性能/ECS 未验证 |
| B-20 | BLOCKED EXTERNAL | 缺 A release profile、C Android/Detox、KVM 与 ECS endpoint |

### 4.2 待完成（优先级排序）

#### P0 — 阻塞性缺失

| 任务 | 文件 | 说明 |
|------|------|------|
| **DB/MySQL 证据** | `database/engine.py` | 连接池已实现；真实 MySQL 迁移/约束/事务证据缺失 |
| **安全网关接入 A** | `safety/gateway.py` | fail-closed port 已实现；A 的 `screen_text()` 与契约缺失 |
| **AI turn 编排** | `ai_bridge/turn_adapter.py` | 严格 adapter 已实现；A 的 `run_screened_turn()` 缺失 |
| **内容制品（24个）** | `content/` | 需要外部作者交付 8 篇知识 + 12 练习 + 2 量表 + 1 危机 + 1 UI |

#### P1 — 重要后续

| 任务 | 说明 |
|------|------|
| **MySQL 集成测试** | 方案要求大量 `docker compose run api-test` 测试 |
| **Ed25519 危机包发布** | 签名/校验已实现；正式内容与审核链输入缺失 |
| **Retention Worker** | 核心清理已实现；真实 MySQL 并发/边界证据缺失 |
| **TOTP 完整实现** | 核心算法已实现；持久 repository/API/reauth/CLI 缺失 |

#### P2 — 可延后

| 任务 | 说明 |
|------|------|
| 语音转写接口 | 只保留接口占位 |
| 本地提醒通知 | 不申请通知权限 |
| iOS/VoiceOver | 无 macOS runner 时标记 UNVERIFIED |
| TensorRT GPU 加速 | 仅 Linux x86_64 + NVIDIA 条件启用 |

---

## 5. 如何扩展每个模块

### 5.1 添加新路由

```python
# 1. 创建模块
src/mental_health_api/mental_health_api/新模块/
├── __init__.py
└── routes.py          # APIRouter + handler

# 2. 注册到 app.py
from mental_health_api.新模块.routes import router as xxx_router
app.include_router(xxx_router)

# 3. 如果是自由文本入口，注册到 safety/free_text_registry.py

# 4. 重新生成 OpenAPI
uv run python scripts/export_openapi.py --write
uv run python scripts/export_openapi.py --check

# 5. 运行全量测试
uv run pytest tests/ -v
```

### 5.2 添加新的数据库表

```python
# 1. 在 database/models.py 添加 SQLAlchemy 模型
# 2. 生成迁移
uv run alembic revision --autogenerate -m "add_xxx_table"
# 3. 运行迁移
uv run alembic upgrade head
# 4. 添加集成测试到 tests/integration/
# 5. 确保 message_ordinal ≠ sequence
```

### 5.3 添加新的错误码

```python
# 1. 在 contracts/public_errors.py 的 CANONICAL_ERRORS 中添加
# 2. 必须同步更新 contracts/errors/canonical_rows.json
# 3. 提升 error-contract version
# 4. 运行契约测试
uv run pytest tests/contract/test_public_errors.py
```

---

## 6. 测试策略

### 6.1 测试分层

```
e2e/         ← 需要 Linux + Docker + KVM + Android（暂无法本地运行）
adversarial/ ← 安全门禁测试（可本地运行）
api/         ← REST 接口测试（可本地运行，用 httpx + ASGITransport）
contract/    ← 契约 schema 测试（可本地运行）
integration/ ← 集成测试（部分需要 MySQL Docker）
unit/        ← 纯逻辑单元测试（可本地运行）
```

### 6.2 常用测试命令

```bash
# 全量测试
uv run pytest tests/ -v

# 只跑能本地运行的（跳过需要 Docker 的）
uv run pytest tests/api/ tests/contract/ tests/unit/ tests/adversarial/ tests/tooling/ -v

# 跑特定模块
uv run pytest tests/api/test_auth.py -v
uv run pytest tests/contract/ -v

# 带覆盖率
uv run pytest tests/ --cov=src/mental_health_api --cov-report=html

# Lint + 格式
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/
uv run mypy src/mental_health_api/
```

---

## 7. 关键命令速查

```bash
# 环境
conda activate mental_health
uv sync --frozen

# 开发服务器（本地，热重载）
uv run uvicorn mental_health_api.app:create_app --factory --reload --port 8000

# Docker 开发环境（MySQL + Redis + Mailpit）
docker compose -f deploy/compose.dev.yml up -d

# Docker 测试环境（完整隔离）
docker compose -f deploy/compose.test.yml up -d --wait mysql redis mailpit

# 数据库迁移
uv run alembic upgrade head

# 生成 OpenAPI
uv run python scripts/export_openapi.py --write

# 质量门禁
uv lock --check
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/
uv run mypy src/mental_health_api/
uv run pytest tests/ -v

# 一键质量检查
uv run python scripts/quality.py python
```

---

## 8. 重要文档引用

| 文档 | 用途 | 优先级 |
|------|------|--------|
| [product_system_prd.md](product_system_prd.md) | 功能需求最高事实源 | ★ 最高 |
| [member_b_backend_delivery_plan.md](member_b_backend_delivery_plan.md) | B 实施计划（B-01~B-20） | ★ 最高 |
| [contracts/openapi/openapi.json](contracts/openapi/openapi.json) | REST API 契约 | 高 |
| [contracts/ws/](contracts/ws/) | WebSocket 协议 | 高 |
| [contracts/errors/canonical_rows.json](contracts/errors/canonical_rows.json) | 26 种错误码 | 高 |
| [deploy/compatibility-matrix.json](deploy/compatibility-matrix.json) | 运行时兼容矩阵 | 中 |

---

## 9. 已知技术债

1. **大多路由返回 503 骨架** — 路由存在不代表领域任务完成；严格状态见 4.1 与 evidence 文档
2. **`# ruff: noqa: E501`** — 部分文件因长 JSON 字符串/ORM 定义而添加了行长度豁免
3. **conda SSL_CERT_FILE 警告** — conda 环境缺少 ssl/cacert.pem，运行时会显示 warning（不影响功能）
4. **tests/ 目录测试未达方案要求** — 当前本地基线 189 tests，仍缺 MySQL/A/C/内容/Android/ECS 门禁测试
5. **content/ 目录为空** — 24 个内容制品需要外部内容作者交付
6. **全仓 mypy 尚未清零** — 当前宽范围检查仍有 78 个旧骨架/未类型化模块错误；本轮功能变更模块的定向 mypy 通过

---

## 10. 对接人已做、未做的明确边界

| | 已做 | 未做 |
|------|------|------|
| **架构** | 18 个路由模块骨架, 10 入口安全网关, 错误码体系, WS 协议 | 真实业务逻辑填充 |
| **数据库** | ORM 模型、AES-256-GCM、进程级 async pool、retention worker（完整迁移前不调度） | 完整 Alembic 表、MySQL 事务/并发/恢复证据 |
| **认证** | Argon2id 哈希, JWT 签发/验证, 密码找回 token | DB 用户存储, 设备管理, refresh 旋转 |
| **部署** | compose.demo.yml, Caddy TLS, 兼容矩阵, 健康检查 | 真实 ECS 部署验证 |
| **测试** | 189 tests (本地单元+契约+API+对抗) | 方案其余测试与全部外部环境门禁 |
| **AI 集成** | fail-closed safety/turn adapters, consent/policy 门禁定义 | A 包真实实现与契约 |

---

> **一句话给下一位开发者：** 本地安全基础已加固，但 B-01～B-20 尚未完成；先读取 evidence/missing-dependency register，再补业务、MySQL 和跨成员真实门禁。
