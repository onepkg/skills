# Managed Agents — 核心概念

## 架构

Managed Agents 围绕四个核心概念构建：

| 概念 | 端点 | 说明 |
|---|---|---|
| **Agent** | `/v1/agents` | 一个持久化、版本化的对象，定义了代理的能力和身份：模型、系统提示词、工具、MCP 服务器、技能。**必须在启动会话之前创建。** 请参见下面的 Agent 章节。 |
| **Session** | `/v1/sessions` | 与代理的有状态交互。通过 ID + 环境 + 初始指令引用预先创建的代理。生成事件流。 |
| **Environment** | `/v1/environments` | 定义容器配置的模板。 |
| **Container** | N/A | 隔离的计算实例，代理的**工具**（bash、文件操作、代码）在此执行。代理循环不在此处运行——它在 Anthropic 的编排层运行，并通过工具调用对容器进行操作。 |

```
                       ┌─────────────────────────────────────┐
                       │  Anthropic orchestration layer      │
Agent (config) ───────▶│  (agent loop: Claude + tool calls)  │
                       └──────────────┬──────────────────────┘
                                      │ tool calls
                                      ▼
Environment (template) ──▶ Container (tool execution workspace)
                                 │
                         Session ─┤
                                 ├── Resources (files, repos, memory stores — attached at startup)
                                 ├── Vault IDs (MCP credential references)
                                 └── Conversation (event stream in/out)
```

> **Agent 创建是前置条件。** Session 通过 ID 引用预先创建的 Agent——`model`/`system`/`tools` 位于 agent 对象上，而非 session 上。每个流程都以 `POST /v1/agents` 开始。

---

## Session 生命周期

```
rescheduling → running ↔ idle → terminated
```

| 状态         | 描述                                                        |
| -------------- | ------------------------------------------------------------------ |
| `idle` | Agent 已完成当前任务，正在等待输入。它要么等待通过 `user.message` 继续工作的输入，要么被阻塞等待 `user.custom_tool_result` 或 `user.tool_confirmation`。附带的 `stop_reason` 包含有关 Agent 停止工作的更多信息。 |
| `running` | Session 已开始运行，Agent 正在积极执行工作。 |
| `rescheduling` | Session 在发生可重试错误后正在（重新）调度，准备由编排系统接管。 |
| `terminated` | Session 已终止，进入不可逆且不可用的状态。  |

- 当会话处于 `running` 或 `idle` 状态时可以发送事件。消息按顺序排队和处理。
- 代理在接收到新事件时从 `idle` 转换为 `running`，完成后返回 `idle`。
- 错误在流中以 `session.error` 事件形式呈现，而非状态值。

### 内置会话功能

- **Context compaction（上下文压缩）** — 如果接近最大上下文，API 会自动压缩会话历史以保持交互持续
- **Prompt caching（提示缓存）** — 历史重复的 token 会被缓存，从而减少处理时间和成本
- **Extended thinking（扩展思考）** — 默认开启，以 `agent.thinking` 事件返回

### Session 操作

| 操作 | 说明 |
|---|---|
| 列出/获取 | 分页列表或按 ID 获取单个资源 |
| 更新 | 仅 `title` 可更新 |
| 归档 | Session 变为**只读**。不可逆。 |
| 删除 | 永久删除会话、事件历史、容器和检查点。 |

---

## Sessions

Session 是在环境中运行的代理实例。

### Session 对象

API 返回的关键字段：

| 字段           | 类型     | 描述                                         |
| --------------- | -------- | --------------------------------------------------- |
| `type` | string | 始终为 `"session"` |
| `id` | string | 唯一会话 ID |
| `title` | string | 人类可读的标题 |
| `status` | string | `idle`、`running`、`rescheduling`、`terminated` |
| `created_at` | string | ISO 8601 时间戳 |
| `updated_at` | string | ISO 8601 时间戳 |
| `archived_at` | string | ISO 8601 时间戳（可为空） |
| `environment_id` | string | 环境 ID |
| `agent` | object | Agent 配置 |
| `resources` | array | 附加的文件、仓库和记忆存储 |
| `metadata` | object | 用户提供的键值对（最多 8 个键） |
| `usage` | object | Token 使用统计 |

### 创建 Session

