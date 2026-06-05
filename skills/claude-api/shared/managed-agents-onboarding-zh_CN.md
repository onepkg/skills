# Managed Agents — 接入流程

> **通过 `/claude-api managed-agents-onboard` 调用的？** 你来对地方了。按以下流程进行访谈——不要向用户总结，直接提问。

当用户想从零开始设置 Managed Agent 时使用此文档。三个步骤：**分支判断已知/探索 → 配置模板 → 设置会话**。最终输出可运行的代码。

> 请结合 `shared/managed-agents-core.md` 阅读——它提供了每个配置项的详细说明。本文档是访谈脚本，而非参考手册。

---

Claude Managed Agents 是一项托管式 Agent 服务：Anthropic 在其编排层上运行 Agent 循环，并为每个会话提供一个沙箱容器，Agent 的工具在其中执行（或者，使用 `self_hosted` 环境时，由你自己的工作节点运行工具——详见 `shared/managed-agents-self-hosted-sandboxes.md`）。你提供 Agent 配置和环境配置；其余的——事件流、沙箱编排、提示缓存、上下文压缩和扩展思考——都由平台代为处理。

**你需要提供的内容：**
- **Agent 配置** —— 工具、技能、模型、系统提示。可复用且支持版本管理。
- **环境配置** —— Agent 工具执行所在的沙箱（`cloud`：网络、包管理；或 `self_hosted`：你自己的基础设施）。可在多个 Agent 间复用。

Agent 的每次运行都是一个**会话**。

---

## 1. 已知需求还是探索？

询问用户：

> 你已经知道自己想构建什么样的 Agent，还是想先了解一些常见模式？

### 探索路径——展示模式

四种形态，相同的运行时代码路径（`sessions.create()` → `sessions.events.send()` → 流式响应）。仅触发器和输出目的地不同。

| 模式 | 触发器 | 示例 |
|---|---|---|
| 事件触发 | Webhook | GitHub PR 推送 → CMA（GitHub 工具）→ Slack | # <------ MC maybe delete?
| 定时调度 | Cron | 每日简报：浏览器 + GitHub + Jira → CMA → Slack | # <------ MC maybe delete?
| 即发即忘 PR | 人工 | Slack 斜杠命令 → CMA（GitHub 工具）→ 通过 CI 的 PR |
| 研究 + 仪表盘 | 人工 | 主题 → CMA（网页搜索 + `frontend-design` 技能）→ HTML 仪表盘 |

询问哪种形态合适，然后以该形态为参考，继续执行已知路径。

### 已知路径——配置模板

三轮提问。每轮中的问题应批量提出，不要逐一询问。

**第 A 轮——工具。** 从这里开始；这是最具体的部分。三种类型，询问用户需要哪些（可任意组合）：

| 类型 | 说明 | 指导方式 |
|---|---|---|
| **预制 Claude Agent 工具**（`agent_toolset_20260401`） | 即开即用：`bash`、`read`、`write`、`edit`、`glob`、`grep`、`web_fetch`、`web_search`。可一次性全部启用，或通过 `enabled: true/false` 单独启用。 | 建议启用完整工具集。列出 8 个工具以便用户了解。详见 `shared/managed-agents-tools.md` → Agent Toolset。 |
| **MCP 工具** | 通过 `mcp_toolset` 实现的第三方集成（GitHub、Linear、Asana 等）。凭证存储在保险库中，而非内联方式。 | 询问需要哪些服务。针对每个服务，说明 MCP 服务器 URL + 保险库凭证的配置方法。详见 `shared/managed-agents-tools.md` → MCP Servers + Vaults。 |
| **自定义工具** | 用户自己的应用处理这些工具调用——Agent 触发 `agent.custom_tool_use`，应用返回结果消息。 | 询问每个工具的：名称、描述、输入 schema。处理事件的应用代码是*他们的*代码——不要生成。详见 `shared/managed-agents-tools.md` → Custom Tools。 |

**第 B 轮——技能、文件和仓库。** Agent 启动时可用的资源。

*技能* — 两种类型，工作方式相同——Claude 会在相关时自动使用它们。每个 Agent 最多 20 个。
- [ ] **预制 Agent 技能**：`xlsx`、`docx`、`pptx`、`pdf`。按名称引用。
- [ ] **自定义技能**：通过 Skills API 上传到用户组织的技能。通过 `skill_id` + 可选 `version` 引用。如果技能尚不存在，引导用户执行 `POST /v1/skills` + `POST /v1/skills/{id}/versions`（beta 头 `skills-2025-10-02`）。详见 `shared/managed-agents-tools.md` → Skills + Skills API。

