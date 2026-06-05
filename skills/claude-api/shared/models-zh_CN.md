# Claude 模型目录

**仅使用此文件中列出的精确模型 ID。** 永远不要猜测或构建模型 ID — 不正确的 ID 会导致 API 错误。尽可能使用别名。有关最新信息，请 WebFetch `shared/live-sources.md` 中的模型概览 URL，或直接查询 Models API（参见下面的程序化模型发现）。

## 程序化模型发现

对于**实时**功能数据 — 上下文窗口、最大输出令牌、功能支持（思考、视觉、努力程度、结构化输出等）— 请查询 Models API，而不是依赖下面的缓存表。当用户询问"X 的上下文窗口是什么"、"模型 X 是否支持视觉/思考/努力程度"、"哪些模型支持功能 Y"，或希望在运行时按功能选择模型时，请使用此方法。

```python
m = client.models.retrieve("claude-opus-4-8")
m.id                 # "claude-opus-4-8"
m.display_name       # "Claude Opus 4.8"
m.max_input_tokens   # 上下文窗口（整数）
m.max_tokens         # 最大输出令牌（整数）

# capabilities 是一个无类型的嵌套字典 — 方括号访问，在叶子节点检查 ["supported"]
caps = m.capabilities
caps["image_input"]["supported"]                       # 视觉
caps["thinking"]["types"]["adaptive"]["supported"]     # 自适应思考
caps["effort"]["max"]["supported"]                     # 努力程度：最大（还有低/中/高）
caps["structured_outputs"]["supported"]
caps["context_management"]["compact_20260112"]["supported"]

# 过滤所有模型 — 直接迭代页面对象（自动分页）；不要使用 .data
[m for m in client.models.list()
 if m.capabilities["thinking"]["types"]["adaptive"]["supported"]
 and m.max_input_tokens >= 200_000]
```

顶级字段（`id`、`display_name`、`max_input_tokens`、`max_tokens`）是类型化属性。`capabilities` 是一个字典 — 使用方括号访问，而不是属性访问。API 为每个模型返回完整的功能树，每个叶子节点都有 `supported: true/false`，因此方括号链是安全的，不需要 `.get()` 保护。TypeScript SDK：相同的方法名称，迭代时也会自动分页。

### 原始 HTTP

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

| 友好名称          | 别名（使用这个）      | 完整 ID                        | 上下文窗口    | 最大输出   | 状态   |
|-------------------|---------------------|-------------------------------|---------------|------------|--------|
| Claude Opus 4.8   | `claude-opus-4-8`   | —                             | 1M            | 128K       | 活跃   |
| Claude Opus 4.7   | `claude-opus-4-7`   | —                             | 1M            | 128K       | 活跃   |
| Claude Opus 4.6   | `claude-opus-4-6`   | —                             | 1M            | 128K       | 活跃   |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | -                             | 1M            | 64K        | 活跃   |
| Claude Haiku 4.5  | `claude-haiku-4-5`  | `claude-haiku-4-5-20251001`   | 200K          | 64K        | 活跃   |

### 模型描述
- **Claude Opus 4.8** — 迄今为止最强大的 Claude 模型 — 高度自主，在长周期智能体工作、知识工作和记忆方面达到最先进水平；写作更清晰、更温暖。与 Opus 4.7 具有相同的 API 表面（仅自适应思考；移除了采样参数和 `budget_tokens`）。1M 上下文窗口，标准 API 定价（无长上下文溢价）。请参阅 `shared/model-migration.md` → 迁移到 Opus 4.8 — 从 4.7 → 4.8 只是模型 ID 交换加上提示重新调整，没有新的破坏性变更。
- **Claude Opus 4.7** — 上一代 Opus。高度自主；在长周期智能体工作、知识工作、视觉和记忆方面表现出色。仅自适应思考；移除了采样参数和 `budget_tokens`。1M 上下文窗口。请参阅 `shared/model-migration.md` → 迁移到 Opus 4.7。
- **Claude Opus 4.6** — 较旧的 Opus。支持自适应思考（推荐），128K 最大输出令牌（大输出需要流式传输）。1M 上下文窗口。
- **Claude Sonnet 4.6** — 我们速度和智能的最佳组合。支持自适应思考（推荐）。1M 上下文窗口。64K 最大输出令牌。
- **Claude Haiku 4.5** — 适用于简单任务的最快且最具成本效益的模型。

