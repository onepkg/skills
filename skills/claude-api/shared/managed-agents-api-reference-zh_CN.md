# 托管代理（Managed Agents）—— 端点参考

所有端点均需包含 `x-api-key` 和 `anthropic-version: 2023-06-01` 请求头。托管代理端点额外需要 `anthropic-beta` 请求头。

## Beta 请求头

```
anthropic-beta: managed-agents-2026-04-01
```

SDK 会自动为所有 `client.beta.{agents,environments,sessions,vaults,memory_stores}.*` 调用添加此请求头。Skills 端点使用 `skills-2025-10-02`；Files 端点使用 `files-api-2025-04-14`。

---

## SDK 方法参考

所有资源均位于 `beta` 命名空间下。Python 和 TypeScript 的方法名称相同。

| 资源 | Python / TypeScript（`client.beta.*`） | Go（`client.Beta.*`） |
| --- | --- | --- |
| Agents | `agents.create` / `retrieve` / `update` / `list` / `archive` | `Agents.New` / `Get` / `Update` / `List` / `Archive` |
| Agent Versions | `agents.versions.list` | `Agents.Versions.List` |
| Environments | `environments.create` / `retrieve` / `update` / `list` / `delete` / `archive` | `Environments.New` / `Get` / `Update` / `List` / `Delete` / `Archive` |
| Environment Work（自托管） | `environments.work.poller` / `stats` / `stop` | 参见 `shared/managed-agents-self-hosted-sandboxes.md` |
| Sessions | `sessions.create` / `retrieve` / `update` / `list` / `delete` / `archive` | `Sessions.New` / `Get` / `Update` / `List` / `Delete` / `Archive` |
| Session Events | `sessions.events.list` / `send` / `stream` | `Sessions.Events.List` / `Send` / `StreamEvents` |
| Session Threads | `sessions.threads.list` / `retrieve` / `archive`；`sessions.threads.events.list` / `stream` | `Sessions.Threads.List` / `Get` / `Archive`；`Sessions.Threads.Events.List` / `StreamEvents` |
| Session Resources | `sessions.resources.add` / `retrieve` / `update` / `list` / `delete` | `Sessions.Resources.Add` / `Get` / `Update` / `List` / `Delete` |
| Vaults | `vaults.create` / `retrieve` / `update` / `list` / `delete` / `archive` | `Vaults.New` / `Get` / `Update` / `List` / `Delete` / `Archive` |
| Credentials | `vaults.credentials.create` / `retrieve` / `update` / `list` / `delete` / `archive` / `mcp_oauth_validate` | `Vaults.Credentials.New` / `Get` / `Update` / `List` / `Delete` / `Archive` / `McpOauthValidate` |
| Memory Stores | `memory_stores.create` / `retrieve` / `update` / `list` / `delete` / `archive` | `MemoryStores.New` / `Get` / `Update` / `List` / `Delete` / `Archive` |
| Memories | `memory_stores.memories.create` / `retrieve` / `update` / `list` / `delete` | `MemoryStores.Memories.New` / `Get` / `Update` / `List` / `Delete` |
| Memory Versions | `memory_stores.memory_versions.list` / `retrieve` / `redact` | `MemoryStores.MemoryVersions.List` / `Get` / `Redact` |

**需要注意的命名差异：**
- Agents 和 Session Threads **没有 delete**——只有 `archive`。Archive 是**永久性的**：代理变为只读，新会话无法引用它，且没有撤销归档的操作。在归档生产环境的代理之前，请先与用户确认。Environments、Sessions、Vaults、Credentials 和 Memory Stores 同时支持 `delete` 和 `archive`；Session Resources、Files、Skills 和 Memories 仅支持 `delete`；Memory Versions 两者都不支持——只有 `redact`。
- Session resources 使用 `add`（而非 `create`）。
- Go 的事件流方法名为 `StreamEvents`（而非 `Stream`）。
- 自托管 worker **不在** `client.beta.*` 下——它来自 `anthropic.lib.environments` / `@anthropic-ai/sdk/helpers/beta/environments` 的 `EnvironmentWorker`；只有 `environments.work.poller/stats/stop` 是客户端方法。

