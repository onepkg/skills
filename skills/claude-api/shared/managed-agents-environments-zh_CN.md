# 托管Agent — 环境与资源

## 环境

创建会话需要提供 `environment_id`。环境是**可复用的配置模板**，用于在 Anthropic 的基础设施中启动容器——你可以针对不同的使用场景创建不同的环境（例如数据可视化与 Web 开发，使用不同的软件包集合）。Anthropic 负责处理扩缩容、容器生命周期和工作编排。

**环境名称必须唯一。** 使用已有名称创建环境将返回 409。

### 网络

| 网络策略                         | 描述                                                    |
| ------------------------------- | ------------------------------------------------------- |
| `unrestricted`                  | 完全出站（法律禁止列表除外）                             |
| `package_managers_and_custom`   | 包管理器 + 自定义 `allowed_hosts`                        |

```json
{
  "networking": {
    "type": "package_managers_and_custom",
    "allowed_hosts": ["api.example.com"]
  }
}
```

**MCP 注意事项：** 如果使用受限网络，请确保 `allowed_hosts` 包含你的 MCP 服务器域名。否则容器无法访问它们，工具将静默失败。

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

若要在**你自己的基础设施**中运行工具执行（而非 Anthropic 的基础设施），设置 `config: {type: "self_hosted"}`——Agent 循环仍保留在 Anthropic 侧，但 `bash`/文件操作/代码执行在你通过出站轮询 Worker 控制的容器中运行。`networking` 块不适用（出站由你控制）。资源挂载（`file`、`github_repository`）和内存存储的行为有所不同——参见 `shared/managed-agents-self-hosted-sandboxes.md` 了解 Worker、凭据以及云托管与自托管的对比。

### 环境 CRUD

| 操作        | 方法     | 路径                                       | 说明 |
| ----------- | -------- | ------------------------------------------ | ---- |
| 创建        | `POST`   | `/v1/environments`                         | |
| 列表        | `GET`    | `/v1/environments`                         | 分页（`limit`、`after_id`、`before_id`） |
| 获取        | `GET`    | `/v1/environments/{id}`                    | |
| 更新        | `POST`   | `/v1/environments/{id}`                    | 更改仅适用于**新**容器；现有会话保留原有配置 |
| 删除        | `DELETE` | `/v1/environments/{id}`                    | 返回 204。 |
| 归档        | `POST`   | `/v1/environments/{id}/archive`            | 使其变为**只读**；现有会话继续运行，新会话无法引用。不可取消归档——终态。 |

---

## 资源

将文件、GitHub 仓库和内存存储附加到会话。**会话创建会阻塞，直到所有资源挂载完成**——容器在所有文件和仓库就位之前不会进入 `running` 状态。每个会话最多 **999 个文件资源**。每个会话支持多个 GitHub 仓库。对于 `type: "memory_store"` 类型的资源（持久化跨会话内存——每个会话最多 8 个），参见 `shared/managed-agents-memory.md`。

### 文件上传（输入——主机 → Agent）

首先通过 Files API 上传文件，然后通过 `file_id` + `mount_path` 引用：

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

**`mount_path` 为必填项**，且必须为绝对路径。父目录会自动创建。Agent 的工作目录默认为 `/workspace`。文件以只读方式挂载——Agent 将修改后的版本写入新路径。

### 会话输出（输出——Agent → 主机）

Agent 可以在会话期间将文件写入 `/mnt/session/outputs/`。这些文件会被 Files API 自动捕获，之后可以列出并下载：

