# 托管智能体 — 入门流程

> **通过 `/claude-api managed-agents-onboard` 调用？** 您来对地方了。运行下面的面试 — 不要将它总结回给用户，提出问题。

当用户想要从头开始设置托管智能体时使用此方法。三步：**根据知道/探索分支 → 配置模板 → 设置会话**。最后输出可工作的代码。

> 请同时阅读 `shared/managed-agents-core.md` — 它包含每个旋钮的完整详细信息。本文档是面试脚本，不是参考。

---

Claude 托管智能体是一个托管的智能体运行时：Anthropic 在其编排层运行智能体循环，并为每个会话提供沙箱容器，智能体的工具在其中执行（或者，使用 `self_hosted` 环境，您自己的工作器运行工具 — 请参阅 `shared/managed-agents-self-hosted-sandboxes.md`）。您提供智能体配置和环境配置；连接性 — 事件流、沙箱编排、提示缓存、上下文压缩和扩展思考 — 已为您处理。

**您提供的内容：**
- **智能体配置** — 工具、技能、模型、系统提示。可重用和版本化。
- **环境配置** — 智能体工具执行的沙箱（`cloud`：网络、包；或 `self_hosted`：您自己的基础设施）。可跨智能体重用。

智能体的每次运行都是一个**会话**。

---

## 1. 知道还是探索？

询问用户：

> 您是已经知道想要构建的智能体，还是想先探索一些常见模式？

### 探索路径 — 展示模式

四种形状，相同的运行时代码路径（`sessions.create()` → `sessions.events.send()` → 流）。只有触发器和接收器不同。

| 模式 | 触发器 | 示例 |
|---|---|---|
| 事件触发 | Webhook | GitHub PR 推送 → CMA（GitHub 工具）→ Slack |
| 定时调度 | Cron | 每日简报：浏览器 + GitHub + Jira → CMA → Slack |
| 即发即弃 PR | 人工 | Slack 斜杠命令 → CMA（GitHub 工具）→ PR 通过 CI |
| 研究 + 仪表板 | 人工 | 主题 → CMA（网络搜索 + `frontend-design` 技能）→ HTML 仪表板 |

询问哪个形状适合，然后继续使用它作为参考的"知道"路径。

### 知道路径 — 配置模板

三轮。批量提出每轮的问题；不要一次问一个。

**A 轮 — 工具。** 从这里开始；这是最具体的部分。三种类型；询问用户想要哪个（任意组合）：

| 类型 | 是什么 | 指南 |
|---|---|---|
| **预构建的 Claude 智能体工具**（`agent_toolset_20260401`） | 开箱即用：`bash`、`read`、`write`、`edit`、`glob`、`grep`、`web_fetch`、`web_search`。一次全部启用，或通过 `enabled: true/false` 单独启用。 | 推荐启用完整工具集。列出 8 个工具，以便用户知道他们得到什么。完整详细信息：`shared/managed-agents-tools.md` → 智能体工具集。 |
| **MCP 工具** | 通过 `mcp_toolset` 进行第三方集成（GitHub、Linear、Asana 等）。凭证位于保管库中，不是内联的。 | 询问哪些服务。对于每个，演练 MCP 服务器 URL + 保管库凭证。完整详细信息：`shared/managed-agents-tools.md` → MCP 服务器 + 保管库。 |
| **自定义工具** | 用户自己的应用处理这些工具调用 — 智能体发出 `agent.custom_tool_use`，应用发回结果消息。 | 询问每个工具：名称、描述、输入架构。处理事件的应用代码是*他们的*代码 — 不要生成它。完整详细信息：`shared/managed-agents-tools.md` → 自定义工具。 |

**B 轮 — 技能、文件和仓库。** 智能体启动时手头有什么。

*技能* — 两种类型；两者工作方式相同 — Claude 在相关时自动使用它们。每个智能体最多 20 个。
- [ ] **预构建的智能体技能**：`xlsx`、`docx`、`pptx`、`pdf`。按名称引用。
- [ ] **自定义技能**：通过技能 API 上传到用户组织的技能。按 `skill_id` + 可选 `version` 引用。如果技能尚不存在，请引导用户完成 `POST /v1/skills` + `POST /v1/skills/{id}/versions`（beta 头 `skills-2025-10-02`）。完整详细信息：`shared/managed-agents-tools.md` → 技能 + 技能 API。

*GitHub 仓库* — 智能体需要磁盘上的任何仓库吗？对于每个：
- [ ] 仓库 URL（`https://github.com/org/repo`）
- [ ] `authorization_token`（PAT 或范围限定到仓库的 GitHub App 令牌）
- [ ] 可选 `mount_path`（默认为 `/workspace/<repo-name>`）和 `checkout`（分支或 SHA）

