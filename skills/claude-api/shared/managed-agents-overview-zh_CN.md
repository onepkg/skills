# 托管智能体 — 概览

托管智能体会话为每个会话提供一个容器作为智能体的工作区。智能体循环在 Anthropic 的编排层上运行；容器是智能体的*工具*执行的地方 — bash 命令、文件操作、代码。您创建一个持久化的**智能体**配置（模型、系统提示、工具、MCP 服务器、技能），然后启动引用它的**会话**。会话将事件流式传输回给您；您向其中发送用户消息和工具结果。

## ⚠️ 强制流程：智能体（一次）→ 会话（每次运行）

**为什么智能体是单独的对象：版本控制。** 智能体是一个持久化、版本化的配置 — 每次更新都会创建一个新的不可变版本，会话在创建时固定到某个版本。这让您可以迭代智能体（调整提示、添加工具）而不会破坏已经在运行的会话，如果变更导致回退，可以回滚，并可以并排进行 A/B 测试版本。如果您每次运行都重新 `agents.create()`，这些都不起作用。

每个会话都引用一个预先创建的 `/v1/agents` 对象。创建一次智能体，存储 ID，并在多次运行中重用它。

| 步骤 | 调用 | 频率 |
|---|---|---|
| 1 | `POST /v1/agents` — `model`、`system`、`tools`、`mcp_servers`、`skills` 位于此处 | **一次。** 存储 `agent.id` **和** `agent.version`。 |
| 2 | `POST /v1/sessions` — `agent: "agent_abc123"` 或 `{type: "agent", id, version}` | **每次运行。** 字符串简写使用最新版本。 |

如果您准备在会话主体上使用 `model`、`system` 或 `tools` 编写 `sessions.create()` — **停止**。这些字段位于 `agents.create()` 中。会话只接受一个*指针*。

**生成代码时，将设置与运行时分开。** `agents.create()` 属于设置脚本（或受保护的 `if agent_id is None:` 块），而不是在热路径的顶部。如果用户的代码在每次调用时都调用 `agents.create()`，他们会积累孤立的智能体并无谓地支付创建延迟。正确的形式是：创建一次 → 持久化 ID（配置文件、环境变量、密钥管理器）→ 每次运行加载 ID 并调用 `sessions.create()`。

**要更改智能体的行为，请使用 `POST /v1/agents/{id}` — 不要创建新的智能体。** 每次更新都会增加版本；运行中的会话保持其固定版本，新会话获得最新版本（或通过 `{type: "agent", id, version}` 显式固定）。请参阅 `shared/managed-agents-core.md` → 智能体 → 版本控制。要在**一个运行中的会话**上更改 `tools`/`mcp_servers`/`vault_ids` 而不接触智能体对象，请使用 `sessions.update()` — 请参阅 `shared/managed-agents-core.md` → 在会话中更新智能体配置。

## Beta 头

托管智能体处于测试阶段。SDK 会自动设置所需的 beta 头：

| Beta 头                    | 启用的功能                                      |
| ------------------------------ | ---------------------------------------------------- |
| `managed-agents-2026-04-01`    | 智能体、环境、会话、事件、会话资源、会话线程、结果、多智能体、保管库、凭证、记忆存储 |
| `skills-2025-10-02`            | 技能 API（用于管理自定义技能定义）   |
| `files-api-2025-04-14`         | 用于文件上传的文件 API                           |

**哪个 beta 头用在哪里：** SDK 在 `client.beta.{agents,environments,sessions,vaults,memory_stores}.*` 调用上自动设置 `managed-agents-2026-04-01`，在 `client.beta.files.*` / `client.beta.skills.*` 调用上自动设置 `files-api-2025-04-14` / `skills-2025-10-02`。调用托管智能体端点时**不需要**添加技能或文件的 beta 头。**例外 — 会话范围的文件列表：** `client.beta.files.list({scope_id: session.id})` 是一个接受托管智能体参数的文件端点，因此它需要**两个**头。在该调用上显式传递 `betas: ["managed-agents-2026-04-01"]`（SDK 添加文件头；您添加托管智能体头）。请参阅 `shared/managed-agents-environments.md` → 会话输出。

## 阅读指南

