# 托管智能体 — 环境与资源

## 环境

创建会话需要 `environment_id`。环境是**可重用的配置模板**，用于在 Anthropic 的基础设施中启动容器 — 您可以为不同的用例创建不同的环境（例如数据可视化 vs Web 开发，带有不同的包集）。Anthropic 处理扩展、容器生命周期和工作编排。

**环境名称必须是唯一的。** 使用现有名称创建环境会返回 409。

### 网络

| 网络策略                  | 描述                                                   |
| ------------------------------- | ------------------------------------------------------------- |
| `unrestricted`                  | 完整出站流量（法律阻止列表除外）                          |
| `package_managers_and_custom`   | 包管理器 + 自定义 `allowed_hosts`                      |

```json
{
  "networking": {
    "type": "package_managers_and_custom",
    "allowed_hosts": ["api.example.com"]
  }
}
```

**MCP 注意事项：** 如果使用受限网络，请确保 `allowed_hosts` 包含您的 MCP 服务器域。否则容器无法访问它们，工具会静默失败。

### 创建环境

SDK 会自动添加 `managed-agents-2026-04-01`。TypeScript：

```ts
const env = await client.beta.environments.create({
  name: "my_env",
  config: {
    type: "cloud",
    networking: { type: "unrestricted" },
  },
});
```

### 自托管沙箱

要在**您自己的基础设施**而不是 Anthropic 的基础设施中运行工具执行，请设置 `config: {type: "self_hosted"}` — 智能体循环保留在 Anthropic 端，但 `bash` / 文件操作 / 代码在您通过出站轮询 worker 控制的容器中执行。`networking` 块不适用（您控制出站）。资源挂载（`file`、`github_repository`）和记忆存储的行为不同 — 请参阅 `shared/managed-agents-self-hosted-sandboxes.md` 了解 worker、凭证以及云 vs 自托管比较。

### 环境 CRUD

| 操作        | 方法   | 路径                                       | 注意 |
| ---------------- | -------- | ------------------------------------------ | ----- |
| 创建           | `POST`   | `/v1/environments`                         | |
| 列表             | `GET`    | `/v1/environments`                         | 分页（`limit`、`after_id`、`before_id`）|
| 获取              | `GET`    | `/v1/environments/{id}`                    | |
| 更新           | `POST`   | `/v1/environments/{id}`                    | 更改仅应用于**新**容器；现有会话保留其原始配置 |
| 删除           | `DELETE` | `/v1/environments/{id}`                    | 返回 204。 |
| 归档          | `POST`   | `/v1/environments/{id}/archive`            | 使其变为**只读**；现有会话继续，新会话无法引用它。无法取消归档 — 终端状态。 |

---

## 资源

将文件、GitHub 仓库和记忆存储附加到会话。**会话创建会阻塞，直到所有资源都挂载完毕** — 容器在每个文件和仓库都就位之前不会进入 `running` 状态。每个会话最多 **999 个文件资源**。每个会话支持多个 GitHub 仓库。对于 `type: "memory_store"` 资源（跨会话的持久记忆 — 每个会话最多 8 个），请参阅 `shared/managed-agents-memory.md`。

### 文件上传（输入 — 主机 → 智能体）

首先通过文件 API 上传文件，然后通过 `file_id` + `mount_path` 引用：

```ts
// 1. 上传
const file = await client.beta.files.upload({
  file: fs.createReadStream("data.csv"),
});

// 2. 作为会话资源附加
const session = await client.beta.sessions.create({
  agent: agent.id,
  environment_id: envId,
  resources: [
    { type: "file", file_id: file.id, mount_path: "/workspace/data.csv" }
  ],
});
```

**`mount_path` 是必需的**，并且必须是绝对路径。父目录会自动创建。智能体工作目录默认为 `/workspace`。文件以只读方式挂载 — 智能体将修改后的版本写入新路径。

### 会话输出（输出 — 智能体 → 主机）

智能体可以在会话期间将文件写入 `/mnt/session/outputs/`。这些会被文件 API 自动捕获，之后可以列出和下载：

```ts
// 轮次完成后，列出此会话范围的输出文件：
for await (const f of client.beta.files.list({
  scope_id: session.id,
  betas: ["managed-agents-2026-04-01"],
})) {
  console.log(f.filename, f.size_bytes);
  const resp = await client.beta.files.download(f.id);
  const text = await resp.text();
}
```

**要求：**
- 必须启用 `write` 工具（或 `bash`），智能体才能创建输出文件。
- 会话范围的 `files.list` / `files.download` 捕获写入 `/mnt/session/outputs/` 的输出。
- 过滤器参数是 **`scope_id`**（REST 查询参数 `?scope_id=<session_id>`）。SDK 的文件资源仅自动添加 `files-api-2025-04-14` 头，因此请显式传递 `betas: ["managed-agents-2026-04-01"]`（或原始 HTTP 上的两个头）— 没有它，API 可能会拒绝 `scope_id` 为未知字段。需要 `@anthropic-ai/sdk` ≥ 0.88.0 / `anthropic`（Python）≥ 0.92.0 — 旧版本不键入 `scope_id`。`ant` CLI 目前**不**暴露此标志；使用 SDK 或 curl。
- 逐字传递 `sessions.create()` 返回的会话 ID（例如 `sesn_011CZx...`）— API 会验证前缀。
- 从 `session.status_idle` 到输出文件出现在 `files.list` 之间有短暂的索引延迟（~1–3 秒）。如果为空，请重试一两次。

