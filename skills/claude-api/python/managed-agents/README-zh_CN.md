# Managed Agents — Python

> **此处未展示的绑定：** 本 README 涵盖了 Python 最常用的 managed-agents 流程。如果你需要某个未展示的类、方法、命名空间、字段或行为，请从 `shared/live-sources.md` 中 WebFetch Python SDK 仓库 **或相关文档页面**，而非自行猜测。不要从 cURL 格式或其他语言的 SDK 进行推断。

> **Agent 是持久化的 — 创建一次，通过 ID 引用。** 保存 `agents.create` 返回的 agent ID，并将其传递给每次后续的 `sessions.create` 调用；不要在请求路径中调用 `agents.create`。Anthropic CLI 是通过版本控制的 YAML 创建 agent 和 environment 的一种便捷方式 — 其 URL 位于 `shared/live-sources.md`。为完整起见，以下示例展示了代码内的创建方式；在生产环境中，create 调用应属于设置阶段，而非请求路径。

## 安装

```bash
pip install anthropic
```

## 客户端初始化

```python
import anthropic

# 默认（使用 ANTHROPIC_API_KEY 环境变量）
client = anthropic.Anthropic()

# 显式指定 API key
client = anthropic.Anthropic(api_key="your-api-key")
```

---

## 创建 Environment

```python
environment = client.beta.environments.create(
    name="my-dev-env",
    config={
        "type": "cloud",
        "networking": {"type": "unrestricted"},
    },
)
print(environment.id)  # env_...
```

---

## 创建 Agent（必需的第一步）

> ⚠️ **不存在内联 agent 配置。** `model`/`system`/`tools` 位于 agent 对象上，而非 session。始终以 `agents.create()` 开始 — session 仅接受 `agent={"type": "agent", "id": agent.id}`。

### 最小示例

```python
# 1. 创建 agent（可复用、可版本化）
agent = client.beta.agents.create(
    name="Coding Assistant",
    model="claude-opus-4-8",
    tools=[{"type": "agent_toolset_20260401", "default_config": {"enabled": True}}],
)

# 2. 启动 session
session = client.beta.sessions.create(
    agent={"type": "agent", "id": agent.id, "version": agent.version},
    environment_id=environment.id,
)
print(session.id, session.status)
```

### 包含系统提示词和自定义工具

```python
import os

agent = client.beta.agents.create(
    name="Code Reviewer",
    model="claude-opus-4-8",
    system="You are a senior code reviewer.",
    tools=[
        {"type": "agent_toolset_20260401"},
        {
            "type": "custom",
            "name": "run_tests",
            "description": "Run the test suite",
            "input_schema": {
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "Path to test file"}
                },
                "required": ["test_path"],
            },
        },
    ],
)

session = client.beta.sessions.create(
    agent={"type": "agent", "id": agent.id, "version": agent.version},
    environment_id=environment.id,
    title="Code review session",
    resources=[
        {
            "type": "github_repository",
            "url": "https://github.com/owner/repo",
            "mount_path": "/workspace/repo",
            "authorization_token": os.environ["GITHUB_TOKEN"],
            "branch": "main",
        }
    ],
)
```

---

## 发送用户消息

```python
client.beta.sessions.events.send(
    session_id=session.id,
    events=[
        {
            "type": "user.message",
            "content": [{"type": "text", "text": "Review the auth module"}],
        }
    ],
)
```

