# 托管智能体 — 自托管沙箱

使用 `config.type: "self_hosted"` 时，**智能体循环保留在 Anthropic 的编排层**，但**工具执行转移到您控制的基础设施** — bash、文件操作和代码在您的容器内运行，因此文件系统内容和网络出口永远不会离开您的环境。与 `config.type: "cloud"`（Anthropic 运行容器）相比。连接是**仅出站**的：您的 Worker 长轮询 Anthropic 的工作队列；Anthropic 从不拨入您的网络。

## 流程

```
1. Create environment:      config: {type: "self_hosted"}        → env_...
2. Generate environment key (Console, on the environment page)   → sk-ant-oat01-...  as ANTHROPIC_ENVIRONMENT_KEY
3. Run a worker:            EnvironmentWorker.run()  or  ant beta:worker poll
4. Sessions reference       environment_id=env_... exactly as for cloud
```

## 创建环境

```python
client = anthropic.Anthropic()

environment = client.beta.environments.create(
    name="self-hosted", config={"type": "self_hosted"}
)
```

`{"type": "self_hosted"}` 就是完整的配置 — 没有池、容量或网络子字段；您可以在自己这边控制这些。

## 运行 Worker — SDK（主要路径）

`EnvironmentWorker` 封装了轮询 → 调度 → 工具执行循环。`.run()` 是始终在线的循环；`.run_one()` / `.runOne()` 处理一个工作项（用于 Webhook 驱动的唤醒）。

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

**自定义工具。** `EnvironmentWorker` 默认运行内置工具集。要添加或替换工具，请使用带有 `beta_agent_toolset(env)` / `betaAgentToolset(env)` 的 `AgentToolContext(workdir=, client=, session_id=)`，并将生成的工具传递给较低层级的 `tool_runner()`。附加到智能体的技能会在工具调用开始前下载到 `{workdir}/skills/<name>/` 目录中（`AgentToolContext` 在提供 `client` 和 `session_id` 时会处理此操作）。下载的技能文件默认由 CLI 和 SDK 自动设置为可执行；如果您自己实现技能下载，则需要自己设置权限。

> **运行时依赖：** SDK 辅助工具需要 `/bin/bash` 位于该确切路径。TypeScript SDK 额外需要 `unzip`、`tar` 以及 Node.js 22+。这些工具在固定路径解析，**不**遵循 `PATH` 覆盖。

## 运行 Worker — `ant` CLI（固定工具集）

`ant` CLI 附带一个使用固定内置工具集（`bash`、`read`、`write`、`edit`、`glob`、`grep`）的 Worker。请按照 Anthropic CLI 文档（参见 `shared/live-sources.md` → Anthropic CLI）安装，然后：

```sh
export ANTHROPIC_ENVIRONMENT_KEY=sk-ant-oat01-...
ant beta:worker poll --environment-id env_... --workdir /workspace
```

- `--workdir` 是工具操作的目录（默认为 `.`）；工具调用被沙箱限制在此目录内。
- `--environment-key` 覆盖环境变量。
- `--on-work <script>` 为每个工作项运行您的脚本（例如为每个会话启动一个新的容器 — 请参阅下面的容器编排）。
- `--unrestricted-paths`、`--max-idle`（默认 `60s`）、`--log-format` — 参见 `ant beta:worker poll --help`。
- 标志可以回退到环境变量（`ANTHROPIC_ENVIRONMENT_ID`、`ANTHROPIC_ENVIRONMENT_KEY`）。
- 在处理完进行中的工作后，以 SIGTERM/SIGINT 方式干净退出。
- **固定工具集** — 如需自定义工具，请使用上面的 SDK Worker。

在 `--on-work` 容器内部，运行 `ant beta:worker run --workdir <dir>` 作为入口点。

## Webhook 驱动的唤醒（代替始终在线）

注册一个 `session.status_run_started` 的 Webhook（参见 `shared/managed-agents-webhooks.md`），验证投递，然后使用 `.run_one()` 处理一个工作项：

