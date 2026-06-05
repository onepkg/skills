---
name: claude-api
description: "构建、调试和优化 Claude API / Anthropic SDK 应用。使用此技能构建的应用应包含提示缓存。还处理在 Claude 模型版本之间迁移现有 Claude API 代码（4.5 → 4.6，4.6 → 4.7，退役模型替换）。触发条件：代码导入 `anthropic`/`@anthropic-ai/sdk`；用户询问 Claude API、Anthropic SDK 或 Managed Agents；用户在文件中添加/修改/调整 Claude 功能（缓存、思考、压缩、工具使用、批处理、文件、引用、内存）或模型（Opus/Sonnet/Haiku）；关于 Anthropic SDK 项目中提示缓存/缓存命中率的问题。跳过：文件导入 `openai`/其他提供商 SDK、文件名如 `*-openai.py`/`*-generic.py`、提供商中立代码、通用编程/ML。"
license: Complete terms in LICENSE.txt
---

# 使用 Claude 构建 LLM 驱动的应用

此技能帮助您使用 Claude 构建 LLM 驱动的应用。根据您的需要选择合适的表面，检测项目语言，然后阅读相关的语言特定文档。

## 开始之前

扫描目标文件（或者，如果没有目标文件，则扫描提示和项目）以查找非 Anthropic 提供商标记 — `import openai`、`from openai`、`langchain_openai`、`OpenAI(`、`gpt-4`、`gpt-5`、文件名如 `agent-openai.py` 或 `*-generic.py`，或任何明确指示保持代码提供商中立的指令。如果您找到任何这些标记，请停止并告诉用户此技能生成 Claude/Anthropic SDK 代码；询问他们是否希望将文件切换到 Claude 或想要非 Claude 实现。不要使用 Anthropic SDK 调用编辑非 Anthropic 文件。

## 输出要求

当用户要求您添加、修改或实现 Claude 功能时，您的代码必须通过以下方式之一调用 Claude：

1. **官方 Anthropic SDK** 用于项目的语言（`anthropic`、`@anthropic-ai/sdk`、`com.anthropic.*` 等）。只要项目有支持的 SDK，这就是默认选择。
2. **原始 HTTP**（`curl`、`requests`、`fetch`、`httpx` 等）— 仅在用户明确要求 cURL/REST/原始 HTTP、项目是 shell/cURL 项目或语言没有官方 SDK 时使用。

切勿混合使用两者 — 不要因为感觉更轻量就在 Python 或 TypeScript 项目中使用 `requests`/`fetch`。切勿回退到 OpenAI 兼容的 shim。

**切勿猜测 SDK 用法。** 函数名、类名、命名空间、方法签名和导入路径必须来自明确的文档 — 要么是本技能中的 `{lang}/` 文件，要么是 `shared/live-sources.md` 中列出的官方 SDK 仓库或文档链接。如果您需要的绑定未在技能文件中明确记录，请在编写代码之前从 `shared/live-sources.md` WebFetch 相关的 SDK 仓库。不要从 cURL 形状或其他语言的 SDK 推断 Ruby/Java/Go/PHP/C# API。

## 默认值

除非用户另有要求：

对于 Claude 模型版本，请使用 Claude Opus 4.8，您可以通过确切的模型字符串 `claude-opus-4-8` 访问它。请默认为任何稍微复杂的事情使用自适应思考（`thinking: {type: "adaptive"}`）。最后，请默认为任何可能涉及长输入、长输出或高 `max_tokens` 的请求使用流式传输 — 它可以防止达到请求超时。如果您不需要处理单个流事件，请使用 SDK 的 `.get_final_message()` / `.finalMessage()` 辅助函数获取完整响应

---

## 子命令

如果此提示底部的用户请求是裸子命令字符串（无散文），请搜索本文档中的每个**子命令**表 — 包括下面附加部分中的任何表 — 并直接遵循匹配的 Action 列。这允许用户通过 `/claude-api <subcommand>` 调用特定流程。如果文档中没有表匹配，则将请求视为正常散文。


---

## 语言检测

在阅读代码示例之前，确定用户使用的语言：