**Agent 简写：** 创建会话时，`agent` 可以接受裸字符串（`agent="agent_abc123"`——使用最新版本）或完整的引用对象（`{type: "agent", id: "agent_abc123", version: 123}`）。

**Model 简写：** 创建代理时，`model` 可以接受裸字符串（`model="claude-opus-4-8"`——使用 `standard` 速度）或完整的配置对象（`{id: "claude-opus-4-6", speed: "fast"}`）。注意：`speed: "fast"` 仅在 Opus 4.6 上受支持。

---

## Agents

**每个流程的第一步。** 会话需要预先创建的代理——在 `managed-agents-2026-04-01` 下没有内联的代理配置。

| 方法 | 路径 | 操作 | 描述 |
| -------- | ------------------------------------------------ | ---------------- | ---------------------------------------- |
| `GET` | `/v1/agents` | ListAgents | 列出代理 |
| `POST` | `/v1/agents` | CreateAgent | 创建保存的代理配置 |
| `GET` | `/v1/agents/{agent_id}` | GetAgent | 获取代理详情 |
| `POST` | `/v1/agents/{agent_id}` | UpdateAgent | 更新代理配置 |
| `POST` | `/v1/agents/{agent_id}/archive` | ArchiveAgent | 归档代理。使其变为**只读**；已有会话可继续运行，新会话无法引用它。没有撤销归档的操作——这是最终状态。 |
| `GET` | `/v1/agents/{agent_id}/versions` | ListAgentVersions | 列出代理版本 |

## Sessions

| 方法 | 路径 | 操作 | 描述 |
| -------- | ------------------------------------------------ | ---------------- | ---------------------------------------- |
| `GET` | `/v1/sessions` | ListSessions | 列出会话（分页） |
| `POST` | `/v1/sessions` | CreateSession | 创建新会话 |
| `GET` | `/v1/sessions/{session_id}` | GetSession | 获取会话详情 |
| `POST` | `/v1/sessions/{session_id}` | UpdateSession | 更新会话 `metadata`/`title`，或 `agent.tools`/`agent.mcp_servers`/`vault_ids`（会话本地覆盖；会话必须处于 `idle` 状态）。参见 `shared/managed-agents-core.md` → 在会话中更新代理配置。 |
| `DELETE` | `/v1/sessions/{session_id}` | DeleteSession | 删除会话 |
| `POST` | `/v1/sessions/{session_id}/archive` | ArchiveSession | 归档会话 |

## Events

| 方法 | 路径 | 操作 | 描述 |
| -------- | ------------------------------------------------ | ---------------- | ---------------------------------------- |
| `GET` | `/v1/sessions/{session_id}/events` | ListEvents | 列出事件（轮询，分页） |
| `POST` | `/v1/sessions/{session_id}/events` | SendEvents | 发送事件（用户消息、工具结果） |
| `GET` | `/v1/sessions/{session_id}/events/stream` | StreamEvents | 通过 SSE 流式传输事件 |

## Session Threads

多代理会话中的每个子代理事件流。参见 `shared/managed-agents-multiagent.md`。

| 方法 | 路径 | 操作 | 描述 |
| -------- | ------------------------------------------------ | ---------------- | ---------------------------------------- |
| `GET` | `/v1/sessions/{session_id}/threads` | ListThreads | 列出线程（分页） |
| `GET` | `/v1/sessions/{session_id}/threads/{thread_id}` | GetThread | 获取单个线程（包含 `agent` 快照、`status`、`parent_thread_id`、`stats`、`usage`） |
| `POST` | `/v1/sessions/{session_id}/threads/{thread_id}/archive` | ArchiveThread | 归档线程 |
| `GET` | `/v1/sessions/{session_id}/threads/{thread_id}/events` | ListThreadEvents | 列出单个线程的历史事件（分页） |
| `GET` | `/v1/sessions/{session_id}/threads/{thread_id}/stream` | StreamThreadEvents | 通过 SSE 流式传输单个线程（SDK：`threads.events.stream`） |

## Session Resources

