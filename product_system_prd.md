# AI 心理咨询与情感陪伴助手——功能闭环型系统 PRD

## 1. 文档控制与使用规则

| 项目 | 内容 |
| --- | --- |
| 文档版本 | 2.1 |
| 文档状态 | 已冻结，可作为三人落地方案与验收的唯一产品基线 |
| 更新日期 | 2026-07-14 |
| 产品形态 | 课程、竞赛或内部演示系统 |
| 目标用户 | 18 岁及以上、希望获得一般情绪支持和自助工具的用户 |
| 首发客户端 | React Native 移动端 |
| 后端 | Python、FastAPI、REST、WebSocket |
| AI | 大语言模型 + 本地情绪识别 + 本地危机识别 + 确定性安全编排 |
| 数据 | 移动端 SQLite、服务端 MySQL，敏感数据加密存储 |
| 最终部署 | 阿里云 ECS x86_64 Linux 服务器上的 Docker Compose；基线镜像为阿里云官方 Ubuntu 24.04 LTS；明确不做嵌入式部署 |
| 危机模式 | 自动安全闭环；不提供真人实时处置，不声称已完成救援或转介 |

### 1.1 统一术语与缩写表

本表是 PRD 与成员 A/B/C 三份落地方案的唯一术语事实源；任务编号（A-01、B-01、C-01）、需求编号（SRC/FR/NFR/DEC）和公开错误码按本文定义使用，不得由成员文档另行改义。

| 术语/缩写 | 全称或中文含义 | 本项目中的精确语义 |
| --- | --- | --- |
| AI / LLM | 人工智能 / 大语言模型 | LLM 只生成候选支持文本，不拥有危机等级、量表计分、权限或最终安全动作 |
| CBT | Cognitive Behavioral Therapy，认知行为疗法 | 仅指经审核的结构化自助练习，不等同于诊断或治疗关系 |
| PHQ-9 / GAD-7 / Q9 | 患者健康问卷 9 项 / 广泛性焦虑量表 7 项 / PHQ-9 第 9 题 | 服务端按冻结版本计分；Q9 非零触发结构化安全确认，但不单独等同于 L2/L3 |
| PII / NER / NFKC / OOD | 个人可识别信息 / 命名实体识别 / Unicode 兼容规范化 / 分布外输入 | 本地规则与独立中文 NER 共同执行；任一不可用、不确定或 OOD 都禁止云 dispatch |
| RAG | Retrieval-Augmented Generation，检索增强生成 | 只检索当前已审核、未撤回、未过期知识，正文始终按不可信资料处理 |
| ECE / MAE / F1 / FPR | 期望校准误差 / 平均绝对误差 / F1 分数 / 假阳性率 | 情绪与危机模型的冻结评测指标，阈值以 A 方案的签名 gate 为准 |
| P50 / P95 | 第 50/95 百分位 | 延迟或性能分布指标，不得用未审核 token 的时间冒充安全首块延迟 |
| API / REST / HTTP / HTTPS | 应用程序接口 / 表述性状态传递 / 超文本传输协议及其 TLS 加密版本 | REST 路径与 method 以 PRD 18.1 和 B 的 OpenAPI 为唯一事实源 |
| GET / POST / PATCH / DELETE | HTTP 读取 / 创建或动作 / 局部更新 / 删除方法 | route 的 method 是契约组成部分，不能互换或发明集合/单项别名 |
| WebSocket / WS / WSS | WebSocket 及其非加密/经 TLS 加密连接 | 实时对话协议；生产/远程目标只使用 WSS |
| TLS / CA | Transport Layer Security，传输层安全 / Certificate Authority，证书颁发机构 | release/remote 必须验证受信任 HTTPS/WSS 证书；本地 e2e 不得把测试 CA 或明文信任带入 release APK |
| DTO / JSON / JSONL / JSON Schema | 数据传输对象 / JSON / 逐行 JSON / JSON 结构约束 | 跨成员契约必须 strict、拒绝未知字段，并通过 canonical/mutation round-trip |
| ACK / CAS | acknowledgement，确认 / compare-and-swap，比较并交换 | C 只 ACK 已连续落地的 server sequence；B 用 CAS 保证 ACK 只前进 |
| RBAC / MFA / TOTP / JWT | 基于角色的访问控制 / 多因素认证 / 基于时间的一次性密码 / JSON Web Token | 管理鉴权、再认证和短期 access token 的安全机制；普通用户无管理权限 |
| TTL / HMAC / AAD | 生存时间 / 基于哈希的消息认证码 / 附加认证数据 | 短期 proof/token 时限、只存摘要和 AES-GCM 主体/用途绑定 |
| AES-GCM / SHA-256 / SHA-512 | 认证加密算法 / 安全哈希算法 | 高敏字段、制品、proof、签名依赖与证据 hash 的冻结算法语义 |
| Ed25519 / JCS / RFC 8032 / RFC 8785 | 椭圆曲线签名 / JSON Canonicalization Scheme / Request for Comments 标准文档中的签名与规范化标准 | B 签离线危机包，C 只按严格模式验证 canonical bytes 和签名 |
| ETag | HTTP 实体标签 | 内容版本缓存验证标识；撤回后必须失效，不能继续显示旧内容 |
| RPO / RTO / SLA | 恢复点目标 / 恢复时间目标 / 服务级目标 | 演示环境恢复与性能目标；未达到时如实 FAIL/未验证，不宣称生产承诺 |
| CI / E2E | 持续集成 / 端到端测试 | 可重复自动化门禁；E2E 必须贯通真实 A→B→C 关键链路 |
| DAG | Directed Acyclic Graph，有向无环图 | A/B/C 任务依赖必须可拓扑执行，任何显式或命令级循环都使方案 FAIL |
| CPU / GPU / CUDA / ONNX / TensorRT / TRT / FP16 | 处理器、NVIDIA 计算平台、开放模型格式、NVIDIA 推理运行时及半精度 | CPU/ONNX 为可用基线；TensorRT 仅在 NVIDIA Linux 能力存在时作为条件加速 |
| RAM / SM | 随机存取内存 / NVIDIA Streaming Multiprocessor 计算能力标识 | 敏感 draft 只可短驻 RAM；TensorRT engine 路径中的 sm 表示目标 GPU compute capability，不是共享存储 |
| ABI / C ABI / ARM / x86_64 | 应用二进制接口 / C 语言 ABI / 两类处理器架构 | C++ 仅可提供 Linux x86_64 模型加载扩展；ARM/嵌入式不在范围 |
| KVM / AVD / APK / JDK | Linux 内核虚拟机 / Android 虚拟设备 / Android 应用安装包 / Java 开发工具包 | Linux CI 上构建并运行真实 Android/Detox 的工具条件，不是 ECS 服务端依赖 |
| SQL / SQLite / MySQL / ORM / CRUD / DB | 数据库查询语言、本地/服务端数据库、对象关系映射、增删改查、数据库 | SQLite 仅端侧；MySQL 是服务端业务事实源，不得用 SQLite 冒充 MySQL 集成证据 |
| SBOM / SDK / RPC / CLI / IDE / UI / OS / URL / UTC / UTF-8 | 软件物料清单、开发包、远程调用、命令行、开发环境、界面、操作系统、地址、协调世界时、字符编码 | 工具链、供应链与接口证据使用的通用工程术语；时间统一 UTC，文本统一 UTF-8 |
| ID / CN / QQ | 标识符 / 中国地区码 / 腾讯 QQ 社交账号 | ID 由服务端或冻结内容产生；CN 用于中国大陆资源制品；QQ 账号按 PII 处理 |
| MYPYPATH | mypy 的 Python 模块搜索路径环境变量 | 只允许仓库相对路径，不能写成员机器绝对路径 |
| BRIGHTER / CC BY 4.0 | 情绪数据集项目名 / Creative Commons Attribution 4.0 许可 | 只在 A 的数据清单、许可核验和模型评测中使用；许可不替代个人信息与用途审核 |
| CARLA / Visio | 自动驾驶仿真工具 / 流程绘图工具 | CARLA 对本项目不适用且依赖面为零；Visio 仅可选外部绘图，无运行时依赖 |
| MSW | Mock Service Worker | 仅可用于前端孤立单测，真实全栈 E2E 禁止用它替代 REST/WS |
| MAC | Media Access Control，网络接口硬件地址 | 项目不把 MAC 当访客标识，不采集或上传它；不要与 HMAC 混淆 |
| PRD / SRC / FR / NFR / DEC | 产品需求文档 / 原始来源 / 功能需求 / 非功能需求 / 决策编号 | 本文的追踪标识；SRC-F01～F05 与 SRC-T01～T12 是最高硬门禁 |
| P0 / P1 / P2 | 必须、重要后续、可选后续优先级 | P0 全部满足才可交付；本轮时间不裁剪 P0 |
| L0 / L1 / L2 / L3 | 常规、关注、高风险、紧迫危险 | 确定性危机路由等级；L2/L3 阻断普通生成并进入自动安全闭环 |
| RED / GREEN / PASS / FAIL / SKIP | 测试驱动与门禁状态 | RED 是预期失败、GREEN 是目标测试通过；SKIP 仅限文档明确的条件能力且不能冒充 PASS |
| ECS / LTS | 阿里云云服务器 / 长期支持版本 | 唯一最终服务端目标为阿里云 ECS x86_64 Linux，基线 Ubuntu 24.04 LTS |
| RN / TS | React Native / TypeScript | 当前唯一移动端技术路线及其实现语言 |

本文是项目最高优先级的功能需求源。需求冲突时按以下顺序处理：

1. 本文第 2 节记录的原始项目硬性要求。
2. 本文的功能闭环、边界、验收和技术决策。
3. 成员 A、B、C 三份落地方案。
4. project_requirements.md、three_person_task_division.md 及既有研究/设计文档。

任何人不得在成员方案、接口实现或客户端文案中弱化五项硬性功能。若发现冲突，应修改下游文档和实现，不能反向修改原始要求的含义。

## 2. 原始项目要求与严格符合性基线

### 2.1 原始功能要求

| 来源编号 | 原始要求 | 本项目必须交付的可验证结果 |
| --- | --- | --- |
| SRC-F01 | 多轮深度对话共情：运用大语言模型，模拟心理咨询师进行多轮对话，展现共情、倾听和引导能力 | 可连续进行不少于 20 轮的安全对话；回复体现情绪确认、复述澄清、开放式提问和经用户同意的行动引导；不诊断、不说教、不制造依赖 |
| SRC-F02 | 情绪状态智能识别：通过分析用户输入的文本（及未来可能的语音语调），识别用户的当前情绪状态（如焦虑、抑郁、压力） | 当前版本完成文本多标签情绪识别、强度、置信度、不确定状态和用户纠正；保留语音转写、声学特征和多模态融合接口 |
| SRC-F03 | 正念与 CBT 练习引导：提供结构化的正念冥想、认知行为疗法（CBT）练习引导，帮助用户管理情绪 | 提供经审核的练习目录、逐步引导、暂停/恢复/跳过/退出、进度和反馈；危机状态禁止用练习替代安全行动 |
| SRC-F04 | 心理健康知识科普与自测：提供科学的心理健康知识，并包含标准化的心理自测量表（如 PHQ-9、GAD-7） | 只发布有来源和版本的审核内容；完整实现 PHQ-9、GAD-7、后端计分、临界值、第 9 题安全联动、非诊断结果和历史记录 |
| SRC-F05 | 危机预警与转介：识别用户话语中的极端言论或自杀 | 所有自由文本入口执行危机检测；按 L0–L3 决策；高风险阻断普通生成，展示 110、120、12356、可信联系人和安全行动；本演示系统准确表述为“求助引导”，不得宣称真人已接管 |

### 2.2 原始技术信息与采用方式

| 来源编号 | 原图技术信息 | 本项目采用方式 | 符合性判定 |
| --- | --- | --- | --- |
| SRC-T01 | AI 核心：Python | AI、安全和后端主实现使用 Python 3.11 | 强制 |
| SRC-T02 | 大语言模型需高安全、符合伦理 | 模型调用前脱敏，输入先检查；候选输出完整复核后才能发送；提示词与安全策略版本化 | 强制 |
| SRC-T03 | 情感分析模型 | 提供独立文本情绪模型，不用大语言模型主观回答冒充稳定分类结果 | 强制 |
| SRC-T04 | 后端服务：FastAPI | 服务端 API 采用 FastAPI，生成 OpenAPI 契约 | 强制 |
| SRC-T05 | WebSocket 实时对话 | 对话使用带 ACK、序列号、续接、取消和幂等语义的 WebSocket 协议 | 强制 |
| SRC-T06 | 移动端 React Native/Flutter 或小程序 | 当前版本统一采用 React Native + TypeScript；不同时维护多套客户端 | 强制，已选 React Native |
| SRC-T07 | SQLite/MySQL 加密存储 | SQLite 保存访客和端侧最小数据；MySQL 保存账户业务数据；令牌使用系统安全存储；高敏字段加密 | 强制 |
| SRC-T08 | 开发语言 Python/C++ | Python 为必需主语言；C++ 只作为 Linux 上的本地模型/TensorRT 性能扩展边界，不为凑技术栈复制业务逻辑 | Python 强制，C++ 条件使用 |
| SRC-T09 | TensorRT | 提供本地情绪/危机模型导出与 TensorRT 推理适配设计；有 NVIDIA Linux 环境时完成构建与基准，无该环境时保留经过测试的 PyTorch/ONNX 回退 | 条件强制，不得阻断无 GPU 演示 |
| SRC-T10 | Git、PyCharm、VSCode | Git 作为唯一版本与配置变更追踪；工程同时兼容 PyCharm 和 VSCode | 强制 |
| SRC-T11 | Visio、CARLA | Visio 可用于系统流程和架构图；CARLA 与本项目心理支持功能无有效依赖，不引入虚假集成，在技术说明中记录不采用理由 | 已评估并明确处置 |
| SRC-T12 | Linux/嵌入式 | 原始信息给出“Linux/嵌入式”可选部署环境；本项目明确选择阿里云 ECS 上的 x86_64 Linux 容器作为唯一最终部署目标，不设计、不实现、不测试嵌入式部署 | 阿里云 ECS Linux 强制，嵌入式明确不采用 |

严格符合不是简单出现技术名词，而是：强制项必须有代码、接口或测试证据；条件项必须有清楚的启用条件、回退路径和不采用理由。

## 3. 已冻结的产品决策

