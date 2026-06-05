# 托管代理 — Webhook

当托管代理资源状态发生变化时，Anthropic 可以向您的 HTTPS 端点发送 POST 请求 — 这是维持 SSE 流或轮询之外的另一种选择。Payload 是**轻量的**（仅包含事件类型 + 资源 ID）；收到后，请获取资源以获取当前状态。每次投递都经过 HMAC 签名。

> **方向很重要。** 本文档涵盖 *Anthropic → 你* 关于会话/保险库状态的通知。它**不**涵盖 *第三方 → 你* 的 *触发* 会话的 webhook（例如调用 `sessions.create()` 的 GitHub push 处理器） — 那是你方的普通应用代码，没有 Anthropic 特定的线路格式。

---

## 注册端点（仅限控制台）

控制台 → **管理 → Webhook**。目前尚无编程式端点管理 API。同一页面支持密钥轮换。

| 字段 | 约束 |
|---|---|
| URL | 端口 443 上的 HTTPS，可公开解析的主机名 |
| 事件类型 | 按 `data.type` 订阅 — 你仅接收已订阅的类型（外加测试事件）|
| 签名密钥 | 以 `whsec_` 为前缀，32 字节，**创建时仅显示一次** — 请妥善保管 |

---

## 验证签名

每次投递都经过 HMAC 签名。**使用 SDK 的 `client.beta.webhooks.unwrap()`** — 它会验证签名，拒绝超过约 5 分钟的 payload，并返回解析后的事件。它从 `ANTHROPIC_WEBHOOK_SIGNING_KEY` 读取 `whsec_` 密钥。

```python
import anthropic
from flask import Flask, request

client = anthropic.Anthropic()  # reads ANTHROPIC_WEBHOOK_SIGNING_KEY from env
app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        event = client.beta.webhooks.unwrap(
            request.get_data(as_text=True),
            headers=dict(request.headers),
        )
    except Exception:
        return "invalid signature", 400

    if event.id in seen_event_ids:  # dedupe retries — id is per-event, not per-delivery
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

将**原始请求体**传递给 `unwrap()` — 重新序列化 JSON 的框架（Express 的 `.json()`、Flask 的 `.get_json()`）会改变字节并破坏 MAC。对于其他语言，请在 SDK 仓库（`shared/live-sources.md`）中查找 `beta.webhooks.unwrap` 绑定；不要手动实现验证。

---

## Payload 信封

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

根据 `data.type` 进行分支判断，通过 `data.id` 获取资源，返回任意 **2xx** 以确认。`created_at` 是*状态转换*发生的时间，而非 webhook 触发的时间。

---

## 支持的 `data.type` 值

| `data.type` | 触发时机 |
|---|---|
| `session.status_scheduled` | 会话已创建并准备好接受事件 |
| `session.status_run_started` | 代理执行已启动（每次转换为 `running` 状态）|
| `session.status_idled` | 代理等待输入（工具审批、自定义工具结果或下一条消息）|
| `session.status_terminated` | 会话遇到终止错误 |
| `session.thread_created` | 多代理：协调器打开了新的子代理线程 |
| `session.thread_idled` | 多代理：子代理线程正在等待输入 |
| `session.outcome_evaluation_ended` | 结果评分器完成一次迭代 |
| `vault.archived` | 保险库已归档 |
| `vault.created` | 保险库已创建 |
| `vault.deleted` | 保险库已删除 |
| `vault_credential.archived` | 保险库凭证已归档 |
| `vault_credential.created` | 保险库凭证已创建 |
| `vault_credential.deleted` | 保险库凭证已删除 |
| `vault_credential.refresh_failed` | MCP OAuth 保险库凭证刷新失败 |

> 这些是 **webhook** `data.type` 值 — 与 SSE 事件类型（`shared/managed-agents-events.md` 中的 `session.status_idle`、`span.outcome_evaluation_end` 等）是独立的命名空间。不要将 SSE 常量复用于 webhook 处理器。

---

## 投递行为与注意事项

- **无排序保证。** 即使评估先完成，`session.status_idled` 也可能在 `session.outcome_evaluation_ended` 之前到达。如果顺序重要，请按信封中的 `created_at` 排序。
- **重试携带相同的 `event.id`。** 非 2xx 状态时至少重试一次。按 `event.id` 去重。
- **3xx 视为失败。** 不跟随重定向 — 如果端点迁移，请在控制台中更新 URL。
- **自动禁用** 在连续约 20 次投递失败后，或如果主机名解析为私有 IP 或返回重定向时立即禁用。请在控制台中手动重新启用。
- **薄 Payload 是有意为之。** 不要期望在 webhook 体中包含 `stop_reason`、`outcome_evaluations`、凭证密钥等内容 — 请获取资源。