1. **查看项目文件**以推断语言：

   - `*.py`、`requirements.txt`、`pyproject.toml`、`setup.py`、`Pipfile` → **Python** — 从 `python/` 读取
   - `*.ts`、`*.tsx`、`package.json`、`tsconfig.json` → **TypeScript** — 从 `typescript/` 读取
   - `*.js`、`*.jsx`（没有 `.ts` 文件）→ **TypeScript** — JS 使用相同的 SDK，从 `typescript/` 读取
   - `*.java`、`pom.xml`、`build.gradle` → **Java** — 从 `java/` 读取
   - `*.kt`、`*.kts`、`build.gradle.kts` → **Java** — Kotlin 使用 Java SDK，从 `java/` 读取
   - `*.scala`、`build.sbt` → **Java** — Scala 使用 Java SDK，从 `java/` 读取
   - `*.go`、`go.mod` → **Go** — 从 `go/` 读取
   - `*.rb`、`Gemfile` → **Ruby** — 从 `ruby/` 读取
   - `*.cs`、`*.csproj` → **C#** — 从 `csharp/` 读取
   - `*.php`、`composer.json` → **PHP** — 从 `php/` 读取

2. **如果检测到多种语言**（例如，同时有 Python 和 TypeScript 文件）：

   - 检查用户的当前文件或问题与哪种语言相关
   - 如果仍然不明确，请问："我检测到 Python 和 TypeScript 文件。您使用哪种语言进行 Claude API 集成？"

3. **如果无法推断语言**（空项目、没有源文件或不支持的语言）：

   - 使用 AskUserQuestion 并提供选项：Python、TypeScript、Java、Go、Ruby、cURL/原始 HTTP、C#、PHP
   - 如果 AskUserQuestion 不可用，则默认为 Python 示例并注明："显示 Python 示例。如果您需要其他语言，请告诉我。"

4. **如果检测到不支持的语言**（Rust、Swift、C++、Elixir 等）：

   - 建议从 `curl/` 使用 cURL/原始 HTTP 示例，并注意可能存在社区 SDK
   - 提供显示 Python 或 TypeScript 示例作为参考实现

5. **如果用户需要 cURL/原始 HTTP 示例**，从 `curl/` 读取。

### 语言特定功能支持

| 语言       | Tool Runner | Managed Agents | 说明                                  |
| ---------- | ----------- | -------------- | ------------------------------------- |
| Python     | 是（beta）  | 是（beta）     | 完全支持 — `@beta_tool` 装饰器        |
| TypeScript | 是（beta）  | 是（beta）     | 完全支持 — `betaZodTool` + Zod        |
| Java       | 是（beta）  | 是（beta）     | Beta 工具使用带注释的类               |
| Go         | 是（beta）  | 是（beta）     | `toolrunner` 包中的 `BetaToolRunner`  |
| Ruby       | 是（beta）  | 是（beta）     | beta 中的 `BaseTool` + `tool_runner`  |
| C#         | 否          | 否             | 官方 SDK                              |
| PHP        | 是（beta）  | 是（beta）     | `BetaRunnableTool` + `toolRunner()`   |
| cURL       | N/A         | 是（beta）     | 原始 HTTP，无 SDK 功能                |

> **Managed Agents 代码示例**：为 Python、TypeScript、Go、Ruby、PHP、Java 和 cURL 提供了专用的语言特定 README（`{lang}/managed-agents/README.md`、`curl/managed-agents.md`）。阅读您的语言的 README 以及语言无关的 `shared/managed-agents-*.md` 概念文件。**代理是持久的 — 创建一次，按 ID 引用。** 存储由 `agents.create` 返回的代理 ID，并将其传递给每个后续的 `sessions.create`；不要在请求路径中调用 `agents.create`。Anthropic CLI 是从版本控制的 YAML 创建代理和环境的一种方便方式 — 其 URL 在 `shared/live-sources.md` 中。如果您需要的绑定未在 README 中显示，请从 `shared/live-sources.md` WebFetch 相关条目，而不是猜测。C# 目前不支持 Managed Agents；使用针对 API 的 cURL 风格原始 HTTP 请求。

---

## 我应该使用哪个表面？

> **从简单开始。** 默认为满足您需求的最简单层级。单个 API 调用和工作流处理大多数用例 — 只有在任务真正需要开放式、模型驱动的探索时才使用代理。

