# 托管智能体 — 工具与技能

## 工具

### 服务器工具 vs 客户端工具

| 类型 | 谁运行它 | 工作原理 |
|---|---|---|
| **预构建的 Claude 智能体工具**（`agent_toolset_20260401`）| Anthropic，在会话的容器上（对于 `cloud` 环境；对于 `self_hosted`，**您的** worker 提供并运行它们 — 请参阅 `shared/managed-agents-self-hosted-sandboxes.md`）| 文件操作、bash、网络搜索等。一次全部启用或使用 `enabled: true/false` 单独配置。 |
| **MCP 工具**（`mcp_toolset`）| Anthropic 的编排层 | 连接的 MCP 服务器暴露的能力。通过工具集按服务器授予访问权限。 |
| **自定义工具** | **您** — 您的应用程序处理调用并返回结果 | 智能体发出 `agent.custom_tool_use` 事件，会话变为 `idle`，您发回 `user.custom_tool_result` 事件。 |

**建议：** 通过 `agent_toolset_20260401` 启用所有预构建工具，然后根据需要逐个禁用。

**版本控制：** 工具集是一个版本化的静态资源。当底层工具发生变化时，会创建新的工具集版本（因此有 `_20260401`），这样您就可以确切地知道自己得到了什么。

### 智能体工具集

`agent_toolset_20260401` 提供这些内置工具：

| 工具                   | 描述                              |
| ---------------------- | ---------------------------------------- |
| `bash` | 在 shell 会话中执行 bash 命令 |
| `read` | 从本地文件系统读取文件，包括文本、图像、PDF 和 Jupyter 笔记本 |
| `write` | 将文件写入本地文件系统 |
| `edit` | 在文件中执行字符串替换 |
| `glob` | 使用 glob 模式进行快速文件模式匹配 |
| `grep` | 使用正则表达式进行文本搜索 |
| `web_fetch` | 从 URL 获取内容 |
| `web_search` | 搜索网络获取信息 |

启用完整工具集：

```json
{
  "tools": [
    { "type": "agent_toolset_20260401" }
  ]
}
```

### 按工具配置

覆盖各个工具的默认设置。此示例启用除 bash 之外的所有工具：

```json
{
  "tools": [
    {
      "type": "agent_toolset_20260401",
      "default_config": { "enabled": true },
      "configs": [
        { "name": "bash", "enabled": false }
      ]
    }
  ]
}
```

| 字段 | 必需 | 描述 |
|---|---|---|
| `type` | ✅ | `"agent_toolset_20260401"` |
| `default_config` | ❌ | 应用于所有工具。`{ "enabled": bool, "permission_policy": {...} }` |
| `configs` | ❌ | 按工具覆盖：`[{ "name": "...", "enabled": bool, "permission_policy": {...} }]` |

### 权限策略

控制服务器执行的工具（智能体工具集 + MCP）何时自动运行 vs 等待批准。不适用于自定义工具。

| 策略 | 行为 |
|---|---|
| `always_allow` | 工具自动执行（默认） |
| `always_ask` | 会话发出 `session.status_idle` 并暂停，直到您发送 `tool_confirmation` 事件 |

```json
{
  "type": "agent_toolset_20260401",
  "default_config": {
    "enabled": true,
    "permission_policy": { "type": "always_allow" }
  },
  "configs": [
    { "name": "bash", "permission_policy": { "type": "always_ask" } }
  ]
}
```

**响应 `always_ask`：** 发送带有触发 `agent_tool_use`/`mcp_tool_use` 事件中 `tool_use_id` 的 `user.tool_confirmation` 事件：

```json
{ "type": "tool_confirmation", "tool_use_id": "sevt_abc123", "result": "allow" }
{ "type": "tool_confirmation", "tool_use_id": "sevt_def456", "result": "deny", "message": "改为读取 .env.example" }
```

拒绝时的可选 `message` 会传递给智能体，以便它可以调整其方法。

要仅启用特定工具，反转默认值并按工具选择加入：

```json
{
  "tools": [
    {
      "type": "agent_toolset_20260401",
      "default_config": { "enabled": false },
      "configs": [
        { "name": "bash", "enabled": true },
        { "name": "read", "enabled": true }
      ]
    }
  ]
}
```

### 自定义工具（客户端）

自定义工具由**您的应用程序**执行，而不是 Anthropic。流程：

1. 智能体决定使用工具 → 会话发出带有输入的 `agent.custom_tool_use` 事件
2. 会话变为 `idle` 等待您
3. 您的应用程序执行工具
4. 您发回带有输出的 `user.custom_tool_result` 事件
5. 会话恢复 `running`

不需要权限策略 — 执行的是您。

```json
{
  "tools": [
    {
      "type": "custom",
      "name": "get_weather",
      "description": "获取城市的当前天气。",
      "input_schema": {
        "type": "object",
        "properties": {
          "city": { "type": "string", "description": "城市名称" }
        },
        "required": ["city"]
      }
    }
  ]
}
```

### MCP 服务器

