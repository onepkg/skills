# HTTP 错误代码参考

此文档记录了 Claude API 返回的 HTTP 错误代码、常见原因以及如何处理它们。有关特定语言的错误处理示例，请参阅 `python/` 或 `typescript/` 文件夹。

## 错误代码摘要

| 代码 | 错误类型                 | 可重试   | 常见原因                             |
| ---- | ----------------------- | --------- | ------------------------------------ |
| 400  | `invalid_request_error` | 否        | 无效的请求格式或参数                 |
| 401  | `authentication_error`  | 否        | 无效或缺失的 API 密钥                |
| 403  | `permission_error`      | 否        | API 密钥缺少权限                     |
| 404  | `not_found_error`       | 否        | 无效的端点或模型 ID                  |
| 413  | `request_too_large`     | 否        | 请求超出大小限制                     |
| 429  | `rate_limit_error`      | 是        | 请求过多                             |
| 500  | `api_error`             | 是        | Anthropic 服务问题                   |
| 529  | `overloaded_error`      | 是        | API 暂时过载                         |

## 详细错误信息

### 400 Bad Request

**原因：**

- 请求体中的 JSON 格式错误
- 缺少必需参数（`model`、`max_tokens`、`messages`）
- 无效的参数类型（例如，应该是整数的地方使用了字符串）
- 空消息数组
- 消息未交替使用 user/assistant

**错误示例：**

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "messages: roles must alternate between \"user\" and \"assistant\""
  },
  "request_id": "req_011CSHoEeqs5C35K2UUqR7Fy"
}
```

**修复：** 发送前验证请求结构。检查：

- `model` 是有效的模型 ID
- `max_tokens` 是正整数
- `messages` 数组非空且正确交替

---

### 401 Unauthorized

**原因：**

- 缺少 `x-api-key` 头或 `Authorization` 头
- 无效的 API 密钥格式
- 已撤销或删除的 API 密钥

**修复：** 确保 `ANTHROPIC_API_KEY` 环境变量设置正确。

---

### 403 Forbidden

**原因：**

- API 密钥没有访问请求模型的权限
- 组织级别限制
- 尝试访问测试版功能但没有测试版访问权限

**修复：** 在控制台中检查您的 API 密钥权限。您可能需要不同的 API 密钥或请求访问特定功能。

---

### 404 Not Found

**原因：**

- 模型 ID 拼写错误（例如，`claude-sonnet-4.6` 而不是 `claude-sonnet-4-6`）
- 使用已弃用的模型 ID
- 无效的 API 端点

**修复：** 使用模型文档中的精确模型 ID。您可以使用别名（例如，`claude-opus-4-8`）。

---

### 413 Request Too Large

**原因：**

- 请求体超出最大大小
- 输入中的令牌过多
- 图像数据过大

**修复：** 减小输入大小 — 截断对话历史、压缩/调整图像大小，或将大文档拆分成块。

---

### 400 验证错误

某些 400 错误特别与参数验证相关：

- `max_tokens` 超出模型限制
- 无效的 `temperature` 值（必须是 0.0-1.0）
- 扩展思考中 `budget_tokens` >= `max_tokens`
- 无效的工具定义 schema

**Opus 4.8 / 4.7 上的模型特定 400 错误：**

- `temperature`、`top_p`、`top_k` 已移除 — 发送其中任何一个都会返回 400。删除该参数；请参阅 `shared/model-migration.md` → 各 SDK 语法参考。
- `thinking: {type: "enabled", budget_tokens: N}` 已移除 — 发送会返回 400。请改用 `thinking: {type: "adaptive"}`。

**旧模型（Opus 4.6 及更早版本）上扩展思考的常见错误：**

```
# 错误：budget_tokens 必须 < max_tokens
thinking: budget_tokens=10000, max_tokens=1000  → 错误！