| 用例                                            | 层级            | 推荐表面                  | 原因                                                         |
| ----------------------------------------------- | --------------- | ------------------------- | ------------------------------------------------------------ |
| 分类、摘要、提取、问答                          | 单个 LLM 调用   | **Claude API**            | 一个请求，一个响应                                             |
| 批处理或嵌入                                    | 单个 LLM 调用   | **Claude API**            | 专用端点                                                       |
| 具有代码控制逻辑的多步骤管道                    | 工作流          | **Claude API + 工具使用** | 您编排循环                                                     |
| 带有自己工具的自定义代理                        | 代理            | **Claude API + 工具使用** | 最大灵活性                                                     |
| 服务器管理的有状态代理，带有工作区              | 代理            | **Managed Agents**        | Anthropic 运行循环并托管工具执行沙箱                           |
| 持久化、版本化的代理配置                        | 代理            | **Managed Agents**        | 代理是存储的对象；会话固定到版本                               |
| 带有文件挂载的长期多轮代理                      | 代理            | **Managed Agents**        | 每会话容器、SSE 事件流、Skills + MCP                         |

> **注意：** 当您希望 Anthropic 运行代理循环*并*托管工具执行的容器时，Managed Agents 是正确的选择 — 文件操作、bash、代码执行都在每会话工作区中运行。如果您希望自己托管计算或运行自己的自定义工具运行时，Claude API + 工具使用是正确的选择 — 使用工具运行器进行自动循环处理，或使用手动循环进行细粒度控制（批准门、自定义日志记录、条件执行）。

> **第三方提供商（Amazon Bedrock、Google Vertex AI、Microsoft Foundry）：** Managed Agents **不适用于** Bedrock、Vertex 或 Foundry。如果您通过任何第三方提供商部署，请对所有用例使用 **Claude API + 工具使用** — 包括否则推荐使用 Managed Agents 的用例。

### 决策树

```
您的应用程序需要什么？

0. 您是否通过 Amazon Bedrock、Google Vertex AI 或 Microsoft Foundry 部署？
   └── 是 → Claude API（+ 代理的工具使用）— Managed Agents 仅限 1P。
   否 → 继续。

1. 单个 LLM 调用（分类、摘要、提取、问答）
   └── Claude API — 一个请求，一个响应

2. 您是否希望 Anthropic 运行代理循环并托管每会话
   容器，其中 Claude 执行工具（bash、文件操作、代码）？
   └── 是 → Managed Agents — 服务器管理会话、持久化代理配置、
       SSE 事件流、Skills + MCP、文件挂载。
       示例："每个任务带有工作区的有状态编码代理"、
                 "将事件流式传输到 UI 的长期研究代理"、
                 "在许多会话中使用的持久化、版本化配置的代理"

3. 工作流（多步骤、代码编排、带有您自己的工具）
   └── Claude API 带工具使用 — 您控制循环

4. 开放式代理（模型决定自己的轨迹、您自己的工具、您托管计算）
   └── Claude API 代理循环（最大灵活性）
```

### 我应该构建代理吗？

在选择代理层级之前，检查所有四个标准：

- **复杂性** — 任务是否是多步骤且难以提前完全指定？（例如，"将此设计文档转化为 PR" vs. "从此 PDF 中提取标题"）
- **价值** — 结果是否证明更高的成本和延迟是合理的？
- **可行性** — Claude 是否能够执行此任务类型？
- **错误成本** — 是否可以捕获和恢复错误？（测试、审查、回滚）

如果对其中任何一个的回答是"否"，请保持在更简单的层级（单个调用或工作流）。

---

## 架构

一切都通过 `POST /v1/messages`。工具和输出约束是此单个端点的功能 — 不是单独的 API。

**用户定义的工具** — 您定义工具（通过装饰器、Zod 模式或原始 JSON），SDK 的工具运行器处理调用 API、执行您的函数和循环直到 Claude 完成。为了完全控制，您可以手动编写循环。

**服务器端工具** — Anthropic 托管的工具，在 Anthropic 的基础设施上运行。代码执行是完全服务器端的（在 `tools` 中声明它，Claude 自动运行代码）。计算机使用可以是服务器托管或自托管。

**结构化输出** — 约束 Messages API 响应格式（`output_config.format`）和/或工具参数验证（`strict: true`）。推荐的方法是 `client.messages.parse()`，它根据您的模式自动验证响应。注意：旧的 `output_format` 参数已弃用；在 `messages.create()` 上使用 `output_config: {format: {...}}`。

**支持端点** — Batches（`POST /v1/messages/batches`）、Files（`POST /v1/files`）、Token Counting 和 Models（`GET /v1/models`、`GET /v1/models/{id}` — 实时能力/上下文窗口发现）馈入或支持 Messages API 请求。

