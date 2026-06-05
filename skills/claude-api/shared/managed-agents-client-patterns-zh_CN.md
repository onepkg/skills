# 托管智能体 — 常见客户端模式

驱动托管智能体会话时您将在客户端编写的模式，基于可工作的 SDK 示例。

代码示例使用 TypeScript — Python 和 cURL 遵循相同的形状；等效示例请参阅 `python/managed-agents/README.md` 和 `curl/managed-agents.md`。

---

## 1. 无损流重连

**问题：** SSE 没有重放功能。如果连接在会话中断开，简单重连会从"现在"打开流，而您会静默错过中间发出的每个事件。

**解决方案：** 重连时，在消费实时流*之前*通过 `events.list()` 获取完整事件历史，并在实时流追赶时按事件 ID 去重。

```ts
const seenEventIds = new Set<string>()
const stream = await client.beta.sessions.events.stream(session.id)

// 流现在已打开并在服务器端缓冲。先读取历史。
for await (const event of client.beta.sessions.events.list(session.id)) {
  seenEventIds.add(event.id)
  handle(event)
}

// 尾随实时流。去重只控制 handle() — 终端检查必须
// 即使是已见过的事件也要运行，否则历史响应中的终端事件
// 会被 continue 跳过，循环永远不会退出。
for await (const event of stream) {
  if (!seenEventIds.has(event.id)) {
    seenEventIds.add(event.id)
    handle(event)
  }
  if (event.type === 'session.status_terminated') break
  if (event.type === 'session.status_idle' && event.stop_reason.type !== 'requires_action') break
}
```

---

## 2. `processed_at` — 排队与已处理

流上的每个事件都带有 `processed_at`（ISO 8601）。对于客户端发送的事件（`user.message`、`user.interrupt`、`user.tool_confirmation`、`user.custom_tool_result`），当事件已排队但尚未被智能体接收时，它为 `null`，一旦被智能体处理就会填充。同一个事件会在流上出现两次 — 一次是 `processed_at: null`，一次带有时间戳。

```ts
for await (const event of stream) {
  if (event.type === 'user.message') {
    if (event.processed_at == null) onQueued(event.id)
    else onProcessed(event.id, event.processed_at)
  }
}
```

使用它来驱动您发送的任何内容的待处理 → 已确认 UI 状态。您如何将本地渲染的乐观消息映射到服务器分配的 `event.id` 是应用特定的（通常通过 `events.send()` 的返回值或 FIFO 排序）。

---

## 3. 中断正在运行的会话

将 `user.interrupt` 作为正常事件发送。会话会继续运行，直到到达安全边界，然后变为空闲。

```ts
await client.beta.sessions.events.send(session.id, {
  events: [{ type: 'user.interrupt' }],
})

// 排空直到会话真正完成 — 完整门控请参阅模式 5。
for await (const event of stream) {
  if (event.type === 'session.status_terminated') break
  if (
    event.type === 'session.status_idle' &&
    event.stop_reason.type !== 'requires_action'
  ) break
}
```

参考：`interrupt.ts` — 在看到 `span.model_request_start` 时立即发送中断，排空到空闲，然后通过 `sessions.retrieve()` 验证。

---

## 4. `tool_confirmation` 往返

当智能体有 `permission_policy: { type: 'always_ask' }` 时，对该工具的任何调用都会触发带有 `evaluated_permission === 'ask'` 的 `agent.tool_use` 事件，并且会话会在等待决定时变为空闲。用 `user.tool_confirmation` 响应。

```ts
for await (const event of stream) {
  if (event.type === 'agent.tool_use' && event.evaluated_permission === 'ask') {
    await client.beta.sessions.events.send(session.id, {
      events: [{
        type: 'user.tool_confirmation',
        tool_use_id: event.id,         // 不是 toolu_ 开头的 ID — 使用 event.id
        result: 'allow',               // 或 'deny'
        // deny_message: '...',        // 可选，仅当 result: 'deny' 时使用
      }],
    })
  }
}
```

关键点：
- `tool_use_id` 是 `event.id`（通常是 `sevt_...`），**不是** `toolu_...` ID。
- `result` 是 `'allow' | 'deny'`。使用 `deny_message` 告诉模型*为什么*您拒绝了 — 它会被回显给智能体。
- 多个待处理工具：为每个带有 `evaluated_permission === 'ask'` 的 `agent.tool_use` 事件响应一次。

参考：`tool-permissions.ts`。

---

## 5. 正确的空闲中断门

不要仅在 `session.status_idle` 时中断。会话会瞬时变为空闲 — 例如，在并行工具执行之间，等待 `user.tool_confirmation` 时，或等待 `user.custom_tool_result` 时。在带有终端 `stop_reason` 的空闲时中断，或在 `session.status_terminated` 时中断。

