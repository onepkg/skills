# 托管智能体 — 事件与控制

## 事件

### 发送事件

通过 `POST /v1/sessions/{id}/events` 向会话发送事件。

| 事件类型                | 何时发送                                        |
| ------------------------- | --------------------------------------------------- |
| `user.message`            | 发送用户消息 |
| `user.interrupt`          | 在智能体运行时中断它 |
| `user.tool_confirmation`  | 批准/拒绝工具调用（当使用 `always_ask` 策略时） |
| `user.custom_tool_result` | 为自定义工具调用提供结果 |
| `user.define_outcome`     | 启动评分标准迭代循环 — 请参阅 `shared/managed-agents-outcomes.md` |

### 接收事件

三种方法：

1. **流式传输（SSE）**：`GET /v1/sessions/{id}/events/stream` — 实时服务器发送事件。**长寿命** — 服务器发送周期性心跳以保持连接活动。
2. **轮询**：`GET /v1/sessions/{id}/events` — 分页事件列表（查询参数：`limit` 默认 1000，`page`）。**立即返回** — 这是普通分页 GET，不是长轮询。
3. **Webhooks**：Anthropic 将会话状态转换 POST 到您的 HTTPS 端点 — 精简负载（仅 ID）、HMAC 签名、控制台注册。请参阅 `shared/managed-agents-webhooks.md`。

所有接收到的事件都带有 `id`、`type` 和 `processed_at`（ISO 8601；如果智能体尚未处理则为 `null`）。

> ⚠️ **稳健的轮询（原始 HTTP）。** 如果您绕过 SDK 并自己编写轮询循环，不要依赖 `requests` 或 `httpx` 超时作为墙上时钟上限 — 它们是**每块**读取超时，每次字节到达时重置。缓慢的响应（心跳、卡住的分块编码体、行为不当的代理）可能会无限期地保持调用阻塞，即使使用 `timeout=(5, 60)` 或 `httpx.Timeout(120)`。这两个库都没有内置的"总墙上时钟"超时。对于硬截止时间：在循环级别跟踪 `time.monotonic()`，如果单个请求超出预算则中断/取消（例如通过看门狗线程，或在 async httpx 周围使用 `asyncio.wait_for()`）。**首选 SDK** — `client.beta.sessions.events.stream()` 和 `client.beta.sessions.events.list()` 明智地处理超时 + 重试。
>
> 如果 `GET /v1/sessions/{id}/events`（分页）在头之后挂起，您很可能错误地使用了 `GET /v1/sessions/{id}/events` 或遇到了服务器端停滞 — 报告它；不要将其视为客户端配置问题。

### 事件类型（接收）

事件类型使用点表示法，按命名空间分组：

| 事件类型 | 描述 |
| --- | --- |
| `agent.message` | 智能体文本输出 |
| `agent.thinking` | 扩展思考块 |
| `agent.tool_use` | 智能体使用了内置工具（`agent_toolset_20260401`） |
| `agent.tool_result` | 内置工具的结果 |
| `agent.mcp_tool_use` | 智能体使用了 MCP 工具 |
| `agent.mcp_tool_result` | MCP 工具的结果 |
| `agent.custom_tool_use` | 智能体调用了自定义工具 — 会话变为空闲，您使用 `user.custom_tool_result` 响应 |
| `agent.thread_context_compacted` | 对话上下文已压缩 |
| `session.status_idle` | 智能体已完成当前任务，正在等待输入。它要么在等待通过 `user.message` 继续工作的输入，要么被阻塞等待 `user.custom_tool_result` 或 `user.tool_confirmation`。附带的 `stop_reason` 包含有关智能体停止的更多信息。 |
| `session.status_running` | 会话已开始运行，智能体正在积极工作。 |
| `session.status_rescheduled` | 会话在发生可重试错误后正在（重新）调度，准备被编排系统接收。 |
| `session.status_terminated` | 会话已终止，进入不可逆转且不可用的状态。  |
| `session.error` | 处理过程中发生错误 |
| `span.model_request_start` | 模型推理已开始 |
| `span.model_request_end` | 模型推理已完成 |
| `span.outcome_evaluation_start` / `_ongoing` / `_end` | 面向结果会话的评分器进度 — 请参阅 `shared/managed-agents-outcomes.md` |
| `session.thread_created` | 子智能体线程已生成（多智能体）— 请参阅 `shared/managed-agents-multiagent.md` |
| `session.thread_status_running` / `_idle` / `_rescheduled` / `_terminated` | 子智能体线程状态转换（多智能体）。`_idle` 带有 `stop_reason`。 |
| `agent.thread_message_sent` / `_received` | 跨线程消息，带有 `to_session_thread_id` / `from_session_thread_id`（多智能体） |

流还会回显用户发送的事件（`user.message`、`user.interrupt`、`user.tool_confirmation`、`user.custom_tool_result`、`user.define_outcome`）。