---

## 当前模型（缓存于：2026-05-26）

| 模型              | 模型 ID             | 上下文         | 输入 $/1M | 输出 $/1M |
| ----------------- | ------------------- | -------------- | --------- | --------- |
| Claude Opus 4.8   | `claude-opus-4-8`   | 1M             | $5.00     | $25.00    |
| Claude Opus 4.7   | `claude-opus-4-7`   | 1M             | $5.00     | $25.00    |
| Claude Opus 4.6   | `claude-opus-4-6`   | 1M             | $5.00     | $25.00    |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M             | $3.00     | $15.00    |
| Claude Haiku 4.5  | `claude-haiku-4-5`  | 200K           | $1.00     | $5.00     |

**始终使用 `claude-opus-4-8`，除非用户明确指定其他模型。** 这是不可协商的。不要使用 `claude-sonnet-4-6`、`claude-sonnet-4-5` 或任何其他模型，除非用户字面上说"use sonnet"或"use haiku"。永远不要为了成本而降级 — 那是用户的决定，不是您的。

**关键：仅使用上表中的确切模型 ID 字符串 — 它们原样完整。不要附加日期后缀。** 例如，使用 `claude-sonnet-4-5`，永远不要使用 `claude-sonnet-4-5-20250514` 或您可能从训练数据中回忆的任何其他日期后缀变体。如果用户请求表中未列出的较旧模型（例如，"opus 4.5"、"sonnet 3.7"），请阅读 `shared/models.md` 获取确切的 ID — 不要自己构造一个。

注意：如果上述任何模型字符串对您来说看起来不熟悉，那是可以预期的 — 那只是意味着它们是在您的训练数据截止后发布的。请放心，它们是真实的模型；我们不会那样捉弄您。

**实时能力查找：** 上表是缓存的。当用户询问"X 的上下文窗口是什么"、"X 是否支持视觉/思考/努力"或"哪些模型支持 Y"时，查询 Models API（`client.models.retrieve(id)` / `client.models.list()`）— 请参阅 `shared/models.md` 获取字段参考和能力过滤示例。

---

## 思考和努力（快速参考）

**Opus 4.8 / 4.7 — 仅自适应思考：** 使用 `thinking: {type: "adaptive"}`。`thinking: {type: "enabled", budget_tokens: N}` 返回 400 — 自适应是唯一开启模式。`{type: "disabled"}` 和省略 `thinking` 都有效。采样参数（`temperature`、`top_p`、`top_k`）也被移除并将返回 400。Opus 4.8 保持与 4.7 相同的请求表面（没有新的破坏性更改）— 请参阅 `shared/model-migration.md` → 迁移到 Opus 4.8 获取行为重新调整，以及 → 迁移到 Opus 4.7 获取从 4.6 或更早版本迁移时的完整破坏性更改列表。注意：禁用 `thinking` 时，Opus 4.8 可能会在可见响应中写入更长的推理 — 保持自适应思考开启，或添加最终答案唯一指令（请参阅迁移指南）。
**Opus 4.6 — 自适应思考（推荐）：** 使用 `thinking: {type: "adaptive"}`。Claude 动态决定何时以及如何思考。不需要 `budget_tokens` — `budget_tokens` 在 Opus 4.6 和 Sonnet 4.6 上已弃用，不应在新代码中使用。自适应思考也自动启用交错思考（不需要 beta 头）。**当用户要求"扩展思考"、"思考预算"或 `budget_tokens` 时：始终使用 Opus 4.8、4.7 或 4.6 配合 `thinking: {type: "adaptive"}`。固定令牌预算的思考概念已弃用 — 自适应思考取代它。不要在新 4.6/4.7/4.8 代码中使用 `budget_tokens`，也不要切换到较旧的模型。** *逐步迁移特例：* `budget_tokens` 在 Opus 4.6 和 Sonnet 4.6 上仍然可用，作为过渡逃生舱口 — 如果您正在迁移现有代码并且在调整 `effort` 之前需要硬令牌上限，请参阅 `shared/model-migration.md` → 过渡逃生舱口。注意：此特例**不适用于** Opus 4.7 或 4.8 — `budget_tokens` 在那里被完全移除。
**努力参数（GA，无 beta 头）：** 通过 `output_config: {effort: "low"|"medium"|"high"|"max"}`（在 `output_config` 内，不是顶层）控制思考深度和整体令牌支出。默认是 `high`（相当于省略它）。`max` 仅限 Opus 层级（Opus 4.6 及更高版本 — 不适用于 Sonnet 或 Haiku）。Opus 4.7 添加了 `"xhigh"`（介于 `high` 和 `max` 之间）— Opus 4.7/4.8 上大多数编码和代理用例的最佳设置，也是 Claude Code 中的默认设置；对于大多数智能敏感工作，使用至少 `high`。适用于 Opus 4.5、Opus 4.6、Opus 4.7、Opus 4.8 和 Sonnet 4.6。在 Sonnet 4.5 / Haiku 4.5 上将出错。在 Opus 4.7 和 4.8 上，努力比任何以前的 Opus 更重要 — 迁移时重新调整它，并以 `high`/`xhigh` 运行长期/代理任务，并在前面提供完整任务规范。与自适应思考结合以获得最佳成本质量权衡。较低的努力意味着更少且更合并的工具调用、更少的前言和更简洁的确认 — `high` 通常是平衡质量和令牌效率的甜蜜点；当正确性比成本更重要时使用 `max`；对于子代理或简单任务使用 `low`。

