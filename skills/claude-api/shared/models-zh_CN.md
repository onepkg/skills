# Claude 模型目录

**只使用本文件中列出的精确模型 ID。** 切勿猜测或构造模型 ID — 错误的 ID 会导致 API 错误。尽可能使用别名。如需最新信息，请通过 WebFetch 获取 `shared/live-sources.md` 中的 Models Overview URL，或直接查询 Models API（参见下面的编程方式发现模型）。

## 编程方式发现模型

对于**实时**能力数据 — 上下文窗口、最大输出 token、功能支持（思考、视觉、努力程度、结构化输出等）— 请查询 Models API，而不是依赖下面的缓存表格。当用户询问"X 的上下文窗口是多少"、"模型 X 是否支持视觉/思考/努力程度"、"哪些模型支持功能 Y"或希望在运行时根据能力选择模型时，使用此方式。

```python
m = client.models.retrieve("claude-opus-4-8")
m.id                 # "claude-opus-4-8"
m.display_name       # "Claude Opus 4.8"
m.max_input_tokens   # context window (int)
m.max_tokens         # max output tokens (int)

# capabilities is an untyped nested dict — bracket access, check ["supported"] at the leaf
caps = m.capabilities
caps["image_input"]["supported"]                       # vision
caps["thinking"]["types"]["adaptive"]["supported"]     # adaptive thinking
caps["effort"]["max"]["supported"]                     # effort: max (also low/medium/high)
caps["structured_outputs"]["supported"]
caps["context_management"]["compact_20260112"]["supported"]

# filter across all models — iterate the page object directly (auto-paginates); do NOT use .data
[m for m in client.models.list()
 if m.capabilities["thinking"]["types"]["adaptive"]["supported"]
 and m.max_input_tokens >= 200_000]
```

顶层字段（`id`、`display_name`、`max_input_tokens`、`max_tokens`）是类型化属性。`capabilities` 是一个字典 — 使用方括号访问，而非属性访问。API 为每个模型返回完整的能力树，每个叶子节点带有 `supported: true/false`，因此方括号链是安全的，无需 `.get()` 保护。TypeScript SDK：方法名相同，迭代时也会自动分页。

### 原始 HTTP 请求

