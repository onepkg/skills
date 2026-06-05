# Managed Agents — 结果评估

**结果评估 (outcome)** 将会话从*对话*提升为*工作*：你定义"完成"的标准，然后执行系统会运行迭代 → 评分 → 修订循环，直到产物满足评估标准、达到 `max_iterations` 或被中断。独立的**评分器**（独立的上下文窗口）根据你的评估标准对每次迭代进行评分，并将各标准的差距反馈给代理。

SDK 会在所有 `client.beta.sessions.*` 调用上自动设置 `managed-agents-2026-04-01` beta 头；结果评估无需额外的头信息。

---

## `user.define_outcome` 事件

结果评估不是 `sessions.create()` 上的字段。你需要先创建一个普通会话，然后发送 `user.define_outcome` 事件。代理在收到后会立即开始工作 — **不要再同时发送 `user.message`** 来启动它。

```python
session = client.beta.sessions.create(
    agent=AGENT_ID,
    environment_id=ENVIRONMENT_ID,
    title="Financial analysis on Costco",
)

client.beta.sessions.events.send(
    session_id=session.id,
    events=[
        {
            "type": "user.define_outcome",
            "description": "Build a DCF model for Costco in .xlsx",
            "rubric": {"type": "text", "content": RUBRIC_MD},
            # or: "rubric": {"type": "file", "file_id": rubric.id}
            "max_iterations": 5,  # optional; default 3, max 20
        }
    ],
)
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `type` | `"user.define_outcome"` | |
| `description` | string | 任务描述。这是代理要完成的工作目标 — 无需单独的 `user.message`。 |
| `rubric` | `{type: "text", content}` \| `{type: "file", file_id}` | **必填。** 包含明确、可独立评分的标准的 Markdown。可通过 `client.beta.files.upload(...)`（beta `files-api-2025-04-14`）上传一次，以便在多个会话中复用。 |
| `max_iterations` | int | 可选。默认 **3**，最大 **20**。 |

该事件会在流中回显，包含服务器分配的 `outcome_id` 和 `processed_at`。

> **编写评估标准。** 使用明确、可评分的标准（"CSV 包含一个数值类型的 `price` 列"），而不是模糊的描述（"数据看起来不错"）— 评分器会独立评估每个标准，模糊的标准会产生噪声很大的循环。如果你没有评估标准，可以让 Claude 分析一个已知的优秀产物，然后将分析结果转化为评估标准。

---

## 结果评估相关事件

这些事件会出现在标准事件流（`sessions.events.stream` / `.list`）中，与常规的 `agent.*` / `session.*` 事件一起出现。

| 事件 | 负载要点 | 含义 |
|---|---|---|
| `span.outcome_evaluation_start` | `outcome_id`、`iteration`（从 0 开始） | 评分器开始对第 *N* 次迭代进行评分。 |
| `span.outcome_evaluation_ongoing` | `outcome_id` | 评分器运行期间的心跳。评分器的推理过程是不透明的 — 你只能看到*正在*运行，而看不到*具体*在想什么。 |
| `span.outcome_evaluation_end` | `outcome_evaluation_start_id`、`outcome_id`、`iteration`、`result`、`explanation`、`usage` | 评分器完成一次迭代。`result` 决定后续操作（见下表）。 |

### `span.outcome_evaluation_end.result`

| `result` | 后续操作 |
|---|---|
| `satisfied` | 会话 → `idle`。此结果评估的终态。 |
| `needs_revision` | 代理开始新一轮迭代。 |
| `max_iterations_reached` | 不再进行评分循环。代理可能会执行最后一次修订，然后会话 → `idle`。 |
| `failed` | 会话 → `idle`。评估标准从根本上与任务不匹配（例如描述和标准相互矛盾）。 |
| `interrupted` | 仅在 `_start` 已在 `user.interrupt` 到达前触发时才会发出。 |

```json
{
  "type": "span.outcome_evaluation_end",
  "id": "sevt_01jkl...",
  "outcome_evaluation_start_id": "sevt_01def...",
  "outcome_id": "outc_01a...",
  "result": "satisfied",
  "explanation": "All 12 criteria met: revenue projections use 5 years of historical data, ...",
  "iteration": 0,
  "usage": { "input_tokens": 2400, "output_tokens": 350, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 1800 },
  "processed_at": "2026-03-25T14:03:00Z"
}
```

---

## 检查状态与获取交付物

**状态** — 可以监听流中的 `span.outcome_evaluation_end` 事件，也可以轮询会话并读取 `outcome_evaluations`：

```python
session = client.beta.sessions.retrieve(session.id)
for ev in session.outcome_evaluations:
    print(f"{ev.outcome_id}: {ev.result}")  # outc_01a...: satisfied
```

**交付物** — 代理会写入 `/mnt/session/outputs/`。当会话进入空闲状态后，可通过 Files API 使用 `scope_id=session.id` 获取。这与 `shared/managed-agents-environments.md` → Session outputs（包括 `files.list` 上的双 beta 头要求）中记录的会话输出机制相同。

---

## 交互规则与注意事项

- **一次只能有一个结果评估。** 等前一个结果评估的终态 `span.outcome_evaluation_end`（`satisfied` / `max_iterations_reached` / `failed` / `interrupted`）到达后再发送下一个 `user.define_outcome`。会话会在链式结果评估之间保留历史记录。
- **可以引导，但不是必须。** 你*可以*在结果评估过程中发送 `user.message` 事件来调整方向，但代理本身已经知道要继续工作直到终态 — 不要发送"继续"的提示。
- **`user.interrupt` 会暂停当前结果评估** — 它将 `result` 标记为 `"interrupted"` 并使会话进入 `idle` 状态，准备好进行新的结果评估或对话轮次。
- **终态后会话可复用** — 可以继续对话，也可以定义新的结果评估。
- **结果评估 ≠ 会话创建字段。** 不要在 `sessions.create()` 中放入 `outcome`、`rubric` 或 `description` — 结果评估始终通过 `user.define_outcome` 事件发送。
- **空闲中断判断条件不变。** 在你的 drain 循环中，继续使用 `event.type === 'session.status_idle' && event.stop_reason?.type !== 'requires_action'` — 不要**仅**依赖 `span.outcome_evaluation_end` 来判断（在 `needs_revision` 情况下会话仍在运行）。参见 `shared/managed-agents-client-patterns.md` 模式 5。

有关原始 HTTP 格式及 Python 之外的其他语言 SDK 绑定，请使用 WebFetch 访问 `https://platform.claude.com/docs/en/managed-agents/define-outcomes.md`（参见 `shared/live-sources.md`）。