**Opus 4.8 / 4.7 — 默认省略思考内容：** `thinking` 块仍然流式传输，但它们的文本为空，除非您选择加入 `thinking: {type: "adaptive", display: "summarized"}`（默认是 `"omitted"`）。静默更改 — 无错误。如果您将推理流式传输给用户，默认看起来像在输出之前长时间暂停；设置 `"summarized"` 以恢复可见进度。

**任务预算（beta，Opus 4.7 / 4.8）：** `output_config: {task_budget: {type: "tokens", total: N}}` 告诉模型它在完整代理循环中有多少令牌 — 它看到运行倒计时并自我调节（最小 20,000；beta 头 `task-budgets-2026-03-13`）。与 `max_tokens` 不同，后者是模型不知道的强制每响应上限。请参阅 `shared/model-migration.md` → 任务预算。

**Sonnet 4.6：** 支持自适应思考（`thinking: {type: "adaptive"}`）。`budget_tokens` 在 Sonnet 4.6 上已弃用 — 改用自适应思考。

**较旧模型（仅在明确要求时）：** 如果用户特别要求 Sonnet 4.5 或其他较旧模型，请使用 `thinking: {type: "enabled", budget_tokens: N}`。`budget_tokens` 必须小于 `max_tokens`（最小 1024）。永远不要仅仅因为用户提到 `budget_tokens` 就选择较旧的模型 — 改用 Opus 4.8 配合自适应思考。

---

## 压缩（快速参考）

**Beta，Opus 4.8、Opus 4.7、Opus 4.6 和 Sonnet 4.6。** 对于可能超过 1M 上下文窗口的长期对话，启用服务器端压缩。API 在接近触发阈值（默认：150K 令牌）时自动总结早期上下文。需要 beta 头 `compact-2026-01-12`。

**关键：** 在每次轮次时将 `response.content`（不仅仅是文本）追加回您的消息。响应中的压缩块必须保留 — API 使用它们在下一个请求中替换压缩的历史。仅提取文本字符串并追加将静默丢失压缩状态。

有关代码示例，请参阅 `{lang}/claude-api/README.md`（压缩部分）。完整文档通过 `shared/live-sources.md` 中的 WebFetch。

---

## 提示缓存（快速参考）

**前缀匹配。** 前缀中任何地方的任何字节更改都会使之后的所有内容失效。渲染顺序是 `tools` → `system` → `messages`。首先保持稳定的内容（冻结的系统提示、确定性工具列表），将易失性内容（时间戳、每请求 ID、变化的问题）放在最后一个 `cache_control` 断点之后。

**顶级自动缓存**（在 `messages.create()` 上使用 `cache_control: {type: "ephemeral"}`）是您不需要细粒度放置时的最简单选项。每个请求最多 4 个断点。最小可缓存前缀约为 1024 令牌 — 较短的前缀将静默不缓存。

**使用 `usage.cache_read_input_tokens` 验证** — 如果在重复请求中为零，则存在静默无效器（系统提示中的 `datetime.now()`、未排序的 JSON、变化的工具集）。

有关放置模式、架构指导和静默无效器审计清单：阅读 `shared/prompt-caching.md`。语言特定语法：`{lang}/claude-api/README.md`（提示缓存部分）。

---

## Managed Agents（Beta）