```python
import os
import anthropic
from anthropic.lib.environments import EnvironmentWorker

environment_key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]
environment_id = os.environ["ANTHROPIC_ENVIRONMENT_ID"]
client = anthropic.AsyncAnthropic(
    auth_token=environment_key,
)  # reads ANTHROPIC_WEBHOOK_SIGNING_KEY from env for webhooks.unwrap()


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

TypeScript：使用 `client.beta.webhooks.unwrap(body, {headers})` 和 `new EnvironmentWorker({...}).runOne()` 的相同结构。

## 容器编排（中层）

`EnvironmentWorker.run()` 在同一个进程中轮询和执行工具。要在**各自**的容器中运行每个会话，请在中层编排器中使用轮询器 — Python `client.beta.environments.work.poller(environment_id=, environment_key=, drain=, block_ms=, reclaim_older_than_ms=, auto_stop=)`；TypeScript `new WorkPoller({client, environmentId, environmentKey, autoStop})` 来自 `@anthropic-ai/sdk/helpers/beta/environments` — 然后，对于每个产生的 `work` 项，启动一个新容器，注入以下环境变量，其入口点运行 `ant beta:worker run` 或 `EnvironmentWorker(...).run_one()`。`block_ms` 为 1–999（或 `None` 表示非阻塞）；`reclaim_older_than_ms` 重新获取租约给已死 Worker 的项；`drain` 在队列为空时停止；`auto_stop` 在迭代器退出后发送停止信号（在启动的容器拥有停止调用时设置为 `False`）。**Go 的轮询器没有 `auto_stop` 退出选项** — 它在处理器返回时调用 `work.Stop`，因此在处理器中阻塞直到会话完成，而不是分离。

| 环境变量 | 值 |
|---|---|
| `ANTHROPIC_SESSION_ID` | `work.data.id` |
| `ANTHROPIC_WORK_ID` | `work.id` |
| `ANTHROPIC_ENVIRONMENT_ID` | `work.environment_id` |
| `ANTHROPIC_ENVIRONMENT_KEY` | 透传 |
| `ANTHROPIC_BASE_URL` | 透传 |

跳过 `work.data.type != "session"` 的项。

## 监控与控制

这些是**控制面**调用 — 使用 `x-api-key` 进行身份验证（不是环境密钥）；`managed-agents-2026-04-01` beta 标头。**从 Worker 主机外部调用它们** — 在 Worker 主机上设置 `ANTHROPIC_API_KEY` 会将组织范围的凭据暴露给智能体工具调用。

| SDK (`client.beta.environments.work.*`) | REST | CLI | 返回 |
|---|---|---|---|
| `stats(environment_id)` | `GET /v1/environments/{id}/work/stats` | `ant beta:environments:work stats` | `{type:"work_queue_stats", depth, pending, oldest_queued_at, workers_polling}` |
| `stop(work_id, environment_id=)` | `POST /v1/environments/{id}/work/{work_id}/stop` | `ant beta:environments:work stop` | `work.state` |

## 与 `cloud` 的差异

| 关注点 | `cloud` | `self_hosted` |
|---|---|---|
| 容器生命周期、加固、网络 | Anthropic | **您** — 以非 root 身份运行，只读根文件系统，删除能力；出口由您的 VPC/防火墙控制 |
| `file` / `github_repository` 资源挂载 | Anthropic 挂载到容器中 | **您** — 通过 `sessions.create(metadata={...})` 传递指针，让您的编排器在调度前获取/克隆 |
| `memory_store` 资源 | 支持 | **尚不支持** |
| 内置工具 | 通过 `agent_toolset_20260401` | 由您的 Worker 提供（`EnvironmentWorker` 默认 / `beta_agent_toolset(env)` / `ant` CLI 固定集） |
| 技能下载 | 自动 | `EnvironmentWorker` / `AgentToolContext` 获取到 `{workdir}/skills/`（需要 `client` + `session_id`） |
| Claude Platform on AWS | 支持 | **不可用** |
| SDK Worker 辅助工具 | 所有 SDK | **仅 Python、TypeScript、Go**（`EnvironmentWorker` / 轮询器不适用于 Java、Ruby、PHP 或 C#）— 使用这三种之一或 `ant` CLI |

## 凭据

| 凭据 | 格式 | 范围 |
|---|---|---|
| `ANTHROPIC_ENVIRONMENT_KEY` | `sk-ant-oat01-...` | 一个环境的工作队列。在 Console 中生成（"Generate environment key"）。作为 `auth_token=` / `authToken` 传递给客户端，**并**作为 `environment_key=` / `environmentKey` 传递给 `EnvironmentWorker`。存储在密钥管理器中；泄露时轮换。 |
| `ANTHROPIC_WEBHOOK_SIGNING_KEY` | `whsec_...` | Webhook 签名验证（如果使用 Webhook 驱动的唤醒）。SDK 会自动读取此环境变量以用于 `client.beta.webhooks.unwrap()`。 |

## 安全 — 您负责的部分

容器加固；出口限制（默认无）；`ANTHROPIC_ENVIRONMENT_KEY` 的保管和轮换；在运行不受信任代码时，每个信任边界使用一个工作空间 + 环境；工具进程的最小权限；日志保留和脱敏。**Anthropic 无法**：快速撤销泄露的环境密钥、验证您的镜像或供应链、在您的容器内沙箱化工具执行、或在工具输出到达您的基础设施后强制执行保留。请参阅 `shared/live-sources.md` 中的自托管沙箱安全页面，获取完整清单。