*GitHub 仓库* — Agent 需要在磁盘上访问哪些仓库？针对每个仓库：
- [ ] 仓库 URL（`https://github.com/org/repo`）
- [ ] `authorization_token`（PAT 或限于该仓库的 GitHub App token）
- [ ] 可选 `mount_path`（默认为 `/workspace/<仓库名称>`）和 `checkout`（分支或 SHA）

输出格式：`resources: [{type: "github_repository", url, authorization_token, ...}]`。详见 `shared/managed-agents-environments.md` → GitHub Repositories。

> ‼️ **创建 PR 还需要 GitHub MCP 服务器。** `github_repository` 仅提供文件系统访问权限——要创建 PR，还需在第 A 轮中附加 GitHub MCP 服务器并通过保险库为其配置凭证。工作流程为：编辑已挂载仓库中的文件 → 通过 `bash` 推送分支 → 通过 MCP 的 `create_pull_request` 工具创建 PR。

*文件* — 是否有本地文件需要注入到会话中？针对每个文件：
- [ ] 通过 Files API 上传 → 持久化 `file_id`
- [ ] 选择 `mount_path`——绝对路径，例如 `/workspace/data.csv`（父目录自动创建；文件以只读方式挂载）

输出格式：`resources: [{type: "file", file_id, mount_path}]`。最多 999 个文件资源。Agent 工作目录默认为 `/workspace`。详见 `shared/managed-agents-environments.md` → Files API。

**第 C 轮——环境 + 身份：**
- [ ] 网络：容器可不受限制地访问互联网，还是将出站流量限制到特定主机？（如果限制，MCP 服务器域名必须包含在 `allowed_hosts` 中，否则工具会静默失败。）
- [ ] 名称？
- [ ] 职责描述（一两句话——将成为系统提示）？
- [ ] 模型？（默认 `claude-opus-4-8`）

---

## 2. 设置会话

每次运行。指向 Agent + 环境，附加凭证，启动会话。

**保险库凭证**（如果 Agent 声明了 MCP 服务器）：
- [ ] 使用现有保险库，还是新建一个？（`client.beta.vaults.create()` + `vaults.credentials.create()`）

凭证为只写模式，按 URL 匹配到 MCP 服务器，自动刷新。详见 `shared/managed-agents-tools.md` → Vaults。

**启动：**
- [ ] 发送给 Agent 的首条消息？

会话创建会阻塞直到所有资源挂载完成。在发送启动消息之前打开事件流。流为 SSE 格式；在 `session.status_terminated` 处断开，或在 `session.status_idle` 且带有终止 `stop_reason` 时断开——即除 `requires_action` 之外的任何状态，`requires_action` 会在会话等待工具确认或自定义工具结果时暂时触发（详见 `shared/managed-agents-client-patterns.md` 模式 5）。用量记录在 `span.model_request_end` 上。Agent 生成的工作成果存放在 `/mnt/session/outputs/` 中——通过 `files.list({scope_id: session.id, betas: ["managed-agents-2026-04-01"]})` 下载。

---

## 3. 输出代码

直接从最后一个访谈答案进入代码——不要介绍设置与运行时的区别，不要说"需要理解的关键点是……"，不要讲解 `agents.create()` 是一次性操作。下面的两块结构已经表明了这一点，无需赘述。针对检测到的每种语言（Python/TS/cURL——参见 SKILL.md → Language Detection），生成**两个明确分隔的代码块**：

**代码块 1——设置（运行一次，存储 ID）：**
1. `environments.create()` → 持久化 `env_id`
2. `agents.create()` 包含第 A–C 轮的所有配置 → 持久化 `agent_id` 和 `agent_version`

标签：`# ONE-TIME SETUP — run once, save the IDs to config/.env`

**代码块 2——运行时（每次调用时执行）：**
1. 从配置/环境变量中加载 `env_id` + `agent_id`
2. `sessions.create(agent=AGENT_ID, environment_id=ENV_ID, resources=[...], vault_ids=[...])`
3. 打开流，通过 `events.send()` 发送启动消息，循环直到 `session.status_terminated` 或 `session.status_idle && stop_reason.type !== 'requires_action'`（完整条件判断参见 `shared/managed-agents-client-patterns.md` 模式 5——不要在仅 `session.status_idle` 时断开）

> ⚠️ **切勿在同一个无保护条件的代码块中同时包含 `agents.create()` 和 `sessions.create()`。** 这会让用户误以为每次运行都需要创建新 Agent——这是第一大反模式。如果用户需要一个单一脚本，请将 Agent 创建逻辑包裹在 `if not os.getenv("AGENT_ID"):` 中。

从 `python/managed-agents/README.md`、`typescript/managed-agents/README.md` 或 `curl/managed-agents.md` 中获取准确语法。不要自行编造字段名。