**Managed Agents** 是第三个表面：服务器管理的有状态代理，带有 Anthropic 托管的工具执行。您创建持久化、版本化的 Agent 配置（`POST /v1/agents`），然后启动引用它的 Sessions。每个会话为代理的工作区配置容器 — bash、文件操作和代码执行在那里运行；代理循环本身在 Anthropic 的编排层上运行，并通过工具对容器进行操作。会话流式传输事件；您发送消息和工具结果回来。

**Managed Agents 仅限第一方。** 它不适用于 Amazon Bedrock、Google Vertex AI 或 Microsoft Foundry。对于第三方提供商上的代理，使用 Claude API + 工具使用。

**强制流程：** Agent（一次）→ Session（每次运行）。`model`/`system`/`tools` 位于代理上，从不在会话上。请参阅 `shared/managed-agents-overview.md` 获取完整阅读指南、beta 头和陷阱。

**Beta 头：** `managed-agents-2026-04-01` — SDK 为所有 `client.beta.{agents,environments,sessions,vaults,memory_stores}.*` 调用自动设置此头。Skills API 使用 `skills-2025-10-02`，Files API 使用 `files-api-2025-04-14`，但您不需要为 `/v1/skills` 和 `/v1/files` 以外的端点显式传递这些。

**子命令** — 直接使用 `/claude-api <subcommand>` 调用：

| 子命令 | 操作 |
|---|---|
| `managed-agents-onboard` | 引导用户从头开始设置 Managed Agent。**立即阅读 `shared/managed-agents-onboarding.md`** 并遵循其采访脚本：心理模型 → know-or-explore 分支 → 模板配置 → 会话设置 → 发出代码。不要总结 — 运行采访。 |

**阅读指南：** 从 `shared/managed-agents-overview.md` 开始，然后是主题性的 `shared/managed-agents-*.md` 文件（core、environments、tools、events、outcomes、multiagent、webhooks、memory、client-patterns、onboarding、api-reference）。对于 Python、TypeScript、Go、Ruby、PHP 和 Java，阅读 `{lang}/managed-agents/README.md` 获取代码示例。对于 cURL，阅读 `curl/managed-agents.md`。**代理是持久的 — 创建一次，按 ID 引用。** 存储由 `agents.create` 返回的代理 ID，并将其传递给每个后续的 `sessions.create`；不要在请求路径中调用 `agents.create`。Anthropic CLI 是从版本控制的 YAML 创建代理和环境的一种方便方式（URL 在 `shared/live-sources.md` 中）。如果您需要的绑定未在语言 README 中显示，请从 `shared/live-sources.md` WebFetch 相关条目，而不是猜测。C# 目前不支持 Managed Agents；使用 `curl/managed-agents.md` 中的原始 HTTP 作为参考。

**当用户想要从头开始设置 Managed Agent 时**（例如，"如何开始"、"引导我创建一个"、"设置新代理"）：阅读 `shared/managed-agents-onboarding.md` 并运行其采访 — 与 `managed-agents-onboard` 子命令相同的流程。

**当用户询问"我如何为 X 编写客户端代码"时：** 使用 `shared/managed-agents-client-patterns.md` — 涵盖无损流重新连接、`processed_at` 排队/处理门、中断、`tool_confirmation` 往返、正确的 idle/terminated 中断门、post-idle 状态竞争、stream-first 排序、文件挂载陷阱、通过自定义工具在主机端保持凭据等。

---

## 阅读指南

检测到语言后，根据用户的需求阅读相关文件：

### 快速任务参考

**单个文本分类/摘要/提取/问答：**
→ 仅阅读 `{lang}/claude-api/README.md`

**聊天 UI 或实时响应显示：**
→ 阅读 `{lang}/claude-api/README.md` + `{lang}/claude-api/streaming.md`

**长期对话（可能超过上下文窗口）：**
→ 阅读 `{lang}/claude-api/README.md` — 参见压缩部分
**迁移到更新的模型（Opus 4.8 / Opus 4.7 / Opus 4.6 / Sonnet 4.6）或替换退役模型：**
→ 阅读 `shared/model-migration.md`
**提示缓存/优化缓存/"为什么我的缓存命中率低"：**
→ 阅读 `shared/prompt-caching.md` + `{lang}/claude-api/README.md`（提示缓存部分）

**函数调用/工具使用/代理：**
→ 阅读 `{lang}/claude-api/README.md` + `shared/tool-use-concepts.md` + `{lang}/claude-api/tool-use.md`