MCP（模型上下文协议）服务器暴露标准化的第三方能力（例如 Asana、GitHub、Linear）。**配置在智能体和保管库之间拆分：**

1. **智能体创建** 声明要连接的服务器（`type`、`name`、`url` — 无认证）。智能体的 `mcp_servers` 数组没有认证字段。
2. **保管库** 存储 OAuth 凭证。在会话创建时通过 `vault_ids` 附加。

这使秘密不会进入可重用的智能体定义。每个保管库凭证都绑定到一个 MCP 服务器 URL；Anthropic 通过 URL 匹配凭证到服务器。

**智能体端 — 声明服务器（无认证）：**

| 字段 | 必需 | 描述 |
|---|---|---|
| `type` | ✅ | `"url"` |
| `name` | ✅ | 唯一名称 — 由 `mcp_toolset.mcp_server_name` 引用 |
| `url` | ✅ | MCP 服务器的端点 URL（可流式 HTTP 传输） |

```json
{
  "mcp_servers": [
    { "type": "url", "name": "linear", "url": "https://mcp.linear.app/mcp" }
  ],
  "tools": [
    { "type": "mcp_toolset", "mcp_server_name": "linear" }
  ]
}
```

**会话端 — 附加保管库：**

```json
{
  "agent": "agent_abc123",
  "environment_id": "env_abc123",
  "vault_ids": ["vlt_abc123"]
}
```

> 💡 **按工具启用（经验性）：** 已观察到 `mcp_toolset` 接受 `default_config: {enabled: false}` + `configs: [{name, enabled: true}]` 用于白名单模式。API 参考仅显示最小的 `{type, mcp_server_name}` 形式。

> 💡 **在运行的会话上更改工具/MCP 服务器：** 当会话为 `idle` 时，`sessions.update()` 可以替换 `agent.tools`、`agent.mcp_servers` 和 `vault_ids` — 这是一个会话本地覆盖，不触及智能体对象。请参阅 `shared/managed-agents-core.md` → 在会话中更新智能体配置。

**大型 MCP 工具输出。** 如果 MCP 工具返回超过 **100K 令牌**，输出会自动卸载到沙箱中的文件 — 智能体会收到截断的预览以及文件路径，并可以 `read` 完整内容。无需配置。

**无效的保管库凭证不会阻止会话创建。** 如果保管库凭证对于声明的 MCP 服务器无效，会话仍会成功创建；`session.error` 事件描述 MCP 认证失败，认证会在下次 `session.status_idle` → `session.status_running` 转换时重试。

> ⚠️ **MCP 认证令牌 ≠ REST API 令牌。** 托管 MCP 服务器（`mcp.notion.com`、`mcp.linear.app` 等）通常需要 **OAuth 承载令牌**，而不是服务的原生 API 密钥。Notion `ntn_` 集成令牌可对 Notion 的 REST API 进行认证，但**不能**作为 Notion MCP 服务器的保管库凭证。这些是不同的认证系统。

### 保管库 — MCP 凭证存储

**保管库** 存储 OAuth 凭证（访问令牌 + 刷新令牌），Anthropic 会通过标准 OAuth 2.0 `refresh_token` 授权代表您自动刷新。这是在启动 SDK 中认证 MCP 服务器的唯一方法。

#### 凭证和沙箱

保管库存储凭证；这些凭证**永远不会进入沙箱**。这是一个故意的安全边界 — 在沙箱中运行的代码（包括智能体编写的任何内容）即使在提示注入下也无法读取或窃取保管库凭证。相反，凭证由 Anthropic 端代理在请求离开沙箱**后**注入：

- **MCP 工具调用** 通过 Anthropic 端代理路由，该代理从保管库获取凭证并将其添加到出站请求。
- **附加 GitHub 仓库上的 Git 操作**（`git pull`、`git push`、GitHub REST 调用）通过 git 代理路由，以同样的方式注入 `github_repository` 资源的 `authorization_token`。

**尚不支持：** 在沙箱内直接运行其他已认证的 CLI（例如 `aws`、`gcloud`、`stripe`）。目前没有办法设置容器环境变量或将保管库凭证暴露给任意进程。如果您现在需要其中一个：

- **优先使用 MCP 服务器** 如果该服务存在 — 它会获得相同的保管库支持的注入。
- **否则，注册自定义工具：** 智能体发出 `agent.custom_tool_use`，您的编排器（已经持有凭证）执行调用并通过相同的已认证事件流返回 `user.custom_tool_result`。不暴露公共端点；沙箱永远看不到秘密。请参阅 `shared/managed-agents-client-patterns.md` → 模式 9。

**不要将 API 密钥放在系统提示或用户消息中作为变通方法** — 它们会持续存在于会话的事件历史中。

> 内部以前称为 TAT（工具/租户访问令牌）。

**流程：**

1. 创建保管库（`client.beta.vaults.create(...)`）— 每个租户/用户一个，或共享一个，具体取决于您的模型
2. 向其中添加 MCP 凭证（`client.beta.vaults.credentials.create(...)`）— 每个凭证都绑定到一个 MCP 服务器 URL
3. 在会话创建时通过 `vault_ids: ["vlt_..."]` 引用保管库
4. Anthropic 在令牌过期前自动刷新；智能体在调用 MCP 工具时使用当前的访问令牌

