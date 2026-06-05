# Managed Agents — 常见客户端模式

在驱动 Managed Agent 会话时你会编写的客户端端模式，基于实际 SDK 示例。

代码示例使用 TypeScript —— Python 和 cURL 遵循相同的结构；请参阅 `python/managed-agents/README.md` 和 `curl/managed-agents.md` 了解对应版本。

---

## 1. 无损流重连

**问题：** SSE 不支持回放。如果连接在会话中断开，简单的重连会从"现在"重新打开流，你会静默丢失中间发出的所有事件。

**解决方案：** 重连时，先通过 `events.list()` 获取完整事件历史，再消费实时流，并在实时流追上时根据事件 ID 去重。

```ts
const seenEventIds = new Set<string>()
const stream = await client.beta.sessions.events.stream(session.id)

// 流现在已打开并在服务端缓冲。先读取历史。
for await (const event of client.beta.sessions.events.list(session.id)) {
  seenEventIds.add(event.id)
  handle(event)
}

// 追踪实时流。去重仅阻止 handle() —— 即使对已见过的事件也必须运行终态检查，
// 否则历史响应中的终态事件会被 `continue` 跳过，导致循环永不退出。
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

## 2. `processed_at` —— 已排队 vs 已处理

流上的每个事件都携带 `processed_at`（ISO 8601）。对于客户端发送的事件（`user.message`、`user.interrupt`、`user.tool_confirmation`、`user.custom_tool_result`），当事件已排队但尚未被代理处理时，该字段为 `null`；一旦代理处理完毕，该字段会被填充。同一事件会在流上出现两次 —— 一次带 `processed_at: null`，一次带时间戳。

```ts
for await (const event of stream) {
  if (event.type === 'user.message') {
    if (event.processed_at == null) onQueued(event.id)
    else onProcessed(event.id, event.processed_at)
  }
}
```

利用此字段为你发送的任何内容驱动待处理 → 已确认的 UI 状态。如何将本地渲染的乐观消息映射到服务端分配的 `event.id` 取决于具体应用（通常通过 `events.send()` 的返回值或 FIFO 顺序）。

---

## 3. 中断正在运行的会话

发送 `user.interrupt` 作为普通事件。会话会继续运行直到到达安全边界，然后进入空闲状态。

```ts
await client.beta.sessions.events.send(session.id, {
  events: [{ type: 'user.interrupt' }],
})

