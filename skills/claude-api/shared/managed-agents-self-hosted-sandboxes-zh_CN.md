# 托管智能体 — 自托管沙箱

使用 `config.type: "self_hosted"`，**智能体循环保留在 Anthropic 的编排层上**，但**工具执行移到您控制的基础设施** — bash、文件操作和代码在您的容器内运行，因此文件系统内容和网络出站永远不会离开您的环境。与 `config.type: "cloud"` 形成对比，其中 Anthropic 运行容器。连接是**仅出站**的：您的工作器长轮询 Anthropic 的工作队列；Anthropic 永远不会拨入您的网络。

## 流程

```
1. 创建环境：      config: {type: "self_hosted"}        → env_...
2. 生成环境密钥（控制台，在环境页面上）   → sk-ant-oat01-... 作为 ANTHROPIC_ENVIRONMENT_KEY
3. 运行工作器：            EnvironmentWorker.run()  或 ant beta:worker poll
4. 会话引用       environment_id=env_...  与 cloud 完全一样
```

## 创建环境

```python
client = anthropic.Anthropic()

environment = client.beta.environments.create(
    name="self-hosted", config={"type": "self_hosted"}
)
```

`{"type": "self_hosted"}` 是完整的配置 — 没有池、容量或网络子字段；您在自己这边控制那些。

## 运行工作器 — SDK（主要路径）

`EnvironmentWorker` 包装轮询 → 分发 → 工具执行循环。`.run()` 是始终在线的循环；`.run_one()` / `.runOne()` 处理一个工作项（用于 webhook 驱动的唤醒）。

**Python — 始终在线：**

```python
import asyncio
import os
from anthropic import AsyncAnthropic
from anthropic.lib.environments import EnvironmentWorker


async def main() -> None:
    environment_key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]
    environment_id = os.environ["ANTHROPIC_ENVIRONMENT_ID"]
    async with AsyncAnthropic(auth_token=environment_key) as client:
        await EnvironmentWorker(
            client,
            environment_id=environment_id,
            environment_key=environment_key,
            workdir="/workspace",
        ).run()


asyncio.run(main())
```

**TypeScript — 始终在线：**

```typescript
import Anthropic from "@anthropic-ai/sdk";
import { EnvironmentWorker } from "@anthropic-ai/sdk/helpers/beta/environments";

const environmentKey = process.env.ANTHROPIC_ENVIRONMENT_KEY!;
const environmentId = process.env.ANTHROPIC_ENVIRONMENT_ID!;
const client = new Anthropic({ authToken: environmentKey });
const ctrl = new AbortController();
process.once("SIGTERM", () => ctrl.abort());

await new EnvironmentWorker({
  client,
  environmentId,
  environmentKey,
  workdir: "/workspace",
  signal: ctrl.signal
}).run();
```

**自定义工具。** `EnvironmentWorker` 默认运行内置工具集。要添加或替换工具，请将 `AgentToolContext(workdir=, client=, session_id=)` 与 `beta_agent_toolset(env)` / `betaAgentToolset(env)` 一起使用，并将生成的工具传递给较低级别的 `tool_runner()`。附加到智能体的技能在工具调用开始之前下载到 `{workdir}/skills/<name>/`（当给定 `client` 和 `session_id` 时，`AgentToolContext` 会处理这个）。下载的技能文件由 CLI 和 SDK 自动标记为可执行；如果您自己实现技能下载，请自行设置权限。

> **运行时依赖项：** SDK 帮助程序需要在确切路径上有 `/bin/bash`。TypeScript SDK 还需要 `unzip`、`tar` 和 Node.js 22+。这些在固定路径解析，**不**遵循 `PATH` 覆盖。

## 运行工作器 — `ant` CLI（固定工具）

`ant` CLI 附带了带有固定内置工具集（`bash`、`read`、`write`、`edit`、`glob`、`grep`）的工作器。按照 Anthropic CLI 文档中的说明安装（请参阅 `shared/live-sources.md` → Anthropic CLI），然后：

```sh
export ANTHROPIC_ENVIRONMENT_KEY=sk-ant-oat01-...
ant beta:worker poll --environment-id env_... --workdir /workspace
```

- `--workdir` 是工具运行的目录（默认 `.`）；工具调用被沙箱限制在其中。
- `--environment-key` 覆盖环境变量。
- `--on-work <script>` 按工作项运行您的脚本（例如，为每个会话旋转一个新容器 — 请参阅下面的容器编排）。
- `--unrestricted-paths`、`--max-idle`（默认 `60s`）、`--log-format` — 请参阅 `ant beta:worker poll --help`。
- 标志回退到环境变量（`ANTHROPIC_ENVIRONMENT_ID`、`ANTHROPIC_ENVIRONMENT_KEY`）。
- 在 SIGTERM/SIGINT 上干净退出，在排空正在进行的工作后。
- **固定工具集** — 对于自定义工具，请使用上面的 SDK 工作器。

在 `--on-work` 容器内，将 `ant beta:worker run --workdir <dir>` 作为入口点运行。

## Webhook 驱动的唤醒（而不是始终在线）

为 `session.status_run_started` 注册一个 webhook（请参阅 `shared/managed-agents-webhooks.md`），验证交付，然后使用 `.run_one()` 排空一个工作项：

