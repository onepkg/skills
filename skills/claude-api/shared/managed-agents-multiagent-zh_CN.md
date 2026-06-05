# 托管代理 —— 多代理会话

协调器代理可以将会话中的任务委托给其他代理。所有代理**共享容器和文件系统**；每个代理在自己的**线程**中运行——线程是一个上下文隔离的事件流，具有自己的对话历史、模型、系统提示词、工具、MCP 服务器和技能（来自该代理自身的配置）。线程是持久的：协调器可以向之前调用过的子代理发送后续消息，该子代理会保留之前的轮次。

SDK 会在所有 `client.beta.{agents,sessions}.*` 调用上自动设置 `managed-agents-2026-04-01` beta 标头；多代理不需要额外的标头。

---

## 在协调器上声明成员列表

`multiagent` 是 `agents.create()` / `agents.update()` 上的**顶级字段** —— **不是** `tools[]` 条目。`agents` 列出 1–20 个成员列表条目。`sessions.create()` 没有任何变化——成员列表从协调器的配置中解析。

```python
orchestrator = client.beta.agents.create(
    name="Engineering Lead",
    model="claude-opus-4-8",
    system="You coordinate engineering work. Delegate code review to the reviewer and test writing to the test agent.",
    tools=[{"type": "agent_toolset_20260401"}],
    multiagent={
        "type": "coordinator",
        "agents": [
            reviewer.id,                                            # bare string — latest version
            {"type": "agent", "id": test_writer.id, "version": 4},  # pinned version
            {"type": "self"},                                       # the coordinator itself
        ],
    },
)

session = client.beta.sessions.create(agent=orchestrator.id, environment_id=env.id)
```

| 成员列表条目 | 形式 | 说明 |
|---|---|---|
| 字符串简写 | `"agent_abc123"` | 引用已存储代理的最新版本。 |
| 代理引用 | `{type: "agent", id, version?}` | 省略 `version` 可在协调器保存时锁定为最新版本。 |
| 自身 | `{type: "self"}` | 协调器可以生成自身的副本。 |

成员列表中最多 **20 个唯一代理**；协调器可以生成每个代理的**多个副本**。**仅支持单级委托**——深度大于 1 会被忽略。

---

## 线程

会话级事件流是**主线程**——它显示协调器的轨迹以及子代理活动的摘要视图（线程状态转换和跨线程消息，而非每个子代理的工具调用）。通过每个线程的端点深入查看特定子代理：

| 操作 | HTTP | SDK (`client.beta.sessions.threads.*`) |
|---|---|---|
| 列出线程 | `GET /v1/sessions/{sid}/threads` | `.list(session_id)` |
| 检索单个线程 | `GET /v1/sessions/{sid}/threads/{tid}` | `.retrieve(thread_id, session_id=...)` |
| 归档 | `POST /v1/sessions/{sid}/threads/{tid}/archive` | `.archive(thread_id, session_id=...)` |
| 列出线程事件 | `GET /v1/sessions/{sid}/threads/{tid}/events` | `.events.list(thread_id, session_id=...)` |
| 流式线程事件 | `GET /v1/sessions/{sid}/threads/{tid}/stream` | `.events.stream(thread_id, session_id=...)` |

每个 `SessionThread` 都包含 `id`、`status`（`running` | `idle` | `rescheduling` | `terminated`）、`agent`（代理配置的解析快照——`id`、`name`、`model`、`system`、`tools`、`skills`、`mcp_servers`、`version`）、`parent_thread_id`（主线程为 null，主线程也包含在列表中）、`archived_at` 以及可选的 `stats`/`usage`。**会话状态聚合线程状态**——如果任何线程为 `running`，则 `session.status` 为 `running`。最多 **25 个并发线程**。在耗尽每个线程的流时，在 `session.thread_status_idle` 处中断（并像处理会话级空闲一样检查其 `stop_reason`）。

---

## 多代理事件（在会话流上）

| 事件 | 负载要点 | 含义 |
|---|---|---|
| `session.thread_created` | `session_thread_id`, `agent_name` | 新线程已创建。 |
| `session.thread_status_running` | `session_thread_id`, `agent_name` | 线程开始活动。 |
| `session.thread_status_idle` | `session_thread_id`, `agent_name`, **`stop_reason`** | 线程正在等待输入。检查 `stop_reason`（与 `session.status_idle.stop_reason` 形状相同）。 |
| `session.thread_status_rescheduled` | `session_thread_id`, `agent_name` | 线程在发生可重试错误后正在重新调度。 |
| `session.thread_status_terminated` | `session_thread_id`, `agent_name` | 线程已归档或遇到致命错误。 |
| `agent.thread_message_sent` | `to_session_thread_id`, `to_agent_name`, `content` | 协调器向另一个线程发送了后续消息。 |
| `agent.thread_message_received` | `from_session_thread_id`, `from_agent_name`, `content` | 代理将其结果传递给协调器。 |

---

## 子代理线程的工具权限和自定义工具

当子代理需要你的客户端提供内容时（`always_ask` 确认，或自定义工具结果），请求会被**交叉发布到主线程**，并附带标识来源线程的 `session_thread_id`——因此你只需监听会话流即可。使用 `user.tool_confirmation`（携带 `tool_use_id`）或 `user.custom_tool_result`（携带 `custom_tool_use_id`）进行回复，并**回显来源事件中的 `session_thread_id`**（SDK 参数类型和文档字符串要求这样做）。服务器也会通过工具使用 ID 进行路由，因此回显是双重保险而非必须——但请务必包含它。

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

## 注意事项

- **不要将成员列表放在 `sessions.create()` 或 `tools[]` 中。** `multiagent` 是代理的顶级字段；先更新协调器，然后启动引用它的会话。
- **不要假设共享上下文。** 线程共享文件系统，但不共享对话历史或工具。如果协调器需要子代理对某件事采取行动，它必须在委托的消息中明确说明（或将其写入磁盘）。
- **深度大于 1 会被忽略。** 子代理自身的 `multiagent` 成员列表（如果有）不会级联——只有会话的协调器才能进行委托。

对于除 Python 之外的其他语言绑定，请 WebFetch `https://platform.claude.com/docs/en/managed-agents/multi-agent.md`（参见 `shared/live-sources.md`）。