| 决策编号 | 决策 | 直接影响 |
| --- | --- | --- |
| DEC-001 | 项目用于课程、竞赛或内部演示，不作为公众危机服务直接上线 | 无真人实时值守；界面不得承诺报警、救援或已完成转介 |
| DEC-002 | 提供访客体验和正式账户 | 访客低门槛使用；账户支持同步、历史、记忆、导出和删除 |
| DEC-003 | 优先实现用户可控长期记忆 | 记忆必须可见、可改、可删、不串户；达不到门禁时关闭跨会话调用，只保留聊天历史 |
| DEC-004 | 危机采用自动安全闭环 | 检测、分级、阻断、资源、可信联系人、安全计划、审计和复核队列全部自动化；复核队列只用于离线质量检查 |
| DEC-005 | 不纳入商业运营 | 无订阅、支付、广告、营销增长和复杂客服排班 |
| DEC-006 | 当前版本只处理文本 | 语音语调为 P2 扩展，当前不得申请麦克风或保存音频 |
| DEC-007 | 项目不提供医疗服务 | 不输出疾病诊断、处方、药物调整、治愈保证或虚构专业资质 |
| DEC-008 | 最终部署只采用阿里云 ECS Linux | 服务端、模型推理、数据库和实时网关最终部署在单台阿里云 ECS x86_64 Linux；基线为官方 Ubuntu 24.04 LTS + Docker Compose。嵌入式不进入架构、任务、测试或发布证据 |

## 4. 产品目标、作用与完成定义

### 4.1 产品目标

1. 让用户在需要倾诉时获得有边界的共情、倾听、澄清和下一步引导。
2. 帮助用户认识当前情绪及其不确定性，而不是给用户贴疾病标签。
3. 让用户能够独立完成短时正念和 CBT 自助练习。
4. 提供可核验的心理健康知识与标准化自测，帮助用户决定是否寻求专业支持。
5. 在出现危险线索时优先保护用户，停止普通对话并连接现实世界求助资源。

### 4.2 产品不追求的结果

- 不以聊天时长、消息数量或用户依赖 AI 作为成功指标。
- 不承诺治疗效果，不替代心理咨询师、精神科医生或紧急服务。
- 不根据一次情绪识别或一次量表结果定义用户人格、疾病或服务权限。
- 不允许 LLM 自行改变量表分数、危机等级、权限或数据保存策略。

### 4.3 功能完成定义

任一功能只有同时具备以下证据才算完成：

1. 有明确用户作用、入口、正常路径和退出路径。
2. 前端具备加载、空数据、成功、失败、弱网、离线、重复提交和权限拒绝状态。
3. 后端具备版本化接口、鉴权、校验、幂等、事务和稳定错误码。
4. 数据具备主体归属、敏感等级、保存、导出、删除和审计规则。
5. 安全路径不能被模型失败、取消生成、断线或提示注入绕过。
6. 有单元、契约、集成或端到端测试，并能追溯到需求编号。
7. 有清楚的降级行为；降级后不得显示虚假成功状态。

## 5. 用户与系统角色

| 角色 | 可用能力 | 明确限制 |
| --- | --- | --- |
| 未登录访客 | 查看 AI 边界、科普、危机资源；进行临时对话、练习和自测；决定是否保存在本机 | 无云端同步、跨设备历史和长期记忆；清除应用数据后不可恢复 |
| 正式账户用户 | 使用全部核心功能、云端历史、设备管理、可控记忆、趋势、导出、删除和注销 | 只能访问本人数据；敏感用途需分项同意 |
| 指定内容作者（外部前置角色，不属于 A/B/C 工程 owner） | 按工程冻结的 source/review/handoff schema，在工程外一次性交付 source register、科普/练习/量表元数据/危机资源/安全 UI 共 24 个草稿和 content-author handoff | 不能参与 content-safety、独立领域或 release-validation 审核，不能读取普通聊天原文；缺少完整不可变作者包时工程只可保留空骨架，不能发布 |
| 安全复核员 | 查看脱敏风险事件，标记确认/误报和规则问题 | 非实时救援人员；不能向用户显示“正在处理”，不能浏览任意会话 |
| 系统管理员 | 管理角色、版本、功能开关和审计查询 | 默认不能读取心理正文；敏感操作需再认证并留下审计 |
| 外部专业审核人 | 审核量表、练习、科普和危机话术 | 不直接使用系统管理权限；审核结果以版本化记录导入 |

## 6. 产品信息架构与页面清单

### 6.1 移动端主导航

移动端采用五个一级入口：

1. 首页：快速倾诉、当前状态、继续练习、开始自测、紧急帮助。
2. 对话：会话列表、创建会话、实时聊天、总结和反馈。
3. 工具：正念、CBT、情绪记录和练习历史。
4. 知识：科普分类、搜索、详情和 PHQ-9/GAD-7 入口。
5. 我的：账户、访客升级、记忆、历史、隐私、设备、导出、删除、注销和关于。

危机入口不依赖主导航位置，登录页、首页、对话页、自测页和离线页都必须可直接进入。

### 6.2 页面与状态矩阵

| 页面组 | 必须页面 | 必须覆盖的非正常状态 |
| --- | --- | --- |
| 启动与告知 | 启动页、年龄声明、AI 身份与边界、隐私同意、访客/登录选择 | 无网、配置加载失败、拒绝可选同意、年龄不满足 |
| 账户 | 注册、登录、找回、设备列表、退出、注销 | 账号不存在不泄露、密码错误、令牌过期、设备被撤销、重复提交 |
| 首页 | 功能入口、最近会话、推荐工具、危机入口 | 新用户空状态、局部加载失败、离线只读 |
| 对话 | 会话列表、聊天、模式选择、生成中、总结、反馈 | WebSocket 断线、重连、乱序、取消、模型超时、输出阻断、风险升级 |
| 情绪 | 当前识别、用户纠正、趋势 | 置信度不足、无历史、缺失区间、纠正保存失败 |
| 练习 | 目录、详情、步骤、暂停、完成、反馈、历史 | 内容过期、恢复失败、提前退出、离线资源不可用 |
| 科普 | 分类、搜索、详情、来源 | 无结果、内容撤回、版本过期、离线缓存过期 |
| 自测 | 说明、答题、漏答提示、结果、历史 | 中途退出、重复提交、后端分数不一致、第 9 题安全联动 |
| 危机 | 全屏安全页、风险确认、资源、可信联系人、安全计划 | 地区未知、无网、拨号不可用、资源过期、用户拒绝回答 |
| 我的 | 记忆、隐私、导出、删除、同意、关于 | 权限不足、导出处理中、删除失败重试、长期记忆降级 |

### 6.3 管理能力的当前交付形态

当前是课程、竞赛或内部演示系统，管理能力冻结为 **FastAPI 结构化管理 API + 仓库内 Git 内容制品 + CLI**，不建设独立 Web 管理端，也不把“管理页面”作为当前发布门禁。管理 API 只接收内容 ID、版本、校验和、审核决定、启停状态等结构化字段；科普、练习、量表、危机资源与安全 UI 文案必须在 Git 制品中编写和评审，管理 API 不接受任意正文，避免形成第十一种未登记自由文本入口。

- 管理员使用邮箱、密码、TOTP MFA 和 5 分钟有效的再认证令牌；恢复码只保存哈希。
- CLI 支持导入、校验、发布、撤回、版本差异、回滚与审计查询。
- PHQ-9/GAD-7 计分规则只读核验，不能在运行时编辑。
- 脱敏风险复核只用于离线质量改进，不是真人实时救援；复核决定使用固定枚举，不接收自由文本备注。
- 模型、提示词、安全规则、角色权限和内容版本的变更均写审计记录。

## 7. 端到端用户流程

### 7.1 访客首次进入

1. 展示 AI 非真人、非医疗、非紧急服务边界。
2. 完成年龄声明；不满足 18 岁时只开放静态安全资源。
3. 用户选择访客体验或正式账户。
4. 客户端调用 `POST /v1/guest-sessions`；服务端创建不可枚举的 `guest_subject_id`，签发 256 bit 随机 opaque guest access token，只保存 token HMAC 摘要并设置 24 小时 TTL。客户端把 token 写入 Keychain/Keystore，并建立加密 SQLite 数据区；服务端绝不信任客户端自报 guest ID。
5. guest token 仅允许 onboarding、注册、统一安全门、realtime ticket 和五项演示核心功能，并只能访问自己的临时会话；用户选择“想说一说、了解情绪、做练习、看知识、做自测”。
6. 任何页面都能进入危机资源；静态资源无需身份，AI/实时链路使用 guest token。服务端为多轮对话、计分、幂等和断线重放暂存最小加密业务记录、风险记录及 outbox，最迟 24 小时删除；SQLite 是访客主动保存记录的持久事实源。

### 7.2 访客升级账户

1. 账户采用邮箱和密码注册；昵称可选，不要求真实姓名。
2. 注册成功后列出访客本地记录类型和数量。
3. 用户逐类选择迁移会话、练习、自测；危机事件不自动迁移为长期记忆。
4. 直接注册必须证明仍有效的 guest session；客户端创建 `batch_id` 和稳定 `item_id`，但服务端只把已认证 guest subject 合并到目标账户，不按设备标识或客户端 ID 合并主体。
5. 迁移标签按 `guest_migration.label`、稳定 item 顺序和派生幂等键逐项安全筛查；全部 L0 后才在一个事务写入。第一个非 L0 立即停止，整批业务写入为零，并创建一个可重放的安全事件。
6. 服务端已有的 24 小时临时记录与 SQLite 待上传记录使用同一批次去重；迁移成功并收到服务端提交证明后才清理本地副本，失败时保留并允许重试。
7. `DELETE /v1/guest-sessions/current` 立即撤销 token 并清除可删除临时数据；过期清理任务执行相同规则。

### 7.3 普通多轮对话

1. 用户选择“只想倾诉、一起理清、想做练习、找知识”之一，也可跳过选择。
2. 输入固定先经过规范化与危机筛查，再做 PII 处理；不得先脱敏到丢失危机特征。
3. 无高风险时，情绪识别和对话状态机生成结构化上下文。
4. 大语言模型生成候选完整回复，输出安全检查通过后再分块推送。
5. 客户端同时显示非诊断情绪线索；用户可以纠正。
6. AI 在合适时机征求是否总结、做练习或结束，不强迫继续。
7. 会话创建时显式选择 `persistence_mode=ephemeral|saved`；账户 `ephemeral` 与所有访客服务端业务数据最多保存 24 小时，`saved` 保存到用户删除。访客可把记录保存在端侧或主动删除。
8. 用户可请求安全会话总结；总结通过输出复核后返回，但只有用户再次明确确认并调用记忆接口时才成为长期记忆，禁止自动写入。

### 7.4 危机自动安全闭环

1. 所有自由文本和 PHQ-9 第 9 题先经过危机筛查。
2. L1 进入结构化安全确认；L2/L3 立即停止普通 LLM、CBT、正念和知识推荐。
3. 展示简短共情、安全确认、110/120/12356、可信联系人和“前往最近急诊”等真实行动。
4. 地区未知时提供中国大陆默认资源和通用当地紧急服务说明。
5. 客户端即使离线也能读取签名且未过期的危机资源包。
6. 服务端保存最小化风险事件、规则/模型版本和执行动作；不在普通日志保存原文。
7. 后续消息保持风险粘滞状态，只有确定性规则满足时才能降级。
8. 系统不自动拨号、不自动发送联系人消息、不显示真人接单状态。

### 7.5 练习闭环

1. 用户主动选择，或在普通风险状态下接受 AI 推荐。
2. 展示目的、预计步骤、适用/不适用场景和随时退出入口。
3. 支持逐步完成、暂停、恢复、跳过和提前结束。
4. 完成后记录可选的前后感受和反馈；不强制填写自由文本。
5. CBT 敏感文本允许单条删除；练习版本随记录保存。

### 7.6 科普与自测闭环

1. 科普只展示已审核、未过期且来源可核验的版本。
2. PHQ-9/GAD-7 开始前显示回顾周期、非诊断说明和退出权利。
3. 客户端检查漏答，服务端使用锁定版本重新计分。
4. PHQ-9 第 9 题非零先触发独立安全确认，再显示总分解释。
5. 结果使用“症状线索/筛查结果”，不使用“确诊”。
6. 用户选择保存、导出或删除记录；结果可链接相关科普和专业求助建议。

### 7.7 数据权利闭环

1. 用户能查看系统保存的会话、记忆、情绪、练习和自测数据。
2. 支持单条删除、按类别删除、导出全部数据和注销账户。
3. 删除任务覆盖主库、缓存、检索索引、端侧副本和可删除派生数据。
4. 删除过程显示请求状态；失败自动重试且不显示虚假完成。
5. 撤回某项可选同意后，新的处理立即停止；核心危机资源仍可访问。

## 8. 账户、访客、设备与权限需求

### 8.1 账户生命周期

| 需求编号 | 要求 | 验收 |
| --- | --- | --- |
| FR-ACC-001 | 邮箱密码注册、登录、刷新、退出、找回、关闭账户 | 注册/登录/找回/关闭 E2E 通过；错误不暴露邮箱是否存在 |
| FR-ACC-002 | 访问令牌短期有效，刷新令牌旋转并可撤销 | 退出或撤销设备后 REST 与 WebSocket 均失效；重放刷新令牌导致令牌族撤销 |
| FR-ACC-003 | 用户查看并撤销设备会话 | 被撤销设备不能继续续接会话，本地敏感缓存被清理 |
| FR-ACC-004 | 所有业务对象由服务端主体 ID 授权 | 修改客户端 user_id 或对象 ID 不能读取他人数据 |
| FR-ACC-005 | 管理端 RBAC、MFA、对象级和字段级权限 | 普通管理员不能检索聊天原文；越权动作 fail closed 并审计 |

密码找回协议固定为：`POST /v1/auth/recovery-requests` 无论邮箱是否存在都返回 HTTP 202；服务端生成 256 bit 一次性 token，仅保存 HMAC 摘要，TTL 15 分钟、限流且单次使用。`POST /v1/auth/recovery-confirmations` 接收 token 与新密码，成功返回 204 并撤销该账户全部 refresh-token family；无效、过期或已使用 token 统一返回 `RECOVERY_TOKEN_INVALID`，不暴露账户状态。B 提供 `RecoveryMailer` port，Linux 开发/测试/演示环境用 Mailpit 完成真实 E2E，邮件不得包含心理内容。

管理 API/CLI 的 MFA 固定使用 TOTP：enrollment seed 加密保存，确认后启用，恢复码只存哈希；敏感管理动作需密码 + TOTP 换取 5 分钟 reauth token。当前范围不建设 Web 管理端。

### 8.2 访客身份与数据