> 💡 **流优先：** 在发送消息*之前*（或同时）打开流。流仅传递其打开后发生的事件 — 先发送后打开流意味着早期事件会以缓冲批次方式到达。请参阅[引导模式](../../shared/managed-agents-events.md#steering-patterns)。

---

## 流式事件 (SSE)

```python
import json

# 流优先：先打开流，然后在流活跃时发送
with client.beta.sessions.stream(
    session_id=session.id,
) as stream:
    client.beta.sessions.events.send(
        session_id=session.id,
        events=[{"type": "user.message", "content": [{"type": "text", "text": "..."}]}],
    )
    for event in stream:
        ...  # 处理事件

# 独立的流迭代：
with client.beta.sessions.stream(
    session_id=session.id,
) as stream:
    for event in stream:
        if event.type == "agent.message":
            for block in event.content:
                if block.type == "text":
                    print(block.text, end="", flush=True)
        elif event.type == "agent.custom_tool_use":
            # 自定义工具调用 — session 现在处于空闲状态
            print(f"\nCustom tool call: {event.tool_name}")
            print(f"Input: {json.dumps(event.input)}")
            # 发送结果回 session（见下文）
        elif event.type == "session.status_idle":
            print("\n--- Agent idle ---")
        elif event.type == "session.status_terminated":
            print("\n--- Session terminated ---")
            break
```

---

## 提供自定义工具结果

```python
client.beta.sessions.events.send(
    session_id=session.id,
    events=[
        {
            "type": "user.custom_tool_result",
            "custom_tool_use_id": "sevt_abc123",
            "content": [{"type": "text", "text": "All 42 tests passed."}],
        }
    ],
)
```

---

## 轮询事件

```python
events = client.beta.sessions.events.list(
    session_id=session.id,
)
for event in events.data:
    print(f"{event.type}: {event.id}")
```

> ⚠️ **优先使用 SDK 而非原生 `requests`/`httpx`。** 如果你自行编写轮询循环，不要假设 `timeout=(5, 60)` 或 `httpx.Timeout(120)` 限制了总调用时长 — 两者都是**逐块**读取超时（每个字节后重置），因此缓慢的响应可能永久阻塞。如需严格的挂钟截止时间，请在循环层面跟踪 `time.monotonic()` 并显式退出，或使用 `asyncio.wait_for()` 包装。请参阅[接收事件](../../shared/managed-agents-events.md#receiving-events)。

---

## 带自定义工具的完整流式循环

```python
import json


def run_custom_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a custom tool and return the result."""
    if tool_name == "run_tests":
        # Your tool implementation here
        return "All tests passed."
    return f"Unknown tool: {tool_name}"


def run_session(client, session_id: str):
    """Stream events and handle custom tool calls."""
    while True:
        with client.beta.sessions.stream(
            session_id=session_id,
        ) as stream:
            tool_calls = []
            for event in stream:
                if event.type == "agent.message":
                    for block in event.content:
                        if block.type == "text":
                            print(block.text, end="", flush=True)
                elif event.type == "agent.custom_tool_use":
                    tool_calls.append(event)
                elif event.type == "session.status_idle":
                    break
                elif event.type == "session.status_terminated":
                    return

        if not tool_calls:
            break

        # 处理自定义工具调用
        results = []
        for call in tool_calls:
            result = run_custom_tool(call.tool_name, call.input)
            results.append({
                "type": "user.custom_tool_result",
                "custom_tool_use_id": call.id,
                "content": [{"type": "text", "text": result}],
            })

        client.beta.sessions.events.send(
            session_id=session_id,
            events=results,
        )
```

---

## 上传文件

```python
with open("data.csv", "rb") as f:
    file = client.beta.files.upload(
        file=f,
    )

# 在 session 中使用
session = client.beta.sessions.create(
    agent={"type": "agent", "id": agent.id, "version": agent.version},
    environment_id=environment.id,
    resources=[{"type": "file", "file_id": file.id, "mount_path": "/workspace/data.csv"}],
)
```

---

## 列出并下载 Session 文件

列出 agent 在 session 期间写入 `/mnt/session/outputs/` 的文件，然后下载它们。

```python
# 列出与 session 关联的文件
files = client.beta.files.list(
    scope_id=session.id,
    betas=["managed-agents-2026-04-01"],
)
for f in files.data:
    print(f.filename, f.size_bytes)
    # 下载每个文件并保存到磁盘
    file_content = client.beta.files.download(f.id)
    file_content.write_to_file(f.filename)
```

> 💡 `session.status_idle` 事件与输出文件出现在 `files.list` 之间存在短暂的索引延迟（约 1–3 秒）。如果列表为空，请重试一两次。

---

## Session 管理

```python
# 获取 session 详情
session = client.beta.sessions.retrieve(session_id="sesn_011CZxAbc123Def456")
print(session.status, session.usage)

# 列出 sessions
sessions = client.beta.sessions.list()

# 删除 session
client.beta.sessions.delete(session_id="sesn_011CZxAbc123Def456")

# 归档 session
client.beta.sessions.archive(session_id="sesn_011CZxAbc123Def456")
```

---

## MCP 服务器集成

```python
# Agent 声明 MCP 服务器（此处无认证 — 认证放在 vault 中）
agent = client.beta.agents.create(
    name="MCP Agent",
    model="claude-opus-4-8",
    mcp_servers=[
        {"type": "url", "name": "my-tools", "url": "https://my-mcp-server.example.com/sse"},
    ],
    tools=[
        {"type": "agent_toolset_20260401", "default_config": {"enabled": True}},
        {"type": "mcp_toolset", "mcp_server_name": "my-tools"},
    ],
)

# Session 附加包含这些 MCP 服务器 URL 凭据的 vault
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment.id,
    vault_ids=[vault.id],
)
```

关于创建 vault 和添加凭据，请参阅 `shared/managed-agents-tools.md` 的 §Vaults 部分。