**凭证形状**：

```json
{
  "display_name": "Notion (workspace-foo)",
  "auth": {
    "type": "mcp_oauth",
    "mcp_server_url": "https://mcp.notion.com/mcp",
    "access_token": "<当前访问令牌>",
    "expires_at": "2026-04-02T14:00:00Z",
    "refresh": {
      "refresh_token": "<刷新令牌>",
      "client_id": "<您的 OAuth client_id>",
      "token_endpoint": "https://api.notion.com/v1/oauth/token",
      "token_endpoint_auth": { "type": "none" }
    }
  }
}
```

`refresh` 块是启用自动刷新的原因 — `token_endpoint` 是 Anthropic 发布 `refresh_token` 授权的地方。`token_endpoint_auth` 是一个可区分的联合：

| `type` | 形状 | 使用时机 |
|---|---|---|
| `"none"` | `{type: "none"}` | 公共 OAuth 客户端（无秘密） |
| `"client_secret_basic"` | `{type: "client_secret_basic", client_secret: "..."}` | 机密客户端，通过 HTTP 基本认证的秘密 |
| `"client_secret_post"` | `{type: "client_secret_post", client_secret: "..."}` | 机密客户端，请求正文中的秘密 |

如果您只有访问令牌而没有刷新能力，请完全省略 `refresh` — 它会工作直到过期，然后智能体将失去访问权限。

> 💡 **获取 OAuth 令牌。** 您如何获取初始访问和刷新令牌取决于 MCP 服务器 — 请查阅其文档。一旦您拥有它们，使用上面的形状将它们存储在保管库凭证中；Anthropic 会从那里通过 `refresh.token_endpoint` 自动刷新。

**作用域：** 保管库是工作区级别的。API 工作区中具有 developer+ 角色的任何人都可以创建、读取（仅限元数据 — 秘密是只写的）和附加保管库。`vault_ids` 可以在会话**创建**时设置，但不能通过会话更新设置（SDK 文档字符串说"尚不支持；设置此字段的请求被拒绝"）。

---

## 技能

技能是可重用的、基于文件系统的资源，为您的智能体提供特定领域的专业知识：工作流、上下文和最佳实践，这些将通用智能体转变为专家。与提示（针对一次性任务的对话级指令）不同，技能按需加载，无需在多个对话中反复提供相同的指导。

两种类型 — 两者工作方式相同；智能体在与手头任务相关时自动使用它们：

| 类型 | 是什么 |
|---|---|
| **预构建的 Anthropic 技能** | 常见文档任务（PowerPoint、Excel、Word、PDF）。按名称引用（例如 `xlsx`）。 |
| **自定义技能** | 您通过技能 API 在组织中创建的技能。通过 `skill_id` + 可选的 `version` 引用。 |

**每个智能体最多 20 个技能。** 智能体创建使用 `managed-agents-2026-04-01`；单独的技能 API（用于管理自定义技能定义）使用 `skills-2025-10-02`。

### 在会话上启用技能

技能通过 `agents.create()` 附加到**智能体**定义：

```ts
const agent = await client.beta.agents.create(
  {
    name: "财务智能体",
    model: "claude-opus-4-8",
    system: "你是一个财务分析智能体。",
    skills: [
      { type: "anthropic", skill_id: "xlsx" },
      { type: "custom", skill_id: "skill_abc123", version: "latest" },
    ],
  }
);
```

Python：

```python
agent = client.beta.agents.create(
    name="财务智能体",
    model="claude-opus-4-8",
    system="你是一个财务分析智能体。",
    skills=[
        {"type": "anthropic", "skill_id": "xlsx"},
        {"type": "custom", "skill_id": "skill_abc123", "version": "latest"},
    ]
)
```

**技能引用字段：**

| 字段 | Anthropic 技能 | 自定义技能 |
|---|---|---|
| `type` | `"anthropic"` | `"custom"` |
| `skill_id` | 技能名称（例如 `"xlsx"`、`"docx"`、`"pptx"`、`"pdf"`）| 来自技能 API 的技能 ID（例如 `"skill_abc123"`）|
| `version` | — | `"latest"` 或特定版本号 |

### 技能 API

| 操作             | 方法   | 路径                                            |
| --------------------- | -------- | ----------------------------------------------- |
| 创建技能          | `POST`   | `/v1/skills`                                    |
| 列出技能           | `GET`    | `/v1/skills`                                    |
| 获取技能             | `GET`    | `/v1/skills/{id}`                               |
| 删除技能          | `DELETE` | `/v1/skills/{id}`                               |
| 创建版本        | `POST`   | `/v1/skills/{id}/versions`                      |
| 列出版本         | `GET`    | `/v1/skills/{id}/versions`                      |
| 获取版本           | `GET`    | `/v1/skills/{id}/versions/{version}`            |
| 删除版本        | `DELETE` | `/v1/skills/{id}/versions/{version}`            |