- `POST /v1/guest-sessions` 是所有未登录 AI/自测/练习调用的身份入口；guest token 可调用 `POST /v1/realtime/tickets`，ticket 必须绑定 guest subject、session、device key 和目标 conversation，不能订阅其他主体会话。
- 访客主体不可枚举，不使用广告 ID、MAC 或可猜设备号；客户端不发送具备授权意义的 `guest_id`。
- SQLite 是访客主动保存会话、自测和练习的持久事实源；为支持真实多轮、后端计分、事务 outbox、序号和 resume，服务端可暂存加密的会话、消息、量表结果、练习进度、风险最小记录和 outbox，TTL 最长 24 小时且不形成跨设备历史或长期记忆。
- 访客可调用 `DELETE /v1/guest-sessions/current` 并清空当前设备数据；服务端清除任务和客户端清除都成功后不可恢复。
- 危机静态资源和 AI 边界说明不依赖身份；安全实时事件使用 guest token。
- 升级账户必须证明 active guest session，按记录类型显式确认；迁移幂等、可恢复且禁止客户端身份合并。

## 9. 用户可控长期记忆

### 9.1 允许记忆的内容

- 用户明确确认的称谓和沟通偏好。
- 用户主动保存的长期目标。
- 用户确认有效的应对方式、练习偏好和支持资源。
- 用户确认后的会话摘要，不保存系统未确认的推测。

### 9.2 禁止自动记忆的内容

- 危机原话、风险等级和安全确认答案。
- PHQ-9/GAD-7 逐题答案。
- 紧急联系人、密码、令牌和精确身份信息。
- 模型推断的疾病、人格、创伤或敏感身份标签。
- 用户已经删除或撤回授权的内容。

### 9.3 记忆控制与降级门禁

| 需求编号 | 要求 |
| --- | --- |
| FR-MEM-001 | 长期记忆只对正式账户开放，默认关闭，由用户主动开启 |
| FR-MEM-002 | 每条记忆显示来源类别、创建时间和最后使用时间，可编辑、删除和暂停使用 |
| FR-MEM-003 | AI 引用记忆时可向用户说明来源；用户纠正后旧值立即失效 |
| FR-MEM-004 | 记忆检索按用户、用途和同意状态隔离，任何跨用户命中视为 P0 缺陷 |
| FR-MEM-005 | 若无法证明可见、可改、可删、不串户和删除后不再引用，功能开关关闭跨会话记忆；会话历史仍可查看但不自动注入模型 |

记忆能力的唯一公共状态由 B 的 `contracts/memory/memory_capability.schema.json` 与 `GET /v1/memory-capability` 提供，响应固定含 `mode=controlled|history_only`、`reason`、`policy_version`、`effective_at`、`memory_version`。切换时 B 发出 `memory.mode.changed`；C 清除能力缓存并重取，A 在 `history_only` 下不得注入任何长期记忆。

`GET /v1/conversations/{conversation_id}/context-proof?turn_id={turn_id}` 返回 `mode`、`included_memory_ids`、`exclusion_reason_codes` 和 `policy_version`，不得返回记忆值或消息正文。记忆 CRUD、tombstone 与删除证明均有 schema；删除成功后旧 `memory_version` 立即失效，任何上下文证明再出现已删除 ID 都是 P0。

## 10. 核心功能一：多轮深度对话共情

### 10.1 产品作用

让用户感到被听见、帮助其澄清感受和需求，并在得到同意后提供可执行的小步骤。AI 使用心理咨询常见的沟通技巧，但必须持续表明自己是 AI 心理支持工具而非持证咨询师。

### 10.2 对话行为合同

每个普通回复按上下文选择以下动作，不机械套用全部动作：

1. 情绪确认：用谨慎语言承认用户可能的感受。
2. 事实复述：准确复述关键事实，不添加未提供的经历。
3. 澄清提问：一次优先提出一个开放式问题。
4. 目标确认：询问用户此刻希望倾诉、理清、练习还是找资源。
5. 行动引导：仅在用户愿意时给出一至三个小步骤。
6. 自主结束：用户表达停止时立即结束，不挽留、不内疚化。

禁止诊断、药物建议、绝对保密承诺、依赖诱导、虚构真人经历、排斥现实关系和未经请求的强制建议。

### 10.3 前端要求

- 显示 AI 标识、会话标题、连接状态、发送状态、取消生成和危机入口。
- 支持逐安全分块展示，不显示未经复核的原始 token。
- 显示“有帮助、无帮助、不准确、让我不舒服”反馈。
- 断线后显示最后确认序号，恢复时不重复消息。
- 风险升级时丢弃未发送普通回复并切换全屏安全流程。

### 10.4 后端与 AI 要求

- 确定性状态机负责阶段、工具权限、风险分支和失败回退；不得让通用 Agent 自主决定安全动作。
- 聊天输入只筛查一次：B 的 `FreeTextSafetyGateway` 构造完整 `FreeTextSafetyRequest(entry_point='chat.message', ...)` 并调用 A 的 `screen_text(request)`；L0 得到短期、一次性、主体绑定的 `screening_decision_id` 后调用 `run_screened_turn`。A 不得在 turn 编排中再次筛查。允许决策只保存在当前 FastAPI 进程内短 TTL 的 DecisionStore，原文/脱敏文本不落盘；消费原子且幂等，进程重启或过期时 fail closed 并要求客户端以原业务幂等键重试。
- v1 部署边界冻结为：FastAPI 进程以内嵌 Python 包方式调用 `mental_health_ai`，`FreeTextSafetyGateway`、DecisionStore、TurnOrchestrator 和 B 的 repository/consent adapters 位于同一进程；`deploy/compose.demo.yml` 的 API 固定单 replica、单 Uvicorn worker。可选独立 `model-runtime` 只执行无状态本地情绪/危机 logits 推理，不拥有 DecisionStore、业务事务、LLM 编排或安全动作。扩容、多 worker、跨进程 AI orchestration 或共享 proof store 均属于新架构版本，必须先设计加密共享存储/路由与故障语义，不能直接复制 v1 容器。
- 处理顺序固定为：B 构造并校验入口上下文 → A 对当前输入做规范化/危机检查/规则+中文 PII NER 并签发允许决策 → `run_screened_turn` 原子消费允许决策 → 情绪识别 → 选择当前脱敏输入、会话历史、授权记忆与已审核知识 → A 对这些逐字段及最终序列化 provider payload 再执行一次 `CloudContextPiiGate` → TurnOrchestrator 只取得并把**未消费**、绑定 payload hash 的内存 `CloudSafePayloadProof` 交给 A-07 provider adapter → provider adapter 是 proof 的唯一消费点：先原子验证/消费 proof，再通过 B 的 `ProviderProcessingPolicyPort` 读取当前 provider 的组织级处理能力；只有 policy 为有效 approved 才继续通过 B 的 `ConsentSnapshotPort` 即时读取当前用户最新云处理同意，三者均有效且同意为 granted 才执行一次远端 dispatch；其余情况只走本地批准模板或审核知识路径 → 输出安全复核 → 原子提交 → WebSocket 推送。最终 PII 门必须先于 policy/同意读取和每一次 provider dispatch，不能复用入口门结论替代，也不能由编排层提前消费 proof、提前缓存 policy 或同意。
- 对话上下文只包含当前会话、用户授权记忆和最小必要已审核知识。
- 本地 PII 识别固定为规则/已知实体与独立中文 NER 的并集。NER 基座固定 `hfl/chinese-macbert-base@a986e004d2a7f2a1c2f5a3edef4e20604a974ed1`（Apache-2.0），使用独立 `pii-ner-v1` checkpoint/tokenizer/config/calibrator，不与情绪或危机 task head 共用；manifest 必须记录基础 revision、许可证、模型/tokenizer/config/calibrator SHA-256、标签、训练数据许可/哈希和运行命令。识别至少覆盖姓名、详细地址、机构、学校/单位、微信/QQ 等社交账号及其他标识。checkpoint/hash/tokenizer/license 缺失、OOD、置信灰区、offset 越界/重叠无法解析、超时或异常时 `cloud_allowed=false`，远端 provider 调用数为 0；本地批准安全路径仍可使用。
- `CloudSafePayloadProof` 只含一次性 nonce、subject/conversation/turn 绑定、最终 payload SHA-256、PII policy/model/tokenizer/calibrator 版本和短 TTL，不含原文、脱敏文本或实体值；provider adapter 必须拒绝 proof 缺失、过期、已消费或 payload hash 不一致。每次 provider 尝试的 proof consume count 精确为 1，随后紧邻一次新鲜 ConsentSnapshot 读取；granted 正常分支 dispatch count=1，其他分支=0。测试必须分别在当前输入、历史、长期记忆、知识引用和最终序列化上下文注入未知中文姓名、详细地址、机构/学校、微信/QQ 变体，并注入 NER unavailable/OOD/offset 错误，所有失败分支的 provider spy 调用数必须为 0。
- `ProviderProcessingPolicySnapshot` 与用户 `ConsentSnapshot` 是两个不可合并的门。前者由 B 拥有，固定字段为 `provider_id`、`policy_version>=1`、`status=disabled|approved|expired`、可空 `matrix_sha256`、可空 `processor_contract_ref`、可空 `independent_review_ref`、`data_region`、`cross_border_status=not_applicable|approved|blocked`、可空 `approved_at`、可空 `review_expires_at`、`loaded_at`。`disabled` 固定所有批准字段为 null 且 cross_border blocked；`approved` 要求三个批准引用和两时间非空、`approved_at<=loaded_at<review_expires_at` 且 cross_border 非 blocked；`expired` 保留批准引用但 `loaded_at>=review_expires_at`。该演示项目不另设 policy 签名密钥：policy JSON 是 Git-reviewed 配置，repository 必须把其 `matrix_sha256` 与同一 commit 中独立复核矩阵文件的实际 SHA-256 做逐字节比对，并校验 schema、引用存在性和时钟。缺配置、解析/schema/matrix hash/引用/时钟失败一律合成为 disabled，远端 provider capability 默认关闭。
- 唯一 dispatch 次序与调用计数固定为：cloud proof consume=1 → policy read=1 → policy approved 时 consent read=1 → consent granted 时 provider dispatch=1。policy disabled/expired/invalid 时 consent read=0、dispatch=0；policy approved 但 consent 非 granted/非法时 dispatch=0。任何重试必须重新签发 proof 并重新读取 policy/consent，不能复用 snapshot。
- `ConsentSnapshot` 固定含 `subject_id`、`consent_type=cloud_model_processing`、`policy_version`、`consent_version`、`status=granted|withdrawn|missing`、可空 `granted_at`、可空 `withdrawn_at`、`loaded_at`，并按 status 判别：`missing` 表示从未授权，固定 `consent_version=0`、`granted_at=null`、`withdrawn_at=null`，`policy_version` 是当前告知版本；`granted` 要求 `consent_version>=1`、`granted_at` 非空、`withdrawn_at=null`；`withdrawn` 要求 `consent_version>=1`、两时间非空且 `withdrawn_at>=granted_at`。A 必须在每次远端 provider dispatch 前即时读取并验证主体/版本/status；不是 `granted` 时远端调用计数必须为 0。撤回只约束撤回后的新 dispatch；已发出的网络请求无法追溯撤回，但其候选仍须输出复核且不得因此继续下一次远端调用。
- Provider 适配器隔离供应商格式，支持超时、熔断、授权门禁和本地模板降级；provider 日志/trace 不得记录正文或 ConsentSnapshot 的主体标识。
- 响应与事件通过事务 outbox 原子提交；同一幂等键只能生成一次逻辑结果。

### 10.5 接口与验收

- REST：创建、查询、重命名、删除、总结和导出会话；总结固定使用 `POST /v1/conversations/{conversation_id}/summaries`，结果经 A 完整输出复核且不自动成为记忆。
- WebSocket 客户端命令：message.send、generation.cancel、session.resume、session.ack、safety.answer；反馈只走 REST，不使用 WebSocket。
- WebSocket 服务端事件：message.accepted、risk.status、emotion.result、response.delta、response.completed、response.blocked、error。
- 至少 20 轮连续对话保持已确认事实、称谓、目标和风险状态一致。
- 模型超时、安全服务失败和输出拒绝均返回可解释降级，不泄露堆栈或供应商信息。
- CI 的非 Mock 结构链路允许 `DeterministicLocalProvider`；但 SRC-F01/SRC-T02 的发布证据必须额外使用至少一个受支持的真实远端 LLM 或本地开源生成模型，以纯合成提示完成 20 轮 smoke，记录 provider、model_id、prompt/policy version、输入集 hash 与完整输出复核结果，客户端未审核 token 必须为 0。环境缺失时明确标记 `LLM_PROVIDER_UNVERIFIED`，不得把 F01/T02 判为完成。
- 共情质量集固定至少 50 个合成场景，由两名独立评审分别对倾听/事实忠实、共情适度、澄清与自主性、安全/非诊断边界、现实关系支持五维按 1–5 评分；每维均值 ≥ 4.0、任一场景不得出现诊断/给药/依赖诱导/危机旁路/虚构事实，否则门禁失败。评审分歧 > 1 分时由第三人仲裁并保留记录。

## 11. 核心功能二：情绪状态智能识别

### 11.1 输出契约

| 字段 | 要求 |
| --- | --- |
| emotion_result_id | 全局唯一且稳定的结果 ID，供纠正、删除和审计引用 |
| conversation_id | 结果所属会话 ID，必须与当前鉴权主体一致 |
| message_id | 触发识别的用户消息 ID，不允许跨消息复用 |
| primary_emotion | 冻结 ID：anxiety、depression、stress、sadness、anger、fear、loneliness、calm、unknown；UI 映射为焦虑、低落、压力、悲伤、愤怒、恐惧、孤独、平静或不确定 |
| secondary_emotions | 零到两个同一冻结枚举的字符串；数组内唯一且不能等于 primary_emotion |
| intensity | 0–3 离散强度，不表示临床严重度 |
| confidence | 校准后的 0–1 置信度 |
| status | classified、uncertain 或 unavailable；模型失败不得伪装为 classified |
| evidence_summary | 必填 1–160 字、不复述敏感原文的受控简短线索；不可用时使用批准的本地说明 |
| model_version | 模型、分词器和校准器版本 |
| occurred_at | 带时区的 UTC 事件时间 |

### 11.2 功能要求

- 当前消息与经授权的近期上下文共同输入，但不得使用其他用户数据。
- 文本过短、反讽、引用他人、否定或分布外输入时允许返回不确定。
- 界面使用“可能、线索、当前感受”等表述，不显示“你患有抑郁症”。
- 用户纠正结果后保留原模型输出和纠正值，不能静默篡改评测证据。
- 情绪趋势为 P1，只展示按日/周聚合和缺失区间，不推导诊断。
- 未来语音接口包含转写文本、声学特征版本、同意状态和融合置信度；当前实现不得采集音频。
- 公共实时事件固定为 `emotion.result`；纠正固定使用 `POST /v1/emotions/{emotion_result_id}/corrections`，请求含 `corrected_primary_emotion`、可空 0–3 整数 `corrected_intensity` 与可选 `correction_note`；趋势固定使用 `GET /v1/emotions/trends?from={UTC}&to={UTC}&granularity=day|week`。
- `correction_note` 属于自由文本，必须先经过第 14.1 节统一安全入口；纠正不会覆盖原模型结果，趋势重算须保留结果版本。