# 正确
thinking: budget_tokens=10000, max_tokens=16000
```

---

### 429 Rate Limited

**原因：**

- 超出每分钟请求数（RPM）
- 超出每分钟令牌数（TPM）
- 超出每日令牌数（TPD）

**要检查的头：**

- `retry-after`：重试前等待的秒数
- `x-ratelimit-limit-*`：您的限制
- `x-ratelimit-remaining-*`：剩余配额

**修复：** Anthropic SDK 会使用指数退避自动重试 429 和 5xx 错误（默认：`max_retries=2`）。有关自定义重试行为，请参阅特定语言的错误处理示例。

---

### 500 Internal Server Error

**原因：**

- 临时的 Anthropic 服务问题
- API 处理中的 bug

**修复：** 使用指数退避重试。如果持续存在，请检查 [status.anthropic.com](https://status.anthropic.com)。

---

### 529 Overloaded

**原因：**

- API 需求高
- 服务容量已达上限

**修复：** 使用指数退避重试。考虑使用不同的模型（Haiku 通常负载较小）、分散请求时间，或实现请求排队。

---

## 常见错误和修复

| 错误                             | 错误代码          | 修复                                                     |
| ------------------------------- | ---------------- | ------------------------------------------------------- |
| Opus 4.8 / 4.7 上的 `temperature`/`top_p`/`top_k` | 400 | 移除参数（参见 `shared/model-migration.md`）              |
| Opus 4.8 / 4.7 上的 `budget_tokens` | 400            | 使用 `thinking: {type: "adaptive"}`                      |
| （旧模型）`budget_tokens` >= `max_tokens` | 400 | 确保 `budget_tokens` < `max_tokens`                      |
| 模型 ID 拼写错误                 | 404              | 使用有效的模型 ID，如 `claude-opus-4-8`                   |
| 第一条消息是 `assistant`         | 400              | 第一条消息必须是 `user`                                  |
| 连续相同角色的消息               | 400              | 交替使用 `user` 和 `assistant`                          |
| 代码中的 API 密钥                | 401（密钥泄露） | 使用环境变量                                            |
| 自定义重试需求                   | 429/5xx          | SDK 自动重试；使用 `max_retries` 自定义                   |

## SDK 中的类型化异常

**始终使用 SDK 的类型化异常类**，而不是使用字符串匹配检查错误消息。每个 HTTP 错误代码映射到特定的异常类：

| HTTP 代码 | TypeScript 类                     | Python 类                       |
| --------- | --------------------------------- | ------------------------------- |
| 400       | `Anthropic.BadRequestError`       | `anthropic.BadRequestError`     |
| 401       | `Anthropic.AuthenticationError`   | `anthropic.AuthenticationError` |
| 403       | `Anthropic.PermissionDeniedError` | `anthropic.PermissionDeniedError` |
| 404       | `Anthropic.NotFoundError`         | `anthropic.NotFoundError`       |
| 429       | `Anthropic.RateLimitError`        | `anthropic.RateLimitError`      |
| 500+      | `Anthropic.InternalServerError`   | `anthropic.InternalServerError` |
| 任何       | `Anthropic.APIError`              | `anthropic.APIError`            |

```typescript
// ✅ 正确：使用类型化异常
try {
  const response = await client.messages.create({...});
} catch (error) {
  if (error instanceof Anthropic.RateLimitError) {
    // 处理速率限制
  } else if (error instanceof Anthropic.APIError) {
    console.error(`API error ${error.status}:`, error.message);
  }
}

// ❌ 错误：不要使用字符串匹配检查错误消息
try {
  const response = await client.messages.create({...});
} catch (error) {
  const msg = error instanceof Error ? error.message : String(error);
  if (msg.includes("429") || msg.includes("rate_limit")) { ... }
}
```

所有异常类都继承自 `Anthropic.APIError`，它有一个 `status` 属性。使用 `instanceof` 检查从最具体到最不具体（例如，在 `APIError` 之前检查 `RateLimitError`）。
