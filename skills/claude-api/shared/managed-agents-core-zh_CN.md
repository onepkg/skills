# 托管智能体 — 核心概念

## 架构

托管智能体围绕四个核心概念构建：

| 概念 | 端点 | 是什么 |
|---|---|---|
| **智能体** | `/v1/agents` | 定义智能体能力和角色的持久化、版本化对象：模型、系统提示、工具、MCP 服务器、技能。**必须在开始会话前创建。** 请参阅下面的智能体部分。 |
| **会话** | `/v1/sessions` | 与智能体的有状态交互。通过 ID 引用预先创建的智能体 + 环境 + 初始指令。生成事件流。 |
| **环境** | `/v1/environments` | 定义容器配置模板的模板。 |
| **容器** | N/A | 一个隔离的计算实例，智能体的**工具**在这里执行（bash、文件操作、代码）。智能体循环不在这里运行 — 它在 Anthropic 的编排层上运行，并通过工具调用在容器上执行操作。 |

```
                       ┌─────────────────────────────────────┐
                       │  Anthropic 编排层                  │
智能体（配置）────────▶│  （智能体循环：Claude + 工具调用）  │
                       └──────────────┬──────────────────────┘
                                      │ 工具调用
                                      ▼
环境（模板）──────▶ 容器（工具执行工作区）
                                 │
                         会话 ──┤
                                 ├── 资源（文件、仓库、记忆存储 — 启动时附加）
                                 ├── 保管库 ID（MCP 凭证引用）
                                 └── 对话（事件流入/流出）
```

> **智能体创建是先决条件。** 会话通过 ID 引用预先创建的智能体 — `model`/`system`/`tools` 位于智能体对象上，永远不在会话上。每个流程都从 `POST /v1/agents` 开始。

---

## 会话生命周期

```
rescheduling → running ↔ idle → terminated
```

| 状态         | 描述                                                        |
| -------------- | ------------------------------------------------------------------ |
| `idle` | 智能体已完成当前任务，正在等待输入。它要么在等待通过 `user.message` 继续工作的输入，要么被阻塞等待 `user.custom_tool_result` 或 `user.tool_confirmation`。附带的 `stop_reason` 包含有关智能体停止的更多信息。 |
| `running` | 会话已开始运行，智能体正在积极工作。 |
| `rescheduling` | 会话在发生可重试错误后正在（重新）调度，准备被编排系统接收。 |
| `terminated` | 会话已终止，进入不可逆转且不可用的状态。  |

- 当会话为 `running` 或 `idle` 时可以发送事件。消息排队并按顺序处理。
- 当收到新事件时，智能体会从 `idle → running` 转换，然后在完成后回到 `idle`。
- 错误在流中显示为 `session.error` 事件，而不是作为状态值。

### 内置会话功能

- **上下文压缩** — 如果您接近最大上下文，API 会自动压缩会话历史以保持交互继续
- **提示缓存** — 历史重复令牌被缓存，减少处理时间和成本
- **扩展思考** — 默认开启，作为 `agent.thinking` 事件返回

### 会话操作

| 操作 | 注意 |
|---|---|
| 列表 / 获取 | 分页列表或按 ID 获取单个资源 |
| 更新 | 只有 `title` 可更新 |
| 归档 | 会话变为**只读**。不可逆转。 |
| 删除 | 永久删除会话、事件历史、容器和检查点。 |

---

## 会话

会话是环境中运行的智能体实例。

### 会话对象

API 返回的关键字段：

| 字段           | 类型     | 描述                                         |
| --------------- | -------- | --------------------------------------------------- |
| `type` | string | 总是 `"session"` |
| `id` | string | 唯一会话 ID |
| `title` | string | 人类可读的标题 |
| `status` | string | `idle`、`running`、`rescheduling`、`terminated` |
| `created_at` | string | ISO 8601 时间戳 |
| `updated_at` | string | ISO 8601 时间戳 |
| `archived_at` | string | ISO 8601 时间戳（可为空） |
| `environment_id` | string | 环境 ID |
| `agent` | object | 智能体配置 |
| `resources` | array | 附加的文件、仓库和记忆存储 |
| `metadata` | object | 用户提供的键值对（最多 8 个键） |
| `usage` | object | 令牌使用统计 |

