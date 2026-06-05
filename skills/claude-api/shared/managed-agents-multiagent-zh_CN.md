# 托管智能体 — 多智能体会话

协调器智能体可以在一个会话内委派给其他智能体。所有智能体**共享容器和文件系统**；每个都在自己的**线程**中运行 — 一个上下文隔离的事件流，带有自己的对话历史、模型、系统提示、工具、MCP 服务器和技能（来自该智能体自己的配置）。线程是持久的：协调器可以向它之前调用过的子智能体发送后续消息，并且该子智能体保留其先前的轮次。

SDK 会在所有 `client.beta.{agents,sessions}.*` 调用上自动设置 `managed-agents-2026-04-01` beta 头；多智能体不需要额外的头。

---

## 在协调器上声明名册

`multiagent` 是 `agents.create()` / `agents.update()` 上的**顶级字段** — **不是** `tools[]` 条目。`agents` 列出 1–20 个名册条目。`sessions.create()` 上没有任何变化 — 名册从协调器的配置中解析。

```python
orchestrator = client.beta.agents.create(
    name="工程主管",
    model="claude-opus-4-8",
    system="你协调工程工作。将代码审查委派给审查员，将测试编写委派给测试智能体。",
    tools=[{"type": "agent_toolset_20260401"}],
    multiagent={
        "type": "coordinator",
        "agents": [
            reviewer.id,                                            # 裸字符串 — 最新版本
            {"type": "agent", "id": test_writer.id, "version": 4},  # 固定版本
            {"type": "self"},                                       # 协调器本身
        ],
    },
)

session = client.beta.sessions.create(agent=orchestrator.id, environment_id=env.id)
```

| 名册条目 | 形状 | 注意 |
|---|---|---|
| 字符串简写 | `"agent_abc123"` | 引用存储智能体的最新版本。 |
| 智能体引用 | `{type: "agent", id, version?}` | 省略 `version` 以在协调器保存时固定最新版本。 |
| Self | `{type: "self"}` | 协调器可以生成自己的副本。 |

名册中最多 **20 个唯一智能体**；协调器可以生成每个智能体的**多个副本**。**仅一级委派** — 深度 > 1 会被忽略。

---

## 线程

会话级事件流是**主线程** — 它显示协调器的跟踪加上子智能体活动的压缩视图（线程状态转换和跨线程消息，不是每个子智能体工具调用）。通过每个线程端点深入查看特定子智能体：

| 操作 | HTTP | SDK (`client.beta.sessions.threads.*`) |
|---|---|---|
| 列出线程 | `GET /v1/sessions/{sid}/threads` | `.list(session_id)` |
| 检索一个 | `GET /v1/sessions/{sid}/threads/{tid}` | `.retrieve(thread_id, session_id=...)` |
| 归档 | `POST /v1/sessions/{sid}/threads/{tid}/archive` | `.archive(thread_id, session_id=...)` |
| 列出线程事件 | `GET /v1/sessions/{sid}/threads/{tid}/events` | `.events.list(thread_id, session_id=...)` |
| 流式传输线程事件 | `GET /v1/sessions/{sid}/threads/{tid}/stream` | `.events.stream(thread_id, session_id=...)` |

每个 `SessionThread` 带有 `id`、`status`（`running` | `idle` | `rescheduling` | `terminated`）、`agent`（智能体配置的已解析快照 — `id`、`name`、`model`、`system`、`tools`、`skills`、`mcp_servers`、`version`）、`parent_thread_id`（对于主线程为 null，它包含在列表中）、`archived_at`，以及可选的 `stats`/`usage`。**会话状态聚合线程状态** — 如果任何线程是 `running`，则 `session.status` 是 `running`。最多 **25 个并发线程**。在排空每个线程流时，在 `session.thread_status_idle` 时中断（并像检查会话级空闲一样检查它的 `stop_reason`）。

---

## 多智能体事件（会话流上）

| 事件 | 负载亮点 | 含义 |
|---|---|---|
| `session.thread_created` | `session_thread_id`、`agent_name` | 创建了新线程。 |
| `session.thread_status_running` | `session_thread_id`、`agent_name` | 线程开始活动。 |
| `session.thread_status_idle` | `session_thread_id`、`agent_name`、**`stop_reason`** | 线程正在等待输入。检查 `stop_reason`（形状与 `session.status_idle.stop_reason` 相同）。 |
| `session.thread_status_rescheduled` | `session_thread_id`、`agent_name` | 线程在可重试错误后正在重新调度。 |
| `session.thread_status_terminated` | `session_thread_id`、`agent_name` | 线程已归档或遇到终端错误。 |
| `agent.thread_message_sent` | `to_session_thread_id`、`to_agent_name`、`content` | 协调器向另一个线程发送了后续消息。 |
| `agent.thread_message_received` | `from_session_thread_id`、`from_agent_name`、`content` | 一个智能体向协调器传递了其结果。 |

---

## 来自子智能体线程的工具权限和自定义工具

当子智能体需要您的客户端时（`always_ask` 确认，或自定义工具结果），请求会**交叉发布到主线程**，带有标识始发线程的 `session_thread_id` — 因此您只需要监视会话流。用 `user.tool_confirmation`（携带 `tool_use_id`）或 `user.custom_tool_result`（携带 `custom_tool_use_id`）回复，**并回显原始事件的 `session_thread_id`**（SDK 参数类型和文档字符串期望它）。服务器也通过工具使用 ID 路由，所以回显是双重保险而不是负载承载 — 但仍要包含它。

```python
for event_id in stop.event_ids:
    pending = events_by_id[event_id]
    confirmation = {
        "type": "user.tool_confirmation",
        "tool_use_id": event_id,
        "result": "allow",
    }
    if pending.session_thread_id is not None:
        confirmation["session_thread_id"] = pending.session_thread_id
    client.beta.sessions.events.send(session.id, events=[confirmation])
```

相同的模式适用于 `user.custom_tool_result`。

---

## 陷阱

- **不要把名册放在 `sessions.create()` 或 `tools[]` 中。** `multiagent` 是顶级智能体字段；更新协调器，然后启动引用它的会话。
- **不要假设共享上下文。** 线程共享文件系统，但不共享对话历史或工具。如果协调器需要子智能体对某物采取行动，它必须在委派消息中说明（或将其写入磁盘）。
- **深度 > 1 被忽略。** 子智能体自己的 `multiagent` 名册（如果有的话）不会级联 — 只有会话的协调器可以委派。

对于 Python 之外的每种语言绑定，请 WebFetch `https://platform.claude.com/docs/en/managed-agents/multi-agent.md`（请参阅 `shared/live-sources.md`）。
