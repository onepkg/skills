# 托管代理——工具与技能

## 工具

### 服务器端工具与客户端工具

| 类型 | 运行方 | 工作方式 |
|---|---|---|
| **预构建的 Claude 代理工具** (`agent_toolset_20260401`) | Anthropic，在会话容器中运行（对于 `cloud` 环境；对于 `self_hosted`，**你的**工作节点提供并运行它们——参见 `shared/managed-agents-self-hosted-sandboxes.md`） | 文件操作、bash、网络搜索等。可一次性全部启用，或通过 `enabled: true/false` 单独配置。 |
| **MCP 工具** (`mcp_toolset`) | Anthropic 的编排层 | 由连接的 MCP 服务器暴露的能力。通过工具集按服务器授予访问权限。 |
| **自定义工具** | **你**——你的应用程序处理调用并返回结果 | 代理发出 `agent.custom_tool_use` 事件，会话进入 `idle` 状态，你发回 `user.custom_tool_result` 事件。 |

**建议：** 通过 `agent_toolset_20260401` 启用所有预构建工具，然后根据需要进行单独禁用。

**版本管理：** 工具集是一个带版本号的静态资源。当底层工具发生变化时，会创建新的工具集版本（因此命名为 `_20260401`），这样你始终清楚自己获取的具体内容。

### 代理工具集

`agent_toolset_20260401` 提供以下内置工具：

| 工具 | 描述 |
|---|---|
| `bash` | 在 shell 会话中执行 bash 命令 |
| `read` | 从本地文件系统读取文件，包括文本、图片、PDF 和 Jupyter 笔记本 |
| `write` | 向本地文件系统写入文件 |
| `edit` | 在文件中执行字符串替换 |
| `glob` | 使用 glob 模式进行快速文件匹配 |
| `grep` | 使用正则表达式进行文本搜索 |
| `web_fetch` | 从 URL 获取内容 |
| `web_search` | 搜索网络信息 |

启用完整的工具集：

```json
{
  "tools": [
    { "type": "agent_toolset_20260401" }
  ]
}
```

### 逐个工具配置

为单个工具覆盖默认配置。此示例启用除 bash 之外的所有工具：

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

| 字段 | 是否必需 | 描述 |
|---|---|---|
| `type` | ✅ | `"agent_toolset_20260401"` |
| `default_config` | ❌ | 应用于所有工具。`{ "enabled": bool, "permission_policy": {...} }` |
| `configs` | ❌ | 逐个工具覆盖：`[{ "name": "...", "enabled": bool, "permission_policy": {...} }]` |

### 权限策略

控制由服务器执行的工具（代理工具集 + MCP）何时自动运行，何时等待审批。不适用于自定义工具。

| 策略 | 行为 |
|---|---|
| `always_allow` | 工具自动执行（默认） |
| `always_ask` | 会话发出 `session.status_idle` 事件并暂停，直到你发送 `tool_confirmation` 事件 |

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

**响应 `always_ask`：** 发送一个 `user.tool_confirmation` 事件，其中包含触发该事件的 `agent_tool_use`/`mcp_tool_use` 事件的 `tool_use_id`：

```json
{ "type": "tool_confirmation", "tool_use_id": "sevt_abc123", "result": "allow" }
{ "type": "tool_confirmation", "tool_use_id": "sevt_def456", "result": "deny", "message": "改为读取 .env.example" }
```

拒绝时附带的可选 `message` 会传递给代理，以便其调整策略。

要仅启用特定工具，可关闭默认设置并逐个选择启用：

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

### 自定义工具（客户端侧）

自定义工具由**你的应用程序**执行，而非 Anthropic。流程如下：

1. 代理决定使用工具 → 会话发出 `agent.custom_tool_use` 事件，包含输入参数
2. 会话进入 `idle` 状态等待你处理
3. 你的应用程序执行工具
4. 你发回 `user.custom_tool_result` 事件，包含输出结果
5. 会话恢复 `running` 状态

不需要权限策略——因为由你执行。

