# 托管智能体 — 事件与操控

## 事件

### 发送事件

通过 `POST /v1/sessions/{id}/events` 向会话发送事件。

| 事件类型 | 何时发送 |
| ------------------------- | --------------------------------------------------- |
| `user.message` | 发送用户消息 |
| `user.interrupt` | 在智能体运行过程中中断它 |
| `user.tool_confirmation` | 批准/拒绝工具调用（当使用 `always_ask` 策略时） |
| `user.custom_tool_result` | 提供自定义工具调用的结果 |
| `user.define_outcome` | 启动基于评分卡的迭代循环 — 见 `shared/managed-agents-outcomes.md` |

### 接收事件

三种方法：

1. **流式（SSE）**：`GET /v1/sessions/{id}/events/stream` — 实时服务器推送事件（Server-Sent Events）。**长连接** — 服务器会定期发送心跳包以保持连接活跃。
2. **轮询**：`GET /v1/sessions/{id}/events` — 分页事件列表（查询参数：`limit` 默认 1000，`page`）。**立即返回** — 这是一个普通的分页 GET 请求，不是长轮询。
3. **Webhooks**：Anthropic 将会话状态转换 POST 到你的 HTTPS 端点 — 轻量负载（仅 ID），HMAC 签名，在控制台注册。见 `shared/managed-agents-webhooks.md`。

所有接收到的事件都带有 `id`、`type` 和 `processed_at`（ISO 8601；如果尚未被智能体处理则为 `null`）。

> ⚠️ **健壮的轮询（原生 HTTP）。** 如果你绕过 SDK 自行实现轮询循环，不要依赖 `requests` 或 `httpx` 的超时作为挂钟时间上限 — 它们是**每块**读取超时，每收到一个字节就会重置。一个缓慢的响应（心跳包、卡住的块编码请求体、行为异常的代理）即使设置了 `timeout=(5, 60)` 或 `httpx.Timeout(120)`，也可能无限期阻塞调用。这两个库都没有内置的"总挂钟时间"超时。如需硬性截止时间：在循环级别跟踪 `time.monotonic()`，如果单个请求超出你的预算则断开/取消（例如通过看门狗线程，或在异步 httpx 周围使用 `asyncio.wait_for()`）。**推荐使用 SDK** — `client.beta.sessions.events.stream()` 和 `client.beta.sessions.events.list()` 能合理处理超时和重试。
>
> 如果 `GET /v1/sessions/{id}/events`（分页）在拿到响应头后挂起，你很可能误调用了 `GET /v1/sessions/{id}/events` 或者遇到了服务端卡顿 — 请报告此问题；不要将其视为客户端配置问题。

### 事件类型（接收）

事件类型使用点号表示法，按命名空间分组：

| 事件类型 | 描述 |
| --- | --- |
| `agent.message` | 智能体文本输出 |
| `agent.thinking` | 扩展思考块 |
| `agent.tool_use` | 智能体使用了内置工具（`agent_toolset_20260401`） |
| `agent.tool_result` | 内置工具的结果 |
| `agent.mcp_tool_use` | 智能体使用了 MCP 工具 |
| `agent.mcp_tool_result` | MCP 工具的结果 |
| `agent.custom_tool_use` | 智能体调用了自定义工具 — 会话进入空闲状态，你需以 `user.custom_tool_result` 响应 |
| `agent.thread_context_compacted` | 对话上下文已被压缩 |
| `session.status_idle` | 智能体已完成当前任务，正在等待输入。它可能在等待通过 `user.message` 继续工作，或被阻塞等待 `user.custom_tool_result` 或 `user.tool_confirmation`。附带的 `stop_reason` 包含关于智能体停止工作原因的更多信息。 |
| `session.status_running` | 会话已开始运行，智能体正在积极工作。 |
| `session.status_rescheduled` | 会话在发生可重试错误后正在（重新）调度，准备由编排系统接管。 |
| `session.status_terminated` | 会话已终止，进入不可逆且不可用的状态。 |
| `session.error` | 处理过程中发生错误 |
| `span.model_request_start` | 模型推理开始 |
| `span.model_request_end` | 模型推理完成 |
| `span.outcome_evaluation_start` / `_ongoing` / `_end` | 面向结果的会话的评分进度 — 见 `shared/managed-agents-outcomes.md` |
| `session.thread_created` | 子智能体线程已生成（多智能体）— 见 `shared/managed-agents-multiagent.md` |
| `session.thread_status_running` / `_idle` / `_rescheduled` / `_terminated` | 子智能体线程状态转换（多智能体）。`_idle` 携带 `stop_reason`。 |
| `agent.thread_message_sent` / `_received` | 跨线程消息，携带 `to_session_thread_id` / `from_session_thread_id`（多智能体） |