```ts
// 回合完成后，列出此会话范围内的输出文件：
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
- 必须启用 `write` 工具（或 `bash`），Agent 才能创建输出文件。
- 会话范围内的 `files.list` / `files.download` 可捕获写入 `/mnt/session/outputs/` 的输出。
- 过滤参数是 **`scope_id`**（REST 查询参数 `?scope_id=<session_id>`）。SDK 的 files 资源仅自动添加 `files-api-2025-04-14` 标头，因此需要显式传递 `betas: ["managed-agents-2026-04-01"]`（或在原始 HTTP 上同时传递两个标头）——否则 API 可能因未知字段而拒绝 `scope_id`。需要 `@anthropic-ai/sdk` ≥ 0.88.0 / `anthropic`（Python）≥ 0.92.0——旧版本不包含 `scope_id` 类型。`ant` CLI **尚未**暴露此标志；请使用 SDK 或 curl。
- 按原样传递 `sessions.create()` 返回的会话 ID（例如 `sesn_011CZx...`）——API 会验证前缀。
- `session.status_idle` 与输出文件出现在 `files.list` 之间存在短暂的索引延迟（约 1–3 秒）。如果为空，请重试一到两次。

> **当 `scope_id` 过滤不可用时的回退方案**（旧版 SDK，或端点返回错误）：发送后续 `user.message` 要求 Agent 读取 `/mnt/session/outputs/` 下的每个文件并返回内容。Agent 将文件内容以 `agent.message` 文本形式流式返回。此方法仅适用于文本文件，且会消耗输出 Token——仅用于应急，不建议作为主要方式。

这样就构成了一个双向文件桥：上传参考数据输入，下载 Agent 制品输出。

### GitHub 仓库

在 Agent 开始执行之前，在初始化阶段将 GitHub 仓库克隆到会话容器中。Agent 可以通过 `bash`（`git`）读取、编辑、提交和推送。每个会话支持多个仓库——每个仓库添加一个 `resources` 条目。仓库会被缓存，因此后续使用同一仓库的会话启动更快。

仓库在会话的整个生命周期内保持挂载——要更改挂载的仓库，请创建新会话。你**可以**通过 `client.beta.sessions.resources.update(resource_id, {session_id, authorization_token})` 在运行中的会话上轮换仓库的 `authorization_token`；资源 `id` 在会话创建时和 `resources.list()` 中返回。

**字段：**

| 字段 | 必填 | 说明 |
|---|---|---|
| `type` | ✅ | `"github_repository"` |
| `url` | ✅ | GitHub 仓库 URL |
| `authorization_token` | ✅ | 具有仓库访问权限的 GitHub Personal Access Token。**绝不会在 API 响应中回显。** |
| `mount_path` | ❌ | 仓库克隆到的路径。默认为 `/workspace/<repo-name>`。 |
| `checkout` | ❌ | `{type: "branch", name: "..."}` 或 `{type: "commit", sha: "..."}`。默认为仓库的默认分支。 |

**Token 权限级别**（细粒度 PAT）：
- `Contents: Read` — 仅克隆
- `Contents: Read and write` — 推送更改和创建 Pull Request

**认证机制：** `authorization_token` 永远不会被放入容器内部。`git pull` / `git push` 以及针对已挂载仓库的 GitHub REST 调用通过 Anthropic 侧的 Git 代理路由，代理在请求离开沙箱后注入 Token。容器中运行的代码——包括 Agent 编写的任何内容——无法读取或窃取该 Token。

> ‼️ **要生成 Pull Request**，你还需要 GitHub **MCP 服务器**访问权限——`github_repository` 资源仅提供文件系统和 Git 访问权限。参见 `shared/managed-agents-tools.md` → MCP 服务器。PR 工作流程为：在挂载的仓库中编辑文件 → 通过 `bash` 推送分支（通过 Git 代理使用 `authorization_token` 进行认证）→ 通过 MCP `create_pull_request` 工具创建 PR（通过 vault 进行认证）。

**TypeScript：**

```ts
// 1. 创建 Agent — 声明 GitHub MCP（此处无需认证）
const agent = await client.beta.agents.create(
  {
    name: 'GitHub Agent',
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

// 2. 启动会话 — 附加 vault 用于 MCP 认证 + 挂载仓库
const session = await client.beta.sessions.create({
  agent: agent.id,
  environment_id: envId,
  vault_ids: [vaultId],  // vault 包含 GitHub MCP OAuth 凭据
  resources: [
    {
      type: 'github_repository',
      url: 'https://github.com/owner/repo',
      authorization_token: process.env.GITHUB_TOKEN,  // 仓库克隆 token（≠ MCP 认证）
      checkout: { type: 'branch', name: 'main' },
    },
  ],
});
```

**Python：**

```python
import os

agent = client.beta.agents.create(
    name="GitHub Agent",
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
    vault_ids=[vault_id],  # vault 包含 GitHub MCP OAuth 凭据
    resources=[{
        "type": "github_repository",
        "url": "https://github.com/owner/repo",
        "authorization_token": os.environ["GITHUB_TOKEN"],  # 仓库克隆 token（≠ MCP 认证）
        "checkout": {"type": "branch", "name": "main"},
    }],
)
```

---

## Files API

上传和管理文件以用作会话资源，并下载 Agent 写入 `/mnt/session/outputs/` 的文件。

| 操作        | 方法     | 路径                                  | SDK |
| ----------- | -------- | ------------------------------------- | --- |
| 上传        | `POST`   | `/v1/files`                           | `client.beta.files.upload({ file })` |
| 列表        | `GET`    | `/v1/files?scope_id=...`              | `client.beta.files.list({ scope_id, betas: ["managed-agents-2026-04-01"] })` |
| 获取元数据  | `GET`    | `/v1/files/{id}`                      | `client.beta.files.retrieveMetadata(id)` |
| 下载        | `GET`    | `/v1/files/{id}/content`              | `client.beta.files.download(id)` → `Response` |
| 删除        | `DELETE` | `/v1/files/{id}`                      | `client.beta.files.delete(id)` |

List 操作上的 `scope_id` 过滤将结果限定为该会话写入 `/mnt/session/outputs/` 的文件。不使用过滤时，你将获取上传到账户的所有文件。