**代理设计（工具表面、上下文管理、缓存策略）：**
→ 阅读 `shared/agent-design.md`

**批处理（非延迟敏感）：**
→ 阅读 `{lang}/claude-api/README.md` + `{lang}/claude-api/batches.md`

**跨多个请求的文件上传：**
→ 阅读 `{lang}/claude-api/README.md` + `{lang}/claude-api/files-api.md`

**Managed Agents（服务器管理的有状态代理，带有工作区）：**
→ 阅读 `shared/managed-agents-overview.md` + 其余的 `shared/managed-agents-*.md` 文件。对于 Python、TypeScript、Go、Ruby、PHP 和 Java，阅读 `{lang}/managed-agents/README.md` 获取代码示例。对于 cURL，阅读 `curl/managed-agents.md`。**代理是持久的 — 创建一次，按 ID 引用。** 存储由 `agents.create` 返回的代理 ID，并将其传递给每个后续的 `sessions.create`；不要在请求路径中调用 `agents.create`。Anthropic CLI 是从版本控制的 YAML 创建代理和环境的一种方便方式（URL 在 `shared/live-sources.md` 中）。如果您需要的绑定未在语言 README 中显示，请从 `shared/live-sources.md` WebFetch 相关条目，而不是猜测。C# 目前不支持 Managed Agents — 使用 `curl/managed-agents.md` 中的原始 HTTP 作为参考。

### Claude API（完整文件参考）

阅读**语言特定的 Claude API 文件夹**（`{language}/claude-api/`）：

1. **`{language}/claude-api/README.md`** — **首先阅读此文件。** 安装、快速入门、常见模式、错误处理。
2. **`shared/tool-use-concepts.md`** — 当用户需要函数调用、代码执行、内存或结构化输出时阅读。涵盖概念基础。
3. **`shared/agent-design.md`** — 设计代理时阅读：bash vs. 专用工具、编程工具调用、工具搜索/skills、上下文编辑 vs. 压缩 vs. 内存、缓存原则。
4. **`{language}/claude-api/tool-use.md`** — 阅读语言特定的工具使用代码示例（工具运行器、手动循环、代码执行、内存、结构化输出）。
5. **`{language}/claude-api/streaming.md`** — 构建聊天 UI 或增量显示响应的界面时阅读。
6. **`{language}/claude-api/batches.md`** — 离线处理许多请求时阅读（非延迟敏感）。以 50% 的成本异步运行。
7. **`{language}/claude-api/files-api.md`** — 跨多个请求发送相同文件而不重新上传时阅读。
8. **`shared/prompt-caching.md`** — 添加或优化提示缓存时阅读。涵盖前缀稳定性设计、断点放置和静默使缓存失效的反模式。
9. **`shared/error-codes.md`** — 调试 HTTP 错误或实现错误处理时阅读。
10. **`shared/model-migration.md`** — 升级到更新模型、替换退役模型或将 `budget_tokens` / prefill 模式转换为当前 API 时阅读。
11. **`shared/live-sources.md`** — WebFetch URL 以获取最新官方文档。

> **注意：** 对于 Java、Go、Ruby、C#、PHP 和 cURL — 这些每个都有一个文件涵盖所有基础知识。根据需要阅读该文件以及 `shared/tool-use-concepts.md` 和 `shared/error-codes.md`。

> **注意：** 对于 Managed Agents 文件参考，请参阅上面的 `## Managed Agents (Beta)` 部分 — 它列出了每个 `shared/managed-agents-*.md` 文件和语言特定的 README。

---

## 何时使用 WebFetch

在以下情况下使用 WebFetch 获取最新文档：

- 用户询问"最新"或"当前"信息
- 缓存的数据似乎不正确
- 用户询问此处未涵盖的功能

实时文档 URL 在 `shared/live-sources.md` 中。

## 常见陷阱

