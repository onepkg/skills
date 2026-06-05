# Managed Agents — Ruby

> **此处未展示的绑定：** 本 README 涵盖了 Ruby 中最常用的 managed-agents 流程。如果你需要的类、方法、命名空间、字段或行为未在此展示，请使用 `shared/live-sources.md` 中的 WebFetch 获取 Ruby SDK 仓库**或相关文档页面**，而非自行猜测。不要从 cURL 形状或其他语言的 SDK 进行推断。

> **Agents 是持久化的——创建一次，通过 ID 引用。** 存储由 `client.beta.agents.create` 返回的 agent ID，并将其传递给后续的每一次 `client.beta.sessions.create` 调用；不要在请求路径中调用 `agents.create`。Anthropic CLI 是从版本控制的 YAML 创建 agents 和 environments 的一种便捷方式——其 URL 在 `shared/live-sources.md` 中。以下示例展示了代码内创建的方式以作完整性说明；在生产环境中，create 调用应属于设置阶段，而非请求路径。

## 安装

```bash
gem install anthropic
```

## 客户端初始化

```ruby
require "anthropic"

# 默认（使用 ANTHROPIC_API_KEY 环境变量）
client = Anthropic::Client.new

# 显式指定 API key
client = Anthropic::Client.new(api_key: "your-api-key")
```

> ⚠️ **尾随下划线：** Ruby SDK 使用 `system_:` 和 `send_(`（尾随下划线）来避免与 `Kernel#system` 和 `Kernel#send` 产生命名冲突。在 managed-agents 代码中请始终使用这些形式。

---

## 创建 Environment

```ruby
environment = client.beta.environments.create(
  name: "my-dev-env",
  config: {
    type: "cloud",
    networking: {type: "unrestricted"}
  }
)
puts "Environment ID: #{environment.id}" # env_...
```

---

## 创建 Agent（必需的第一步）

> ⚠️ **没有内联 agent 配置。** `model`/`system_`/`tools` 位于 agent 对象上，而非 session。始终以 `client.beta.agents.create()` 开始——session 接受 `agent: agent.id` 或者类型化哈希形式 `agent: {type: "agent", id: agent.id, version: agent.version}`。

### 最小示例

```ruby
# 1. 创建 agent（可复用、带版本管理）
agent = client.beta.agents.create(
  name: "Coding Assistant",
  model: :"claude-opus-4-8",
  system_: "You are a helpful coding assistant.",
  tools: [{type: "agent_toolset_20260401"}]
)

# 2. 启动 session
session = client.beta.sessions.create(
  agent: {type: "agent", id: agent.id, version: agent.version},
  environment_id: environment.id,
  title: "Quickstart session"
)
puts "Session ID: #{session.id}"
```

### 更新 Agent

更新会创建新版本；每个版本的 agent 对象是不可变的。

```ruby
updated_agent = client.beta.agents.update(
  agent.id,
  version: agent.version,
  system_: "You are a helpful coding agent. Always write tests."
)
puts "New version: #{updated_agent.version}"

# 列出所有版本
client.beta.agents.versions.list(agent.id).auto_paging_each do |version|
  puts "Version #{version.version}: #{version.updated_at.iso8601}"
end

# 归档 agent
archived = client.beta.agents.archive(agent.id)
puts "Archived at: #{archived.archived_at.iso8601}"
```

---

## 发送用户消息

```ruby
client.beta.sessions.events.send_(
  session.id,
  events: [{
    type: "user.message",
    content: [{type: "text", text: "Review the auth module"}]
  }]
)
```