| 方法 | 路径 | 操作 | 描述 |
| -------- | ------------------------------------------------------- | ---------------- | ---------------------------------------- |
| `GET` | `/v1/sessions/{session_id}/resources` | ListResources | 列出附加到会话的资源 |
| `POST` | `/v1/sessions/{session_id}/resources` | AddResource | 附加 `file` 或 `github_repository` 资源（SDK 方法：`add`，而非 `create`）。`memory_store` 资源仅在创建会话时附加。 |
| `GET` | `/v1/sessions/{session_id}/resources/{resource_id}` | GetResource | 获取单个资源 |
| `POST` | `/v1/sessions/{session_id}/resources/{resource_id}` | UpdateResource | 更新资源 |
| `DELETE` | `/v1/sessions/{session_id}/resources/{resource_id}` | DeleteResource | 从会话中移除资源 |

## Environments

| 方法 | 路径 | 操作 | 描述 |
| -------- | ---------------------------------------------------------------- | -------------------- | ----------------------------------- |
| `POST`   | `/v1/environments`                                     | CreateEnvironment    | 创建环境                  |
| `GET`    | `/v1/environments`                                     | ListEnvironments     | 列出环境                   |
| `GET`    | `/v1/environments/{environment_id}`                    | GetEnvironment       | 获取环境详情             |
| `POST`   | `/v1/environments/{environment_id}`                    | UpdateEnvironment    | 更新环境                  |
| `DELETE` | `/v1/environments/{environment_id}`                    | DeleteEnvironment    | 删除环境。返回 204。 |
| `POST`   | `/v1/environments/{environment_id}/archive`            | ArchiveEnvironment   | 归档环境。使其变为**只读**；已有会话可继续运行，新会话无法引用它。没有撤销归档的操作——这是最终状态。 |
| `GET`    | `/v1/environments/{environment_id}/work/stats`         | WorkQueueStats       | 自托管工作队列深度/待处理/工作者。`x-api-key` 认证。参见 `shared/managed-agents-self-hosted-sandboxes.md`。 |
| `POST`   | `/v1/environments/{environment_id}/work/{work_id}/stop` | StopWork            | 自托管：停止已认领的工作项。`x-api-key` 认证。 |

对于 `type: "self_hosted"`，`config` 为裸 `{"type": "self_hosted"}`——`networking` 和 `packages` 不适用。

## Vaults

Vaults 存储 Anthropic 代您管理的 MCP 凭证——支持自动刷新的 OAuth 凭证或静态 bearer 令牌。通过 `vault_ids` 附加到会话。概念指南和凭证格式请参见 `managed-agents-tools.md` §Vaults。

| 方法 | 路径 | 操作 | 描述 |
| -------- | ------------------------------------------------ | ---------------- | ---------------------------------------- |
| `POST`   | `/v1/vaults`                                     | CreateVault      | 创建 vault                           |
| `GET`    | `/v1/vaults`                                     | ListVaults       | 列出 vaults                              |
| `GET`    | `/v1/vaults/{vault_id}`                          | GetVault         | 获取 vault 详情                        |
| `POST`   | `/v1/vaults/{vault_id}`                          | UpdateVault      | 更新 vault                             |
| `DELETE` | `/v1/vaults/{vault_id}`                          | DeleteVault      | 删除 vault                             |
| `POST`   | `/v1/vaults/{vault_id}/archive`                  | ArchiveVault     | 归档 vault                            |

## Credentials

Credentials 是存储在 vault 中的单个密钥。

| 方法 | 路径 | 操作 | 描述 |
| -------- | ----------------------------------------------------------------- | ------------------ | ---------------------------- |
| `POST`   | `/v1/vaults/{vault_id}/credentials`                               | CreateCredential   | 创建凭证          |
| `GET`    | `/v1/vaults/{vault_id}/credentials`                               | ListCredentials    | 列出 vault 中的凭证    |
| `GET`    | `/v1/vaults/{vault_id}/credentials/{credential_id}`               | GetCredential      | 获取凭证元数据      |
| `POST`   | `/v1/vaults/{vault_id}/credentials/{credential_id}`               | UpdateCredential   | 更新凭证            |
| `DELETE` | `/v1/vaults/{vault_id}/credentials/{credential_id}`               | DeleteCredential   | 删除凭证            |
| `POST`   | `/v1/vaults/{vault_id}/credentials/{credential_id}/archive`       | ArchiveCredential  | 归档凭证           |
| `POST`   | `/v1/vaults/{vault_id}/credentials/{credential_id}/mcp_oauth_validate` | McpOauthValidate | 验证 MCP OAuth 凭证 |