## 遗留模型（仍活跃）

| 友好名称          | 别名（使用这个）      | 完整 ID                        | 状态   |
|-------------------|---------------------|-------------------------------|--------|
| Claude Opus 4.5   | `claude-opus-4-5`   | `claude-opus-4-5-20251101`    | 活跃   |
| Claude Opus 4.1   | `claude-opus-4-1`   | `claude-opus-4-1-20250805`    | 活跃   |
| Claude Sonnet 4.5 | `claude-sonnet-4-5` | `claude-sonnet-4-5-20250929`  | 活跃   |
| Claude Sonnet 4   | `claude-sonnet-4-0` | `claude-sonnet-4-20250514`    | 活跃   |
| Claude Opus 4     | `claude-opus-4-0`   | `claude-opus-4-20250514`      | 活跃   |

## 已弃用模型（即将停用）

| 友好名称          | 别名（使用这个）      | 完整 ID                        | 状态       | 停用日期       |
|-------------------|---------------------|-------------------------------|------------|--------------|
| Claude Haiku 3    | —                   | `claude-3-haiku-20240307`     | 已弃用     | 2026年4月19日 |

## 已停用模型（不再可用）

| 友好名称          | 完整 ID                        | 停用日期     |
|-------------------|-------------------------------|-------------|
| Claude Sonnet 3.7 | `claude-3-7-sonnet-20250219`  | 2026年2月19日 |
| Claude Haiku 3.5  | `claude-3-5-haiku-20241022`   | 2026年2月19日 |
| Claude Opus 3     | `claude-3-opus-20240229`      | 2026年1月5日  |
| Claude Sonnet 3.5 | `claude-3-5-sonnet-20241022`  | 2025年10月28日 |
| Claude Sonnet 3.5 | `claude-3-5-sonnet-20240620`  | 2025年10月28日 |
| Claude Sonnet 3   | `claude-3-sonnet-20240229`    | 2025年7月21日  |
| Claude 2.1        | `claude-2.1`                  | 2025年7月21日  |
| Claude 2.0        | `claude-2.0`                  | 2025年7月21日  |

## 解析用户请求

当用户按名称请求模型时，使用此表查找正确的模型 ID：

| 用户说...                                  | 使用此模型 ID                  |
|-------------------------------------------|--------------------------------|
| "opus"、"最强大的"                         | `claude-opus-4-8`              |
| "opus 4.8"                                | `claude-opus-4-8`              |
| "opus 4.7"                                | `claude-opus-4-7`              |
| "opus 4.6"                                | `claude-opus-4-6`              |
| "opus 4.5"                                | `claude-opus-4-5`              |
| "opus 4.1"                                | `claude-opus-4-1`              |
| "opus 4"、"opus 4.0"                      | `claude-opus-4-0`（已弃用 — 建议使用 `claude-opus-4-8`） |
| "sonnet"、"平衡的"                        | `claude-sonnet-4-6`            |
| "sonnet 4.6"                              | `claude-sonnet-4-6`            |
| "sonnet 4.5"                              | `claude-sonnet-4-5`            |
| "sonnet 4"、"sonnet 4.0"                  | `claude-sonnet-4-0`            |
| "sonnet 3.7"                              | 已停用 — 建议使用 `claude-sonnet-4-5` |
| "sonnet 3.5"                              | 已停用 — 建议使用 `claude-sonnet-4-5` |
| "haiku"、"快速"、"便宜"                   | `claude-haiku-4-5`             |
| "haiku 4.5"                               | `claude-haiku-4-5`             |
| "haiku 3.5"                               | 已停用 — 建议使用 `claude-haiku-4-5` |
| "haiku 3"                                 | 已弃用 — 建议使用 `claude-haiku-4-5` |