| 用户想要...                       | 阅读这些文件                                        |
| -------------------------------------- | ------------------------------------------------------- |
| **从头开始 / "帮我设置一个智能体"** | `shared/managed-agents-onboarding.md` — 引导式访谈（在哪里→谁→什么→观察），然后生成代码 |
| 了解 API 如何工作           | `shared/managed-agents-core.md`                         |
| 查看完整端点参考        | `shared/managed-agents-api-reference.md`                |
| **创建智能体**（必需的第一步） | `shared/managed-agents-core.md`（智能体部分）+ 语言文件 |
| 更新/版本化智能体                | `shared/managed-agents-core.md`（智能体 → 版本控制）— 更新，不要重新创建 |
| 创建会话                       | `shared/managed-agents-core.md` + `{lang}/managed-agents/README.md` |
| 配置工具和权限        | `shared/managed-agents-tools.md`                        |
| 设置 MCP 服务器                     | `shared/managed-agents-tools.md`（MCP 服务器部分）  |
| 流式传输事件 / 处理 tool_use        | `shared/managed-agents-events.md` + 语言文件       |
| 通过 webhook 接收会话状态变更通知（不轮询） | `shared/managed-agents-webhooks.md` — 控制台注册的端点、HMAC 验证、精简负载 + 获取 |
| 定义结果 / 评分标准的迭代循环 | `shared/managed-agents-outcomes.md` — `user.define_outcome` 事件、评分器、`span.outcome_evaluation_*` 事件 |
| 协调多个智能体 / 子智能体 / 线程 | `shared/managed-agents-multiagent.md` — 智能体上的 `multiagent: {type: "coordinator", agents: [...]}`、会话线程、交叉发布的工具确认 |
| 设置环境                    | `shared/managed-agents-environments.md` + 语言文件 |
| 在您自己的基础设施 / VPC 中运行工具执行（自托管沙箱） | `shared/managed-agents-self-hosted-sandboxes.md` — `config:{type:"self_hosted"}`、`ANTHROPIC_ENVIRONMENT_KEY`、`EnvironmentWorker.run()` / `ant beta:worker poll` |
| 上传文件 / 附加仓库            | `shared/managed-agents-environments.md`（资源）     |
| 为智能体提供跨会话的持久记忆 | `shared/managed-agents-memory.md` — 记忆存储、`memory_store` 会话资源、先决条件、版本/修订 |
| 存储 MCP 凭证                  | `shared/managed-agents-tools.md`（保管库部分）       |
| 调用需要密钥的非 MCP API / CLI | `shared/managed-agents-client-patterns.md` 模式 9 — 没有容器环境变量；保管库仅适用于 MCP；通过自定义工具在主机端保留密钥 |

## 常见陷阱

- **先智能体，然后会话 — 没有例外** — 会话的 `agent` 字段**只**接受字符串 ID 或 `{type: "agent", id, version}`。`model`、`system`、`tools`、`mcp_servers`、`skills` 是 **`POST /v1/agents` 的顶级字段**，永远不在 `sessions.create()` 上。如果用户还没有创建智能体，那是每个示例的第零步。
- **智能体一次，不是每次运行** — `agents.create()` 是一个设置步骤。存储返回的 `agent_id` 并重用它；不要在热路径的顶部调用 `agents.create()`。如果智能体的配置需要更改，使用 `POST /v1/agents/{id}` — 每次更新都会创建一个新版本，会话可以固定到特定版本以实现可重现性。
- **MCP 认证通过保管库进行** — 智能体的 `mcp_servers` 数组仅声明 `{type, name, url}`（无认证）。凭证位于保管库中（`client.beta.vaults.credentials.create`）并通过 `vault_ids` 附加到会话。Anthropic 使用存储的刷新令牌自动刷新 OAuth 令牌。
- **流式传输以获取事件** — `GET /v1/sessions/{id}/events/stream` 是实时接收智能体输出的主要方式。
- **SSE 流没有重放 — 重连时合并** — 如果在 `agent.tool_use`、`agent.mcp_tool_use` 或 `agent.custom_tool_use` 等待解析时（前两个的 `user.tool_confirmation`，最后一个的 `user.custom_tool_result`）流断开，会话会死锁（客户端断开 → 会话空闲 → 重连发生 → 没有客户端解析发生）。在每次（重）连时：使用 `GET /v1/sessions/{id}/events/stream` 打开流，获取 `GET /v1/sessions/{id}/events`，按事件 ID 去重，然后继续。请参阅 `shared/managed-agents-events.md` → 断开流后的重连。
- **不要相信 HTTP 库超时作为墙上时钟上限** — `requests` `timeout=(c, r)` 和 `httpx.Timeout(n)` 是*每块*读取超时；它们每个字节都会重置，因此缓慢的连接可能会无限期阻塞。对于原始 HTTP 轮询的硬截止时间，在循环级别跟踪 `time.monotonic()` 并显式退出。首选 SDK 的 `sessions.events.stream()` / `session.events.list()` 而不是手动编写的 HTTP。请参阅 `shared/managed-agents-events.md` → 接收事件。
- **消息排队** — 您可以在会话 `running` 或 `idle` 时发送事件；它们按顺序处理。在发送下一条消息之前无需等待响应。
- **环境 `config.type` 是 `"cloud"` 或 `"self_hosted"`** — `cloud` 在 Anthropic 的基础设施上运行容器；`self_hosted` 将工具执行移到您自己的基础设施中（请参阅 `shared/managed-agents-self-hosted-sandboxes.md`）。
- **每个资源上的归档是永久性的** — 归档智能体、环境、会话、保管库、凭证或记忆存储会使其变为只读，无法取消归档。特别是对于智能体、环境和记忆存储，归档的资源不能被新会话引用（现有会话继续）。不要将归档生产智能体、环境或记忆存储作为清理操作 — **在归档前始终与用户确认**。