> 💡 **先开启流：** 在发送消息*之前*（或同时）开启流。流只传递开启后发生的事件——先发送消息后开启流意味着早期事件会以缓冲方式一次性到达。参见 [Steering Patterns](../../shared/managed-agents-events.md#steering-patterns)。

---

## 流式事件（SSE）

```ruby
# 先开启流，再发送用户消息
stream = client.beta.sessions.events.stream_events(session.id)

client.beta.sessions.events.send_(
  session.id,
  events: [{
    type: "user.message",
    content: [{type: "text", text: "Summarize the repo README"}]
  }]
)

stream.each do |event|
  case event.type
  in :"agent.message"
    event.content.each { |block| print block.text }
  in :"agent.tool_use"
    puts "\n[使用工具: #{event.name}]"
  in :"session.status_idle"
    break
  in :"session.error"
    puts "\n[错误: #{event.error&.message || "未知"}]"
    break
  else
    # 忽略其他事件类型
  end
end
```

> ℹ️ 事件 `.type` 是 Symbol 类型（使用 `:"agent.message"` 比较，而非 `"agent.message"`）。

### 重连与尾部追踪

在 session 中间重连时，先列出已发生的事件以去重，然后追踪实时事件：

```ruby
require "set"

stream = client.beta.sessions.events.stream_events(session.id)

# 流已开启并正在缓冲。在追踪实时事件前先列出历史记录。
seen_event_ids = Set.new
client.beta.sessions.events.list(session.id).auto_paging_each { |past| seen_event_ids << past.id }

# 追踪实时事件，跳过已出现的
stream.each do |event|
  next if seen_event_ids.include?(event.id)
  seen_event_ids << event.id
  case event.type
  in :"agent.message"
    event.content.each { |block| print block.text }
  in :"session.status_idle"
    break
  else
    # 忽略其他事件类型
  end
end
```

---

## 提供自定义工具结果

> ℹ️ Ruby 中 `user.custom_tool_result` 的 managed-agents 绑定尚未在本 skill 或 apps 源代码示例中记录。请参考 `shared/managed-agents-events.md` 了解 wire 格式，以及 `anthropic` Ruby gem 仓库了解对应的参数。

---

## 轮询事件

```ruby
client.beta.sessions.events.list(session.id).auto_paging_each do |event|
  puts "#{event.type}: #{event.id}"
end
```

---

## 上传文件

```ruby
require "pathname"

file = client.beta.files.upload(file: Pathname("data.csv"))
puts "File ID: #{file.id}"

# 挂载到 session 中
session = client.beta.sessions.create(
  agent: agent.id,
  environment_id: environment.id,
  resources: [
    {
      type: "file",
      file_id: file.id,
      mount_path: "/workspace/data.csv"
    }
  ]
)
```

### 在已有 Session 上添加和管理资源

```ruby
# 向已开启的 session 附加一个文件
resource = client.beta.sessions.resources.add(
  session.id,
  type: "file",
  file_id: file.id
)
puts resource.id # "sesrsc_01ABC..."

# 列出 session 上的资源
listed = client.beta.sessions.resources.list(session.id)
listed.data.each { |entry| puts "#{entry.id} #{entry.type}" }

# 移除资源
client.beta.sessions.resources.delete(resource.id, session_id: session.id)
```

---

## 列出和下载 Session 文件

> ℹ️ 列出和下载 agent 在 session 期间写入的文件尚未在 Ruby 的此 skill 或 apps 源代码示例中记录。请参见 `shared/managed-agents-events.md` 和 `anthropic` Ruby gem 仓库了解文件列表/下载的绑定。

---

## Session 管理

```ruby
# 列出 environments
environments = client.beta.environments.list

# 检索特定 environment
env = client.beta.environments.retrieve(environment.id)

# 归档 environment（只读，已有 session 继续运行）
client.beta.environments.archive(environment.id)

# 删除 environment（仅在无 session 引用时）
client.beta.environments.delete(environment.id)

# 删除 session
client.beta.sessions.delete(session.id)
```

---

## MCP 服务器集成

```ruby
# Agent 声明 MCP 服务器（认证信息不在此处——认证信息存放在 vault 中）
agent = client.beta.agents.create(
  name: "GitHub Assistant",
  model: :"claude-opus-4-8",
  mcp_servers: [
    {
      type: "url",
      name: "github",
      url: "https://api.githubcopilot.com/mcp/"
    }
  ],
  tools: [
    {type: "agent_toolset_20260401"},
    {type: "mcp_toolset", mcp_server_name: "github"}
  ]
)

# Session 附加包含这些 MCP 服务器 URL 凭据的 vault
session = client.beta.sessions.create(
  agent: {type: "agent", id: agent.id, version: agent.version},
  environment_id: environment.id,
  vault_ids: [vault.id]
)
```

关于创建 vault 和添加凭据，请参见 `shared/managed-agents-tools.md` §Vaults。

---

## Vaults

```ruby
# 创建 vault
vault = client.beta.vaults.create(
  display_name: "Alice",
  metadata: {external_user_id: "usr_abc123"}
)
puts vault.id # "vlt_01ABC..."

# 添加 OAuth 凭据
credential = client.beta.vaults.credentials.create(
  vault.id,
  display_name: "Alice's Slack",
  auth: {
    type: "mcp_oauth",
    mcp_server_url: "https://mcp.slack.com/mcp",
    access_token: "xoxp-...",
    expires_at: "2026-04-15T00:00:00Z",
    refresh: {
      token_endpoint: "https://slack.com/api/oauth.v2.access",
      client_id: "1234567890.0987654321",
      scope: "channels:read chat:write",
      refresh_token: "xoxe-1-...",
      token_endpoint_auth: {
        type: "client_secret_post",
        client_secret: "abc123..."
      }
    }
  }
)

# 轮换凭据（例如，在 token 刷新后）
client.beta.vaults.credentials.update(
  credential.id,
  vault_id: vault.id,
  auth: {
    type: "mcp_oauth",
    access_token: "xoxp-new-...",
    expires_at: "2026-05-15T00:00:00Z",
    refresh: {refresh_token: "xoxe-1-new-..."}
  }
)

# 归档 vault
client.beta.vaults.archive(vault.id)
```

---

## GitHub 仓库集成

将 GitHub 仓库挂载为 session 资源（vault 持有 GitHub MCP 凭据）：

```ruby
session = client.beta.sessions.create(
  agent: agent.id,
  environment_id: environment.id,
  vault_ids: [vault.id],
  resources: [
    {
      type: "github_repository",
      url: "https://github.com/org/repo",
      mount_path: "/workspace/repo",
      authorization_token: "ghp_your_github_token"
    }
  ]
)
```

同一 session 上的多个仓库：

```ruby
resources = [
  {
    type: "github_repository",
    url: "https://github.com/org/frontend",
    mount_path: "/workspace/frontend",
    authorization_token: "ghp_your_github_token"
  },
  {
    type: "github_repository",
    url: "https://github.com/org/backend",
    mount_path: "/workspace/backend",
    authorization_token: "ghp_your_github_token"
  }
]
```

轮换仓库的授权 token：

```ruby
listed = client.beta.sessions.resources.list(session.id)
repo_resource_id = listed.data.first.id

client.beta.sessions.resources.update(
  repo_resource_id,
  session_id: session.id,
  authorization_token: "ghp_your_new_github_token"
)
```
