# 托管智能体 — Webhooks

当托管智能体资源更改状态时，Anthropic 可以 POST 到您的 HTTPS 端点 — 这是保持 SSE 流或轮询的替代方法。负载是**精简的**（仅限事件类型 + 资源 ID）；收到后，获取资源以获取当前状态。每次交付都是 HMAC 签名的。

> **方向很重要。** 此页面涵盖关于会话/保管库状态的 *Anthropic → 您* 的通知。它**不**涵盖 *第三方 → 您* 的 *触发*会话的 webhook（例如调用 `sessions.create()` 的 GitHub 推送处理程序）— 那是您端的普通应用程序代码，没有 Anthropic 特定的线路格式。

---

## 注册端点（仅限控制台）

控制台 → **管理 → Webhooks**。目前没有程序化的端点管理 API。同一页面支持秘密轮换。

| 字段 | 约束 |
|---|---|
| URL | 端口 443 上的 HTTPS，可公开解析的主机名 |
| 事件类型 | 按 `data.type` 订阅 — 您只收到订阅的类型（加上测试事件）|
| 签名秘密 | 以 `whsec_` 为前缀，32 字节，**创建时只显示一次** — 存储它 |

---

## 验证签名

每次交付都是 HMAC 签名的。**使用 SDK 的 `client.beta.webhooks.unwrap()`** — 它会验证签名，拒绝超过 ~5 分钟的旧负载，并返回解析的事件。它从 `ANTHROPIC_WEBHOOK_SIGNING_KEY` 读取 `whsec_` 秘密。

```python
import anthropic
from flask import Flask, request

client = anthropic.Anthropic()  # 从环境变量读取 ANTHROPIC_WEBHOOK_SIGNING_KEY
app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        event = client.beta.webhooks.unwrap(
            request.get_data(as_text=True),
            headers=dict(request.headers),
        )
    except Exception:
        return "无效签名", 400

    if event.id in seen_event_ids:  # 去重重试 — id 是每个事件的，不是每次交付的
        return "", 204
    seen_event_ids.add(event.id)

    match event.data.type:
        case "session.status_idled":
            session = client.beta.sessions.retrieve(event.data.id)
            notify_user(session)
        case "vault_credential.refresh_failed":
            alert_oncall(event.data.id)

    return "", 204
```

将**原始请求体**传递给 `unwrap()` — 重新序列化 JSON 的框架（Express `.json()`、Flask `.get_json()`）会更改字节并破坏 MAC。对于其他语言，请在 SDK 仓库中查找 `beta.webhooks.unwrap` 绑定（`shared/live-sources.md`）；不要手动编写验证。

---

## 负载信封

```json
{
  "type": "event",
  "id": "event_01ABC...",
  "created_at": "2026-03-18T14:05:22Z",
  "data": {
    "type": "session.status_idled",
    "id": "session_01XYZ...",
    "organization_id": "8a3d2f1e-...",
    "workspace_id": "c7b0e4d9-..."
  }
}
```

打开 `data.type`，按 `data.id` 获取资源，返回任何 **2xx** 以确认。`created_at` 是 *状态转换*发生的时间，而不是 webhook 触发的时间。

---

## 支持的 `data.type` 值

| `data.type` | 触发时机 |
|---|---|
| `session.status_scheduled` | 会话已创建并准备好接受事件 |
| `session.status_run_started` | 智能体执行已启动（每次转换为 `running`）|
| `session.status_idled` | 智能体等待输入（工具批准、自定义工具结果或下一条消息）|
| `session.status_terminated` | 会话遇到终端错误 |
| `session.thread_created` | 多智能体：协调器打开了新的子智能体线程 |
| `session.thread_idled` | 多智能体：子智能体线程正在等待输入 |
| `session.outcome_evaluation_ended` | 结果评分器完成了一次迭代 |
| `vault.archived` | 保管库已归档 |
| `vault.created` | 保管库已创建 |
| `vault.deleted` | 保管库已删除 |
| `vault_credential.archived` | 保管库凭证已归档 |
| `vault_credential.created` | 保管库凭证已创建 |
| `vault_credential.deleted` | 保管库凭证已删除 |
| `vault_credential.refresh_failed` | MCP OAuth 保管库凭证无法刷新 |

> 这些是 **webhook** `data.type` 值 — 与 SSE 事件类型（`shared/managed-agents-events.md` 中的 `session.status_idle`、`span.outcome_evaluation_end` 等）是分开的命名空间。不要在 webhook 处理程序中重用 SSE 常量。

---

## 交付行为和陷阱

- **无顺序保证。** 即使评估先完成，`session.status_idled` 也可能在 `session.outcome_evaluation_ended` 之前到达。如果顺序很重要，请按信封 `created_at` 排序。
- **重试带有相同的 `event.id`。** 非 2xx 至少重试一次。按 `event.id` 去重。
- **3xx 是失败。** 不遵循重定向 — 如果您的端点移动，请更新控制台中的 URL。
- **连续失败约 20 次后自动禁用**，如果主机名解析为私有 IP 或返回重定向则立即禁用。在控制台手动重新启用。
- **精简负载是有意的。** 不要期望在 webhook 正文中包含 `stop_reason`、`outcome_evaluations`、凭证秘密等。获取资源。
