# Streaming — Python

## 快速开始

```python
with client.messages.stream(
    model="claude-opus-4-8",
    max_tokens=64000,
    messages=[{"role": "user", "content": "Write a story"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### 异步

```python
async with async_client.messages.stream(
    model="claude-opus-4-8",
    max_tokens=64000,
    messages=[{"role": "user", "content": "Write a story"}]
) as stream:
    async for text in stream.text_stream:
        print(text, end="", flush=True)
```

---

## 处理不同类型的内容

Claude 可能返回文本、思考块或工具调用。请相应地处理每种情况：

> **Opus 4.8 / Opus 4.7 / Opus 4.6:** 使用 `thinking: {type: "adaptive"}`。在旧版模型上，请改用 `thinking: {type: "enabled", budget_tokens: N}`。

```python
with client.messages.stream(
    model="claude-opus-4-8",
    max_tokens=64000,
    thinking={"type": "adaptive"},
    messages=[{"role": "user", "content": "Analyze this problem"}]
) as stream:
    for event in stream:
        if event.type == "content_block_start":
            if event.content_block.type == "thinking":
                print("\n[Thinking...]")
            elif event.content_block.type == "text":
                print("\n[Response:]")

        elif event.type == "content_block_delta":
            if event.delta.type == "thinking_delta":
                print(event.delta.thinking, end="", flush=True)
            elif event.delta.type == "text_delta":
                print(event.delta.text, end="", flush=True)
```

---

## 带工具调用的流式传输

Python 工具运行器目前返回完整的消息。如果需要在工具调用时进行逐 token 流式传输，可以在手动循环中对单个 API 调用使用流式传输：

```python
with client.messages.stream(
    model="claude-opus-4-8",
    max_tokens=64000,
    tools=tools,
    messages=messages
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

    response = stream.get_final_message()
    # Continue with tool execution if response.stop_reason == "tool_use"
```

---

## 获取最终消息

```python
with client.messages.stream(
    model="claude-opus-4-8",
    max_tokens=64000,
    messages=[{"role": "user", "content": "Hello"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

    # Get full message after streaming
    final_message = stream.get_final_message()
    print(f"\n\nTokens used: {final_message.usage.output_tokens}")
```

---

## 带进度更新的流式传输

```python
def stream_with_progress(client, **kwargs):
    """流式传输响应并附带进度更新。"""
    total_tokens = 0
    content_parts = []

    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            if event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    text = event.delta.text
                    content_parts.append(text)
                    print(text, end="", flush=True)

            elif event.type == "message_delta":
                if event.usage and event.usage.output_tokens is not None:
                    total_tokens = event.usage.output_tokens

        final_message = stream.get_final_message()

    print(f"\n\n[Tokens used: {total_tokens}]")
    return "".join(content_parts)
```

---

## 流中的错误处理

```python
try:
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=64000,
        messages=[{"role": "user", "content": "Write a story"}]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
except anthropic.APIConnectionError:
    print("\nConnection lost. Please retry.")
except anthropic.RateLimitError:
    print("\nRate limited. Please wait and retry.")
except anthropic.APIStatusError as e:
    print(f"\nAPI error: {e.status_code}")
```

---

## 流事件类型

| 事件类型                 | 描述               | 触发时机                       |
| --------------------- | ------------------ | ------------------------------ |
| `message_start`       | 包含消息元数据        | 在开始时触发一次                 |
| `content_block_start` | 新内容块开始          | 当文本/工具调用块开始时          |
| `content_block_delta` | 增量内容更新          | 每个 token/片段                 |
| `content_block_stop`  | 内容块完成            | 当块完成时                      |
| `message_delta`       | 消息级更新            | 包含 `stop_reason`、usage       |
| `message_stop`        | 消息完成              | 在结束时触发一次                 |

## 最佳实践

1. **始终刷新输出** — 使用 `flush=True` 立即显示 token
2. **处理部分响应** — 如果流被中断，您可能会得到不完整的内容
3. **跟踪 token 使用量** — `message_delta` 事件包含使用量信息
4. **设置超时** — 为您的应用程序设置适当的超时时间
5. **默认使用流式传输** — 即使在流式传输时也可以使用 `.get_final_message()` 获取完整响应，这为您提供超时保护，无需处理单个事件