## Memory Stores

工作空间范围内的持久化记忆，可在会话之间保留。通过在 `resources[]` 中添加 `{"type": "memory_store", "memory_store_id": ...}` 条目附加到会话（仅限创建会话时）。概念指南、FUSE 挂载代理接口、前置条件和版本控制请参见 `shared/managed-agents-memory.md`。

| 方法 | 路径 | 操作 | 描述 |
| -------- | ------------------------------------------------ | ------------------ | ---------------------------------------- |
| `POST`   | `/v1/memory_stores`                              | CreateMemoryStore  | 创建 store（`name`、`description`、`metadata`） |
| `GET`    | `/v1/memory_stores`                              | ListMemoryStores   | 列出 stores（`include_archived`、`created_at_{gte,lte}`） |
| `GET`    | `/v1/memory_stores/{memory_store_id}`            | GetMemoryStore     | 获取 store 详情                        |
| `POST`   | `/v1/memory_stores/{memory_store_id}`            | UpdateMemoryStore  | 更新 store                             |
| `DELETE` | `/v1/memory_stores/{memory_store_id}`            | DeleteMemoryStore  | 删除 store                             |
| `POST`   | `/v1/memory_stores/{memory_store_id}/archive`    | ArchiveMemoryStore | 归档 store。使其变为**只读**；已有会话可继续运行，新会话无法引用它。没有撤销归档的操作。 |

## Memories

store 中的单个文本文档（每个 ≤ 100KB）。`create` 在指定 `path` 创建，如果路径已被占用则返回 `409`（`memory_path_conflict_error`，附 `conflicting_memory_id`）；`update` 通过 `mem_...` ID 进行修改（重命名和/或内容）。只有 `update` 接受 `precondition`（`{"type": "content_sha256", "content_sha256": ...}`）——不匹配时返回 `409`（`memory_precondition_failed_error`）。列表端点接受 `view: "basic"|"full"`（控制是否填充 `content`；`retrieve` 默认为 `full`）。

| 方法 | 路径 | 操作 | 描述 |
| -------- | ----------------------------------------------------------------- | -------------- | ---------------------------------------- |
| `GET`    | `/v1/memory_stores/{memory_store_id}/memories`                    | ListMemories   | 返回 `Memory | MemoryPrefix`；可通过 `path_prefix`、`depth`、`order_by`/`order` 过滤 |
| `POST`   | `/v1/memory_stores/{memory_store_id}/memories`                    | CreateMemory   | 在 `path` 创建（SDK：`memories.create`）；如果路径被占用则返回 `409 memory_path_conflict_error` |
| `GET`    | `/v1/memory_stores/{memory_store_id}/memories/{memory_id}`        | GetMemory      | 读取单个记忆（默认 `view="full"`） |
| `PATCH`  | `/v1/memory_stores/{memory_store_id}/memories/{memory_id}`        | UpdateMemory   | 按 ID 更改 `content`、`path` 或两者；可选 `precondition` |
| `DELETE` | `/v1/memory_stores/{memory_store_id}/memories/{memory_id}`        | DeleteMemory   | 删除（可选 `expected_content_sha256`） |

## Memory Versions

每次变更的不可变快照（`memver_...`）——用于审计和回滚。`operation` ∈ `created` / `modified` / `deleted`。

| 方法 | 路径 | 操作 | 描述 |
| -------- | ----------------------------------------------------------------------------- | --------------------- | ---------------------------------------- |
| `GET`    | `/v1/memory_stores/{memory_store_id}/memory_versions`                         | ListMemoryVersions    | 最新优先；可通过 `memory_id`、`operation`、`session_id`、`api_key_id`、`created_at_{gte,lte}` 过滤 |
| `GET`    | `/v1/memory_stores/{memory_store_id}/memory_versions/{version_id}`            | GetMemoryVersion      | 列出字段 + 完整 `content`             |
| `POST`   | `/v1/memory_stores/{memory_store_id}/memory_versions/{version_id}/redact`     | RedactMemoryVersion   | 清除 `content`/`content_sha256`/`content_size_bytes`/`path`；保留操作者和时间戳 |