**没有 agent，session 就毫无意义。** Session 通过 ID 引用预先创建的 agent。首先通过 `agents.create()` 创建 agent，然后引用它：

```ts
// 1. Create the agent (reusable, versioned)
const agent = await client.beta.agents.create(
  {
    name: "Coding Assistant",
    model: "claude-opus-4-8",
    system: "You are a helpful coding agent.",
    tools: [{ type: "agent_toolset_20260401"}],
  },
);

// 2. Start a session that references it
const session = await client.beta.sessions.create(
  {
    agent: agent.id,  // string shorthand → latest version. Or: { type: "agent", id: agent.id, version: agent.version }
    environment_id: environmentId,
    title: "Hello World Session",
  },
);
```

**创建 Session 的参数：**

| 字段           | 类型     | 是否必填 | 描述                                    |
| --------------- | -------- | -------- | ---------------------------------------------- |
| `agent`         | string 或 object | **是** | 字符串简写 `"agent_abc123"`（最新版本）或 `{type: "agent", id, version}` |
| `environment_id`| string   | **是**  | 环境 ID                                 |
| `title`         | string   | 否       | 人类可读的名称（出现在日志/仪表板中） |
| `resources`     | array    | 否       | 启动时附加到容器的文件、GitHub 仓库或记忆存储。记忆存储仅在创建会话时可用（不能通过 `resources.add()` 添加）。 |
| `vault_ids`     | array    | 否       | Vault ID（`vlt_*`）— 带自动刷新的 MCP 凭据。参见 `shared/managed-agents-tools.md` → Vaults。 |
| `metadata`      | object   | 否       | 用户提供的键值对                  |

**Agent 配置字段**（传递给 `agents.create()`，而非 `sessions.create()`）：

| 字段         | 类型     | 是否必填 | 描述                                    |
| ------------- | -------- | -------- | ---------------------------------------------- |
| `name`        | string   | **是**  | 人类可读的名称（1-256 个字符）              |
| `model`       | string 或 object | **是** | Claude 模型 ID（纯字符串或 `{id, speed}` 对象）。支持所有 Claude 4.5+ 模型。 |
| `system`      | string   | 否       | 系统提示词——定义 Agent 的行为（最多 100K 个字符） |
| `tools`       | array    | 否       | 包含三种类型：(1) 预构建的 Claude Agent 工具（`agent_toolset_20260401`），(2) MCP 工具（`mcp_toolset`），(3) 自定义客户端工具。最多 128 个。 |
| `mcp_servers` | array    | 否       | MCP 服务器连接——标准化的第三方能力（例如 GitHub、Asana）。最多 20 个，名称唯一。参见 `shared/managed-agents-tools.md` → MCP Servers。 |
| `skills`      | array    | 否       | 带有渐进式披露的定制"最佳实践"上下文。最多 20 个。参见 `shared/managed-agents-tools.md` → Skills。 |
| `description` | string   | 否       | Agent 的描述（最多 2048 个字符）    |
| `multiagent`  | object   | 否       | `{type: "coordinator", agents: [...]}` — 此代理可以委托给的成员列表。参见 `shared/managed-agents-multiagent.md`。 |
| `metadata`    | object   | 否       | 任意键值对（最多 16 个，键 ≤64 字符，值 ≤512 字符） |

---

## Agents

**这是每个 Managed Agents 流程的起点。** Agent 对象是持久化、版本化的配置——你只需创建一次，然后在每次启动会话时通过 ID 引用它。没有 agent 就没有 session。

### Agent 对象

API 是**扁平**的——`model`、`system`、`tools` 等是顶层字段，不包装在 `agent:{}` 子对象中。

| 字段              | 类型     | 是否必填 | 描述                                        |
| ------------------ | -------- | -------- | -------------------------------------------------- |
| `name`             | string   | 是      | 人类可读的名称                                |
| `model`            | string   | 是      | Claude 模型 ID                                    |
| `system`           | string   | 否       | 系统提示词                                      |
| `tools`            | array    | 否       | Agent 工具集 / MCP 工具集 / 自定义工具         |
| `mcp_servers`      | array    | 否       | MCP 服务器连接                             |
| `skills`           | array    | 否       | Skill 引用（最多 20 个）                          |
| `description`      | string   | 否       | Agent 的描述                           |
| `multiagent`       | object   | 否       | 协调器成员列表——参见 `shared/managed-agents-multiagent.md` |
| `metadata`         | object   | 否       | 任意键值对                          |