- 不要截断传递给 API 的文件或内容的输入。如果内容太长而无法适应上下文窗口，请通知用户并讨论选项（分块、摘要等），而不是静默截断。
- **Opus 4.8 / 4.7 思考：** 仅自适应。`thinking: {type: "enabled", budget_tokens: N}` 返回 400 — `budget_tokens` 被完全移除（连同 `temperature`、`top_p`、`top_k`）。使用 `thinking: {type: "adaptive"}`。Opus 4.8 从 4.7 继承此表面，没有新的破坏性更改。
- **Opus 4.6 / Sonnet 4.6 思考：** 使用 `thinking: {type: "adaptive"}` — 不要在新 4.6 代码中使用 `budget_tokens`（在 Opus 4.6 和 Sonnet 4.6 上已弃用；对于现有代码的逐步迁移，请参阅 `shared/model-migration.md` 中的过渡逃生舱口 — 注意此特例不适用于 Opus 4.7 或 4.8）。对于较旧的模型，`budget_tokens` 必须小于 `max_tokens`（最小 1024）。如果您弄错了，这将抛出错误。
- **4.6/4.7/4.8 系列预填充已移除：** 助手消息预填充（last-assistant-turn 预填充）在 Opus 4.6、Opus 4.7、Opus 4.8 和 Sonnet 4.6 上返回 400 错误。使用结构化输出（`output_config.format`）或系统提示指令来控制响应格式。
- **在编辑之前确认迁移范围：** 当用户要求将代码迁移到更新的 Claude 模型而没有命名特定文件、目录或文件列表时，**首先询问要应用的范围** — 整个工作目录、特定子目录或特定文件集。在用户确认之前不要开始编辑。祈使语气如"迁移我的代码库"、"将我的项目移动到 X"、"升级到 Sonnet 4.6"或裸"迁移到 Opus 4.8"**仍然是模糊的** — 它们告诉您要做什么，但没有告诉您在哪里，所以请问。仅在提示命名确切文件、特定目录或显式文件列表时 proceeding without asking（"迁移 `app.py`"、"迁移 `services/` 下的所有内容"、"更新 `a.py` 和 `b.py`"）。请参阅 `shared/model-migration.md` 步骤 0。
- **`max_tokens` 默认值：** 不要低估 `max_tokens` — 达到上限会在思想中间截断输出并需要重试。对于非流式请求，默认为 `~16000`（保持响应低于 SDK HTTP 超时）。对于流式请求，默认为 `~64000`（超时不是问题，所以给模型空间）。仅在有硬性理由时才降低：分类（`~256`）、成本上限或故意短输出。
- **128K 输出令牌：** Opus 4.6、Opus 4.7 和 Opus 4.8 支持高达 128K `max_tokens`，但 SDK 需要对如此大的值进行流式传输以避免 HTTP 超时。使用 `.stream()` 配合 `.get_final_message()` / `.finalMessage()`。
- **工具调用 JSON 解析（4.6/4.7/4.8 系列）：** Opus 4.6、Opus 4.7、Opus 4.8 和 Sonnet 4.6 可能在工具调用 `input` 字段中产生不同的 JSON 字符串转义（例如，Unicode 或正斜杠转义）。始终使用 `json.loads()` / `JSON.parse()` 解析工具输入 — 永远不要对序列化输入进行原始字符串匹配。
- **结构化输出（所有模型）：** 在 `messages.create()` 上使用 `output_config: {format: {...}}` 而不是已弃用的 `output_format` 参数。这是一般 API 更改，不是 4.6 特定的。
- **不要重新实现 SDK 功能：** SDK 提供高级辅助函数 — 使用它们而不是从头开始构建。具体来说：使用 `stream.finalMessage()` 而不是在 `new Promise()` 中包装 `.on()` 事件；使用类型化异常类（`Anthropic.RateLimitError` 等）而不是字符串匹配错误消息；使用 SDK 类型（`Anthropic.MessageParam`、`Anthropic.Tool`、`Anthropic.Message` 等）而不是重新定义等效接口。
- **不要为 SDK 数据结构定义自定义类型：** SDK 为所有 API 对象导出类型。对消息使用 `Anthropic.MessageParam`，对工具定义使用 `Anthropic.Tool`，对工具结果使用 `Anthropic.ToolUseBlock` / `Anthropic.ToolResultBlockParam`，对响应使用 `Anthropic.Message`。定义您自己的 `interface ChatMessage { role: string; content: unknown }` 会复制 SDK 已经提供的内容并失去类型安全性。
- **报告和文档输出：** 对于生成报告、文档或可视化的任务，代码执行沙箱预安装了 `python-docx`、`python-pptx`、`matplotlib`、`pillow` 和 `pypdf`。Claude 可以生成格式化文件（DOCX、PDF、图表）并通过 Files API 返回它们 — 考虑将其用于"报告"或"文档"类型请求，而不是纯 stdout 文本。