## Files

| 方法 | 路径 | 操作 | 描述 |
| -------- | ------------------------------------------------ | ---------------- | ---------------------------------------- |
| `POST`   | `/v1/files`                            | UploadFile       | 上传文件                            |
| `GET`    | `/v1/files`                            | ListFiles        | 列出文件                               |
| `GET`    | `/v1/files/{file_id}`                  | GetFile          | 获取文件元数据（SDK 方法：`retrieve_metadata`） |
| `GET`    | `/v1/files/{file_id}/content`          | DownloadFile     | 下载文件内容                    |
| `DELETE` | `/v1/files/{file_id}`                  | DeleteFile       | 删除文件                            |

## Skills

| 方法 | 路径 | 操作 | 描述 |
| -------- | --------------------------------------------------------------- | ------------------ | ---------------------------- |
| `POST`   | `/v1/skills`                                          | CreateSkill        | 创建 skill               |
| `GET`    | `/v1/skills`                                          | ListSkills         | 列出 skills                  |
| `GET`    | `/v1/skills/{skill_id}`                               | GetSkill           | 获取 skill 详情            |
| `DELETE` | `/v1/skills/{skill_id}`                               | DeleteSkill        | 删除 skill               |
| `POST`   | `/v1/skills/{skill_id}/versions`                      | CreateVersion      | 创建 skill 版本         |
| `GET`    | `/v1/skills/{skill_id}/versions`                      | ListVersions       | 列出 skill 版本          |
| `GET`    | `/v1/skills/{skill_id}/versions/{version}`            | GetVersion         | 获取 skill 版本            |
| `DELETE` | `/v1/skills/{skill_id}/versions/{version}`            | DeleteVersion      | 删除 skill 版本         |

---

## 请求/响应模式快速参考

### CreateAgent 请求体

**始终从这里开始。** `model`、`system`、`tools`、`mcp_servers`、`skills` 是此对象上的顶层字段——它们**不**放在 session 上。

```json
{
  "name": "string (required, 1-256 chars)",
  "model": "claude-opus-4-8 (required — bare string, or {id, speed} object)",
  "description": "string (optional, up to 2048 chars)",
  "system": "string (optional, up to 100,000 chars)",
  "tools": [
    { "type": "agent_toolset_20260401" }
  ],
  "skills": [
    { "type": "anthropic", "skill_id": "xlsx" },
    { "type": "custom", "skill_id": "skill_abc123", "version": "1" }
  ],
  "mcp_servers": [
    {
      "type": "url",
      "name": "github",
      "url": "https://api.githubcopilot.com/mcp/"
    }
  ],
  "multiagent": {
    "type": "coordinator",
    "agents": [
      "agent_abc123",
      { "type": "agent", "id": "agent_def456", "version": 4 },
      { "type": "self" }
    ]
  },
  "metadata": {
    "key": "value (max 16 pairs, keys ≤64 chars, values ≤512 chars)"
  }
}
```

> 限制：`tools` 最多 128 个，`skills` 最多 20 个，`mcp_servers` 最多 20 个（名称唯一）。`multiagent.agents` 1–20 条（字符串 ID | `{type:"agent",id,version?}` | `{type:"self"}`）——参见 `shared/managed-agents-multiagent.md`。

### CreateSession 请求体

```json
{
  "agent": "agent_abc123 (required — string shorthand for latest version, or {type: \"agent\", id, version} object)",
  "environment_id": "env_abc123 (required)",
  "title": "string (optional)",
  "resources": [
    {
      "type": "github_repository",
      "url": "https://github.com/owner/repo (required)",
      "authorization_token": "ghp_... (required)",
      "mount_path": "/workspace/repo (optional — defaults to /workspace/<repo-name>)",
      "checkout": { "type": "branch", "name": "main" }
    }
  ],
  "vault_ids": ["vlt_abc123 (optional — MCP credentials with auto-refresh)"],
  "metadata": {
    "key": "value"
  }
}
```

