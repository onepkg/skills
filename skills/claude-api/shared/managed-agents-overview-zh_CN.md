# Managed Agents — 概述

Managed Agents 为每个会话预置一个容器作为代理的工作空间。代理循环运行在 Anthropic 的编排层；容器是代理的*工具*执行的地方——bash 命令、文件操作、代码。你创建一个持久化的 **Agent** 配置（模型、系统提示、工具、MCP 服务器、技能），然后启动引用该配置的 **Sessions**。会话将事件流式返回给你；你向其中发送用户消息和工具结果。

## ⚠️ 强制流程：Agent（一次）→ Session（每次运行）

**为什么代理是独立对象：版本管理。** 代理是一个持久化、带版本管理的配置——每次更新都会创建一个新的不可变版本，会话在创建时固定到一个版本。这让你可以在不破坏已运行会话的情况下迭代代理（调整提示、添加工具），在变更引发回退时回滚，并可以并排进行 A/B 测试版本。如果你每次运行都重新调用 `agents.create()`，这些功能都无法实现。

每个会话都引用一个预先创建的 `/v1/agents` 对象。创建一次代理，存储 ID，并在不同运行中复用。

| 步骤 | 调用 | 频率 |
|---|---|---|
| 1 | `POST /v1/agents`——`model`、`system`、`tools`、`mcp_servers`、`skills` 在此定义 | **一次。** 保存 `agent.id` **和** `agent.version`。 |
| 2 | `POST /v1/sessions`——`agent: "agent_abc123"` 或 `{type: "agent", id, version}` | **每次运行。** 字符串简写使用最新版本。 |

如果你正准备在会话体上使用 `model`、`system` 或 `tools` 调用 `sessions.create()`——**停下来**。这些字段属于 `agents.create()`。会话仅接受一个*指针*。

**生成代码时，将设置与运行时分离。** `agents.create()` 应放在设置脚本（或带保护的 `if agent_id is None:` 块）中，而不是放在热路径的顶部。如果用户的代码每次调用都执行 `agents.create()`，他们正在积累孤立的代理并为毫无收益的创建延迟买单。正确的做法是：创建一次→持久化 ID（配置文件、环境变量、密钥管理器）→每次运行时加载 ID 并调用 `sessions.create()`。

**要更改代理的行为，使用 `POST /v1/agents/{id}`——不要创建新代理。** 每次更新都会提升版本号；正在运行的会话保持其固定的版本，新会话获取最新版本（或通过 `{type: "agent", id, version}` 显式固定）。参见 `shared/managed-agents-core.md` → Agents → Versioning。要在**某个正在运行的会话**上更改 `tools`/`mcp_servers`/`vault_ids` 而不影响代理对象，请使用 `sessions.update()`——参见 `shared/managed-agents-core.md` → Updating the agent configuration mid-session。

## Beta 标头

Managed Agents 目前处于 beta 阶段。SDK 会自动设置所需的 beta 标头：

| Beta 标头                       | 启用的功能                                           |
| ------------------------------ | ---------------------------------------------------- |
| `managed-agents-2026-04-01`    | Agents、Environments、Sessions、Events、Session Resources、Session Threads、Outcomes、Multiagent、Vaults、Credentials、Memory Stores |
| `skills-2025-10-02`            | Skills API（用于管理自定义技能定义）                    |
| `files-api-2025-04-14`         | Files API（用于文件上传）                              |

**哪个 beta 标头放在哪里：** SDK 在 `client.beta.{agents,environments,sessions,vaults,memory_stores}.*` 调用上自动设置 `managed-agents-2026-04-01`，在 `client.beta.files.*` / `client.beta.skills.*` 调用上自动设置 `files-api-2025-04-14` / `skills-2025-10-02`。你在调用 Managed Agents 端点时**不需要**添加 Skills 或 Files 的 beta 标头。**例外——会话范围的文件列表：** `client.beta.files.list({scope_id: session.id})` 是一个接受 Managed Agents 参数的 Files 端点，因此它需要**两个**标头。在该调用上显式传递 `betas: ["managed-agents-2026-04-01"]`（SDK 会添加 Files 标头；你再添加 Managed Agents 标头）。参见 `shared/managed-agents-environments.md` → Session outputs。


## 阅读指南