### 11.3 模型与 TensorRT

- 实施前必读 `project_docs/03_research/member_a_research_report.md`。生产文本基线采用固定 revision 的 `hfl/chinese-macbert-base`，情绪与危机使用独立 checkpoint、标签映射、校准和版本；每个模型制品记录来源、许可证/数据使用依据、训练/评测脚本、数据 manifest/hash、checkpoint/tokenizer hash 与下载/离线策略。缺少权重时不得以全 `unknown` 假模型宣称完成。
- 基线模型必须可在 CPU/PyTorch/ONNX 环境运行；A/B 共享 Python `uv.lock`、`.python-version`，标准 CPU clean clone 固定执行 `uv sync --frozen --extra ai --extra onnx`，只有具备 NVIDIA Linux/CUDA/TensorRT 能力的专用 job 才追加 `--extra tensorrt`。同一 `uv.lock` 解析全部 extras，但 CPU import/测试不得要求安装或加载 TensorRT/CUDA，也不允许 A/B 各自漂移依赖。
- TensorRT 采用稳定的 Linux 条件加速 profile：TensorRT 10.16.1 + CUDA 12.9，实际容器 image digest 与 driver/compute capability 写入兼容矩阵；engine 不作为跨版本/硬件可移植制品。C++ 共享库 `libemotion_trt.so` 暴露 create/infer/destroy C ABI，Python `native_loader.py` 通过 ctypes 调用；危机模型使用同样边界但独立 engine/manifest。
- engine 不提交 Git，固定路径 `artifacts/tensorrt/{task}/{model_version}/{sm}/model.plan`，其中 `task` 精确为 `emotion|crisis`；两类 engine 必须是不同路径，禁止同版本/SM 覆盖。manifest 记录 task、TensorRT/CUDA/driver/compute capability、ONNX/engine hash、label map、calibration 与 build command；schema/mutation test 必须证明 task 缺失、非法或 emotion/crisis 路径/hash 碰撞均失败。FP16 与 ONNX 最大概率绝对误差 ≤ 5e-3、top-label 等价率 ≥ 99.5%，并重新跑全部情绪/危机门禁；任一失败回退 CPU/ONNX。
- 有 NVIDIA Linux 环境时报告 PyTorch/ONNX/TensorRT 延迟、吞吐和差异；无环境时 GPU profile 标为未验证，但 CPU/ONNX 必须通过，且能力检测与安全回退有测试。
- 加速结果不能改变标签语义、阈值或不确定逻辑。

### 11.4 验收

- 分标签报告 Precision、Recall、F1、混淆矩阵、ECE/校准误差和不确定比例；发布门禁固定为 Macro F1 ≥ 0.75、每标签 F1 ≥ 0.60、负向情绪标签 Recall ≥ 0.80 且 Precision ≥ 0.70、强度 MAE ≤ 0.60、weighted kappa ≥ 0.60、每标签 ECE ≤ 0.05，任一不满足则 SRC-F02 未通过。
- 测试否定、引用、反讽、长文本、空白、Unicode、方言文字和 OOD。
- 用户纠正、删除和撤回训练同意的事件链可追踪。

## 12. 核心功能三：正念与 CBT 练习

### 12.1 首发目录

| 类别 | 必须练习 |
| --- | --- |
| 正念 | 呼吸觉察、身体扫描、五感着陆、三分钟短正念 |
| CBT | 情绪记录、自动思维识别、支持/反对证据、替代想法、小步行动计划 |
| 调节 | 压力缓解、睡前放松、情绪稳定 |

### 12.2 内容结构

每个练习记录标题、类别、目的、适用场景、不适用场景、预计时长、步骤、退出文案、完成反馈、来源、`review_record_id`、版本、状态和复核日期；审核记录必须符合第 16 节共享 schema。

首发内容必须以 `content/exercises/manifest.json` 作为版本化事实源，固定包含以下 12 个 ID：`breathing_awareness`、`body_scan`、`five_senses_grounding`、`three_minute_mindfulness`、`cbt_emotion_record`、`cbt_automatic_thought`、`cbt_evidence_review`、`cbt_alternative_thought`、`cbt_small_step_plan`、`stress_relief`、`sleep_relaxation`、`emotion_stabilization`。每项必须具备 `source`、`review_record_id`、`reviewed_at`、`checksum` 和 `status=published`，且 review decision 为 approved、content checksum 一致后才可进入发布包；空目录或仅有 API 壳视为 SRC-F03 失败。

### 12.3 功能规则

- 用户可主动进入，或由 AI 建议后由用户确认。
- 支持开始、暂停、恢复、跳过、提前结束和重新开始。
- 退出不产生“失败”或连续签到损失。
- CBT 不把用户想法判定为错误，而是帮助检查多种解释。
- L2/L3 状态禁止开始普通练习；L1 先完成安全确认。
- CBT 自由文本默认仅本人可见，允许单条删除。
- 用户可查看练习历史、完成状态、暂停位置与本人完成反馈；完成反馈写入 `exercise_session_id`、评分和可选自由文本，文本必须通过统一安全入口。
- 历史与反馈 API 必须支持重复提交幂等、撤回内容后的只读说明，以及删除用户数据后的墓碑传播。

练习状态的唯一事实源为 B 维护的 `contracts/content/exercise_session_state.schema.json`，C 必须由该 schema 生成 reducer 类型，A 只消费已审核 action ID：

| 当前状态 | 允许动作 | 下一状态/规则 |
| --- | --- | --- |
| `not_started` | `start` | 创建新 session 后进入 `in_progress` |
| `in_progress` | `pause` | `paused` |
| `paused` | `resume` | `in_progress`，恢复原 step |
| `in_progress` | `skip` | 仍为 `in_progress` 并推进到下一可跳过 step；最后一步不能用 skip 冒充 complete |
| `in_progress` 或 `paused` | `exit` | `exited`，终态且不标记失败 |
| `in_progress` | `complete` | 仅最后一步完成后进入 `completed`，终态 |
| `in_progress` 或 `paused` | 风险升级 L2/L3 或内容撤回 | `interrupted`，记录公开 reason ID，终态 |
| `completed`、`exited` 或 `interrupted` | `restart` | 旧 session 不变；内容仍发布时创建新的 `in_progress` session |

任何未列迁移返回稳定契约错误且不改变服务端状态；应用退出、断网或令牌过期本身不推进状态，只能从服务端状态恢复。

### 12.4 验收

- 每个练习从所有合法状态进入和退出均有状态机测试。
- 应用被杀、令牌过期或网络中断后不产生错误完成记录。
- 内容撤回后新会话不可开始，进行中的用户收到清楚说明。

## 13. 核心功能四：心理知识、PHQ-9 与 GAD-7

### 13.1 科普知识

- 覆盖常见情绪、焦虑、压力、睡眠、求助方式、心理咨询常识和危机应对。
- 每篇内容包含来源、作者/机构、`review_record_id`、审核日期、版本、适用地区和状态。
- 只有已发布且未过期内容可进入检索增强生成。
- 检索到的内容按不可信输入处理，正文中的指令不能覆盖系统安全策略。
- 回答显示来源和内容更新时间；无可靠内容时明确说不知道。
- 知识内容清单和评审记录必须版本化，发布流程不能直接读取未审核草稿。

首发知识事实源固定为 `content/knowledge/manifest.json`，文章固定存放于 `content/knowledge/articles/{article_id}.zh-CN.v1.json`，ID 集合精确等于：`emotion_basics`、`anxiety_self_help`、`stress_management`、`sleep_and_emotions`、`when_to_seek_help`、`how_counseling_works`、`crisis_support_guide`、`mindfulness_cbt_basics`。每篇 JSON 必须含 `article_id`、`title`、`body_markdown`、`topics`、`source_refs`、`author_or_institution`、`review_record_id`、`version`、`region=CN-mainland`、`status=published`、`reviewed_at`、`expires_at`、`checksum`；manifest 精确引用八个路径和校验和。缺少、多出、空正文、来源不可解析、审核不通过或 checksum 不匹配均阻断发布，空 API/RAG 壳不算 SRC-F04 完成。

B 负责内容导入、撤回和缓存失效，A 只从这八项中检索并把正文当作不可信资料，C 展示来源、版本和更新时间。真实全栈 E2E 至少完成一次 `B 导入已审核文章 → A RAG 命中并保留 citation → C 展示正文/来源 → B 撤回 → A/C 不再返回缓存`。

所有科学内容共用 `content/sources/source-register.schema.json` 与 `content/sources/source-register.json`。每个 source record 固定含权威机构/作者、标题、原始 URL 或出版物标识、许可/使用依据、适用地区、获取时间、版本和 checksum；每篇知识的 claim、每个练习步骤/禁忌、每份量表和每条危机/安全 UI 文案必须映射 `source_refs`。内容制品还要列出 `forbidden_claims` 与适用/禁忌说明，语义校验不能只检查“非空”。

内容流程固定为：指定内容作者按冻结 schema 在工程外一次性交付权威来源清单、24 个草稿与 author handoff → B-12 Stage 1 仅校验并集成该不可变作者包 → A 审查安全边界与科学声明 → 独立领域/临床审核人审查高风险内容并留下 `qualification_ref` → B 校验完整 review chain 与 checksum 后打包/导入。指定内容作者和独立审核人是明确的外部内容治理前置角色，不归入 A/B/C 工程代码 owner；C 只负责客户端信息结构、可读性反馈和忠实呈现，不签 author/reviewer 阶段。每个制品只有一条 active release approval record，但该记录必须内含按顺序签署的 `review_chain`，不能用“单个 reviewer”冒充三段审核。作者不得审核自己的制品，任意相邻审核角色不得是同一人；若项目无法提供可验证的作者包、专业资质或量表授权依据，只能保留未发布演示草稿且 SRC-F03/SRC-F04 的正式内容发布门禁不得声称 PASS。

工程交接固定为：外部指定作者先交不可变的 source register + 24 drafts + author handoff 包 → B-12 Stage 1 按冻结 schema 校验并提交该作者包、source/review/handoff schemas、pending registry 和空 active registry → A-11 从该 clean clone 提交 content-safety handoff → 独立审核人提供不可由测试生成的 independent-domain handoff → B-12 Stage 2 才能写 release-validation 阶段、生成 24 条 active record 并导入。B-13/B-14/B-15 只依赖 B-12 Stage 2；任一作者包或 handoff 缺失、拒绝、内部引用不一致或 checksum 变化时 active registry 保持为空，不允许用自动化测试伪造签署。

### 13.2 PHQ-9

- 使用锁定、来源可证明的简体中文版本；题干、选项、回顾周期和计分不得由 LLM 改写。
- 九题均为 0–3 分，总分 0–27。
- 结果区间：0–4 最低或轻微，5–9 轻度，10–14 中度，15–19 中重度，20–27 重度症状线索。
- 第 9 题任何非零回答立即进入独立安全确认，不能被低总分抵消，也不能直接等同 L2/L3。
- 锁定制品路径为 `content/assessments/phq9.zh-CN.v1.json`；题目 ID、题干、选项、回顾周期、计分和来源校验和不可由客户端或 LLM 改写。

### 13.3 GAD-7

- 使用锁定、来源可证明的简体中文版本；七题均为 0–3 分，总分 0–21。
- 结果区间：0–4 最低或轻微，5–9 轻度，10–14 中度，15–21 重度焦虑症状线索。
- 锁定制品路径为 `content/assessments/gad7.zh-CN.v1.json`；与 PHQ-9 共用全局 `content/reviews/review-register.json` 中的两条 assessment 审核记录，记录来源、审核人、审核日期、版本、校验和和发布决定。

### 13.4 前后端规则

- 客户端负责逐题交互和漏答提示，服务端使用量表版本重新计分。
- 客户端分数与服务端不一致时，以服务端为准并记录契约错误，不静默展示旧分数。
- 保存版本、答案、分数、完成时间、是否保存和安全联动结果。
- 结果页始终显示非诊断说明、专业支持建议和危机资源入口。
- PHQ-9 第 9 题非零时，服务端必须先持久化量表结果与安全触发事件并发出 `safety.question`；客户端在收到并完成安全确认前不得进入普通结果页。
- 普通结果、held、released、deleted、版本冲突和安全可见性必须由第 18.7 节公共 schema 表达；客户端不得从分数自行生成 severity 或结果文案。
- PHQ-9/GAD-7 定义制品必须内嵌已审核的 `display` 结果对象；API 原样返回 `title`、`summary`、`non_diagnostic_notice`、`recommended_actions`、`resource_refs` 和 `content_version`，C 不得从 template ID 自行创作文案。

### 13.5 验收

- 覆盖最低分、最高分、所有临界值前后、漏答、非法选项、重复提交和版本失配。
- PHQ-9 第 9 题非零无论总分多少都触发安全路径。
- 未授权或过期量表版本不能发布。

## 14. 核心功能五：危机预警与求助引导

### 14.1 检测范围

- 自伤、自杀想法、计划、时间、手段、准备行为和近期尝试。
- 对他人严重伤害的当前意图、计划和手段。
- 极端绝望、告别、无法保证当前安全和疑似正在发生的紧急事件。
- 正确区分否定、假设、引用、历史经历、新闻讨论、隐喻和当前意图。
- 所有最终用户业务自由文本必须经同一个 `FreeTextSafetyGateway` 进入安全服务；v1 固定入口集合**精确等于**：`chat.message`、`conversation.title`、`feedback.comment`、`exercise.reflection`、`emotion.correction_note`、`memory.value`、`knowledge.search`、`assessment.optional_note`、`profile.nickname`、`guest_migration.label`。新增入口必须提升契约版本。Git 内容制品与只接受结构化枚举/ID 的管理 API 不属于运行时最终用户自由文本入口。
- 每个入口在注册表中声明 route、field、最大长度、业务所有者和失败策略；未注册的自由文本字段不得上线。参数化契约测试必须证明没有路由可绕过安全检测。
- 任一入口判定 L2/L3 时，原业务写入必须为零，风险事件与 outbox 在同一事务原子提交；安全服务不可用时 fail closed，禁止继续普通业务。

### 14.2 风险等级与动作

