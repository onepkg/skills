# HTTP 错误代码参考

本文档记录了 Claude API 返回的 HTTP 错误代码、常见原因以及处理方法。有关语言特定的错误处理示例，请参见 `python/` 或 `typescript/` 文件夹。

## 错误代码汇总

| 代码 | 错误类型                  | 可重试     | 常见原因                         |
| ---- | ----------------------- | --------- | ------------------------------------ |
| 400  | `invalid_request_error` | 否        | 请求格式或参数无效                   |
| 401  | `authentication_error`  | 否        | API 密钥无效或缺失                   |
| 403  | `permission_error`      | 否        | API 密钥缺少权限                     |
| 404  | `not_found_error`       | 否        | 端点或模型 ID 无效                   |
| 413  | `request_too_large`     | 否        | 请求超过大小限制                     |
| 429  | `rate_limit_error`      | 是        | 请求过多                             |
| 500  | `api_error`             | 是        | Anthropic 服务问题                   |
| 529  | `overloaded_error`      | 是        | API 暂时过载                         |

## 详细错误信息

### 400 Bad Request

**原因：**

- 请求体中的 JSON 格式错误
- 缺少必需参数（`model`、`max_tokens`、`messages`）
- 无效的参数类型（例如，期望整数却传入字符串）
- 空的 messages 数组
- messages 未交替使用 user/assistant

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

**修复方法：** 在发送前验证请求结构。检查：

- `model` 是有效的模型 ID
- `max_tokens` 是正整数
- `messages` 数组非空且正确交替

---

### 401 Unauthorized

**原因：**

- 缺少 `x-api-key` 请求头或 `Authorization` 请求头
- API 密钥格式无效
- API 密钥已被撤销或删除

**修复方法：** 确保正确设置了 `ANTHROPIC_API_KEY` 环境变量。

---

### 403 Forbidden

**原因：**

- API 密钥没有所请求模型的访问权限
- 组织级别限制
- 尝试在无测试版访问权限的情况下使用测试版功能

**修复方法：** 在控制台中检查你的 API 密钥权限。你可能需要不同的 API 密钥或请求特定功能的访问权限。

---

### 404 Not Found

**原因：**

- 模型 ID 拼写错误（例如，`claude-sonnet-4.6` 写成 `claude-sonnet-4-6`）
- 使用了已弃用的模型 ID
- API 端点无效

**修复方法：** 使用模型文档中的确切模型 ID。你也可以使用别名（例如 `claude-opus-4-8`）。

---

### 413 Request Too Large

**原因：**

- 请求体超过最大大小
- 输入中的 token 数量过多
- 图像数据过大

**修复方法：** 减小输入大小——截断对话历史记录、压缩/调整图像大小，或将大文档拆分为多个块。

---

### 400 验证错误

某些 400 错误与参数验证特别相关：

- `max_tokens` 超过了模型的限制
- 无效的 `temperature` 值（必须为 0.0-1.0）
- 扩展思考中的 `budget_tokens` >= `max_tokens`
- 无效的工具定义模式

**Opus 4.8 / 4.7 上的模型特定 400 错误：**

- `temperature`、`top_p`、`top_k` 已被移除——发送其中任何一个都会返回 400。删除该参数；请参见 `shared/model-migration.md` → 各 SDK 语法参考。
- `thinking: {type: "enabled", budget_tokens: N}` 已被移除——发送它会返回 400。请使用 `thinking: {type: "adaptive"}` 代替。

**旧版模型（Opus 4.6 及更早版本）上扩展思考的常见错误：**

```
# 错误：budget_tokens 必须小于 max_tokens
thinking: budget_tokens=10000, max_tokens=1000  → 错误！

# 正确
thinking: budget_tokens=10000, max_tokens=16000
```

---

### 429 Rate Limited

**原因：**

- 超过每分钟请求数限制（RPM）
- 超过每分钟 token 数限制（TPM）
- 超过每日 token 数限制（TPD）

**需要检查的请求头：**

- `retry-after`：重试前等待的秒数
- `x-ratelimit-limit-*`：你的限制额度
- `x-ratelimit-remaining-*`：剩余配额

**修复方法：** Anthropic SDK 会自动重试 429 和 5xx 错误，并采用指数退避策略（默认 `max_retries=2`）。如需自定义重试行为，请参见语言特定的错误处理示例。

---

### 500 Internal Server Error

**原因：**

- Anthropic 服务临时问题
- API 处理中的错误

**修复方法：** 使用指数退避重试。如果持续出现，请查看 [status.anthropic.com](https://status.anthropic.com)。

---

### 529 Overloaded

**原因：**

- API 需求量大
- 服务容量已达上限

**修复方法：** 使用指数退避重试。考虑使用不同的模型（Haiku 通常负载较低）、分散请求时间，或实现请求排队。

---

## 常见错误及修复方法

| 错误                               | 错误码          | 修复方法                                                     |
| ------------------------------- | ---------------- | ------------------------------------------------------- |
| 在 Opus 4.8 / 4.7 上使用 `temperature`/`top_p`/`top_k` | 400 | 移除该参数（参见 `shared/model-migration.md`）             |
| 在 Opus 4.8 / 4.7 上使用 `budget_tokens` | 400            | 使用 `thinking: {type: "adaptive"}`                      |
| `budget_tokens` >= `max_tokens`（旧版模型） | 400 | 确保 `budget_tokens` < `max_tokens`                  |
| 模型 ID 拼写错误                | 404              | 使用有效的模型 ID，如 `claude-opus-4-8`               |
| 第一条消息是 `assistant`    | 400              | 第一条消息必须是 `user`                            |
| 连续相同角色的消息  | 400              | 交替使用 `user` 和 `assistant`                        |
| 代码中硬编码 API 密钥                 | 401（密钥泄露） | 使用环境变量                                |
| 需要自定义重试              | 429/5xx          | SDK 会自动重试；可通过 `max_retries` 自定义 |

## SDK 中的类型化异常

**始终使用 SDK 的类型化异常类**，而不是使用字符串匹配来检查错误消息。每个 HTTP 错误代码都对应一个特定的异常类：

| HTTP 状态码 | TypeScript 类                      | Python 类                      |
| --------- | --------------------------------- | --------------------------------- |
| 400       | `Anthropic.BadRequestError`       | `anthropic.BadRequestError`       |
| 401       | `Anthropic.AuthenticationError`   | `anthropic.AuthenticationError`   |
| 403       | `Anthropic.PermissionDeniedError` | `anthropic.PermissionDeniedError` |
| 404       | `Anthropic.NotFoundError`         | `anthropic.NotFoundError`         |
| 429       | `Anthropic.RateLimitError`        | `anthropic.RateLimitError`        |
| 500+      | `Anthropic.InternalServerError`   | `anthropic.InternalServerError`   |
| 任意      | `Anthropic.APIError`              | `anthropic.APIError`              |

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

// ❌ 错误：不要用字符串匹配检查错误消息
try {
  const response = await client.messages.create({...});
} catch (error) {
  const msg = error instanceof Error ? error.message : String(error);
  if (msg.includes("429") || msg.includes("rate_limit")) { ... }
}
```

所有异常类都继承自 `Anthropic.APIError`，它具有 `status` 属性。使用 `instanceof` 检查时，应从最具体到最不具体（例如，先检查 `RateLimitError`，再检查 `APIError`）。