> **当 `scope_id` 过滤不可用时的回退**（旧 SDK，或端点返回错误）：发送后续的 `user.message`，要求智能体 `read` `/mnt/session/outputs/` 下的每个文件并返回内容。智能体以 `agent.message` 文本流的形式将文件正文传回。这仅适用于文本文件，并且需要输出令牌成本 — 使用它来解除阻塞，而不是作为主要路径。

这为您提供了一个双向文件桥：上传参考数据，下载智能体工件。

### GitHub 仓库

在初始化期间，在智能体开始执行之前将 GitHub 仓库克隆到会话容器中。智能体可以通过 `bash`（`git`）读取、编辑、提交和推送。每个会话支持多个仓库 — 每个仓库添加一个 `resources` 条目。仓库会被缓存，因此使用同一仓库的未来会话启动更快。

仓库在会话的整个生命周期内都会附加 — 要更改挂载的仓库，请创建新会话。您**可以**通过 `client.beta.sessions.resources.update(resource_id, {session_id, authorization_token})` 在运行的会话上轮换仓库的 `authorization_token`；资源 `id` 在会话创建时返回并由 `resources.list()` 返回。

**字段：**

| 字段 | 必需 | 注意 |
|---|---|---|
| `type` | ✅ | `"github_repository"` |
| `url` | ✅ | GitHub 仓库 URL |
| `authorization_token` | ✅ | 具有仓库访问权限的 GitHub 个人访问令牌。**永远不会在 API 响应中回显。** |
| `mount_path` | ❌ | 仓库克隆的路径。默认为 `/workspace/<仓库名称>`。 |
| `checkout` | ❌ | `{type: "branch", name: "..."}` 或 `{type: "commit", sha: "..."}`。默认为仓库的默认分支。 |

**令牌权限级别**（细粒度 PAT）：
- `Contents: Read` — 仅克隆
- `Contents: Read and write` — 推送更改和创建拉取请求

**认证工作原理：** `authorization_token` 永远不会放置在容器内。对附加仓库的 `git pull` / `git push` 和 GitHub REST 调用通过 Anthropic 端的 git 代理路由，该代理在请求离开沙箱后注入令牌。在容器中运行的代码 — 包括智能体编写的任何内容 — 无法读取或窃取它。

> ‼️ **要生成拉取请求**，您还需要 GitHub **MCP 服务器**访问权限 — `github_repository` 资源仅提供文件系统 + git 访问。请参阅 `shared/managed-agents-tools.md` → MCP 服务器。PR 工作流程是：在挂载的仓库中编辑文件 → 通过 `bash` 推送分支（使用 `authorization_token` 通过 git 代理认证）→ 通过 MCP `create_pull_request` 工具创建 PR（通过保管库认证）。

**TypeScript：**

```ts
// 1. 创建智能体 — 声明 GitHub MCP（此处无认证）
const agent = await client.beta.agents.create(
  {
    name: 'GitHub 智能体',
    model: 'claude-opus-4-8',
    mcp_servers: [
      { type: 'url', name: 'github', url: 'https://api.githubcopilot.com/mcp/' },
    ],
    tools: [
      { type: 'agent_toolset_20260401', default_config: { enabled: true } },
      { type: 'mcp_toolset', mcp_server_name: 'github' },
    ],
  },
);

// 2. 启动会话 — 附加 MCP 认证的保管库 + 挂载仓库
const session = await client.beta.sessions.create({
  agent: agent.id,
  environment_id: envId,
  vault_ids: [vaultId],  // 保管库包含 GitHub MCP OAuth 凭证
  resources: [
    {
      type: 'github_repository',
      url: 'https://github.com/owner/repo',
      authorization_token: process.env.GITHUB_TOKEN,  // 仓库克隆令牌（≠ MCP 认证）
      checkout: { type: 'branch', name: 'main' },
    },
  ],
});
```

**Python：**

```python
import os

agent = client.beta.agents.create(
    name="GitHub 智能体",
    model="claude-opus-4-8",
    mcp_servers=[{
        "type": "url",
        "name": "github",
        "url": "https://api.githubcopilot.com/mcp/",
    }],
    tools=[
        {"type": "agent_toolset_20260401", "default_config": {"enabled": True}},
        {"type": "mcp_toolset", "mcp_server_name": "github"},
    ],
)

session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=env_id,
    vault_ids=[vault_id],  # 保管库包含 GitHub MCP OAuth 凭证
    resources=[{
        "type": "github_repository",
        "url": "https://github.com/owner/repo",
        "authorization_token": os.environ["GITHUB_TOKEN"],  # 仓库克隆令牌（≠ MCP 认证）
        "checkout": {"type": "branch", "name": "main"},
    }],
)
```

---

## 文件 API

上传和管理文件以用作会话资源，并下载智能体写入 `/mnt/session/outputs/` 的文件。

| 操作        | 方法   | 路径                                  | SDK |
| ---------------- | -------- | ------------------------------------- | --- |
| 上传           | `POST`   | `/v1/files`                           | `client.beta.files.upload({ file })` |
| 列表             | `GET`    | `/v1/files?scope_id=...`              | `client.beta.files.list({ scope_id, betas: ["managed-agents-2026-04-01"] })` |
| 获取元数据     | `GET`    | `/v1/files/{id}`                      | `client.beta.files.retrieveMetadata(id)` |
| 下载         | `GET`    | `/v1/files/{id}/content`              | `client.beta.files.download(id)` → `Response` |
| 删除           | `DELETE` | `/v1/files/{id}`                      | `client.beta.files.delete(id)` |

列表上的 `scope_id` 过滤器将结果限定为该会话写入 `/mnt/session/outputs/` 的文件。如果没有过滤器，您会获得上传到您账户的所有文件。