流也会回显用户发送的事件（`user.message`、`user.interrupt`、`user.tool_confirmation`、`user.custom_tool_result`、`user.define_outcome`）。

---

## 操控模式

通过事件表面驱动会话的实用模式。

### 先开流再发送

**在发送事件之前先打开流。** 流只提供*打开之后*发生的事件 — 它不会重放当前状态或历史事件。如果你先发送消息再打开流，早期事件（包括快速的状态转换）会作为一个缓冲批次到达，你将无法实时响应它们。

```ts
// ✅ 正确 — 流和发送同时进行
const [response] = await Promise.all([
  streamEvents(sessionId),   // 打开 SSE 连接
  sendMessage(sessionId, text),
]);

// ❌ 错误 — 流打开之前的事件会作为一个缓冲批次到达
await sendMessage(sessionId, text);
const response = await streamEvents(sessionId);
```

**如需完整历史记录**，使用 `GET /v1/sessions/{id}/events`（分页列表）— 流只提供从连接开始的实时事件。

### 断开后重连

**SSE 流没有重放功能。** 如果你的连接断开（httpx 读取超时、网络抖动）并重新连接，你只会收到*重连之后*发出的事件。断开期间发出的任何事件都会从流中丢失。

**合并模式：** 每次（重）连接时，将流与历史记录获取重叠，并按事件 ID 去重：

```python
def connect_with_consolidation(client, session_id):
    # 1. 先打开 SSE 流
    stream = client.beta.sessions.events.stream(session_id=session_id)

    # 2. 获取历史记录以覆盖任何间隔
    history = client.beta.sessions.events.list(
        session_id=session_id,
    )

    # 3. 先输出历史记录，然后输出流 — 按 event.id 去重
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

**你不必等待响应再发送下一条消息。** 用户事件会在服务端排队并按顺序处理。这对于用户发送快速后续消息的聊天桥接场景非常有用：

```ts
// 三条消息都进入同一个会话；智能体按顺序处理
await sendMessage(sessionId, "Summarize the README");
await sendMessage(sessionId, "Actually also check the CONTRIBUTING guide");
await sendMessage(sessionId, "And compare the two");
// 一次流式接收 — 智能体将三条消息作为连贯的轮次一并响应
```

事件可以随时发送到会话。无需等待特定的会话状态即可通过 `client.beta.sessions.events.send()` 将新事件入队。

### 中断

`interrupt` 事件**会插队**（排在任何待处理用户消息之前），并强制会话进入 `idle` 状态。用于"停止"/"算了"/"取消"等命令：

```ts
await client.beta.sessions.events.send(sessionId, {
  events: [{ type: 'interrupt' }],
});
```

智能体会在任务中途停止。它不会将中断视为一条消息 — 它只是停止。发送后续的 `user` 事件来解释接下来该做什么。如果结果评估（outcome）处于激活状态，中断还会标记 `span.outcome_evaluation_end.result: "interrupted"`（见 `shared/managed-agents-outcomes.md`）。

> **注意**：在当前实现中，中断事件的 ID 可能为空。排查问题时，请将 `processed_at` 时间戳与周围的事件 ID 结合使用。

### 事件载荷

某些事件携带了超出状态变更本身的有用元数据：

`session.status_idle` — 包含一个 `stop_reason` 字段，详细说明会话停止的原因以及用户需要采取何种进一步操作。
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

`span.model_request_end` 包含一个 `model_usage` 字段，用于成本追踪和效率分析：

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

**`agent.thread_context_compacted`** — 当对话历史被摘要以适配上下文时发出。包含 `pre_compaction_tokens` 以便了解压缩了多少内容：

```json
{
  "id": "sevt_abc123",
  "processed_at": "2026-03-24T14:05:15.787Z",
  "type": "agent.thread_context_compacted"
}
```

### 归档

当会话使用完毕后，将其归档以释放资源：

```ts
await client.beta.sessions.archive(sessionId);
```

> 归档**会话**是常规清理操作 — 会话是每次运行创建的，用完即弃。**不要将此做法推广到智能体或环境**：它们是持久的、可复用的资源，归档操作是不可逆的（无法取消归档；新建的会话无法引用它们）。见 `shared/managed-agents-overview.md` → 常见陷阱。