```ts
for await (const event of stream) {
  handle(event)
  if (event.type === 'session.status_terminated') break
  if (event.type === 'session.status_idle') {
    if (event.stop_reason.type === 'requires_action') continue // 在等待您 — 处理它
    break // end_turn 或 retries_exhausted — 两者都是终端
  }
}
```

`session.status_idle` 上的 `stop_reason.type` 值：
- `requires_action` — 智能体正在等待客户端事件（工具确认、自定义工具结果）。处理它，不要中断。
- `retries_exhausted` — 终端失败。中断，然后检查 `sessions.retrieve()` 获取错误状态。
- `end_turn` — 正常完成。

---

## 6. 后空闲状态写入竞争

SSE 流发出 `session.status_idle` 略微早于会话的可查询状态反映它。在空闲时立即中断并调用 `sessions.delete()` 或 `sessions.archive()` 的客户端会间歇性收到 400 "无法在运行时删除/归档"。

清理前轮询：

```ts
let s
for (let i = 0; i < 10; i++) {
  s = await client.beta.sessions.retrieve(session.id)
  if (s.status !== 'running') break
  await new Promise(r => setTimeout(r, 200))
}
if (s?.status !== 'running') {
  await client.beta.sessions.archive(session.id)
} // 否则：2 秒后仍在运行 — 不要归档，让它稳定下来或升级
```

---

## 7. 流优先，然后发送

始终**在**发送启动事件**之前**打开流。否则智能体可能在您的消费者附加之前处理事件并发出第一批事件，而您会错过它们。

```ts
const stream = await client.beta.sessions.events.stream(session.id)
await client.beta.sessions.events.send(session.id, {
  events: [{ type: 'user.message', content: [{ type: 'text', text: '你好' }] }],
})
for await (const event of stream) { /* ... */ }
```

`Promise.all([stream, send])` 形状也可以工作，但流优先更简单并且有相同效果 — 流在打开时就开始缓冲。

---

## 8. 文件挂载陷阱

**挂载的资源具有与您上传的文件不同的 `file_id`。** 会话创建会制作一个会话范围的副本。

```ts
const uploaded = await client.beta.files.upload({ file })
// uploaded.id         → 原始文件
const session = await client.beta.sessions.create({
  /* ... */
  resources: [{ type: 'file', file_id: uploaded.id, mount_path: '/workspace/data.csv' }],
})
// session.resources[0].file_id !== uploaded.id  ← 不同的 ID
```

通过 `files.delete(uploaded.id)` 删除原始文件；会话范围的副本会随会话一起被垃圾回收。`mount_path` 必须是绝对路径 — 请参阅 `shared/managed-agents-environments.md`。

---

## 9. 非 MCP API 和 CLI 的机密 — 通过自定义工具保留在主机端

**问题：** 您希望智能体调用第三方 API 或运行需要机密（API 密钥、令牌、服务账号凭证）的 CLI，但目前无法在会话容器内设置环境变量，并且保管库目前仅持有 MCP 凭证 — 它们不会暴露给容器的 shell。因此，通过 `bash` 工具运行的 `curl`、已安装的 CLI 或 SDK 客户端没有一流的位置可以读取机密。

**解决方案：** 将认证调用移到您这边。在智能体上声明自定义工具；当智能体发出 `agent.custom_tool_use` 时，您的编排器（正在读取 SSE 流的进程）使用自己的凭证执行调用并通过 `events.send()` 返回结果。容器永远看不到密钥。

```ts
// 智能体模板：声明工具，无凭证
tools: [{ type: 'custom', name: 'linear_graphql', input_schema: { /* query, vars */ } }]

// 编排器：使用主机端凭证处理调用
for await (const event of stream) {
  if (event.type === 'agent.custom_tool_use' && event.name === 'linear_graphql') {
    const result = await linear.request(event.input.query, event.input.vars) // 主机的密钥
    await client.beta.sessions.events.send(session.id, {
      events: [{ type: 'user.custom_tool_result', tool_use_id: event.id, result }],
    })
  }
}
```

相同的形状适用于 `gh` CLI、本地评估脚本或任何其他需要主机端认证或二进制文件的内容。

**安全注意：** 这不会暴露公共端点。`agent.custom_tool_use` 通过您的编排器已经用您的 Anthropic API 密钥打开的 SSE 流到达，而 `user.custom_tool_result` 通过相同密钥下的 `events.send()` 返回。您的编排器是客户端，不是服务器 — 没有经过认证的东西在监听。

**不要将 API 密钥嵌入系统提示或用户消息中作为变通方法。** 提示和消息存储在会话的事件历史中，由 `events.list()` 返回，并包含在压缩摘要中 — 放在那里的机密会被持久化，并且在会话的生命周期内可通过 API 读取。