```bash
curl https://api.anthropic.com/v1/models/claude-opus-4-8 \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

```json
{
  "id": "claude-opus-4-8",
  "display_name": "Claude Opus 4.8",
  "max_input_tokens": 1000000,
  "max_tokens": 128000,
  "capabilities": {
    "image_input": {"supported": true},
    "structured_outputs": {"supported": true},
    "thinking": {"supported": true, "types": {"enabled": {"supported": false}, "adaptive": {"supported": true}}},
    "effort": {"supported": true, "low": {"supported": true}, …, "max": {"supported": true}},
    …
  }
}
```

## 当前模型（推荐）

| 友好名称         | 别名（推荐使用）  | 完整 ID                        | 上下文         | 最大输出     | 状态   |
|-------------------|---------------------|-------------------------------|----------------|------------|--------|
| Claude Opus 4.8   | `claude-opus-4-8`   | —                             | 1M             | 128K       | 活跃 |
| Claude Opus 4.7   | `claude-opus-4-7`   | —                             | 1M             | 128K       | 活跃 |
| Claude Opus 4.6   | `claude-opus-4-6`   | —                             | 1M             | 128K       | 活跃 |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | -                             | 1M             | 64K        | 活跃 |
| Claude Haiku 4.5  | `claude-haiku-4-5`  | `claude-haiku-4-5-20251001`   | 200K           | 64K        | 活跃 |

### 模型描述
- **Claude Opus 4.8** — 迄今为止最强大的 Claude 模型 — 高度自主，在长周期智能体工作、知识工作和记忆方面处于最先进水平；写作风格更清晰、更温暖。API 表面与 Opus 4.7 相同（仅支持自适应思考；取消了采样参数和 `budget_tokens`）。1M 上下文窗口，标准 API 定价（无需长上下文溢价）。参见 `shared/model-migration.md` → 迁移至 Opus 4.8 — 从 4.7 迁移到 4.8 只需替换模型 ID 并重新调整提示词，无新的破坏性变更。
- **Claude Opus 4.7** — 上一代 Opus。高度自主；在长周期智能体工作、知识工作、视觉和记忆方面表现出色。仅支持自适应思考；取消了采样参数和 `budget_tokens`。1M 上下文窗口。参见 `shared/model-migration.md` → 迁移至 Opus 4.7。
- **Claude Opus 4.6** — 较旧的 Opus。支持自适应思考（推荐），128K 最大输出 token（大输出需要流式传输）。1M 上下文窗口。
- **Claude Sonnet 4.6** — 速度与智能的最佳结合。支持自适应思考（推荐）。1M 上下文窗口。64K 最大输出 token。
- **Claude Haiku 4.5** — 针对简单任务最快且最具成本效益的模型。

## 旧版模型（仍活跃）

| 友好名称         | 别名（推荐使用）  | 完整 ID                        | 状态   |
|-------------------|---------------------|-------------------------------|--------|
| Claude Opus 4.5   | `claude-opus-4-5`   | `claude-opus-4-5-20251101`    | 活跃 |
| Claude Opus 4.1   | `claude-opus-4-1`   | `claude-opus-4-1-20250805`    | 活跃 |
| Claude Sonnet 4.5 | `claude-sonnet-4-5` | `claude-sonnet-4-5-20250929`  | 活跃 |
| Claude Sonnet 4   | `claude-sonnet-4-0` | `claude-sonnet-4-20250514`    | 活跃 |
| Claude Opus 4     | `claude-opus-4-0`   | `claude-opus-4-20250514`      | 活跃 |

## 已弃用模型（即将停用）

| 友好名称     | 别名（推荐使用） | 完整 ID                       | 状态         | 停用日期      |
|---------------|-----------------|-------------------------------|------------|--------------|
| Claude Haiku 3    | —                   | `claude-3-haiku-20240307`     | 已弃用 | 2026 年 4 月 19 日 |

## 已退役模型（不再可用）

| 友好名称         | 完整 ID                        | 退役日期     |
|-------------------|-------------------------------|-------------|
| Claude Sonnet 3.7 | `claude-3-7-sonnet-20250219`  | 2026 年 2 月 19 日 |
| Claude Haiku 3.5  | `claude-3-5-haiku-20241022`   | 2026 年 2 月 19 日 |
| Claude Opus 3     | `claude-3-opus-20240229`      | 2026 年 1 月 5 日 |
| Claude Sonnet 3.5 | `claude-3-5-sonnet-20241022`  | 2025 年 10 月 28 日 |
| Claude Sonnet 3.5 | `claude-3-5-sonnet-20240620`  | 2025 年 10 月 28 日 |
| Claude Sonnet 3   | `claude-3-sonnet-20240229`    | 2025 年 7 月 21 日 |
| Claude 2.1        | `claude-2.1`                  | 2025 年 7 月 21 日 |
| Claude 2.0        | `claude-2.0`                  | 2025 年 7 月 21 日 |

## 解析用户请求

当用户按名称请求模型时，使用此表格查找正确的模型 ID：

| 用户说...                              | 使用此模型 ID              |
|-------------------------------------------|--------------------------------|
| "opus"、"most powerful"                   | `claude-opus-4-8`              |
| "opus 4.8"                                | `claude-opus-4-8`              |
| "opus 4.7"                                | `claude-opus-4-7`              |
| "opus 4.6"                                | `claude-opus-4-6`              |
| "opus 4.5"                                | `claude-opus-4-5`              |
| "opus 4.1"                                | `claude-opus-4-1`              |
| "opus 4"、"opus 4.0"                      | `claude-opus-4-0`（已弃用 — 建议使用 `claude-opus-4-8`） |
| "sonnet"、"balanced"                      | `claude-sonnet-4-6`            |
| "sonnet 4.6"                              | `claude-sonnet-4-6`            |
| "sonnet 4.5"                              | `claude-sonnet-4-5`            |
| "sonnet 4"、"sonnet 4.0"                  | `claude-sonnet-4-0`            |
| "sonnet 3.7"                              | 已退役 — 建议使用 `claude-sonnet-4-5` |
| "sonnet 3.5"                              | 已退役 — 建议使用 `claude-sonnet-4-5` |
| "haiku"、"fast"、"cheap"                  | `claude-haiku-4-5`             |
| "haiku 4.5"                               | `claude-haiku-4-5`             |
| "haiku 3.5"                               | 已退役 — 建议使用 `claude-haiku-4-5` |
| "haiku 3"                                 | 已弃用 — 建议使用 `claude-haiku-4-5` |