// 持续消费直到会话真正结束 —— 参见模式 5 了解完整门控。
for await (const event of stream) {
  if (event.type === 'session.status_terminated') break
  if (
    event.type === 'session.status_idle' &&
    event.stop_reason.type !== 'requires_action'
  ) break
}
```

参考：`interrupt.ts` —— 在看到 `span.model_request_start` 的瞬间发送中断，消费到空闲状态，然后通过 `sessions.retrieve()` 验证。

---

## 4. `tool_confirmation` 往返

当代理设置了 `permission_policy: { type: 'always_ask' }` 时，对该工具的任何调用都会触发一个 `agent.tool_use` 事件，其中 `evaluated_permission === 'ask'`，并且会话进入空闲状态等待决策。使用 `user.tool_confirmation` 进行响应。

```ts
for await (const event of stream) {
  if (event.type === 'agent.tool_use' && event.evaluated_permission === 'ask') {
    await client.beta.sessions.events.send(session.id, {
      events: [{
        type: 'user.tool_confirmation',
        tool_use_id: event.id,         // 不是 toolu_ 格式的 ID —— 使用 event.id
        result: 'allow',               // 或 'deny'
        // deny_message: '...',        // 可选，仅与 result: 'deny' 一起使用
      }],
    })
  }
}
```

关键点：
- `tool_use_id` 是 `event.id`（通常是 `sevt_...`），**不是** `toolu_...` 格式的 ID。
- `result` 为 `'allow' | 'deny'`。使用 `deny_message` 告知模型你拒绝的*原因* —— 该信息会被回传至代理。
- 多个待处理工具：对每个 `evaluated_permission === 'ask'` 的 `agent.tool_use` 事件分别响应一次。

参考：`tool-permissions.ts`。

---

## 5. 正确的空闲中断门控

不要仅凭 `session.status_idle` 就中断。会话会短暂地进入空闲状态 —— 例如在并行工具执行之间、等待 `user.tool_confirmation` 时、或等待 `user.custom_tool_result` 时。仅在空闲且带有终态 `stop_reason` 时中断，或在收到 `session.status_terminated` 时中断。

```ts
for await (const event of stream) {
  handle(event)
  if (event.type === 'session.status_terminated') break
  if (event.type === 'session.status_idle') {
    if (event.stop_reason.type === 'requires_action') continue // 正在等待你 —— 处理它
    break // end_turn 或 retries_exhausted —— 均为终态
  }
}
```

`session.status_idle` 上 `stop_reason.type` 的值：
- `requires_action` —— 代理正在等待客户端事件（工具确认、自定义工具结果）。处理它，不要中断。
- `retries_exhausted` —— 终态失败。中断，然后检查 `sessions.retrieve()` 获取错误状态。
- `end_turn` —— 正常完成。

---

## 6. 空闲后状态写入的竞态条件

SSE 流发出 `session.status_idle` 的时间略早于会话的可查询状态反映该状态。在空闲时立即中断并调用 `sessions.delete()` 或 `sessions.archive()` 的客户端会间歇性地收到 400 错误，提示"无法在运行中删除/归档"。

清理前先轮询：

```ts
let s
for (let i = 0; i < 10; i++) {
  s = await client.beta.sessions.retrieve(session.id)
  if (s.status !== 'running') break
  await new Promise(r => setTimeout(r, 200))
}
if (s?.status !== 'running') {
  await client.beta.sessions.archive(session.id)
} // else: 2 秒后仍在运行 —— 不要归档，让其稳定或升级处理
```

---

## 7. 先开流，再发送

始终在发送启动事件**之前**打开流。否则代理可能在你的消费者连接之前就处理事件并发出首批事件，从而导致你错过它们。

```ts
const stream = await client.beta.sessions.events.stream(session.id)
await client.beta.sessions.events.send(session.id, {
  events: [{ type: 'user.message', content: [{ type: 'text', text: 'Hello' }] }],
})
for await (const event of stream) { /* ... */ }
```

`Promise.all([stream, send])` 这种形式也可以，但先开流更简单，且效果相同 —— 流一旦打开即开始缓冲。

---

## 8. 文件挂载注意事项

**挂载的资源拥有与你上传的文件不同的 `file_id`。** 会话创建会生成一个会话作用域的副本。

```ts
const uploaded = await client.beta.files.upload({ file })
// uploaded.id         → 原始文件
const session = await client.beta.sessions.create({
  /* ... */
  resources: [{ type: 'file', file_id: uploaded.id, mount_path: '/workspace/data.csv' }],
})
// session.resources[0].file_id !== uploaded.id  ← 不同的 ID
```

通过 `files.delete(uploaded.id)` 删除原始文件；会话作用域的副本会随会话一起被垃圾回收。`mount_path` 必须是绝对路径 —— 参见 `shared/managed-agents-environments.md`。

---

## 9. 非 MCP API 和 CLI 的密钥 —— 通过自定义工具将其保留在主机端

**问题：** 你希望代理调用需要密钥（API 密钥、令牌、服务账号凭证）的第三方 API 或运行 CLI，但目前无法在会话容器内设置环境变量，而密钥库目前仅保存 MCP 凭证 —— 它们不会暴露给容器的 shell。因此通过 `bash` 工具运行的 `curl`、已安装的 CLI 或 SDK 客户端没有一等公民的位置来读取密钥。

**解决方案：** 将需要认证的调用移至你这一端。在代理上声明一个自定义工具；当代理发出 `agent.custom_tool_use` 时，你的编排器（读取 SSE 流的进程）使用自己的凭证执行调用，并以 `user.custom_tool_result` 进行响应。容器永远不会看到密钥。

```ts
// 代理模板：声明工具，不包含凭证
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

同样的模式适用于 `gh` CLI、本地评估脚本或任何其他需要主机端认证或二进制文件的操作。

**安全说明：** 这不会暴露公共端点。`agent.custom_tool_use` 通过你的编排器已使用 Anthropic API 密钥保持打开的 SSE 流到达，而 `user.custom_tool_result` 在同一个密钥下通过 `events.send()` 返回。你的编排器是客户端，而不是服务器 —— 没有任何未经认证的端点在监听。

**不要将 API 密钥嵌入系统提示或用户消息中作为变通方案。** 提示和消息存储在会话的事件历史中，可通过 `events.list()` 返回，并包含在压缩摘要中 —— 放置在那里的密钥会在会话生命周期内持久保存并可通过 API 读取。