| 用户想要...                               | 请阅读这些文件                                          |
| -------------------------------------- | ------------------------------------------------------- |
| **从头开始 / "帮我设置一个 agent"**      | `shared/managed-agents-onboarding.md`——引导式访谈（WHERE→WHO→WHAT→WATCH），然后生成代码 |
| 了解 API 的工作原理                      | `shared/managed-agents-core.md`                         |
| 查看完整的端点参考                       | `shared/managed-agents-api-reference.md`                |
| **创建 agent**（必需的第一步）           | `shared/managed-agents-core.md`（Agents 部分）+ 语言文件 |
| 更新/版本管理 agent                     | `shared/managed-agents-core.md`（Agents → Versioning）——更新，不要重新创建 |
| 创建 session                            | `shared/managed-agents-core.md` + `{lang}/managed-agents/README.md` |
| 配置工具和权限                           | `shared/managed-agents-tools.md`                        |
| 设置 MCP 服务器                          | `shared/managed-agents-tools.md`（MCP Servers 部分）    |
| 流式传输事件 / 处理 tool_use             | `shared/managed-agents-events.md` + 语言文件            |
| 通过 webhook 接收会话状态变更通知（无需轮询） | `shared/managed-agents-webhooks.md`——控制台注册的端点、HMAC 验证、轻量负载+获取 |
| 定义 outcome / 基于评分标准的迭代循环     | `shared/managed-agents-outcomes.md`——`user.define_outcome` 事件、评分器、`span.outcome_evaluation_*` 事件 |
| 协调多个代理 / 子代理 / 线程              | `shared/managed-agents-multiagent.md`——代理上的 `multiagent: {type: "coordinator", agents: [...]}`、会话线程、跨帖工具确认 |
| 设置环境                                 | `shared/managed-agents-environments.md` + 语言文件      |
| 在你的基础设施/VPC 中运行工具执行（自托管沙箱） | `shared/managed-agents-self-hosted-sandboxes.md`——`config:{type:"self_hosted"}`、`ANTHROPIC_ENVIRONMENT_KEY`、`EnvironmentWorker.run()` / `ant beta:worker poll` |
| 上传文件 / 附加仓库                      | `shared/managed-agents-environments.md`（Resources）    |
| 为代理提供跨会话的持久化记忆              | `shared/managed-agents-memory.md`——memory stores、`memory_store` 会话资源、前提条件、版本/编辑 |
| 存储 MCP 凭据                            | `shared/managed-agents-tools.md`（Vaults 部分）         |
| 调用需要密钥的非 MCP API / CLI           | `shared/managed-agents-client-patterns.md` 模式 9——容器无环境变量；vaults 仅适用于 MCP；通过自定义工具在主机端保留密钥 |

## 常见陷阱

- **先有 Agent，再有 Session——无例外**——会话的 `agent` 字段**只**接受字符串 ID 或 `{type: "agent", id, version}`。`model`、`system`、`tools`、`mcp_servers`、`skills` 是 **`POST /v1/agents` 的顶级字段**，绝不在 `sessions.create()` 上。如果用户尚未创建 agent，那是每个示例的第零步。
- **Agent 只需一次，而非每次运行**——`agents.create()` 是一个设置步骤。保存返回的 `agent_id` 并复用它；不要在热路径顶部调用 `agents.create()`。如果代理的配置需要变更，使用 `POST /v1/agents/{id}`——每次更新创建一个新版本，会话可以固定到特定版本以实现可重现性。
- **MCP 认证通过 vaults 进行**——代理的 `mcp_servers` 数组仅声明 `{type, name, url}`（不含认证）。凭据存放在 vaults（`client.beta.vaults.credentials.create`）中并通过 `vault_ids` 附加到会话。Anthropic 使用存储的刷新令牌自动刷新 OAuth 令牌。
- **流式传输以获取事件**——`GET /v1/sessions/{id}/events/stream` 是实时接收代理输出的主要方式。
- **SSE 流没有重放——通过合并重新连接**——如果流在 `agent.tool_use`、`agent.mcp_tool_use` 或 `agent.custom_tool_use` 待处理决议（前两个为 `user.tool_confirmation`，最后一个为 `user.custom_tool_result`）时断开，会话将死锁（客户端断开→会话空闲→重新连接发生→客户端决议未发生）。在每次（重）连接时：通过 `GET /v1/sessions/{id}/events/stream` 打开流，获取 `GET /v1/sessions/{id}/events`，按事件 ID 去重，然后继续。参见 `shared/managed-agents-events.md` → Reconnecting after a dropped stream。
- **不要将 HTTP 库的超时视为挂钟上限**——`requests` 的 `timeout=(c, r)` 和 `httpx.Timeout(n)` 是*每块*的读取超时；它们在每个字节后重置，因此涓流连接可能会无限阻塞。要对原始 HTTP 轮询设置硬性截止时间，在循环级别跟踪 `time.monotonic()` 并显式中止。优先使用 SDK 的 `sessions.events.stream()` / `session.events.list()` 而非手写 HTTP。参见 `shared/managed-agents-events.md` → Receiving Events。
- **消息队列**——你可以在会话处于 `running` 或 `idle` 状态时发送事件；它们会按顺序处理。无需等待响应即可发送下一条消息。
- **环境的 `config.type` 为 `"cloud"` 或 `"self_hosted"`**——`cloud` 在 Anthropic 的基础设施上运行容器；`self_hosted` 将工具执行移至你自己的环境（参见 `shared/managed-agents-self-hosted-sandboxes.md`）。
- **所有资源的归档都是永久性的**——归档 agent、environment、session、vault、credential 或 memory store 会使其变为只读且无法取消归档。对于 agent、environment 和 memory store，已归档的资源不能被新会话引用（现有会话继续运行）。不要调用 `.archive()` 来清理生产环境中的 agent、environment 或 memory store——**在归档之前务必与用户确认**。