---

## 控制模式

通过事件界面驱动会话的实用模式。

### 流优先排序

**在发送事件之前打开流。** 流只传递在它打开*之后*发生的事件 — 它不会重放当前状态或历史事件。如果您先发送消息然后打开流，早期事件（包括快速状态转换）会作为单个批量缓冲到达，您会失去实时响应它们的能力。

```ts
// ✅ 正确 — 同时对流和发送
const [response] = await Promise.all([
  streamEvents(sessionId),   // 打开 SSE 连接
  sendMessage(sessionId, text),
]);

// ❌ 错误 — 流打开之前的事件作为单个缓冲批次到达
await sendMessage(sessionId, text);
const response = await streamEvents(sessionId);
```

**对于完整历史，** 使用 `GET /v1/sessions/{id}/events`（分页列表）— 流只从连接开始为您提供实时事件。

### 断开流后的重连

**SSE 流没有重放。** 如果您的连接断开（httpx 读取超时、网络中断）并且您重新连接，您只会获得重连*之后*发出的事件。在间隙期间发出的任何事件都会从流中丢失。

**合并模式：** 在每次（重）连时，将流与历史获取重叠并按事件 ID 去重：

```python
def connect_with_consolidation(client, session_id):
    # 1. 首先打开 SSE 流
    stream = client.beta.sessions.events.stream(session_id=session_id)

    # 2. 获取历史以覆盖任何间隙
    history = client.beta.sessions.events.list(
        session_id=session_id,
    )

    # 3. 先产生历史，然后流 — 按 event.id 去重
    seen = set()
    for ev in history.data:
        seen.add(ev.id)
        yield ev
    for ev in stream:
        if ev.id not in seen:
            seen.add(ev.id)
            yield ev
```

### 消息排队

**您不必在发送下一条消息之前等待响应。** 用户事件在服务器端排队并按顺序处理。这对于用户发送快速后续消息的聊天桥接很有用：

```ts
// 所有三个都进入一个会话；智能体按顺序处理它们
await sendMessage(sessionId, "总结 README");
await sendMessage(sessionId, "实际上还要检查 CONTRIBUTING 指南");
await sendMessage(sessionId, "并比较两者");
// 流一次 — 智能体将所有三个作为连贯轮次响应
```

事件可以随时发送到会话。无需等待特定的会话状态即可通过 `client.beta.sessions.events.send()` 排队新事件。

### 中断

`interrupt` 事件**跳过队列**（在任何待处理的用户消息之前）并将会话强制进入 `idle`。将其用于"停止" / "没关系" / "取消"命令：

```ts
await client.beta.sessions.events.send(sessionId, {
  events: [{ type: 'interrupt' }],
});
```

智能体在任务中停止。它不会将中断视为消息 — 它只是停止。发送后续 `user` 事件来解释要改为做什么。如果结果处于活动状态，中断还会标记 `span.outcome_evaluation_end.result: "interrupted"`（请参阅 `shared/managed-agents-outcomes.md`）。

> **注意**：在当前实现中，中断事件可能具有空 ID。在排除故障时，将 `processed_at` 时间戳与周围的事件 ID 一起使用。

### 事件负载

一些事件除了状态变更本身之外还带有有用的元数据：

`session.status_idle` — 包含 `stop_reason` 字段，详细说明会话停止的原因以及用户需要采取的进一步操作类型。
```json
{
  "id": "sevt_456",
  "processed_at": "2026-04-07T04:27:43.197Z",
  "stop_reason": {
    "event_ids": [
      "sevt_123"
    ],
    "type": "requires_action"
  },
  "type": "status_idle"
}
```

`span.model_request_end` 包含用于成本跟踪和效率分析的 `model_usage` 字段：

```json
{
  "type": "span.model_request_end",
  "id": "sevt_456",
  "is_error": false,
  "model_request_start_id": "sevt_123",
  "model_usage": {
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 6656,
    "input_tokens": 3571,
    "output_tokens": 727
  },
  "processed_at": "2026-04-07T04:11:32.189Z"
}
```

**`agent.thread_context_compacted`** — 在对话历史被总结以适应上下文时发出。包含 `pre_compaction_tokens`，以便您知道压缩了多少：

```json
{
  "id": "sevt_abc123",
  "processed_at": "2026-03-24T14:05:15.787Z",
  "type": "agent.thread_context_compacted"
}
```

### 归档

完成会话后，归档它以释放资源：

```ts
await client.beta.sessions.archive(sessionId);
```

> 归档**会话**是常规清理 — 会话是每次运行和一次性的。**不要将此推广到智能体或环境**：这些是持久的、可重用的资源，归档它们是永久性的（无法取消归档；新会话无法引用它们）。请参阅 `shared/managed-agents-overview.md` → 常见陷阱。