```python
import os
import anthropic
from anthropic.lib.environments import EnvironmentWorker

environment_key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]
environment_id = os.environ["ANTHROPIC_ENVIRONMENT_ID"]
client = anthropic.AsyncAnthropic(
    auth_token=environment_key,
)  # 从 env 读取 ANTHROPIC_WEBHOOK_SIGNING_KEY 用于 webhooks.unwrap()


async def handle(raw: bytes, headers: dict[str, str]) -> dict:
    event = client.beta.webhooks.unwrap(raw.decode(), headers=headers)
    if event.data.type != "session.status_run_started":
        return {"status": "ignored"}
    await EnvironmentWorker(
        client,
        environment_id=environment_id,
        environment_key=environment_key,
        workdir="/workspace",
    ).run_one()
    return {"status": "ok"}
```

TypeScript：相同的形状，带有 `client.beta.webhooks.unwrap(body, {headers})` 和 `new EnvironmentWorker({...}).runOne()`。

## 容器编排（中级）

`EnvironmentWorker.run()` 在同一进程中轮询和执行工具。要在**自己的**容器中运行每个会话，请在精简的编排器中使用中级轮询器 — Python `client.beta.environments.work.poller(environment_id=, environment_key=, drain=, block_ms=, reclaim_older_than_ms=, auto_stop=)`；TypeScript `new WorkPoller({client, environmentId, environmentKey, autoStop})` 来自 `@anthropic-ai/sdk/helpers/beta/environments` — 并且，对于每个产生的 `work` 项，使用注入的这些环境变量启动一个新容器，其入口点运行 `ant beta:worker run` 或 `EnvironmentWorker(...).run_one()`。`block_ms` 是 1–999（或 `None` 用于非阻塞）；`reclaim_older_than_ms` 回收租给死工作器的项目；`drain` 在队列为空时停止；`auto_stop` 在迭代器退出后发布停止信号（当启动的容器拥有停止调用时设置为 `False`）。**Go 的轮询器没有 `auto_stop` 选择退出** — 它在处理程序返回时调用 `work.Stop`，所以在处理程序中阻塞直到会话完成，而不是分离。

| 环境变量 | 值 |
|---|---|
| `ANTHROPIC_SESSION_ID` | `work.data.id` |
| `ANTHROPIC_WORK_ID` | `work.id` |
| `ANTHROPIC_ENVIRONMENT_ID` | `work.environment_id` |
| `ANTHROPIC_ENVIRONMENT_KEY` | 传递 |
| `ANTHROPIC_BASE_URL` | 传递 |

跳过 `work.data.type != "session"` 的项目。

## 监控和控制

这些是**控制平面**调用 — 使用 `x-api-key` 认证（不是环境密钥）；`managed-agents-2026-04-01` beta 头。**从工作器主机外部调用它们** — 在工作器主机上设置 `ANTHROPIC_API_KEY` 会将组织范围的凭证暴露给智能体工具调用。

| SDK（`client.beta.environments.work.*`） | REST | CLI | 返回 |
|---|---|---|---|
| `stats(environment_id)` | `GET /v1/environments/{id}/work/stats` | `ant beta:environments:work stats` | `{type:"work_queue_stats", depth, pending, oldest_queued_at, workers_polling}` |
| `stop(work_id, environment_id=)` | `POST /v1/environments/{id}/work/{work_id}/stop` | `ant beta:environments:work stop` | `work.state` |

## 与 `cloud` 对比的变化

| 关注点 | `cloud` | `self_hosted` |
|---|---|---|
| 容器生命周期、加固、网络 | Anthropic | **您** — 以非 root 身份运行、只读 rootfs、删除能力；出站是您的 VPC/防火墙允许的任何内容 |
| `file` / `github_repository` 资源挂载 | Anthropic 挂载到容器 | **您** — 通过 `sessions.create(metadata={...})` 传递指针，并让您的编排器在分发之前获取/克隆 |
| `memory_store` 资源 | 支持 | **尚不支持** |
| 内置工具 | 通过 `agent_toolset_20260401` | 由您的工作器提供（`EnvironmentWorker` 默认 / `beta_agent_toolset(env)` / `ant` CLI 固定集） |
| 技能下载 | 自动 | `EnvironmentWorker` / `AgentToolContext` 获取到 `{workdir}/skills/`（需要 `client` + `session_id`） |
| Claude Platform on AWS | 支持 | **不可用** |
| SDK 工作器帮助程序 | 所有 SDK | **仅限 Python、TypeScript、Go**（`EnvironmentWorker` / 轮询器不在 Java、Ruby、PHP 或 C# 中）— 使用这三个之一或 `ant` CLI |

## 凭证

| 凭证 | 格式 | 范围 |
|---|---|---|
| `ANTHROPIC_ENVIRONMENT_KEY` | `sk-ant-oat01-...` | 一个环境的工作队列。在控制台中生成（"生成环境密钥"）。作为客户端上的 `auth_token=` / `authToken` 以及 `EnvironmentWorker` 上的 `environment_key=` / `environmentKey` 传递。存储在密钥管理器中；暴露时轮换。 |
| `ANTHROPIC_WEBHOOK_SIGNING_KEY` | `whsec_...` | Webhook 签名验证（如果使用 webhook 驱动的唤醒）。SDK 会自动为 `client.beta.webhooks.unwrap()` 读取此环境变量。 |

## 安全性 — 您拥有什么

容器加固；出站限制（没有默认值）；`ANTHROPIC_ENVIRONMENT_KEY` 保管和轮换；运行不受信任的代码时，每个信任边界一个工作区 + 环境；工具进程的最小特权；日志保留和修订。**Anthropic 不能：** 快速撤销泄露的环境密钥、验证您的镜像或供应链、在您的容器内沙箱化工具执行，或在工具输出到达您的基础设施后强制执行保留。完整的检查清单请参阅 `shared/live-sources.md` 中的自托管沙箱安全页面。
