# 托管智能体 — 结果

**结果**将会话从*对话*提升到*工作*：您陈述"完成"的样子，并且 harness 运行迭代 → 评分 → 修改循环，直到工件满足评分标准，达到 `max_iterations`，或被中断。一个单独的**评分器**（独立上下文窗口）针对您的评分标准对每次迭代进行评分，并将按标准的差距反馈给智能体。

SDK 会在所有 `client.beta.sessions.*` 调用上自动设置 `managed-agents-2026-04-01` beta 头；结果不需要额外的头。

---

## `user.define_outcome` 事件

结果不是 `sessions.create()` 上的字段。您创建一个正常的会话，然后发送 `user.define_outcome` 事件。智能体在收到后开始工作 — **不要同时也发送 `user.message`** 来启动它。

```python
session = client.beta.sessions.create(
    agent=AGENT_ID,
    environment_id=ENVIRONMENT_ID,
    title="Costco 财务分析",
)

client.beta.sessions.events.send(
    session_id=session.id,
    events=[
        {
            "type": "user.define_outcome",
            "description": "为 Costco 构建 .xlsx 格式的 DCF 模型",
            "rubric": {"type": "file", "file_id": rubric.id},
            # 或："rubric": {"type": "text", "content": RUBRIC_MD},
            "max_iterations": 5,  # 可选；默认 3，最大 20
        }
    ],
)
```

| 字段 | 类型 | 注意 |
|---|---|---|
| `type` | `"user.define_outcome"` | |
| `description` | string | 任务。这是智能体工作的目标 — 不需要单独的 `user.message`。 |
| `rubric` | `{type: "text", content}` \| `{type: "file", file_id}` | **必需。** 带有明确、可独立评分标准的 Markdown。上传一次即可跨会话重用。 |
| `max_iterations` | int | 可选。默认 **3**，最大 **20**。 |

事件会在流上随服务器分配的 `outcome_id` 和 `processed_at` 回显。

> **编写评分标准。** 使用明确、可分级的标准（"CSV 具有数字 `price` 列"），不要凭感觉（"数据看起来不错"）— 评分器独立对每个标准进行评分，因此模糊的标准会产生嘈杂的循环。如果您没有评分标准，让 Claude 分析已知良好的工件并将该分析转化为评分标准。

---

## 结果特定事件

这些出现在标准事件流（`sessions.events.stream` / `.list`）上，与通常的 `agent.*` / `session.*` 事件一起。

| 事件 | 负载亮点 | 含义 |
|---|---|---|
| `span.outcome_evaluation_start` | `outcome_id`、`iteration`（0 索引） | 评分器开始对迭代 *N* 评分。 |
| `span.outcome_evaluation_ongoing` | `outcome_id` | 评分器运行时的心跳。评分器推理是不透明的 — 您看到的是*它正在工作*，不是*它在想什么*。 |
| `span.outcome_evaluation_end` | `outcome_evaluation_start_id`、`outcome_id`、`iteration`、`result`、`explanation`、`usage` | 评分器完成了一次迭代。`result` 决定接下来会发生什么（下表）。 |

### `span.outcome_evaluation_end.result`

| `result` | 接下来 |
|---|---|
| `satisfied` | 会话 → `idle`。此结果的终端状态。 |
| `needs_revision` | 智能体开始另一次迭代。 |
| `max_iterations_reached` | 没有更多的评分器周期。智能体可能运行最后一次修改，然后会话 → `idle`。 |
| `failed` | 会话 → `idle`。评分标准与任务根本不匹配（例如描述和评分标准矛盾）。 |
| `interrupted` | 仅在 `_start` 已触发后 `user.interrupt` 到达时发出。 |

```json
{
  "type": "span.outcome_evaluation_end",
  "id": "sevt_01jkl...",
  "outcome_evaluation_start_id": "sevt_01def...",
  "outcome_id": "outc_01a...",
  "result": "satisfied",
  "explanation": "所有 12 条标准都已满足：收入预测使用了 5 年历史数据，...",
  "iteration": 0,
  "usage": { "input_tokens": 2400, "output_tokens": 350, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 1800 },
  "processed_at": "2026-03-25T14:03:00Z"
}
```

---

## 检查状态和检索工件

**状态** — 要么监视流中的 `span.outcome_evaluation_end`，要么轮询会话并读取 `outcome_evaluations`：

```python
session = client.beta.sessions.retrieve(session.id)
for ev in session.outcome_evaluations:
    print(f"{ev.outcome_id}: {ev.result}")  # outc_01a...: satisfied
```

**工件** — 智能体写入 `/mnt/session/outputs/`。空闲后，使用带有 `scope_id=session.id` 的文件 API 获取。这与 `shared/managed-agents-environments.md` → 会话输出中记录的会话输出机制相同（包括 `files.list` 上的双 beta 头要求）。

---

## 交互规则和陷阱

- **一次一个结果。** 仅在先前的终端 `span.outcome_evaluation_end`（`satisfied` / `max_iterations_reached` / `failed` / `interrupted`）之后链接发送下一个 `user.define_outcome`。会话会跨链接结果保留历史记录。
- **引导是允许的，但可选。** 您*可以*在结果进行中发送 `user.message` 事件来推动方向，但智能体已经知道要一直工作到终端 — 不要发送"继续"提示。
- **`user.interrupt` 暂停当前结果** — 它标记 `result: "interrupted"` 并使会话保持 `idle`，准备好进行新结果或对话轮次。
- **终端后，会话可重用** — 继续对话或定义新结果。
- **结果 ≠ 会话创建字段。** 不要在 `sessions.create()` 上放置 `outcome`、`rubric` 或 `description` — 结果始终作为 `user.define_outcome` 事件发送。
- **空闲中断门不变。** 在您的排空循环中，继续使用 `event.type === 'session.status_idle' && event.stop_reason?.type !== 'requires_action'` — **不要**仅在 `span.outcome_evaluation_end` 上门控（在 `needs_revision` 时，会话会继续运行）。请参阅 `shared/managed-agents-client-patterns.md` 模式 5。

对于 Python 之外的原始 HTTP 形状和每种语言的 SDK 绑定，请 WebFetch `https://platform.claude.com/docs/en/managed-agents/define-outcomes.md`（请参阅 `shared/live-sources.md`）。