| 等级 | 含义 | 强制动作 |
| --- | --- | --- |
| L0 | 无当前风险线索 | 继续普通支持，保留最小安全状态 |
| L1 | 模糊、历史或被动线索，当前意图不清 | 结构化确认当前安全，提供资源，建议联系可信任的人；完成前不自动降回 L0 |
| L2 | 当前想法或存在计划、手段、时间等要素 | 中止普通建议，直接询问即时危险，突出 110/120/12356、可信联系人和急诊 |
| L3 | 正在实施、即将实施、近期严重尝试或无法保持安全 | 保持简短支持，持续显示立即拨打 110/120、前往急诊和联系身边人的操作 |

### 14.3 自动安全闭环边界

- 允许：风险检测、结构化追问、资源展示、一键拨号、复制号码、打开系统联系人选择、创建用户自己的安全计划、记录脱敏风险事件。
- 不允许：后台静默报警、自动发送联系人消息、共享位置、声称真人已接管、声称救援已出发、把 AI 追问称作临床评估。
- 安全复核队列用于离线评测与规则改进，不改变当次用户处置，也不承诺响应时间。
- 离线复核结果不得解除或改写当次会话的实时风险状态；现有代码中任何 human-close/人工关闭字段都属于旧边界，最终契约必须删除或改为不影响用户实时处置的离线 review 字段。
- 中国大陆默认资源为 110、120、12356；服务时段和地区信息必须有来源、验证时间和启停状态。
- 唯一资源事实源为 `content/crisis/china-mainland.zh-CN.v1.json`，唯一离线包 schema 为 `content/crisis/offline-bundle.schema.json`；B 的签名输出固定为 `content/crisis/offline-bundle.zh-CN.v1.json`，移动端资产固定为 `mobile/src/assets/crisis/offline-bundle.zh-CN.v1.json` 与 `mobile/src/assets/crisis/trusted-keys.json`。A 只复核安全内容，B 创建/签名/复制/API 分发，C 只按生成类型消费且不得改写或暂存这两个资产。
- 公共包固定含 `resource_status=active|degraded`、`degraded_reason=null|bundle_missing|checksum_failed|signature_failed|expired`、`bundle_version`、`verified_at`、`expires_at`、`resources`、`sha256`、`signature`。仅 schema、校验和、签名和有效期全部通过时为 `active`；不存在 `complete` 或 `resource_bundle_status` 别名。
- 移动端签名离线资源包必须同时内置 110、120、12356；包损坏、签名失败或过期时仍显示内置号码并标为 `resource_status=degraded`，不得显示“资源完整/已更新”。
- 离线包签名固定为 Ed25519 + RFC 8785 JCS。待签名 unsigned object 不含 `sha256`/`signature`；`sha256` 是其 JCS UTF-8 字节的小写 SHA-256，`signature` 是同一字节的 Ed25519 base64url-no-padding 签名。包必须含 `signature_alg=Ed25519`、`canonicalization=RFC8785-JCS`、`key_id`；公钥事实源为 `content/crisis/trusted-keys.json`，包含有效期、状态、吊销与轮换，私钥只来自外部 secret。B/C 使用共享跨语言 canonical vectors 证明互操作。
- B 必须提供可从 clean clone 复现的 demo 签名链：一次性工具只在 Git ignored 的 `.local/secrets/` 生成 Linux mode 0600 的 Ed25519 demo 私钥并确定性写公钥 registry；随后显式 `--write` 生成服务端离线包和移动端两个资产，再以 `--check-vectors`/`--check` 验证。私钥不得进入 stdout、日志、镜像、仓库或证据；此 demo key 不得表述为生产密钥。
- 用户安全计划当前实现为端侧 SQLCipher 加密的结构化安全卡：已审核 warning-sign ID、coping-action ID、resource ID，以及最多 3 个用户手工输入的纯数字电话；联系人标签只能选固定审核枚举 `family|friend|other|trusted_contact_1|trusted_contact_2|trusted_contact_3`。若用户从系统联系人选择器选择对象，系统返回的显示名只作为 OS 受控、不可编辑、本机元数据展示，不进入云端、日志或业务自由文本。安全计划不得出现第 11 个可编辑自由文本字段；mutation/E2E 必须从真实页面控件和提交 payload 证明自由文本入口仍精确为十个。不请求通讯录权限、不上传云端、不自动拨号/发信；支持查看、编辑、导出和删除，危机页与离线页均可打开。

### 14.4 故障规则

- 模型、数据库或网络失败时，端侧静态资源和安全模板仍可用。
- 安全服务失败时不得绕过检查调用云 LLM；返回保守安全响应。
- 用户取消生成只取消普通候选回复，不能取消已触发的安全事件提交。
- 风险页面不得依赖登录、云模型或普通内容服务。

### 14.5 验收

- 测试直接表达、隐喻、否定、引用、历史、讽刺、拼音/拆字、Unicode 和多轮升级。
- 危机发布门禁同时约束漏报与“全部判高危”退化：L3 Recall ≥ 0.98 且 one-sided 95% confidence lower bound ≥ 0.95，L3 Precision ≥ 0.80 且 lower bound ≥ 0.70；L2+ Recall ≥ 0.95 且 lower bound ≥ 0.90，L2+ Precision ≥ 0.70 且 lower bound ≥ 0.60；1000 条 L0 hard-negative 集的 L2/L3 总 false-positive rate ≤ 0.03，关键分群各 ≤ 0.05；危机概率 ECE ≤ 0.05；强制 imminent-risk 对抗集零漏报。评测集至少含 1000 条 L0 hard negative、300 条 L2、300 条 L3，否定、引用、历史、假设、新闻/创作、隐喻、拼音拆字和方言关键分群各 ≥ 100；逐阈值报告 confusion matrix、precision/recall/FPR、置信区间和分群差异。
- `tests/evaluation/gates/crisis_gate.v1.json` 冻结上述阈值、`deployment_positive_prior=0.02` 和首发 `max_alerts_per_1000_turns=50`；后续候选的 prevalence-adjusted alert rate 还不得超过已批准基线 1.5 倍。gate 文件、数据 manifest、模型/calibrator/rule hashes 一起进入签名评测报告；任一门禁失败则 SRC-F05 未通过。
- 任一高风险用例不能继续输出普通 CBT、冥想、励志或泛化知识。
- 离线、断线、令牌过期和 API 故障时仍能触达资源。

## 15. 关联功能闭环

### 15.1 首页与推荐

- 首页只根据用户主动选择、当前会话和授权数据推荐功能。
- 情绪结果只能建议练习或自测，不能自动启动或改变账户权限。
- 高风险状态覆盖普通推荐，首页优先显示安全资源。

### 15.2 反馈与纠错

- `POST /v1/feedback` 与 `GET /v1/feedback/{feedback_id}` 是唯一通用反馈 API；目标与类别是判别联合：`ai_response=helpful|not_helpful|inaccurate|uncomfortable`、`knowledge_article=inaccurate|outdated|unclear`、`crisis_event=false_positive`。服务端校验目标属于当前主体，重复 `Idempotency-Key` 返回同一记录。
- 可选 comment 通过 `feedback.comment` 安全入口；被拦截时普通反馈写入为零。危机误报反馈只进入离线质量复核，不能改变风险粘滞状态。
- 情绪纠正继续使用情绪专用接口，不混入通用反馈。

### 15.3 本地提醒

- 本地提醒为 P1 延后项，不是当前发布门禁；当前版本不申请通知权限、不创建提醒任务。

## 16. 管理端、内容和版本治理

| 需求编号 | 功能 | 验收 |
| --- | --- | --- |
| FR-ADMIN-001 | 内容状态：草稿、待审核、已发布、待复核、已撤回、已归档 | 未发布/过期/撤回内容不能出现在 API、RAG 或客户端缓存 |
| FR-ADMIN-002 | 危机资源维护地区、语言、号码、来源、验证时间、服务时段和启停 | 资源下线能同步服务端与端侧增量包 |
| FR-ADMIN-003 | 离线风险复核状态：待复核、已确认、误报、已关闭 | 只显示脱敏事件；改判保留原始结论和版本，且绝不改变用户当次实时风险状态 |
| FR-ADMIN-004 | 模型、提示词、规则和量表版本查看、比较、启用和回滚 | 非兼容版本不能发布；回滚有审计和回归证据 |
| FR-ADMIN-005 | 角色、权限、再认证和审计查询 | 默认拒绝；管理员不能通过搜索获取普通聊天正文 |

所有练习、知识、量表、危机资源和安全 UI 文案统一引用 `content/reviews/review-record.schema.json`，实例唯一事实源为 `content/reviews/review-register.json`。每条 active release approval record 必填 `review_record_id`、`content_type=knowledge|exercise|assessment|crisis_resource|safety_ui`、`content_id`、`content_version`、`draft_author_id`、`review_chain`、`release_decision=approved|rejected|needs_changes`、`source_refs`、`content_checksum`、`next_review_at`。`review_chain` 精确按 `content_safety_review`、`independent_domain_review`、`release_validation` 三阶段排列；每阶段固定含 `reviewer_id`、`reviewer_role`、可空 `qualification_ref`、`reviewed_at`、`decision`、`input_checksum`，后一阶段 input checksum 必须等于前一阶段批准的 checksum。`content_safety_review` 由 A 或其指定安全审核角色执行，`independent_domain_review` 必须独立于作者且高风险内容需可验证资质，`release_validation` 由 B 的导入/发布责任角色验证 schema、source、chain 与最终 checksum，不改写正文。只有三阶段均 approved、release_decision=approved 且最终 checksum 相符的制品可发布。

首发 registry 精确包含 24 条 active release approval record：8 篇知识、12 项练习、PHQ-9、GAD-7、中国大陆危机资源包和 `content/safety/ui-manifest.zh-CN.v1.json`；`review_record_id` 和 `(content_type, content_id, content_version)` 各自唯一，每个制品恰好命中一条、registry 不得有孤儿记录。历史 rejected/superseded 记录放在按内容 ID 分区的 archive，不计入 active 24 条。课程/竞赛没有可验证资质时 `qualification_ref=null`，界面只能写“项目内容审核”，不得声称临床或持证专家背书；对应 SRC-F03/SRC-F04 的正式专业内容门禁仍为 FAIL。

安全 UI manifest 固定包含当前安全确认 prompt、`safe_now|not_safe|unsure` 回答，以及 `call_110|call_120|call_12356|contact_trusted_person|open_nearest_emergency|recheck_safety` action 的 ID、已审核简体中文文案、kind、版本、checksum、`review_record_id` 与 source refs；未知或 checksum 不匹配时 fail closed，并随移动端离线包内置。

## 17. 数据模型与生命周期

| 实体 | 关键字段 | 主要约束 |
| --- | --- | --- |
| LocalGuestProfile | local_profile_id、sqlite_key_ref、created_at | 仅端侧；SQLCipher；不承担服务端授权 |
| GuestSubject/GuestSession | guest_subject_id、token_digest、device_key_hash、scopes、expires_at、revoked_at | 服务端短期主体；不可枚举；最长 24 小时；token 明文不落库 |
| User | user_id、email_hash、password_hash、nickname、status | 身份与心理数据逻辑隔离；不存明文密码 |
| DeviceSession | device_id、refresh_family、last_seen、revoked_at | 可撤销；令牌摘要存储 |
| Consent | subject_id、type、policy_version、consent_version、status、granted_at、withdrawn_at | 核心、云模型、记忆、趋势、训练分开；云模型当前 snapshot 必须在每次 provider dispatch 前读取 |
| Conversation | conversation_id、subject_id、mode、persistence_mode、risk_state、next_event_sequence、version | 按主体授权；`mode=chat|assessment_safety|free_text_safety`；支持删除和导出 |
| Message | role、content_ciphertext、status、message_ordinal、model_version | 敏感正文加密；`message_ordinal` 是会话消息顺序；不得复用 WS sequence |
| MemoryItem | type、value_ciphertext、source、confirmed_at、disabled_at | 只存用户确认内容；可见可改可删 |
| EmotionResult | labels、intensity、confidence、model_version、correction | 非诊断；原结果与纠正并存 |
| ExerciseDefinition | steps、contraindications、source、review_record_id、version、status | 仅已发布且审核记录校验通过的版本可用 |
| ExerciseSession | definition_version、step、state、started_at、completed_at | 状态机约束；支持历史、暂停、恢复和撤回说明 |
| ExerciseFeedback | exercise_session_id、rating、comment_ciphertext、idempotency_key | 本人可见；自由文本先筛查并单独加密 |
| KnowledgeContent | source、review_record_id、version、status、expires_at | 仅审核白名单进入检索 |
| AssessmentDefinition | scale_type、items、scoring、source、review_record_id、version、status | 题干与计分版本锁定 |
| AssessmentResult | answers_ciphertext、score、version、safety_trigger | 后端计分；可删除 |
| AssessmentSafetyTrigger | trigger_id、assessment_result_id、item_id、answer、idempotency_key | 仅内部受控访问；与结果和安全 outbox 同事务提交 |
| SafetyContext | safety_context_id、kind、conversation_id、state、current_risk_level、question_event_id | `kind=assessment|free_text`；安全回答的唯一上下文 |
| CrisisResource | region、number/url、source、verified_at、active | 端侧离线同步；过期可撤回 |
| CrisisEvent | risk_level、signals、policy_version、actions、review | 独立权限；普通日志无原文 |
| Feedback | target_type、category、comment_ciphertext、status | 用户可选择是否附上下文 |
| AuditLog | actor、action、object_ref、time、result、hash_chain | 防篡改；不保存无必要正文 |

`sequence` 只属于 `ServerEventEnvelope`/outbox；一个 message 可产生多个服务端事件，`messages.message_ordinal` 与事件 sequence 分开分配。B 在同一事务使用 `conversations.next_event_sequence` 分配 outbox sequence。

| 数据类别 | 默认保存与清理规则 |
| --- | --- |
| guest 服务端会话/消息/量表/练习/outbox | 最长 24 小时；升级成功只迁移用户选择的记录；撤销或过期清除 |
| 账户 `ephemeral` 会话 | 最长 24 小时，不进入长期记忆 |
| 账户 `saved` 会话及用户确认记忆 | 保存至用户删除/注销；记忆可单条禁用与删除 |
| 已 ACK 的普通 outbox | 7 天后清理；未 ACK 在对应业务 retention 内保留 |
| 最小风险事件/安全 outbox | 默认 30 天，只含脱敏信号/版本/动作，不保留自由文本 |
| AuditLog | 90 天；仅最小 actor/action/object hash/result，不含心理正文 |
| 加密备份 | 7 天滚动；恢复后必须重放删除墓碑 |
| 删除墓碑 | 30 天，用于防止备份/缓存复活，不含被删除正文 |