```json
{
  "tools": [
    {
      "type": "custom",
      "name": "get_weather",
      "description": "获取某个城市的当前天气。",
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

MCP（模型上下文协议）服务器暴露标准化的第三方能力（例如 Asana、GitHub、Linear）。**配置在代理和保管库之间拆分：**

1. **代理创建**时声明要连接的服务器（`type`、`name`、`url`——不含认证信息）。代理的 `mcp_servers` 数组没有认证字段。
2. **保管库**存储 OAuth 凭证。通过会话创建时的 `vault_ids` 关联。

这样可以将密钥与可重用的代理定义分离。每个保管库凭证关联一个 MCP 服务器 URL；Anthropic 通过 URL 匹配凭证与服务器。

**代理侧——声明服务器（不含认证）：**

| 字段 | 是否必需 | 描述 |
|---|---|---|
| `type` | ✅ | `"url"` |
| `name` | ✅ | 唯一名称——由 `mcp_toolset.mcp_server_name` 引用 |
| `url` | ✅ | MCP 服务器的端点 URL（Streamable HTTP 传输） |

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

**会话侧——关联保管库：**

```json
{
  "agent": "agent_abc123",
  "environment_id": "env_abc123",
  "vault_ids": ["vlt_abc123"]
}
```

> 💡 **逐个工具启用（经验之谈）：** 已观察到 `mcp_toolset` 支持 `default_config: {enabled: false}` + `configs: [{name, enabled: true}]` 的白名单模式。API 参考仅展示最简的 `{type, mcp_server_name}` 形式。

> 💡 **在运行中的会话上更改工具/MCP 服务器：** 当会话处于 `idle` 状态时，`sessions.update()` 可以替换 `agent.tools`、`agent.mcp_servers` 和 `vault_ids`——这是会话本地覆盖，不会触及代理对象。参见 `shared/managed-agents-core.md` → 在会话中途更新代理配置。

**大型 MCP 工具输出。** 如果 MCP 工具返回超过 **100K tokens** 的内容，输出会自动转存到沙箱中的文件——代理会收到截断的预览内容加上文件路径，可以通过 `read` 工具读取完整内容。无需配置。

**无效的保管库凭证不会阻止会话创建。** 如果保管库凭证对于声明的 MCP 服务器无效，会话仍会成功创建；会发出 `session.error` 事件描述 MCP 认证失败信息，并在下一次 `session.status_idle` → `session.status_running` 转换时重试认证。

> ⚠️ **MCP 认证令牌 ≠ REST API 令牌。** 托管的 MCP 服务器（`mcp.notion.com`、`mcp.linear.app` 等）通常需要 **OAuth 持有者令牌**，而非服务的原生 API 密钥。Notion 的 `ntn_` 集成令牌可以认证 Notion 的 REST API，但**不能**作为 Notion MCP 服务器的保管库凭证使用。这是两套不同的认证体系。

### 保管库——MCP 凭证存储

**保管库**存储 OAuth 凭证（访问令牌 + 刷新令牌），Anthropic 通过标准 OAuth 2.0 `refresh_token` 授权自动为你刷新。这是在启动 SDK 中认证 MCP 服务器的唯一方式。

#### 凭证与沙箱

保管库存储凭证；这些凭证**永远不会进入沙箱**。这是一个有意为之的安全边界——在沙箱中运行的代码（包括代理编写的任何内容）即使在提示注入攻击下也无法读取或窃取保管库中的凭证。相反，凭证由 Anthropic 侧代理在**请求离开沙箱后**注入：

- **MCP 工具调用**通过 Anthropic 侧代理路由，该代理从保管库获取凭证并将其添加到出站请求中。
- **关联的 GitHub 仓库的 Git 操作**（`git pull`、`git push`、GitHub REST 调用）通过 git 代理路由，以相同方式注入 `github_repository` 资源的 `authorization_token`。

**尚不支持：** 在沙箱内部直接运行其他需要认证的 CLI（例如 `aws`、`gcloud`、`stripe`）。目前无法设置容器环境变量或将保管库凭证暴露给任意进程。如果你当前需要使用这些工具：

- **优先选择相应的 MCP 服务器**（如果存在）——它可以使用相同的基于保管库的注入机制。
- **否则，注册一个自定义工具：** 代理发出 `agent.custom_tool_use` 事件，你的编排器（已持有凭证）执行调用并通过同一个已认证事件流返回 `user.custom_tool_result` 结果。不会暴露公共端点；沙箱永远不会看到密钥。参见 `shared/managed-agents-client-patterns.md` → 模式 9。

**不要将 API 密钥作为变通方案放入系统提示或用户消息中**——它们会持久保存在会话的事件历史中。

> 内部曾称为 TAT（工具/租户访问令牌）。

**流程：**

1. 创建保管库（`client.beta.vaults.create(...)`）——根据你的模式，可以为每个租户/用户创建一个，或共享一个
2. 向其中添加 MCP 凭证（`client.beta.vaults.credentials.create(...)`）——每个凭证关联一个 MCP 服务器 URL
3. 在创建会话时通过 `vault_ids: ["vlt_..."]` 引用保管库
4. Anthropic 在令牌过期前自动刷新；代理在调用 MCP 工具时使用当前的访问令牌

**凭证结构：**

```json
{
  "display_name": "Notion (workspace-foo)",
  "auth": {
    "type": "mcp_oauth",
    "mcp_server_url": "https://mcp.notion.com/mcp",
    "access_token": "<current access token>",
    "expires_at": "2026-04-02T14:00:00Z",
    "refresh": {
      "refresh_token": "<refresh token>",
      "client_id": "<your OAuth client_id>",
      "token_endpoint": "https://api.notion.com/v1/oauth/token",
      "token_endpoint_auth": { "type": "none" }
    }
  }
}
```

`refresh` 块是启用自动刷新的关键——`token_endpoint` 是 Anthropic 发送 `refresh_token` 授权请求的地址。`token_endpoint_auth` 是一个区分联合类型：

| `type` | 结构 | 使用场景 |
|---|---|---|
| `"none"` | `{type: "none"}` | 公开 OAuth 客户端（无密钥） |
| `"client_secret_basic"` | `{type: "client_secret_basic", client_secret: "..."}` | 机密客户端，通过 HTTP Basic 认证传递密钥 |
| `"client_secret_post"` | `{type: "client_secret_post", client_secret: "..."}` | 机密客户端，在请求体中传递密钥 |

如果你只有访问令牌而没有刷新能力，可以完全省略 `refresh`——令牌将在过期前正常工作，之后代理将失去访问权限。

> 💡 **获取 OAuth 令牌。** 如何获取初始的访问令牌和刷新令牌取决于 MCP 服务器——请查阅其文档。获取后，使用上述结构将其存储在保管库凭证中；Anthropic 随后会通过 `refresh.token_endpoint` 自动刷新。

**作用域：** 保管库是工作空间级别的。API 工作空间中具有 developer+ 角色的任何人都可以创建、读取（仅元数据——密钥是只写的）和关联保管库。`vault_ids` 可以在会话**创建**时设置，但不能通过会话更新设置（SDK 文档字符串注明"尚不支持；设置此字段的请求将被拒绝"）。

---

## 技能

技能是可重用的、基于文件系统的资源，为代理提供特定领域的专业知识：工作流、上下文和最佳实践，将通用代理转变为专家。与提示词（针对一次性任务的对话级别指令）不同，技能按需加载，无需在多次对话中重复提供相同的指导。

两种类型——两者工作方式相同；代理在相关任务时会自动使用它们：

| 类型 | 说明 |
|---|---|
| **预构建的 Anthropic 技能** | 常见文档任务（PowerPoint、Excel、Word、PDF）。通过名称引用（例如 `xlsx`）。 |
| **自定义技能** | 你通过 Skills API 在组织中创建的技能。通过 `skill_id` + 可选的 `version` 引用。 |

**每个代理最多 20 个技能。** 代理创建使用 `managed-agents-2026-04-01`；单独的 Skills API（用于管理自定义技能定义）使用 `skills-2025-10-02`。

### 在会话上启用技能

技能通过 `agents.create()` 附加到**代理**定义中：

```ts
const agent = await client.beta.agents.create(
  {
    name: "Financial Agent",
    model: "claude-opus-4-8",
    system: "You are a financial analysis agent.",
    skills: [
      { type: "anthropic", skill_id: "xlsx" },
      { type: "custom", skill_id: "skill_abc123", version: "latest" },
    ],
  }
);
```

Python:

```python
agent = client.beta.agents.create(
    name="Financial Agent",
    model="claude-opus-4-8",
    system="You are a financial analysis agent.",
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
| `skill_id` | 技能名称（例如 `"xlsx"`、`"docx"`、`"pptx"`、`"pdf"`） | 来自 Skills API 的技能 ID（例如 `"skill_abc123"`） |
| `version` | — | `"latest"` 或特定版本号 |

### Skills API

| 操作 | 方法 | 路径 |
|---|---|---|
| 创建技能 | `POST` | `/v1/skills` |
| 列出技能 | `GET` | `/v1/skills` |
| 获取技能 | `GET` | `/v1/skills/{id}` |
| 删除技能 | `DELETE` | `/v1/skills/{id}` |
| 创建版本 | `POST` | `/v1/skills/{id}/versions` |
| 列出版本 | `GET` | `/v1/skills/{id}/versions` |
| 获取版本 | `GET` | `/v1/skills/{id}/versions/{version}` |
| 删除版本 | `DELETE` | `/v1/skills/{id}/versions/{version}` |