### 生命周期：一次创建，多次运行，原地更新

Agent 是一个**持久化资源**，而非每次运行的参数。预期的模式：

```
┌─ setup (once) ─────────┐     ┌─ runtime (every invocation) ─┐
│ agents.create()        │     │ sessions.create(             │
│   → store agent_id     │ ──→ │   agent={type:..., id: ID}   │
│     in config/env/db   │     │ )                            │
└────────────────────────┘     └──────────────────────────────┘
```

**反模式：** 在每次脚本运行的开头调用 `agents.create()`。这会导致积累孤立的 agent 对象，每次调用都会产生创建延迟，并且破坏了版本化模型。如果你在每次请求或每次 cron 执行时调用的函数中看到 `agents.create()`，那是不正确的——应将其提升为一次性设置并持久化 ID。

### 版本控制

每次 `POST /v1/agents/{id}`（更新）都会创建一个新的不可变版本（数字时间戳，例如 `1772585501101368014`）。Agent 的历史记录是仅追加的——你不能编辑过去的版本。

**为什么要版本化：**
- **可复现性** — 将会话固定到已知良好的配置：`{type: "agent", id, version: 3}`
- **安全迭代** — 更新 agent 而不影响已在旧版本上运行的会话
- **回滚** — 如果新的系统提示词出现退化，在调试时将新会话固定回之前的版本

**`version` 是可选的。** 省略它（或使用字符串简写 `agent="agent_abc123"`）将在创建会话时获取最新版本。显式传递它（`{type: "agent", id, version: N}`）以固定版本确保可复现性。

**获取要固定的版本：** `agents.create()` 和 `agents.update()` 都会在响应中返回 `version`。将其与 `agent_id` 一起存储。要获取现有 agent 的当前最新版本：`GET /v1/agents/{id}` → `.version`。

**何时更新 vs 创建新 Agent：** 当概念上是同一个 agent 但行为有所调整（更好的提示词、额外的工具）时，进行更新（`POST /v1/agents/{id}`）。当它是一个不同身份/目的时，创建新 agent。经验法则：如果你会为它指定相同的 `name`，就更新。

### Agent 端点

| 操作        | 方法   | 路径                                  |
| ---------------- | -------- | ------------------------------------- |
| 创建           | `POST`   | `/v1/agents`                          |
| 列出             | `GET`    | `/v1/agents`                          |
| 获取              | `GET`    | `/v1/agents/{id}`                     |
| 更新           | `POST`   | `/v1/agents/{id}`                     |
| 归档          | `POST`   | `/v1/agents/{id}/archive`             |

> ⚠️ **归档是永久性的。** 归档使 agent 变为只读：现有会话可以继续运行，但**新会话无法引用它**，且无法取消归档。由于 agent 没有 `delete`，这是终态生命周期状态。切勿将归档作为常规清理手段用于生产环境中的 agent——请先与用户确认。

### 在 Session 中使用 Agent

通过字符串 ID（最新版本）或带有显式版本的对象来引用 agent：

```python
# String shorthand — uses the agent's latest version
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment_id,
)

# Or pin to a specific version (int)
session = client.beta.sessions.create(
    agent={"type": "agent", "id": agent.id, "version": agent.version},
    environment_id=environment_id,
)
```

### 在会话中更新 Agent 配置

`sessions.update()` 可以在**现有**会话上更改 `agent.tools`、`agent.mcp_servers`（包括权限策略）和 `vault_ids`。这是一个**会话级别的本地覆盖**——它不会创建新的 agent 版本，也不会传播回 agent 对象。提供的数组是**完全替换**；要追加一个工具，请先 `GET` 会话，修改，然后 `POST` 回去。会话必须处于 `idle` 状态——如果正在运行请先中断。

```python
client.beta.sessions.update(
    session.id,
    agent={
        "tools": [
            {"type": "agent_toolset_20260401"},
            {"type": "mcp_toolset", "mcp_server_name": "linear"},
        ],
        "mcp_servers": [{"type": "url", "name": "linear", "url": "https://mcp.linear.app/sse"}],
    },
    vault_ids=["vlt_..."],
)
```