在线主库、缓存、检索索引与可删除派生数据在删除请求接受后 24 小时内完成；加密备份在 7 天窗口内自然淘汰，期间访问路径必须由 tombstone 阻断。客户端显示各阶段而非虚假完成。数据删除必须传播到 MySQL、SQLite、缓存、检索索引、outbox 副本和可删除派生数据；备份恢复后重放删除墓碑。

## 18. API 与实时协议基线

### 18.1 REST 资源

- `/v1/auth`：注册、登录、刷新、退出、设备管理、`recovery-requests` 和 `recovery-confirmations`。
- `/v1/guest-sessions`：创建、查询当前与删除当前访客会话；`/v1/guest-migrations`：预览、创建和查询迁移。
- /v1/consents：查询、授予和撤回。
- /v1/conversations：列表、创建、详情、总结、删除和导出。
- `/v1/memories`：列表、创建确认、修改、停用和删除；`GET /v1/memory-capability` 与 context-proof 提供降级证明。
- /v1/emotions：结果、`POST /v1/emotions/{emotion_result_id}/corrections` 和 `GET /v1/emotions/trends`。
- /v1/exercises：目录、详情、会话、进度、历史和完成反馈。
- `/v1/knowledge`：分类、详情和 `POST /v1/knowledge/search` JSON body；不得把敏感搜索词放入 URL/query string。
- 自测定义与提交：`GET /v1/assessments/{scale}/definitions/{version}`、`POST /v1/assessments/{scale}/submissions`；path `scale` 精确为 `phq9|gad7`，公共对象内 `scale` 精确为 `PHQ9|GAD7`。
- 自测结果闭环：`GET /v1/assessment-results/{assessment_result_id}`、`GET /v1/assessment-results?cursor={opaque}&limit=20&scale={phq9|gad7}`、`GET /v1/assessment-results/{assessment_result_id}/export`、`DELETE /v1/assessment-results/{assessment_result_id}`。
- /v1/crisis-resources：按地区获取资源及离线包版本。
- /v1/privacy：导出、删除和注销请求。
- /v1/feedback：提交和查看本人反馈状态。
- `/v1/safety-contexts/{safety_context_id}/rechecks`：为 held 安全上下文创建新的结构化确认问题。
- /v1/admin：内容、资源、风险复核、版本、角色和审计；独立鉴权。

上述十类自由文本入口中的所有 REST 路由都必须携带 `Idempotency-Key` header；chat 的 WebSocket 自由文本使用 client command envelope 的 `idempotency_key`。B 维护 `contracts/errors/public_errors.schema.json` 与 canonical rows，至少固定 validation/auth/forbidden/not-found/conflict/idempotency/rate-limit/service-unavailable/safety-gate/text-entry/WS-ack-resume/output/assessment/recovery/guest/content/deleted/internal 类错误的 `code`、HTTP status、`retryable` 和 `client_action`，C 只能按该契约渲染。

### 18.2 WebSocket 双向信封与 ACK

B 维护 `contracts/ws/client_commands.schema.json` 与 `contracts/ws/server_events.schema.json`，不得用一个含 sequence 的模糊信封同时表示双向消息。

- `ClientCommandEnvelope` 固定含 `protocol_version`、`command_id`、`conversation_id`、`idempotency_key`、`sent_at`、`type`、typed `payload`，**不含 sequence**。类型精确为 `message.send`、`generation.cancel`、`session.resume`、`session.ack`、`safety.answer`。
- `ServerEventEnvelope` 固定含 `protocol_version`、`event_id`、`conversation_id`、按事件可空的 `message_id`、`sequence`、`idempotency_key`、`occurred_at`、`type`、typed `payload`。类型精确为 `message.accepted`、`risk.status`、`emotion.result`、`response.delta`、`response.completed`、`response.blocked`、`safety.question`、`safety.resources`、`assessment.result.available`、`memory.mode.changed`、`error`。

客户端 payload：`message.send={client_message_id,text,mode:null|support|clarify|exercise|knowledge}`；`generation.cancel={response_id}`；`session.resume={last_ack}` 且 `last_ack>=-1`；`session.ack={acked_sequence}` 且 `acked_sequence>=0`；`safety.answer` 按第 18.5 节。服务端 payload：`response.delta={response_id,chunk_index,text}`；`response.completed={response_id,total_chunks,response_source,outcome,feedback_target_id}`；`response.blocked={response_id,outcome,template_id,public_error_code}`；其余事件使用各自公共 schema。`message.accepted` 是 normal/safety_required 判别联合并保留 command/message 关联。

`sequence` 是同一 `conversation_id` 内单调递增的非负整数，首个服务端逻辑事件固定为 `0`，跨 outbox bundle、重连与进程恢复不得重置；客户端尚未确认任何事件时 `last_ack=-1`。C 只有在 schema 校验、reducer 应用和本地必要提交全部成功后，才 ACK 最高连续 sequence；B 用 CAS 只前进 ACK，拒绝倒退或越过缺口。resume 重放严格为 `sequence > last_ack`。错误事件使用公开错误 schema，不返回堆栈、内部 reason、原始输入或供应商响应。

### 18.3 `emotion.result` v1 契约

公共 payload 固定包含 `emotion_result_id`、`conversation_id`、`message_id`、`primary_emotion`、`secondary_emotions`、`intensity`、`confidence`、`status`、`evidence_summary`、`model_version`、`occurred_at`。A 维护 `contracts/ai/emotion_result.schema.json` 与 canonical rows，B 负责无损持久化和 REST 映射，C 只按生成类型解码；v1 对象出现未知字段或缺失必填字段时必须拒绝并记录公开契约错误，兼容变化只能通过新协议版本发布。

纠正请求与响应中的 `corrected_intensity` 都是可空 0–3 整数；成功固定返回 HTTP 201 与 `correction_id`、`emotion_result_id`、`corrected_primary_emotion`、可空 `corrected_intensity`、`accepted_at`，不回显 `correction_note`。趋势响应固定为 `from`、`to`、`granularity`、`points`；每个 point 固定含 `period_start`、`period_end`、非负整数 `sample_count`、`emotion_distribution`、可空 0–3 `mean_intensity`、`data_status=sufficient|sparse|empty`。

`emotion_distribution` 是固定九键对象，键精确等于 primary 枚举，值为 0–1 比例；`sample_count=0` 时九值全为 0、`mean_intensity=null`、`data_status=empty`；样本 1–2 时 `data_status=sparse` 且九值之和为 1（容差 1e-6）；样本至少 3 时 `data_status=sufficient` 且九值之和为 1。纠正和趋势只访问当前主体已授权、未删除数据，不能覆盖原模型值或输出诊断。A 的 `contracts/ai/emotion_result.schema.json` 表达 secondary 不变量；B 维护 `contracts/emotions/emotion_correction.schema.json`、`contracts/emotions/emotion_trend.schema.json` 和 `contracts/emotions/canonical_rows.json` 表达纠正与 distribution 不变量；C 由这些 schema 生成 Zod，三端真实 round-trip 共用 canonical rows。

### 18.4 `assessment_safety_trigger` v1 契约

内部事件固定字段为 `trigger_id`、`subject_id`、必填 `conversation_id`、`assessment_result_id`、`scale`、`scale_version`、`item_id`、`answer`、`idempotency_key`、`occurred_at`；其中 `answer` 只存在于受控内部 schema，不进入公共 WebSocket payload。量表可以从聊天外独立启动：第 9 题非零时，B 必须在同一事务中复用已授权会话或创建 `mode=assessment_safety` 的专用会话，使 trigger、outbox 和所有 WS 信封始终拥有同一个非空 `conversation_id`。

提交前先把可选 `assessment.optional_note` 送统一自由文本门；非 L0 时不得计分、不得建立 AssessmentResult/trigger，只产生通用安全上下文。仅 L0 才执行：校验并重新计分 → 检测第 9 题 → 解析/创建安全会话 → 同一事务写入会话（如新建）、`AssessmentResult`、`AssessmentSafetyTrigger`、`SafetyContext(kind=assessment)` 与 `safety.question` outbox → HTTP 202。重复提交返回同一结果/会话/trigger/event；回滚时五类记录均为零。

HTTP 202 使用第 18.5 节 `AssessmentSafetyRequiredResponse` 分支，其中 `safety_context_kind=assessment`、`safety_context_id=assessment_result_id`、`risk_level=L1`、`scale=PHQ9`、`item_id=PHQ9_Q9`；不含 `entry_point`。这里 L1 只表示“待结构化安全确认”，不把第 9 题直接判为 L2/L3。公共响应/事件不携带第 9 题答案、分数或自由文本。只有安全回答状态表明确允许时才释放结果，不能把“收到任意回答”视为完成。

### 18.5 `free_text_safety` v1 契约

A 提供 `screen_text(request: FreeTextSafetyRequest)` 并维护 `contracts/ai/free_text_safety.schema.json`。`FreeTextSafetyRequest` v1 必填 `request_id`、`subject_id`、可空 `conversation_id`、`entry_point`、`field_name`、`context_ref`、仅驻留进程内存的 `text`、`idempotency_key`、UTC `occurred_at`；B 必须从已匹配的 route/field registry 构造该 DTO，并拒绝 entry point、字段或上下文不一致的请求。注册、搜索等未登录/非聊天入口也必须带服务端签发的 guest/pre-auth `subject_id`，不接受客户端自报主体。

`context_ref` 只由 B 根据已鉴权 route/subject 构造，C 不发送具备授权意义的 context ref；v1 grammar 精确为：`chat.message=conversation:{conversation_id}`、title patch=`conversation:{id}`、title create=`subject:{subject_id}:new-conversation`、feedback=`response:{id}|knowledge:{id}|crisis-event:{id}|exercise-session:{id}`、reflection=`exercise-session:{id}:entry:{entry_id|new}`、correction=`emotion-result:{id}`、memory patch=`memory:{id}`、memory create=`subject:{subject_id}:new-memory`、knowledge=`subject:{subject_id}:knowledge-search`、assessment=`assessment:{PHQ9|GAD7}:{version}`、nickname registration=`subject:{subject_id}:registration`、nickname patch=`profile:{subject_id}`、migration=`guest-migration:{batch_id}:item:{item_id}`。route、field、entry point 或 grammar 不匹配返回 `TEXT_ENTRY_CONTEXT_MISMATCH`。

当 A 返回 L1–L3 且没有 conversation 时，B 在安全事务内创建 `mode=free_text_safety` 会话；已有会话先做主体授权。L1 原子写 `SafetyContext(kind=free_text)` 与 `safety.question`；L2/L3 还写最小 CrisisEvent、`risk.status` 与 `safety.resources`；原业务写入始终为零。B 维护 `contracts/safety/safety_required_response.schema.json`、`safety_question.schema.json`、`safety_answer.schema.json` 与 canonical rows。

`SafetyRequiredResponse` 是以 `safety_context_kind` 为 discriminator、拒绝未知字段的 `oneOf`，共有 base 字段：`status=safety_required`、`safety_event_id`、非空 `conversation_id`、`risk_level=L1|L2|L3`、`safety_context_kind`、`safety_context_id`、`prompt_template_id`、`action_ids`、`resource_bundle_version`。`FreeTextSafetyRequiredResponse` 固定 `safety_context_kind=free_text` 且额外必填十入口之一的 `entry_point`，禁止 assessment 字段；用于自由文本 REST HTTP 202 和 WS `message.accepted` safety 分支。`AssessmentSafetyRequiredResponse` 固定 `safety_context_kind=assessment`、`risk_level=L1`，额外必填 `assessment_result_id`、`scale=PHQ9`、`item_id=PHQ9_Q9`、`result_release_state=held_for_safety`、`safety_required=true`、`result_visible=false`、`result=null`，且 `safety_context_id` 必须等于 `assessment_result_id`，禁止 `entry_point`；用于量表 POST HTTP 202。L1 event ID 指向 `safety.question`，free-text L2/L3 指向首个 `risk.status`；同一业务响应的 HTTP/WS ID（若同时存在）必须完全一致。

`safety.question` payload 固定为 `{safety_context_kind,safety_context_id,safety_state:'confirmation_required',prompt_template_id,action_ids,resource_bundle_version}`；`safety.answer` payload 固定为 `{safety_event_id,safety_context_kind,safety_context_id,answer_id:'safe_now'|'not_safe'|'unsure'}`，幂等键只在 command envelope。A 提供确定性 answer decision DTO/function，B 负责鉴权、事务、outbox 和 assessment release，C 负责确认 UI/reducer。

| answer_id | 确定性结果与事件 | assessment | generic free text |
| --- | --- | --- | --- |
| `safe_now` | 状态 `confirmed_safe`、风险降为 L0，先发 `risk.status` | 同一事务改为 released，随后发 `assessment.result.available` | 不自动重放原业务，因为服务端不保存被阻断明文；C 只可在 RAM 保留 draft，提示用户用**新的业务幂等键**重新提交并再次筛查 |
| `unsure` | 保守升为 L2，依次发 `risk.status`、`safety.resources` | 保持 held | 原业务写入仍为零 |
| `not_safe` | 升为 L3，依次发 `risk.status`、`safety.resources` | 保持 held | 原业务写入仍为零 |

L2/L3 后如需再次确认，B 通过 `POST /v1/safety-contexts/{id}/rechecks` 创建**新的** server-owned `safety.question`；只有其 `safe_now` 才按上表释放。相同 command 幂等键返回相同事件；同键不同答案返回稳定 idempotency conflict；已回答 question 不可再次突变。旧 generic 业务幂等键永远返回原 safety response，新业务提交必须使用新键并重新筛查。

guest migration 标签按 item_id 排序并派生 item key/context ref，先全部筛查，全部 L0 才写入；首个非 L0 为整批建立一个 safety context，业务写入为零。C 使用响应 conversation/event 取得 realtime ticket，从当前 ACK（新会话 -1）续接；事务任一写入失败全部回滚并返回 `SAFETY_GATE_UNAVAILABLE`。

### 18.6 实时事件序号所有权

成员 A 只输出通过完整复核的 `ReviewedStreamChunk`，字段为响应 ID、从 0 开始的响应内 `chunk_index`、公共 event type 与安全 payload，不读取或预留会话序号。成员 B 是最终 `ServerEventEnvelope.sequence` 的唯一分配者：在 MySQL outbox 同一事务锁定 `conversations.next_event_sequence`、按 chunk_index 顺序包装事件并逐一分配会话序号、写入后推进游标。成员 C 只按最终 `(conversation_id, sequence)` ACK、去重和续接。不存在 A/B 双重取号、号段预留或事务外 sequence 推进。

### 18.7 自测公共结果 schema

B 维护并生成五个唯一事实源：`contracts/assessments/assessment_submission_response.schema.json`、`contracts/assessments/assessment_result.schema.json`、`contracts/assessments/assessment_result_available.schema.json`、`contracts/assessments/assessment_result_export.schema.json`、`contracts/assessments/canonical_rows.json`；A 复核内部 trigger 不泄露，C 只按生成类型消费。