### 创建会话

**没有智能体的会话是没有意义的。** 会话通过 ID 引用预先创建的智能体。首先通过 `agents.create()` 创建智能体，然后引用它：

```ts
// 1. 创建智能体（可重用，版本化）
const agent = await client.beta.agents.create(
  {
    name: "编码助手",
    model: "claude-opus-4-8",
    system: "你是一个有用的编码智能体。",
    tools: [{ type: "agent_toolset_20260401"}],
  },
);

// 2. 启动引用它的会话
const session = await client.beta.sessions.create(
  {
    agent: agent.id,  // 字符串简写 → 最新版本。或者：{ type: "agent", id: agent.id, version: agent.version }
    environment_id: environmentId,
    title: "Hello World 会话",
  },
);
```

**会话创建参数：**

| 字段           | 类型     | 必需 | 描述                                    |
| --------------- | -------- | -------- | ---------------------------------------------- |
| `agent`         | string 或 object | **是** | 字符串简写 `"agent_abc123"`（最新版本）或 `{type: "agent", id, version}` |
| `environment_id`| string   | **是**  | 环境 ID                                 |
| `title`         | string   | 否       | 人类可读的名称（显示在日志/仪表板中） |
| `resources`     | array    | 否       | 文件、GitHub 仓库或记忆存储，在启动时附加到容器。记忆存储只能在会话创建时添加（不能通过 `resources.add()` 添加）。 |
| `vault_ids`     | array    | 否       | 保管库 ID（`vlt_*`）— 具有自动刷新功能的 MCP 凭证。请参阅 `shared/managed-agents-tools.md` → 保管库。 |
| `metadata`      | object   | 否       | 用户提供的键值对                  |

**智能体配置字段**（传递给 `agents.create()`，而不是 `sessions.create()`）：

| 字段         | 类型     | 必需 | 描述                                    |
| ------------- | -------- | -------- | ---------------------------------------------- |
| `name`        | string   | **是**  | 人类可读的名称（1-256 个字符）              |
| `model`       | string 或 object | **是** | Claude 模型 ID（裸字符串，或 `{id, speed}` 对象）。支持所有 Claude 4.5+ 模型。 |
| `system`      | string   | 否       | 系统提示 — 定义智能体的行为（最多 100K 字符） |
| `tools`       | array    | 否       | 包含三种：(1) 预构建的 Claude 智能体工具（`agent_toolset_20260401`）、(2) MCP 工具（`mcp_toolset`）、(3) 自定义客户端工具。最多 128 个。 |
| `mcp_servers` | array    | 否       | MCP 服务器连接 — 标准化的第三方能力（例如 GitHub、Asana）。最多 20 个，名称唯一。请参阅 `shared/managed-agents-tools.md` → MCP 服务器。 |
| `skills`      | array    | 否       | 具有渐进式披露的自定义"最佳实践"上下文。最多 20 个。请参阅 `shared/managed-agents-tools.md` → 技能。 |
| `description` | string   | 否       | 智能体的描述（最多 2048 个字符）    |
| `multiagent`  | object   | 否       | `{type: "coordinator", agents: [...]}` — 此智能体可以委派的名册。请参阅 `shared/managed-agents-multiagent.md`。 |
| `metadata`    | object   | 否       | 任意键值对（最多 16 个，键 ≤64 字符，值 ≤512 字符） |

---

## 智能体

**这是每个托管智能体流程开始的地方。** 智能体对象是一个持久化、版本化的配置 — 您创建一次，然后每次启动会话时通过 ID 引用它。没有智能体 → 没有会话。

### 智能体对象

API 是**扁平的** — `model`、`system`、`tools` 等是顶级字段，不包装在 `agent:{}` 子对象中。