> `agent` 字段仅接受字符串 ID 或 `{type: "agent", id, version}`——`model`/`system`/`tools` 位于 agent 上，而非此处。
>
> **`checkout`** 接受 `{type: "branch", name: "..."}` 或 `{type: "commit", sha: "..."}`。省略则使用仓库的默认分支。

### CreateEnvironment 请求体

```json
{
  "name": "string (required)",
  "description": "string (optional)",
  "config": {
    "type": "cloud | self_hosted",
    "networking": {
      "type": "unrestricted | limited (union — see SDK types)"
    },
    "packages": { }
  },
  "metadata": { "key": "value" }
}
```

### SendEvents 请求体

```json
{
  "events": [
    {
      "type": "user.message",
      "content": [
        {
          "type": "text",
          "text": "Hello"
        }
      ]
    }
  ]
}
```

### 定义 Outcome 事件

```json
{
  "type": "user.define_outcome",
  "description": "Build a DCF model for Costco in .xlsx",
  "rubric": { "type": "file", "file_id": "file_01..." },
  "max_iterations": 5
}
```

> `rubric` 为必填：`{type: "text", content}` 或 `{type: "file", file_id}`。`max_iterations` 默认为 3，最大 20。随 `outcome_id` + `processed_at` 一起返回。参见 `shared/managed-agents-outcomes.md`。

### 工具结果事件

```json
{
  "type": "user.custom_tool_result",
  "custom_tool_use_id": "sevt_abc123",
  "content": [{ "type": "text", "text": "Result data" }],
  "is_error": false
}
```

---

## 错误处理

托管代理端点使用标准的 Anthropic API 错误格式。错误以 HTTP 状态码和包含 `type`、`error` 和 `request_id` 的 JSON 体返回：

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Description of what went wrong"
  },
  "request_id": "req_011CRv1W3XQ8XpFikNYG7RnE"
}
```

向 Anthropic 报告问题时请附上 `request_id`——它可以帮助我们端到端地追踪请求。内部的 `error.type` 是以下之一：

| 状态码 | 错误类型 | 描述 |
|---|---|---|
| 400 | `invalid_request_error` | 请求格式错误或缺少必要参数 |
| 401 | `authentication_error` | API 密钥无效或缺失 |
| 403 | `permission_error` | API 密钥无权执行此操作 |
| 404 | `not_found_error` | 请求的资源不存在 |
| 409 | `invalid_request_error` | 请求与资源的当前状态冲突（例如，向已归档的会话发送消息） |
| 413 | `request_too_large` | 请求体超过最大允许大小 |
| 429 | `rate_limit_error` | 请求过于频繁——请查看速率限制请求头以确定重试时机 |
| 500 | `api_error` | 发生内部服务器错误 |
| 529 | `overloaded_error` | 服务暂时过载——请使用退避策略重试 |

请注意，`409 Conflict` 的 `error.type` 为 `"invalid_request_error"`（没有独立的 `conflict_error` 类型）；需同时检查 HTTP 状态码和 `message` 来区分冲突与其他无效请求。

---

## 速率限制

托管代理端点具有按组织的每分钟请求数（RPM）限制，与您的 [Messages API 令牌限制](https://platform.claude.com/docs/en/api/rate-limits) 相互独立。会话内的模型推理仍会消耗您组织的标准 ITPM/OTPM 限制。

| 端点组 | 范围 | RPM | 最大并发数 |
|---|---|---|---|
| 创建操作（Agents、Sessions、Vaults） | 组织 | 60 | — |
| 所有其他操作（Agents、Sessions、Vaults） | 组织 | 600 | — |
| 所有操作（Environments） | 组织 | 60 | 5 |

Files 和 Skills 端点使用标准的层级[速率限制](https://platform.claude.com/docs/en/api/rate-limits)。

当超出限制时，API 返回 `429` 状态码并附带 `rate_limit_error`（响应格式参见[错误处理](#错误处理)）以及 `retry-after` 请求头，指示等待多少秒后重试。Anthropic SDK 会读取此请求头并自动重试。