- HTTP 201 body 固定含 `assessment_result_id`、可空 `conversation_id`、`result_release_state=released`、`safety_required=false`、`safety_event_id=null`、`result_visible=true`、`result`（下述 available 对象）。
- HTTP 202 body 精确复用第 18.5 节 `AssessmentSafetyRequiredResponse`；`status=safety_required` 与 `safety_required=true` 同时存在，其中前者是 safety response discriminator、后者是 assessment submission compatibility flag。除该分支定义字段外不得增加 `entry_point`、逐题答案、分数或自由文本。
- available result 固定含 `assessment_result_id`、`status=available`、`scale=PHQ9|GAD7`、`scale_version`、`review_period_days=14`、`score`、`severity`、`display={title,summary,non_diagnostic_notice,recommended_actions,resource_refs,content_version}`、`completed_at`、`result_release_state=released`。display 必须来自对应定义制品的已审核文案，不返回让客户端自行创作的 template ID。PHQ-9 score 0–27 且 severity 为 `minimal|mild|moderate|moderately_severe|severe`；GAD-7 score 0–21 且 severity 为 `minimal|mild|moderate|severe`，所有区间严格按第 13.2/13.3 节。
- deleted tombstone 固定含 `assessment_result_id`、`status=deleted`、`deleted_at`，不得含答案、分数、severity 或旧文案；GET 返回 HTTP 410 与公开码 `ASSESSMENT_RESULT_DELETED`。held GET 返回 HTTP 423 `SAFETY_CONFIRMATION_REQUIRED`，版本失配提交返回 HTTP 409 `ASSESSMENT_VERSION_CONFLICT`。
- `assessment.result.available` payload 使用同名 schema，只含 `assessment_result_id`、`result_release_state=released`；收到后 C 再 GET full result。
- 六类 route 的鉴权主体只能是当前正式账户或服务端签发的当前 guest subject；列表、详情、导出、删除全部按 subject_id 隔离，跨主体固定 404。history 按 `completed_at DESC, assessment_result_id DESC` 稳定游标分页，limit 1–100，默认 20。
- 单条 export 只允许 released 结果，返回 `application/json` 与 `AssessmentResultExport={export_version:'assessment-result.v1',generated_at,result}`，其中 result 精确复用 available result 且不得包含逐题答案、optional note、内部 trigger、安全事件或其他主体数据；held 返回 423，deleted 返回 410。DELETE 成功和同主体重复删除均返回 204，立即写 tombstone、清除历史/详情/导出访问并触发 B-16 删除传播；跨主体仍为 404。
- canonical rows 必须覆盖 PHQ-9/GAD-7 每个临界值、201 released、202 held、详情/历史/单条 export、删除 204、held 423、available、deleted/410、跨主体 404 和 version mismatch/409；公共 schema 不包含逐题答案。

### 18.8 知识检索边界

B 的 MySQL 内容库和检索 adapter 是知识事实源，并实现 A 定义的 `KnowledgeRetrieverPort`；A 每次 turn 只消费 B 返回的当前 approved、未撤回、未过期 snippet/citation，把正文视为不可信输入，不建立第二套本地数据库、索引或长期缓存。C 只通过 REST/ETag/内容版本缓存；撤回后 B 令 ETag 失效，A 下一次检索不命中，C 再请求得到 gone/empty 并删除旧缓存。RAG 发布门禁为 Recall@3 ≥ 0.90。

### 18.9 移动端安全导航判别联合

危机导航参数必须由 schema 生成并精确区分：`manual_resources` 不含 level/conversation；`safety_confirmation` 含 `conversationId`、`safetyEventId`、`safetyContextKind`、`safetyContextId` 且不伪造 level；`risk` 含 `conversationId`、`eventId`、`level=L1|L2|L3`。未知组合拒绝导航并显示离线静态资源。

## 19. 前端工程要求

- React Native 0.84.0 + TypeScript；业务规则由服务端契约驱动，客户端不得复制危机等级或量表计分作为最终结果。Detox 固定 20.51.3，Android 是必验平台；该组合必须写入 `package.json`、精确 npm `packageManager` 和 `package-lock.json`。
- 导航、服务器状态、表单状态和 WebSocket 状态分别管理，禁止用单一 loading 布尔值覆盖所有状态。
- 令牌使用 iOS Keychain/Android Keystore 对应安全存储；OP-SQLite 17.1.2 以 `package.json` 的 `"op-sqlite":{"sqlcipher":true}` 编译 SQLCipher，数据库 key 只取自 Keychain/Keystore。启动时检查 `PRAGMA cipher_status`、plaintext canary 与未加密 fallback，任一失败拒绝打开敏感库；不得同时引入另一套 Expo SQLite。
- 应用切换器快照、通知预览、剪贴板和崩溃日志不得暴露敏感正文。
- Android TalkBack、系统字体放大、非颜色提示、大触控目标和减少动态效果是强制证据；VoiceOver 仅在有 macOS runner 时验证并明确记录结果。
- Android 核心 E2E 为强制发布证据；iOS 保留平台无关实现和 CI 任务，有 macOS/Xcode runner 时必须执行核心 build/E2E，无 runner 时明确标记“iOS 未验证”且不得声称通过。竞赛演示可选择一个主展示平台，但不能写平台专属业务规则。
- Detox 工程必须包含 `.detoxrc.js`、`e2e/jest.config.js`、Android test runner、Gradle instrumentation、专用 `e2e` buildType/source set、仅该测试 APK 使用的 network security config 与可复制 AVD/KVM 启动脚本。`android.emu.e2e` 只允许 `http://10.0.2.2:8080`/`ws://10.0.2.2:8080` 访问本地 Compose override：基础 `deploy/compose.demo.yml` 与 `deploy/compose.e2e.yml` 合并后，由同名 `caddy` service 在 host `127.0.0.1:8080` 提供测试专用 listener；不得创建第二个 `caddy-e2e` service。release manifest 必须保持 cleartext=false 且不能打包 e2e trust config。`android.emu.release` 只连接预置阿里云 HTTPS/WSS endpoint，remote 命令绝不加载 e2e override。基础 Linux Compose 只启动 MySQL、Redis、Caddy、内嵌 A Python 包的 FastAPI、可选无状态 model-runtime 和 Mailpit。Android emulator 在 Linux host/CI 使用 KVM 运行，不在 Compose 中伪造 mobile-e2e 容器。

## 20. 后端工程要求

- FastAPI 应用按认证、会话、AI 编排、内容、练习、自测、危机、隐私和管理域拆分。
- OpenAPI 与 WebSocket schema 是 A/B/C 共同契约；变更必须先更新契约测试。
- B 在基础任务即创建最小 `Dockerfile`、`deploy/compose.dev.yml` 与 `deploy/compose.test.yml`，让后续 MySQL/Redis 测试命令真实可运行；最终再由部署任务加固，而不是让前置任务依赖尚未创建的 Compose。
- MySQL 为服务端事实源；SQLite 只用于端侧和测试，不以 SQLite 行为代替 MySQL 约束测试。
- 会话响应、风险事件和推送事件使用事务 outbox 保证原子提交。
- 安全服务失败时 fail closed；不得直接绕过成员 A 的安全编排调用 LLM。
- 统一请求 ID、结构化脱敏日志、健康检查、就绪检查、指标和追踪。
- B-01 是共享 Python 环境的唯一 bootstrap/lock owner：先创建根 `.python-version`、uv workspace `pyproject.toml`、`uv.lock`、A/B package entries 和 `ai`/`onnx`/带 Linux x86_64 marker 的 `tensorrt` optional extras，再发布标准 CPU `uv sync --frozen --extra ai --extra onnx` 可成功且 import 不加载 TensorRT/CUDA 的 clean-clone 证据；NVIDIA Linux 专用 job 另执行 `uv sync --frozen --extra ai --extra onnx --extra tensorrt`。在该交接完成前 A-01 不得执行。后续 A 若需新增 Python 依赖，先提交 dependency request，由 B 更新/复核同一 lock；任一任务结束都运行 `uv lock --check` 与 lock 无漂移检查，禁止各自维护第二份 requirements/lock。
- 最终服务端目标是阿里云 ECS x86_64 Linux 上的课程/竞赛/内部演示环境，不是公众生产：`deploy/compose.demo.yml` 固定含 Caddy TLS reverse proxy、单 replica/单 Uvicorn worker 的 FastAPI（进程内加载 A Python 包）、可选无状态 `model-runtime`、MySQL、Redis、migration job、持久卷和可选 Mailpit demo profile；不得再建立独立 AI orchestration/DecisionStore 服务。secrets 位于仓库外，脚本只提供健康检查、备份、恢复、按 image digest 回滚和运行证据，不包含 ECS 购买、控制台配置或上线步骤。禁止嵌入式 profile。
- 工具链事实源为 `pyproject.toml`、`.editorconfig`、`project_docs/04_technical_design/ide_setup.md` 和经审查合并的 VSCode 示例配置；PyCharm 与 VSCode 必须调用相同的 pytest、Ruff、mypy 命令，不允许绝对路径或仅某位成员机器可用的解释器配置。
- `project_docs/04_technical_design/tool_disposition.md` 必须记录：Git 为配置管理事实源；Visio 仅是可选外部绘图工具且无运行时依赖；CARLA 不适用于心理支持系统。`tests/tooling/test_no_carla_dependency.py` 扫描 Python、Node、原生依赖、Compose、SBOM 和运行配置并要求零 CARLA surface。
- 遇到 SDK/框架行为不确定时，实施者必须先查官方文档与 pinned upstream source/release，再查对应 GitHub issue/discussion；任务证据记录 URL、版本、最小复现和采纳/拒绝理由，论坛答案本身不构成验收证据。

## 21. 安全、隐私与伦理要求

| 编号 | 要求 |
| --- | --- |
| NFR-SEC-001 | TLS、密码自适应哈希、高敏字段加密、密钥与代码分离、最小权限 |
| NFR-SEC-002 | 输入长度/Unicode 校验、参数化查询、限流、账号枚举防护、WebSocket 洪泛防护 |
| NFR-SEC-003 | 提示注入、角色诱导、敏感信息套取、自伤方法索取和越权工具调用对抗测试 |
| NFR-PRIV-001 | 心理对话、情绪、自测和危机数据按敏感信息处理，分项同意、最小化和可撤回 |
| NFR-PRIV-002 | 默认不采集真实姓名、位置、通讯录、麦克风、原始语音和广告标识 |
| NFR-PRIV-003 | 用户可访问、更正、导出、删除、撤回同意和注销；训练默认关闭 |
| NFR-PRIV-004 | 在处理任何真实个人信息或公开发布前，由 B 建立并维护 `project_docs/04_technical_design/privacy_compliance_matrix.md`，逐项记录适用法律及版本/生效日期、处理目的、处理依据、数据类别、控制者/受托处理者、保存期、访问/更正/导出/删除、事件响应、跨境、第三方 AI、工程控制、自动化证据、owner、独立复核人和复核有效期；工程团队只能证明控制已实现，不能自行声明法律合规，适用性和最终结论必须由具备资质的法律/隐私复核人签署 |
| NFR-PRIV-005 | 当前中国境内课程/竞赛/内部演示基线至少复核《个人信息保护法》《数据安全法》以及 2025 年修正、2026-01-01 起施行的《网络安全法》；实现与发布前必须按官方现行文本重新核验。未完成合规矩阵、单独同意、委托处理/合同与必要的跨境评估时，第三方云模型的跨境或受托处理路径保持关闭，并回退至经批准的本地模型或不发送敏感数据 |
| NFR-ETH-001 | 明确 AI 身份；不虚构资质，不诱导依赖，不排斥现实关系，不诊断或给药 |
| NFR-ETH-002 | 风险、量表和情绪结果都允许用户理解与反馈；模型不拥有最终安全动作权限 |

NFR-PRIV-005 的官方基线来源为：全国人大《中华人民共和国个人信息保护法》、全国人大《中华人民共和国数据安全法》、全国人大《中华人民共和国网络安全法（2025 年修正）》。法律文本和监管要求会变化，文档中的工程映射不是法律意见，实施者必须在真实数据测试或发布前记录官方复核日期与外部复核结论：

- 个人信息保护法：https://gdca.miit.gov.cn/zwgk/zcwj/flfg/art/2021/art_1f7ffcec321a49129dc852fbba74e4c8.html
- 数据安全法：https://www.npc.gov.cn/npc/c2/c30834/202106/t20210610_311888.html
- 网络安全法（2025 年修正）：https://www.npc.gov.cn/npc/c1773/c1848/c21114/wlaqfxz/wlaqfxz002/202511/t20251103_449242.html

## 22. 性能、可靠性与降级

| 编号 | 指标/行为 |
| --- | --- |
| NFR-PERF-001 | 基线 100 个并发 WebSocket 会话时，非模型 REST P95 不高于 500 ms |
| NFR-PERF-002 | 模型正常时，收到完整消息到首个已安全复核分块 P95 不高于 3 秒；不能用未审核首 token 计算 |
| NFR-REL-001 | WebSocket 支持 ACK、sequence、resume、去重和取消；客户端只观察到一次有序逻辑事件 |
| NFR-REL-002 | LLM 不可用时返回本地共情边界模板；危机资源始终独立可用 |
| NFR-REL-003 | 备份恢复后验证权限、事件顺序、内容版本和删除墓碑；RPO 24 小时，RTO 4 小时作为演示环境目标 |
| NFR-REL-004 | 代码、模型、提示词、规则、内容和 schema 有兼容矩阵和回滚记录 |

性能证据分成两个单一 owner 的入口：A 维护 `tests/performance/model_benchmark.py` 与 `scripts/run_ai_performance_gate.py`，负责情绪/危机/LLM 路径和 CPU/ONNX/TensorRT 条件基准；B 维护 `tests/performance/locustfile.py` 与 `scripts/run_system_performance_gate.py`，负责 REST/WS/MySQL/outbox 端到端负载。两脚本都读取冻结阈值、预热、持续时间和并发数，输出 JSON/Markdown 证据并在 P95/错误率超限时非零退出；B-20 聚合两份报告，不存在共享脚本 owner。不得用手工截图代替可重跑命令。

## 23. 测试与质量门禁

### 23.1 测试层级