作为 `resources: [{type: "github_repository", url, authorization_token, ...}]` 发出。完整详细信息：`shared/managed-agents-environments.md` → GitHub 仓库。

> ‼️ **PR 创建也需要 GitHub MCP 服务器。** `github_repository` 仅提供文件系统访问 — 要打开 PR，还要在 A 轮中附加 GitHub MCP 服务器并通过保管库进行认证。工作流程是：在挂载的仓库中编辑文件 → 通过 `bash` 推送分支（使用 `authorization_token` 通过 git 代理认证）→ 通过 MCP `create_pull_request` 工具创建 PR。

*文件* — 任何用于播种会话的本地文件？对于每个：
- [ ] 通过文件 API 上传 → 持久化 `file_id`
- [ ] 选择一个 `mount_path` — 绝对路径，例如 `/workspace/data.csv`（父目录自动创建；文件以只读方式挂载）

作为 `resources: [{type: "file", file_id, mount_path}]` 发出。最多 999 个文件资源。智能体工作目录默认为 `/workspace`。完整详细信息：`shared/managed-agents-environments.md` → 文件 API。

**C 轮 — 环境 + 身份：**
- [ ] 网络：容器的无限制互联网，还是将出站锁定到特定主机？（如果锁定，MCP 服务器域必须在 `allowed_hosts` 中，否则工具会静默失败。）
- [ ] 名称？
- [ ] 工作（一两句话 — 变为系统提示）？
- [ ] 模型？（默认 `claude-opus-4-8`）

---

## 2. 设置会话

每次运行。指向智能体 + 环境，附加凭证，启动。

**保管库凭证**（如果智能体声明了 MCP 服务器）：
- [ ] 现有保管库，还是创建一个？（`client.beta.vaults.create()` + `vaults.credentials.create()`）

凭证是只写的，按 URL 匹配到 MCP 服务器，自动刷新。请参阅 `shared/managed-agents-tools.md` → 保管库。

**启动：**
- [ ] 给智能体的第一条消息？

会话创建会阻塞，直到所有资源都挂载完毕。在发送启动之前打开事件流。流是 SSE；在 `session.status_terminated` 时中断，或在 `session.status_idle` 且带有终端 `stop_reason` 时中断 — 即除了 `requires_action` 之外的任何东西，`requires_action` 在会话等待工具确认或自定义工具结果时瞬时触发（请参阅 `shared/managed-agents-client-patterns.md` 模式 5）。使用情况落在 `span.model_request_end` 上。智能体写入的工件最终位于 `/mnt/session/outputs/` — 通过 `files.list({scope_id: session.id, betas: ["managed-agents-2026-04-01"]})` 下载。

---

## 3. 发出代码

直接从最后一次面试回答转到代码 — 不要前言关于设置与运行时的拆分，不要"要内化的关键事情..."，不要关于 `agents.create()` 是一次性的演讲。下面的两个块结构已经展示了这一点；不要叙述它。为检测到的每种语言生成**两个清晰分开的块**（Python/TS/cURL — 请参阅 SKILL.md → 语言检测）：

**块 1 — 设置（运行一次，将 ID 保存到配置/.env）：**
1. `environments.create()` → 持久化 `env_id`
2. 使用 §A–C 轮中的所有内容执行 `agents.create()` → 持久化 `agent_id` 和 `agent_version`

标签：`# 一次性设置 — 运行一次，将 ID 保存到 config/.env`

**块 2 — 运行时（在每次调用时运行）：**
1. 从 config/env 加载 `env_id` + `agent_id`
2. `sessions.create(agent=AGENT_ID, environment_id=ENV_ID, resources=[...], vault_ids=[...])`
3. 打开流，`events.send()` 启动，循环直到 `session.status_terminated` 或 `session.status_idle && stop_reason.type !== 'requires_action'`（完整门控请参阅 `shared/managed-agents-client-patterns.md` 模式 5 — 不要在裸 `session.status_idle` 上中断）

> ⚠️ **永远不要在同一个无保护块中发出 `agents.create()` 和 `sessions.create()`。** 这会教会用户在每次运行时创建新的智能体 — 第一反模式。如果他们需要单个脚本，请将智能体创建包装在 `if not os.getenv("AGENT_ID"):` 中。

从 `python/managed-agents/README.md`、`typescript/managed-agents/README.md` 或 `curl/managed-agents.md` 中提取确切语法。不要编造字段名称。