| 字段              | 类型     | 必需 | 描述                                        |
| ------------------ | -------- | -------- | -------------------------------------------------- |
| `name`             | string   | 是      | 人类可读的名称                                |
| `model`            | string   | 是      | Claude 模型 ID                                    |
| `system`           | string   | 否       | 系统提示                                      |
| `tools`            | array    | 否       | 智能体工具集 / MCP 工具集 / 自定义工具         |
| `mcp_servers`      | array    | 否       | MCP 服务器连接                             |
| `skills`           | array    | 否       | 技能引用（最多 20 个）                          |
| `description`      | string   | 否       | 智能体的描述                           |
| `multiagent`       | object   | 否       | 协调器名册 — 请参阅 `shared/managed-agents-multiagent.md` |
| `metadata`         | object   | 否       | 任意键值对                          |

### 生命周期：创建一次，运行多次，就地更新

智能体是一个**持久资源**，而不是每次运行的参数。预期的模式：

```
┌─ 设置（一次）────────┐     ┌─ 运行时（每次调用）──────────┐
│ agents.create()        │     │ sessions.create(             │
│   → 存储 agent_id     │ ──→ │   agent={type:..., id: ID}   │
│     在配置/环境/数据库中   │     │ )                            │
└────────────────────────┘     └──────────────────────────────┘
```

**反模式：** 在每次脚本运行的顶部调用 `agents.create()`。这会积累孤立的智能体对象，每次调用都要支付创建延迟，并且破坏了版本控制模型。如果您在按请求或按定时任务调用的函数中看到 `agents.create()`，那是错误的 — 将其提升到一次性设置并持久化 ID。

### 版本控制

每个 `POST /v1/agents/{id}`（更新）都会创建一个新的不可变版本（数字时间戳，例如 `1772585501101368014`）。智能体的历史是仅追加的 — 您不能编辑过去的版本。

**为什么要版本控制：**
- **可重现性** — 将会话固定到已知良好的配置：`{type: "agent", id, version: 3}`
- **安全迭代** — 更新智能体而不会破坏已经在旧版本上运行的会话
- **回滚** — 如果新系统提示导致回退，在调试时将会话固定回先前版本

**`version` 是可选的。** 省略它（或使用字符串简写 `agent="agent_abc123"`）以在会话创建时获取最新版本。显式传递它（`{type: "agent", id, version: N}`）以固定以实现可重现性。

**获取要固定的版本：** `agents.create()` 和 `agents.update()` 都在响应中返回 `version`。将其与 `agent_id` 一起存储。要获取现有智能体的当前最新版本：`GET /v1/agents/{id}` → `.version`。

**何时更新 vs 创建新智能体：** 当概念上是同一个智能体但行为调整时（更好的提示、额外工具），更新（`POST /v1/agents/{id}`）。当是不同的角色/目的时创建新智能体。经验法则：如果您会给它相同的 `name`，就更新。

### 智能体端点

| 操作        | 方法   | 路径                                  |
| ---------------- | -------- | ------------------------------------- |
| 创建           | `POST`   | `/v1/agents`                          |
| 列表             | `GET`    | `/v1/agents`                          |
| 获取              | `GET`    | `/v1/agents/{id}`                     |
| 更新           | `POST`   | `/v1/agents/{id}`                     |
| 归档          | `POST`   | `/v1/agents/{id}/archive`             |

> ⚠️ **归档是永久性的。** 归档使智能体变为只读：现有会话继续运行，但**新会话无法引用它**，并且无法取消归档。由于智能体没有 `delete`，这是终端生命周期状态。永远不要将归档生产智能体作为常规清理 — 先与用户确认。

### 在会话中使用智能体

通过字符串 ID（最新版本）或带有显式版本的对象引用智能体：

```python
# 字符串简写 — 使用智能体的最新版本
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment_id,
)

# 或者固定到特定版本（整数）
session = client.beta.sessions.create(
    agent={"type": "agent", "id": agent.id, "version": agent.version},
    environment_id=environment_id,
)
```

### 在会话中更新智能体配置

`sessions.update()` 可以在**现有**会话上更改 `agent.tools`、`agent.mcp_servers`（包括权限策略）和 `vault_ids`。这是一个**会话本地覆盖** — 它不会创建新的智能体版本，也不会传播回智能体对象。提供的数组是**完全替换**；要附加一个工具，`GET` 会话，修改，然后 `POST` 回去。会话必须是 `idle` — 如果正在运行则先中断。

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