| 层级 | 必测内容 |
| --- | --- |
| 单元 | 领域模型、状态机、风险规则、量表计分、练习进度、权限、脱敏、记忆过滤 |
| 契约 | OpenAPI、WebSocket、错误码、枚举、时间、幂等和版本兼容 |
| 集成 | FastAPI、进程内 A Python 包、可选无状态 model-runtime、MySQL、outbox、WebSocket、内容、自测、删除传播 |
| 移动端 | 导航、表单、SQLite、安全存储、离线、重连、字体缩放和读屏语义 |
| E2E | 访客→账户、20 轮对话、练习、自测、第 9 题、危机、导出、删除和注销 |
| AI 评测 | 共情、上下文、情绪分类、危机召回、输出安全、提示注入和分群差异 |
| 性能/恢复 | REST/WebSocket 并发、模型超时、熔断、服务重启、备份恢复和版本回滚 |

### 23.2 硬性发布门禁

1. SRC-F01 至 SRC-F05 全部有前端、后端、AI/数据和自动化验收证据。
2. SRC-T01 至 SRC-T12 均有实际采用、条件适配或明确不适用证据。
3. L2/L3 任何测试不得进入普通 LLM、CBT、正念或知识回答。
4. PHQ-9/GAD-7 版本、计分、临界值和第 9 题联动全部通过。
5. 跨用户读取、跨会话串线、跨用户记忆命中和删除后复活均为零。
6. 安全检查失败不能回退为未经检查的模型输出。
7. 访客、账户、弱网、离线和数据权利流程有 E2E 证据。
8. 无未解决的 P0/P1 严重缺陷、无真实密钥、无真实用户敏感测试数据。
9. 非 Mock 的真实纵向链路完成 20 轮连续对话，并覆盖断线续接、取消、重复幂等、反馈落库、零未审核 token 和零重复逻辑消息。
10. PHQ-9/GAD-7 与 12 个首发练习均来自带来源、审核人、日期、校验和和发布状态的版本化内容制品，不接受空目录或临时硬编码。
11. Linux clean-clone 在 PyCharm 与 VSCode 使用同一组 pytest、Ruff、mypy 和移动端命令得到一致结果；依赖、Compose、配置和 SBOM 的 CARLA 命中为零，Visio 仅作为可选外部绘图工具。
12. 最终发布证据只针对预置的阿里云 ECS x86_64 Linux endpoint 及等价本地 Linux 容器栈；任何嵌入式部署、交叉编译、设备运行时或嵌入式回退均不在验收范围，也不得写成待完成条件。
13. 真实 LLM provider smoke、两人共情质量评分、情绪门禁、危机门禁和 RAG Recall@3 全部达到本文数值；任何未验证项显式 FAIL，不能由 deterministic provider 替代。
14. 24 个首发内容/安全制品全部有 checksum 匹配的 approved review record、source mapping 与语义字段；高风险内容缺少独立专业审核/授权证据时不得声称正式内容门禁 PASS。
15. guest token/24 小时清理、统一十入口安全事务、safety answer 三分支、memory history-only、密码找回、反馈、assessment 定义/提交/详情/历史/单条导出/删除和端侧安全计划均有真实集成/E2E。
16. 远端 provider 默认关闭；每次调用顺序必须严格为一次性 `CloudSafePayloadProof` consume=1 → B-owned `ProviderProcessingPolicySnapshot` read=1 → 仅 policy approved 时最新 ConsentSnapshot read=1 → 仅 consent granted 时 dispatch=1。policy 缺失/disabled/expired/非法、独立复核/合同/处理区域依据缺失，或 consent missing/withdrawn 时 dispatch=0。proof 必须先覆盖当前输入、历史、记忆、知识与最终序列化 payload 的规则+独立中文 NER；任一 backend/offset/OOD/灰区失败、proof 错配或撤销/过期后的下一次请求均不得 dispatch。
17. 危机门禁必须同时满足 Recall、Precision、hard-negative FPR、ECE 与关键分群阈值；“全部判 L2/L3”或只报告 Recall 一律失败。

### 23.3 真实全栈 20 轮证据

- 固定入口：`mobile/e2e/liveStack20Turn.e2e.ts` 与 `tests/e2e/test_live_stack_evidence.py`。
- 固定环境：Linux Compose 启动 MySQL、Redis、单 worker FastAPI（进程内 A Python 包）、可选无状态 model-runtime 和 Mailpit；Android emulator 在 Linux host/CI KVM 上运行，不能伪装成 Compose 服务。允许用确定性本地 Provider 验证结构链路，但不得绕过真实输入安全、情绪/危机模型、云模型同意门、输出复核、事务 outbox、WebSocket 与移动端 reducer；另按门禁运行真实 LLM smoke。
- 固定断言：20 轮上下文事实一致；首个 sequence 为 0 且全会话连续；断线后从 `last_ack` 续接；取消不会取消安全事件；重复幂等键只产生一个逻辑消息；反馈真实写入 MySQL；客户端收到的未审核 token 为 0；重复逻辑消息为 0。
- A 提供可复现的确定性 Provider、真实 provider profile 与安全 canonical rows，B 提供 Linux Compose、数据库和实时链路，C 驱动真实 Android 客户端 E2E；根脚本 `scripts/run_live_stack_e2e.py` 依次启动 Compose、AVD/Detox 与 `tests/e2e/test_live_stack_evidence.py`，聚合退出码并清理。canonical local 参数为 `--compose deploy/compose.demo.yml --mobile-dir mobile --android-avd MentalHealthApi35 --evidence-dir artifacts/evidence/live-stack`；remote smoke 参数为 `--remote-base-url $ALIYUN_ECS_BASE_URL --mobile-dir mobile --android-avd MentalHealthApi35 --synthetic-only --evidence-dir artifacts/evidence/aliyun-ecs-smoke`，只测试预置 endpoint，不提供云部署步骤。三人共同签署同一证据文件，单端 Mock 只能补充；禁止不存在的 `--exit-code-from mobile-e2e`。

## 24. 原始要求追踪矩阵

| 原始要求 | AI/领域 | 后端/数据 | 移动端 | 主要验收 |
| --- | --- | --- | --- | --- |
| SRC-F01 多轮共情 | 状态机、LLM、上下文、输出复核 | 会话、WebSocket、outbox、幂等 | 聊天、取消、重连、反馈 | 20 轮一致性与安全回复 |
| SRC-F02 情绪识别 | 文本模型、校准、不确定、语音接口 | 结果、纠正、趋势 API | 结果、纠正、趋势 | 分标签指标与边界用例 |
| SRC-F03 正念/CBT | 推荐门禁、内容安全 | 目录、版本、进度 | 步骤、暂停、恢复、退出 | 全状态流程与危机阻断 |
| SRC-F04 科普/自测 | 审核知识检索、回答边界 | 内容、量表版本、后端计分 | 知识、答题、结果、历史 | 临界值、第 9 题和来源 |
| SRC-F05 危机 | 检测、融合、L0–L3、模板 | 风险状态、资源、审计 | 全屏安全页、离线资源 | 高召回、无普通流程旁路 |

## 25. 三人交付边界

### 25.1 成员 A：AI、安全算法与确定性编排

负责 SRC-F01、SRC-F02 和 SRC-F05 的 AI 核心，以及练习/知识推荐安全边界、模型评测、阿里云 ECS Linux TensorRT 运行兼容；共同复核 CARLA 零依赖扫描和真实全栈证据。不得负责账户事实源、客户端最终交互、后台权限实现、云资源开通教程或任何嵌入式部署工作。

### 25.2 成员 B：FastAPI、WebSocket、账户、数据与阿里云 ECS Linux 运行兼容

负责账户/访客迁移、REST/WebSocket、MySQL、加密、内容/练习/自测/危机资源服务、管理 API、隐私请求、阿里云 ECS Linux 运行兼容和恢复证据；同时负责 `.editorconfig`、PyCharm/VSCode 统一命令说明、Git 证据、`tool_disposition.md`、Visio 可选性声明和 CARLA 零依赖自动扫描。现有用户 `.vscode/` 若存在必须审查后合并，禁止直接覆盖。不得绕过 AI 安全服务、在后端重新定义量表和风险语义，或把云资源开通教程加入交付范围。

### 25.3 成员 C：React Native、端侧 SQLite、产品体验与 E2E

负责全部移动端页面、状态、可访问性、弱网、离线资源、访客端侧数据、账户交互和端到端验收；负责 VSCode 移动端/Android 任务配置、真实 20 轮客户端驱动，并共同复核 CARLA 零依赖。不得在客户端复制另一套最终危机分级、情绪模型或量表计分逻辑，也不承担嵌入式部署。

三份成员落地方案必须共同引用本文需求编号、明确接口交接物和跨成员验收，不得形成三个无法集成的独立项目。

## 26. 实施顺序与系统停止条件

跨成员 DAG 固定如下，任务文档必须写 `depends_on`/`produces`，不得把契约首建推迟到最终汇总任务：

1. **Phase 0 基础契约骨架**：B-01 必须最先建立共享 Python workspace/lock 与最小 Compose，A-01 明确依赖其 clean-clone handoff。随后 A-01～A-05 依次完成，其中 A-04 先发布 free-text/safety/answer schema，A-05 发布 emotion/crisis schema；B-02 **只消费这批当时已存在的 A-04/A-05 契约**，并冻结 public errors、REST skeleton、guest/safety/memory/assessment 的 B-owned skeleton 与 WS 双信封。B-02 不得声称已消费尚未产生的 A-09 reviewed-chunk 或 A-11 assessment-trigger。C-01 可独立建立完整 React Native baseline；C-02 **只在** A-14 聚合契约与 B-17 最终公共契约 freeze 后生成并提交正式 TS/Zod。此前若需要界面原型，只能使用明确标为 prototype-only 的本地 fixture，不能提交为 contract package，也不能声称前后端集成通过。首次生成的 untracked 文件必须用 `git add -N` 后 diff，或生成到临时目录 byte-compare；单独 `git diff --exit-code` 不足以证明无漂移。
2. **Phase 1 领域契约与实现**：B-03/B-04 完成数据与同意 adapter 后，A-07/A-09 发布 provider/consent 与 reviewed-chunk；B-06/B-07 完成会话/outbox/WS，B-08 只消费 A-04 free-text/answer 契约并建立通用 SafetyContext，不能反向依赖 A-11。外部作者包就绪后 B-12 Stage 1 建立 pending content/fail-closed knowledge skeleton；A-08 Stage 1 只建立 port/policy/fake/fail-closed 门禁，A-11 依赖该阶段审查 24 个 pending 制品并发布 assessment-trigger 与 A content-safety handoff；B-12 Stage 2 和 B-14 分别消费 A-11 handoff/trigger。B-12 Stage 2 完成 MySQL/retrieval adapter 后才运行 A-08 Stage 2 的真实生命周期和 Recall@3，证据由 A-13 聚合，禁止反向阻塞 A-11。A-12 只汇合 A-02～A-07、A-08 Stage 1、A-09～A-11，B-10 以 A-09 reviewed chunks 和 A-12 turn contract 接通真实聊天。每个 route task 都重新生成 OpenAPI/WS 并 byte-compare；A-14 最后只聚合全部已发布 AI 契约和跨语言 round-trip。A 独占 `tests/contract/test_emotion_result_contract.py`，B 只消费/运行，禁止同路径双 owner。
3. **Phase 2 最小纵向链路**：打通 guest session/账户、安全门单次筛查、真实对话、WS ACK/resume 和 Android 客户端；再接情绪、练习、知识、自测、危机、记忆、反馈与数据权利。
4. **Phase 3 证据**：C-01～C-16 完成后，C-17 Stage 1 可独立产出只验证客户端启动的 Detox/AVD/E2E harness ready 证据，不等待 A/B release；并行地 A-13 产签名 AI release profile，B-17 最终冻结 OpenAPI/WS/public errors 与工具配置，B-18 运行全入口安全总门禁，B-19 生成阿里云 ECS Linux 运行兼容/恢复/系统性能证据。B-20 同时消费 A-13、B-19 和 C-17 Stage 1 创建根编排器，最后 C-17 Stage 2 消费 B-20 运行 local/remote 联合验收。该顺序不得写成 B-20 与 C-17 整体互相依赖；同时运行真实 provider、情绪/危机/内容门禁和弱网/离线验证。先完成硬性要求审查，再完成产品质量与第三者零上下文审查。

若出现以下任一情况，不得宣称项目完成：

- 五项硬性功能任一只有界面或假数据，没有真实后端/AI闭环。
- 高风险路径仍能输出普通建议，或危机资源依赖登录/云模型。
- 量表由客户端单独计分且后端不复核。
- 账户数据、访客迁移、记忆或删除存在串户风险。
- 技术清单只写在文档中，没有对应实现或合理条件说明。
- 三人方案的接口、字段、错误码、任务依赖或验收定义互相矛盾。

## 27. 明确不在当前范围

- 公众正式生产发布、真人危机值守、自动报警或自动联系紧急联系人。
- 互联网诊疗、疾病诊断、处方、用药建议和医疗证明。
- 未成年人模式。
- 商业订阅、支付、广告、营销和复杂客服运营。
- 当前版本的语音采集与语调识别；只保留接口。
- 独立 Web 管理端；当前以结构化 FastAPI 管理 API、CLI 与 Git 内容制品交付。
- 本地练习/自测提醒与通知权限；作为 P1 后续能力，不影响本轮核心功能完成。
- 嵌入式部署、嵌入式 Linux、交叉编译、设备固件和端侧嵌入式推理；最终服务端只要求可运行于阿里云 ECS x86_64 Linux 容器，且本文不提供云资源开通或部署操作教程。
- 为满足工具清单而虚假接入 CARLA。
- 企业多租户、国际化和多地区法律适配。

## 28. 文档交付与审查要求

本文完成后必须生成三份独立但可集成的落地文档：

1. 成员 A：AI、安全算法与确定性编排落地方案。
2. 成员 B：FastAPI、WebSocket、账户、数据与阿里云 ECS Linux 运行兼容方案（不含云服务器部署教程）。
3. 成员 C：React Native、端侧数据与产品体验落地方案。

对抗式审查必须按顺序执行：

1. 首先逐条检查 SRC-F01–SRC-F05 与 SRC-T01–SRC-T12 是否严格覆盖，缺一项即失败。
2. 再检查产品闭环、前后端一致性、接口、数据、安全、隐私、可测试性、任务边界和零上下文可执行性。
3. 最后进行“第三者直接落地演练”：审查者假设自己此前完全不了解项目，仅依据本 PRD、三份成员方案和仓库现状，逐项验证能否确定环境准备、精确文件路径、接口签名、任务顺序、依赖、测试命令、预期结果、提交边界、跨成员交接和失败回退。
4. 任何依赖隐含上下文的模糊指令，以及未定义缩写、占位内容、缺失接口或无法执行的验证命令，均视为零上下文可落地性失败。
5. 审查发现的问题必须写入审查报告、修改正式文档并复审；只有硬性符合性、系统质量和第三者可落地性三道门禁最终均为 PASS，才能结束本轮文档工作。
