---
name: claude-api
description: "构建、调试和优化 Claude API / Anthropic SDK 应用程序。使用此技能构建的应用应包含提示缓存。同时处理现有 Claude API 代码在 Claude 模型版本之间的迁移（4.5 → 4.6, 4.6 → 4.7, 已退役模型替换）。触发条件：代码导入 `anthropic`/`@anthropic-ai/sdk`；用户询问 Claude API、Anthropic SDK 或托管智能体；用户在文件中添加/修改/调优 Claude 功能（缓存、思考、压缩、工具使用、批处理、文件、引用、记忆）或模型（Opus/Sonnet/Haiku）；关于 Anthropic SDK 项目中提示缓存/缓存命中率的疑问。跳过条件：文件导入 `openai`/其他供应商 SDK，文件名类似 `*-openai.py`/`*-generic.py`，供应商无关的代码，通用编程/机器学习。"
license: 完整条款见 LICENSE.txt
---

# 使用 Claude 构建 LLM 驱动的应用

此技能帮助您使用 Claude 构建 LLM 驱动的应用。根据需求选择合适的界面，检测项目语言，然后阅读相应语言的文档。

## 开始之前

扫描目标文件（如果没有目标文件，则扫描提示词和项目）中的非 Anthropic 供应商标记——`import openai`、`from openai`、`langchain_openai`、`OpenAI(`、`gpt-4`、`gpt-5`、文件名如 `agent-openai.py` 或 `*-generic.py`，或任何明确要求保持代码供应商无关的指令。如果发现上述标记，请停止操作并告知用户此技能生成的是 Claude/Anthropic SDK 代码；询问他们是要将文件切换为 Claude，还是需要非 Claude 的实现。请勿用 Anthropic SDK 调用编辑非 Anthropic 文件。

## 输出要求

当用户要求您添加、修改或实现 Claude 功能时，您的代码必须通过以下方式之一调用 Claude：

1. **项目语言的官方 Anthropic SDK**（`anthropic`、`@anthropic-ai/sdk`、`com.anthropic.*` 等）。当项目存在支持的 SDK 时，这是默认选择。
2. **原始 HTTP**（`curl`、`requests`、`fetch`、`httpx` 等）——仅当用户明确要求使用 cURL/REST/原始 HTTP，项目是 shell/cURL 项目，或该语言没有官方 SDK 时使用。

切勿混合使用这两种方式——不要因为在 Python 或 TypeScript 项目中感觉更轻量就去使用 `requests`/`fetch`。切勿退回到兼容 OpenAI 的适配层。

**切勿猜测 SDK 用法。** 函数名、类名、命名空间、方法签名和导入路径必须来自明确的文档——要么是本技能中的 `{lang}/` 文件，要么是 `shared/live-sources.md` 中列出的官方 SDK 仓库或文档链接。如果所需的绑定在技能文件中没有明确文档，请在编写代码之前从 `shared/live-sources.md` 中 WebFetch 相关 SDK 仓库。请勿根据 cURL 格式或其他语言的 SDK 推断 Ruby/Java/Go/PHP/C# 的 API。

## 默认设置

除非用户另有要求：

对于 Claude 模型版本，请使用 Claude Opus 4.8，您可以通过精确的模型字符串 `claude-opus-4-8` 访问。对于任何稍复杂的任务，请默认使用自适应思考（`thinking: {type: "adaptive"}`）。最后，对于任何可能涉及长输入、长输出或高 `max_tokens` 的请求，请默认使用流式传输——这可以避免请求超时。如果不需要处理单个流事件，请使用 SDK 的 `.get_final_message()` / `.finalMessage()` 辅助方法来获取完整响应。

---

## 子命令

如果此提示底部的用户请求是一个裸子命令字符串（无叙述内容），则搜索本文档中的所有 **子命令** 表格——包括下面附加部分中的——并直接执行匹配的操作列。这允许用户通过 `/claude-api <子命令>` 调用特定流程。如果文档中没有表格匹配，则将请求视为普通叙述内容。

---

## 语言检测

在阅读代码示例之前，确定用户使用的语言：

1. **查看项目文件** 以推断语言：

   - `*.py`、`requirements.txt`、`pyproject.toml`、`setup.py`、`Pipfile` → **Python**——从 `python/` 读取
   - `*.ts`、`*.tsx`、`package.json`、`tsconfig.json` → **TypeScript**——从 `typescript/` 读取
   - `*.js`、`*.jsx`（无 `.ts` 文件）→ **TypeScript**——JS 使用相同的 SDK，从 `typescript/` 读取
   - `*.java`、`pom.xml`、`build.gradle` → **Java**——从 `java/` 读取
   - `*.kt`、`*.kts`、`build.gradle.kts` → **Java**——Kotlin 使用 Java SDK，从 `java/` 读取
   - `*.scala`、`build.sbt` → **Java**——Scala 使用 Java SDK，从 `java/` 读取
   - `*.go`、`go.mod` → **Go**——从 `go/` 读取
   - `*.rb`、`Gemfile` → **Ruby**——从 `ruby/` 读取
   - `*.cs`、`*.csproj` → **C#**——从 `csharp/` 读取
   - `*.php`、`composer.json` → **PHP**——从 `php/` 读取

2. **如果检测到多种语言**（例如同时存在 Python 和 TypeScript 文件）：

   - 检查用户当前文件或问题与哪种语言相关
   - 如果仍然不明确，请询问："我检测到了 Python 和 TypeScript 文件。您使用哪种语言进行 Claude API 集成？"

3. **如果无法推断语言**（空项目，无源文件，或不受支持的语言）：

   - 使用 AskUserQuestion 并提供选项：Python、TypeScript、Java、Go、Ruby、cURL/原始 HTTP、C#、PHP
   - 如果 AskUserQuestion 不可用，则默认使用 Python 示例并注明："正在展示 Python 示例。如果您需要其他语言，请告知。"

4. **如果检测到不受支持的语言**（Rust、Swift、C++、Elixir 等）：

   - 建议使用 `curl/` 中的 cURL/原始 HTTP 示例，并注明可能存在社区 SDK
   - 主动提供 Python 或 TypeScript 示例作为参考实现

5. **如果用户需要 cURL/原始 HTTP 示例**，从 `curl/` 读取。

### 语言特定功能支持

| 语言       | 工具运行器   | 托管智能体    | 说明                                  |
| ---------- | ----------- | ------------- | ------------------------------------- |
| Python     | 是（测试版） | 是（测试版）   | 完全支持——`@beta_tool` 装饰器          |
| TypeScript | 是（测试版） | 是（测试版）   | 完全支持——`betaZodTool` + Zod           |
| Java       | 是（测试版） | 是（测试版）   | 使用注解类的测试版工具使用             |
| Go         | 是（测试版） | 是（测试版）   | `toolrunner` 包中的 `BetaToolRunner`    |
| Ruby       | 是（测试版） | 是（测试版）   | 测试版中的 `BaseTool` + `tool_runner`   |
| C#         | 否          | 否             | 官方 SDK                              |
| PHP        | 是（测试版） | 是（测试版）   | `BetaRunnableTool` + `toolRunner()`    |
| cURL       | 不适用      | 是（测试版）   | 原始 HTTP，无 SDK 功能                |

> **托管智能体代码示例**：为 Python、TypeScript、Go、Ruby、PHP、Java 和 cURL 提供了各语言专用的 README（`{lang}/managed-agents/README.md`、`curl/managed-agents.md`）。请阅读您语言的 README 以及语言无关的 `shared/managed-agents-*.md` 概念文件。**智能体是持久的——创建一次，通过 ID 引用。** 保存 `agents.create` 返回的智能体 ID，并将其传递给每次后续的 `sessions.create` 调用；不要在请求路径中调用 `agents.create`。Anthropic CLI 是从版本控制的 YAML 创建智能体和环境的一种便捷方式——其 URL 位于 `shared/live-sources.md` 中。如果所需的绑定未在 README 中显示，请从 `shared/live-sources.md` 中 WebFetch 相关条目，而不是猜测。C# 目前不支持托管智能体；请使用 cURL 风格的原始 HTTP 请求调用 API。

---

## 应该使用哪个界面？

> **从简单开始。** 默认使用满足需求的最简单层级。单次 API 调用和工作流可满足大多数用例——只有当任务确实需要开放式、模型驱动的探索时才使用智能体。

| 用例                                          | 层级            | 推荐界面                   | 原因                                                          |
| ----------------------------------------------- | --------------- | ------------------------- | ------------------------------------------------------------ |
| 分类、摘要、提取、问答                           | 单次 LLM 调用    | **Claude API**            | 一次请求，一次响应                                           |
| 批处理或嵌入                                     | 单次 LLM 调用    | **Claude API**            | 专用端点                                                     |
| 代码控制逻辑的多步骤流水线                       | 工作流          | **Claude API + 工具使用**   | 您来编排循环                                                 |
| 使用自有工具的自定义智能体                       | 智能体          | **Claude API + 工具使用**   | 最大灵活性                                                   |
| 带工作空间的服务端有状态智能体                   | 智能体          | **托管智能体**             | Anthropic 运行循环并托管工具执行沙箱                          |
| 持久化、版本化的智能体配置                       | 智能体          | **托管智能体**             | 智能体是已存储的对象；会话固定到某个版本                      |
| 带文件挂载的长时间多轮智能体                     | 智能体          | **托管智能体**             | 每会话容器、SSE 事件流、Skills + MCP                          |

> **注意：** 当您希望 Anthropic 运行智能体循环并托管工具执行的容器时——文件操作、bash、代码执行都在每会话工作空间中运行——托管智能体是正确的选择。如果您希望自行托管计算或运行自己的自定义工具运行时，Claude API + 工具使用是正确的选择——使用工具运行器进行自动循环处理，或使用手动循环进行细粒度控制（审批门控、自定义日志记录、条件执行）。

> **第三方供应商（Amazon Bedrock、Google Vertex AI、Microsoft Foundry）：** 托管智能体在 Bedrock、Vertex 或 Foundry 上**不可用**。如果您通过任何第三方供应商部署，请在所有用例中使用 **Claude API + 工具使用**——包括本来会推荐使用托管智能体的情况。

### 决策树

```
您的应用需要什么？

0. 您是否通过 Amazon Bedrock、Google Vertex AI 或 Microsoft Foundry 部署？
   └── 是 → Claude API（智能体使用 + 工具使用）——托管智能体仅限第一方。
   否 → 继续。

1. 单次 LLM 调用（分类、摘要、提取、问答）
   └── Claude API——一次请求，一次响应

2. 您是否希望 Anthropic 运行智能体循环并托管每会话容器，
   让 Claude 在其中执行工具（bash、文件操作、代码）？
   └── 是 → 托管智能体——服务端管理的会话、持久化的智能体配置、
       SSE 事件流、Skills + MCP、文件挂载。
       示例："带每任务工作空间的有状态编码智能体"、
                 "长时间运行的研究智能体，向 UI 流式传输事件"、
                 "具有跨多个会话使用的持久化、版本化配置的智能体"

3. 工作流（多步骤、代码编排、使用自有工具）
   └── Claude API 带工具使用——您控制循环

4. 开放式智能体（模型自行决定轨迹、使用自有工具、自行托管计算）
   └── Claude API 智能体循环（最大灵活性）
```

### 应该构建智能体吗？

在选择智能体层级之前，检查所有四个标准：

- **复杂度**——任务是否多步骤且难以提前完全指定？（例如："将这份设计文档变成 PR" 对比 "从这份 PDF 中提取标题"）
- **价值**——结果是否值得更高的成本和延迟？
- **可行性**——Claude 在这种任务类型上是否胜任？
- **错误成本**——错误能否被捕获并从中恢复？（测试、审查、回滚）

如果对其中任何一项的回答是"否"，请保持在更简单的层级（单次调用或工作流）。

---

## 架构

一切通过 `POST /v1/messages` 进行。工具和输出约束是这个单一端点的功能——不是独立的 API。

**用户定义的工具**——您定义工具（通过装饰器、Zod 模式或原始 JSON），SDK 的工具运行器负责调用 API、执行您的函数并保持循环直到 Claude 完成。如需完全控制，您可以手动编写循环。

**服务端工具**——由 Anthropic 托管的工具，在 Anthropic 的基础设施上运行。代码执行完全在服务端进行（在 `tools` 中声明，Claude 自动运行代码）。计算机使用可以是服务端托管或自行托管。

**结构化输出**——约束 Messages API 的响应格式（`output_config.format`）和/或工具参数验证（`strict: true`）。推荐的方法是使用 `client.messages.parse()`，它会自动根据您的模式验证响应。注意：旧的 `output_format` 参数已弃用；请在 `messages.create()` 上使用 `output_config: {format: {...}}`。

**辅助端点**——批处理（`POST /v1/messages/batches`）、文件（`POST /v1/files`）、令牌计数和模型（`GET /v1/models`、`GET /v1/models/{id}`——实时能力和上下文窗口发现）为 Messages API 请求提供支持。

---

## 当前模型（缓存日期：2026-05-26）

| 模型              | 模型 ID              | 上下文       | 输入 $/1M | 输出 $/1M |
| ----------------- | ------------------- | ------------ | --------- | ----------- |
| Claude Opus 4.8   | `claude-opus-4-8`   | 1M           | $5.00     | $25.00      |
| Claude Opus 4.7   | `claude-opus-4-7`   | 1M           | $5.00     | $25.00      |
| Claude Opus 4.6   | `claude-opus-4-6`   | 1M           | $5.00     | $25.00      |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M           | $3.00     | $15.00      |
| Claude Haiku 4.5  | `claude-haiku-4-5`  | 200K         | $1.00     | $5.00       |

**始终使用 `claude-opus-4-8`，除非用户明确指定了不同的模型。** 这是不可协商的。除非用户明确说"使用 sonnet"或"使用 haiku"，否则不要使用 `claude-sonnet-4-6`、`claude-sonnet-4-5` 或任何其他模型。切勿为了成本而降级——那是用户的决定，不是您的决定。

**关键：仅使用上表中确切的模型 ID 字符串——它们本身已经完整。不要附加日期后缀。** 例如，使用 `claude-sonnet-4-5`，切勿使用 `claude-sonnet-4-5-20250514` 或您可能从训练数据中记起的任何其他日期后缀变体。如果用户请求了表中未列出的旧模型（例如"opus 4.5"、"sonnet 3.7"），请阅读 `shared/models.md` 以获取确切的 ID——不要自行构造。

注意：如果您觉得上面的一些模型字符串看起来很陌生，这在意料之中——这仅仅意味着它们是在您的训练数据截止日期之后发布的。请放心，它们是真实的模型；我们不会这样捉弄您。

**实时能力查询：** 上表已缓存。当用户询问"X 的上下文窗口是多少"、"X 是否支持视觉/思考/effort"或"哪些模型支持 Y"时，请查询 Models API（`client.models.retrieve(id)` / `client.models.list()`）——请参阅 `shared/models.md` 了解字段参考和能力过滤示例。

---

## 思考与 Effort（快速参考）

**Opus 4.8 / 4.7——仅自适应思考：** 使用 `thinking: {type: "adaptive"}`。`thinking: {type: "enabled", budget_tokens: N}` 会返回 400 错误——自适应是唯一的开启模式。`{type: "disabled"}` 和省略 `thinking` 都可以工作。采样参数（`temperature`、`top_p`、`top_k`）也同样被移除，使用会返回 400 错误。Opus 4.8 保持与 4.7 相同的请求表面（无新的破坏性变更）——请参阅 `shared/model-migration.md` → 迁移到 Opus 4.8 了解行为重新调优，以及 → 迁移到 Opus 4.7 了解从 4.6 或更早版本迁移时的完整破坏性变更列表。注意：在禁用 `thinking` 的情况下，Opus 4.8 可能会在可见响应中写入更长的推理内容——保持自适应思考开启，或添加一个仅回复最终答案的指令（请参阅迁移指南）。
**Opus 4.6——自适应思考（推荐）：** 使用 `thinking: {type: "adaptive"}`。Claude 动态决定何时思考以及思考多少。无需 `budget_tokens`——`budget_tokens` 在 Opus 4.6 和 Sonnet 4.6 上已弃用，不应在新代码中使用。自适应思考还会自动启用交错思考（无需 beta 头）。**当用户要求"扩展思考"、"思考预算"或 `budget_tokens` 时：始终使用 Opus 4.8、4.7 或 4.6，配合 `thinking: {type: "adaptive"}`。固定令牌预算用于思考的概念已弃用——自适应思考取而代之。不要在 4.6/4.7/4.8 的新代码中使用 `budget_tokens`，也不要切换到旧模型。** *渐进迁移例外：* `budget_tokens` 在 Opus 4.6 和 Sonnet 4.6 上仍然可用，作为过渡性逃生舱——如果您正在迁移现有代码并在调优 `effort` 之前需要硬性令牌上限，请参阅 `shared/model-migration.md` → 过渡性逃生舱。注意：此例外**不**适用于 Opus 4.7 或 4.8——在这些版本上 `budget_tokens` 已完全移除。
**Effort 参数（GA，无需 beta 头）：** 通过 `output_config: {effort: "low"|"medium"|"high"|"max"}`（在 `output_config` 内部，不是顶层）控制思考深度和总体令牌消耗。默认值为 `high`（等同于省略该参数）。`max` 仅限 Opus 层级（Opus 4.6 及更新版本——不适用于 Sonnet 或 Haiku）。Opus 4.7 新增了 `"xhigh"`（介于 `high` 和 `max` 之间）——对于 Opus 4.7/4.8 上的大多数编码和智能体用例来说是最佳设置，也是 Claude Code 中的默认设置；对于大多数对智能敏感的工作，至少使用 `high`。适用于 Opus 4.5、Opus 4.6、Opus 4.7、Opus 4.8 和 Sonnet 4.6。在 Sonnet 4.5 / Haiku 4.5 上会报错。在 Opus 4.7 和 4.8 上，effort 比任何之前的 Opus 版本都更重要——迁移时重新调优它，并在 `high`/`xhigh` 级别下运行长周期/智能体任务，同时提前给出完整任务规范。与自适应思考结合使用以获得最佳成本质量权衡。较低的 effort 意味着更少且更整合的工具调用、更少的前置说明和更简洁的确认——`high` 通常是平衡质量和令牌效率的最佳点；当正确性比成本更重要时使用 `max`；对子智能体或简单任务使用 `low`。

**Opus 4.8 / 4.7——thinking 内容默认省略：** `thinking` 块仍然会流式传输，但其文本为空，除非您选择使用 `thinking: {type: "adaptive", display: "summarized"}`（默认值为 `"omitted"`）。静默变更——无错误。如果您向用户流式传输推理内容，默认情况看起来像是在输出之前长时间停顿；设置 `"summarized"` 可恢复可见进度。

**任务预算（测试版，Opus 4.7 / 4.8）：** `output_config: {task_budget: {type: "tokens", total: N}}` 告诉模型它在整个智能体循环中有多少令牌可用——它会看到运行的倒计时并自我调节（最低 20,000；beta 头 `task-budgets-2026-03-13`）。与 `max_tokens` 不同，后者是模型不知情的、强制性的每响应上限。请参阅 `shared/model-migration.md` → 任务预算。

**Sonnet 4.6：** 支持自适应思考（`thinking: {type: "adaptive"}`）。`budget_tokens` 在 Sonnet 4.6 上已弃用——请改用自适应思考。

**旧模型（仅在明确请求时使用）：** 如果用户特别要求 Sonnet 4.5 或其他旧模型，使用 `thinking: {type: "enabled", budget_tokens: N}`。`budget_tokens` 必须小于 `max_tokens`（最低 1024）。切勿因为用户提到 `budget_tokens` 就选择旧模型——请使用 Opus 4.8 配合自适应思考。

---

## 压缩（快速参考）

**测试版，Opus 4.8、Opus 4.7、Opus 4.6 和 Sonnet 4.6。** 对于可能超过 1M 上下文窗口的长时间对话，启用服务端压缩。当上下文接近触发阈值（默认：150K 令牌）时，API 会自动汇总较早的上下文。需要 beta 头 `compact-2026-01-12`。

**关键：** 在每一轮中都将 `response.content`（不仅是文本）追加回您的消息中。响应中的压缩块必须保留——API 使用它们在下一次请求中替换已压缩的历史记录。仅提取文本字符串并追加它会静默丢失压缩状态。

请参阅 `{lang}/claude-api/README.md`（压缩部分）了解代码示例。完整文档可通过 `shared/live-sources.md` 中的 WebFetch 获取。

---

## 提示缓存（快速参考）

**前缀匹配。** 前缀中任何位置的任何字节更改都会使其之后的所有内容失效。渲染顺序为 `tools` → `system` → `messages`。将稳定内容放在前面（冻结的系统提示、确定性的工具列表），将可变内容（时间戳、每请求 ID、变化的问题）放在最后一个 `cache_control` 断点之后。

**顶层自动缓存**（在 `messages.create()` 上设置 `cache_control: {type: "ephemeral"}`）是在不需要精细放置时最简单的选项。每请求最多 4 个断点。可缓存的最小前缀约为 1024 个令牌——较短的前缀静默地不会缓存。

**通过 `usage.cache_read_input_tokens` 验证**——如果跨重复请求该值为零，则存在静默无效器（系统提示中的 `datetime.now()`、未排序的 JSON、变化的工具集）。

有关放置模式、架构指导以及静默无效器审计清单：请阅读 `shared/prompt-caching.md`。语言特定的语法：`{lang}/claude-api/README.md`（提示缓存部分）。

---

## 托管智能体（测试版）

**托管智能体**是第三种界面：服务端管理的、有状态的智能体，具有 Anthropic 托管的工具执行功能。您创建一个持久的、版本化的智能体配置（`POST /v1/agents`），然后启动引用该配置的会话。每个会话为智能体提供一个容器作为工作空间——bash、文件操作和代码执行在其中运行；智能体循环本身在 Anthropic 的编排层上运行，并通过工具对容器进行操作。会话流式传输事件；您发送消息和工具结果回去。

**托管智能体仅限第一方。** 它在 Amazon Bedrock、Google Vertex AI 或 Microsoft Foundry 上不可用。对于第三方供应商上的智能体，请使用 Claude API + 工具使用。

**必需流程：** 智能体（一次）→ 会话（每次运行）。`model`/`system`/`tools` 位于智能体上，永远不会在会话上。请参阅 `shared/managed-agents-overview.md` 了解完整的阅读指南、beta 头以及陷阱。

**Beta 头：** `managed-agents-2026-04-01`——SDK 会自动为所有 `client.beta.{agents,environments,sessions,vaults,memory_stores}.*` 调用设置此头。Skills API 使用 `skills-2025-10-02`，Files API 使用 `files-api-2025-04-14`，但除了 `/v1/skills` 和 `/v1/files` 之外的端点您不需要显式传递这些头。

**子命令**——直接使用 `/claude-api <子命令>` 调用：

| 子命令 | 操作 |
|---|---|
| `managed-agents-onboard` | 引导用户从头设置托管智能体。**立即阅读 `shared/managed-agents-onboarding.md`** 并遵循其访谈脚本：心智模型 → 了解或探索分支 → 模板配置 → 会话设置 → 生成代码。不要总结——执行访谈。 |

**阅读指南：** 从 `shared/managed-agents-overview.md` 开始，然后是专题性的 `shared/managed-agents-*.md` 文件（核心、环境、工具、事件、结果、多智能体、webhook、记忆、客户端模式、入门、API 参考）。对于 Python、TypeScript、Go、Ruby、PHP 和 Java，阅读 `{lang}/managed-agents/README.md` 了解代码示例。对于 cURL，阅读 `curl/managed-agents.md`。**智能体是持久的——创建一次，通过 ID 引用。** 保存 `agents.create` 返回的智能体 ID，并将其传递给每次后续的 `sessions.create` 调用；不要在请求路径中调用 `agents.create`。Anthropic CLI 是从版本控制的 YAML 创建智能体和环境的一种便捷方式（URL 在 `shared/live-sources.md` 中）。如果所需的绑定未在语言 README 中显示，请从 `shared/live-sources.md` 中 WebFetch 相关条目，而不是猜测。C# 目前不支持托管智能体；请使用 `curl/managed-agents.md` 中的原始 HTTP 作为参考。

**当用户希望从头设置托管智能体时**（例如"如何开始"、"带我创建一个"、"设置一个新智能体"）：阅读 `shared/managed-agents-onboarding.md` 并运行其访谈——与 `managed-agents-onboard` 子命令相同的流程。

**当用户询问"如何为 X 编写客户端代码"时：** 查阅 `shared/managed-agents-client-patterns.md`——涵盖无损流重连、`processed_at` 排队/处理门控、中断、`tool_confirmation` 往返、正确的空闲/终止断开门控、空闲后状态竞态、流优先排序、文件挂载陷阱、通过自定义工具将凭证保留在主机端等。

---

## 阅读指南

在检测到语言后，根据用户需求阅读相关文件：

### 快速任务参考

**单次文本分类/摘要/提取/问答：**
→ 仅阅读 `{lang}/claude-api/README.md`

**聊天 UI 或实时响应显示：**
→ 阅读 `{lang}/claude-api/README.md` + `{lang}/claude-api/streaming.md`

**长时间对话（可能超出上下文窗口）：**
→ 阅读 `{lang}/claude-api/README.md`——参见压缩部分

**迁移到更新模型（Opus 4.8 / Opus 4.7 / Opus 4.6 / Sonnet 4.6）或替换已退役模型：**
→ 阅读 `shared/model-migration.md`

**提示缓存 / 优化缓存 / "为什么我的缓存命中率很低"：**
→ 阅读 `shared/prompt-caching.md` + `{lang}/claude-api/README.md`（提示缓存部分）

**函数调用 / 工具使用 / 智能体：**
→ 阅读 `{lang}/claude-api/README.md` + `shared/tool-use-concepts.md` + `{lang}/claude-api/tool-use.md`

**智能体设计（工具表面、上下文管理、缓存策略）：**
→ 阅读 `shared/agent-design.md`

**批处理（非延迟敏感）：**
→ 阅读 `{lang}/claude-api/README.md` + `{lang}/claude-api/batches.md`

**跨多个请求上传文件：**
→ 阅读 `{lang}/claude-api/README.md` + `{lang}/claude-api/files-api.md`

**托管智能体（带工作空间的服务端管理有状态智能体）：**
→ 阅读 `shared/managed-agents-overview.md` 以及其余 `shared/managed-agents-*.md` 文件。对于 Python、TypeScript、Go、Ruby、PHP 和 Java，阅读 `{lang}/managed-agents/README.md` 了解代码示例。对于 cURL，阅读 `curl/managed-agents.md`。**智能体是持久的——创建一次，通过 ID 引用。** 保存 `agents.create` 返回的智能体 ID，并将其传递给每次后续的 `sessions.create` 调用；不要在请求路径中调用 `agents.create`。Anthropic CLI 是从版本控制的 YAML 创建智能体和环境的一种便捷方式（URL 在 `shared/live-sources.md` 中）。如果所需的绑定未在语言 README 中显示，请从 `shared/live-sources.md` 中 WebFetch 相关条目，而不是猜测。C# 目前不支持托管智能体——请使用 `curl/managed-agents.md` 中的原始 HTTP 作为参考。

### Claude API（完整文件参考）

阅读**特定语言的 Claude API 文件夹**（`{language}/claude-api/`）：

1. **`{language}/claude-api/README.md`**——**首先阅读此文件。** 安装、快速入门、常见模式、错误处理。
2. **`shared/tool-use-concepts.md`**——当用户需要函数调用、代码执行、记忆或结构化输出时阅读。涵盖概念基础。
3. **`shared/agent-design.md`**——在设计智能体时阅读：bash 与专用工具、编程式工具调用、工具搜索/skills、上下文编辑与压缩与记忆、缓存原则。
4. **`{language}/claude-api/tool-use.md`**——阅读以获取特定语言的工具使用代码示例（工具运行器、手动循环、代码执行、记忆、结构化输出）。
5. **`{language}/claude-api/streaming.md`**——在构建聊天 UI 或增量显示响应的界面时阅读。
6. **`{language}/claude-api/batches.md`**——在离线处理大量请求时阅读（非延迟敏感）。以 50% 的成本异步运行。
7. **`{language}/claude-api/files-api.md`**——在无需重新上传的情况下跨多个请求发送同一文件时阅读。
8. **`shared/prompt-caching.md`**——在添加或优化提示缓存时阅读。涵盖前缀稳定性设计、断点放置以及静默使缓存失效的反模式。
9. **`shared/error-codes.md`**——在调试 HTTP 错误或实现错误处理时阅读。
10. **`shared/model-migration.md`**——在升级到更新模型、替换已退役模型或翻译 `budget_tokens`/预填充模式到当前 API 时阅读。
11. **`shared/live-sources.md`**——用于获取最新官方文档的 WebFetch URL。

> **注意：** 对于 Java、Go、Ruby、C#、PHP 和 cURL——这些语言各自有一个涵盖所有基础知识的文件。根据需要阅读该文件加上 `shared/tool-use-concepts.md` 和 `shared/error-codes.md`。

> **注意：** 关于托管智能体的文件参考，请参见上面的 `## 托管智能体（测试版）` 部分——其中列出了每个 `shared/managed-agents-*.md` 文件和特定语言的 README。

---

## 何时使用 WebFetch

在以下情况下使用 WebFetch 获取最新文档：

- 用户要求"最新"或"当前"信息
- 缓存的数据似乎不正确
- 用户询问此处未涵盖的功能

实时文档 URL 位于 `shared/live-sources.md` 中。

## 常见陷阱

- 在向 API 传递文件或内容时，不要截断输入。如果内容太长而无法放入上下文窗口，请通知用户并讨论选项（分块、摘要等），而不是静默截断。
- **Opus 4.8 / 4.7 思考：** 仅自适应。`thinking: {type: "enabled", budget_tokens: N}` 返回 400 错误——`budget_tokens` 已完全移除（连同 `temperature`、`top_p`、`top_k`）。使用 `thinking: {type: "adaptive"}`。Opus 4.8 从 4.7 继承了此表面，无新的破坏性变更。
- **Opus 4.6 / Sonnet 4.6 思考：** 使用 `thinking: {type: "adaptive"}`——不要在 4.6 的新代码中使用 `budget_tokens`（在 Opus 4.6 和 Sonnet 4.6 上均已弃用；对于现有代码的渐进迁移，请参阅 `shared/model-migration.md` 中的过渡性逃生舱——注意此例外不适用于 Opus 4.7 或 4.8）。对于旧模型，`budget_tokens` 必须小于 `max_tokens`（最低 1024）。如果设置错误会抛出错误。
- **4.6/4.7/4.8 系列预填充已移除：** 在 Opus 4.6、Opus 4.7、Opus 4.8 和 Sonnet 4.6 上，助手消息预填充（最后助手轮次预填充）返回 400 错误。请改用结构化输出（`output_config.format`）或系统提示指令来控制响应格式。
- **在编辑前确认迁移范围：** 当用户要求将代码迁移到更新的 Claude 模型但未指定具体文件、目录或文件列表时，**先询问要应用于哪个范围**——整个工作目录、特定子目录，还是一组特定文件。在用户确认之前不要开始编辑。命令式措辞如"迁移我的代码库"、"将我的项目迁移到 X"、"升级到 Sonnet 4.6"或裸写"迁移到 Opus 4.8"**仍然是模糊的**——它们告诉您做什么但没有告诉您在哪里做，所以需要询问。只有在提示词明确指定了确切的文件、特定的目录或明确的文件列表（"迁移 `app.py`"、"迁移 `services/` 下的所有内容"、"更新 `a.py` 和 `b.py`"）时才无需询问直接进行。请参阅 `shared/model-migration.md` 的第 0 步。
- **`max_tokens` 默认值：** 不要将 `max_tokens` 设置得太低——达到上限会在思考中途截断输出并需要重试。对于非流式请求，默认使用约 `16000`（保持响应在 SDK HTTP 超时内）。对于流式请求，默认使用约 `64000`（超时不是问题，所以给模型留出空间）。只有在有充分理由时才设置得更低：分类（约 `256`）、成本上限或故意缩短输出。
- **128K 输出令牌：** Opus 4.6、Opus 4.7 和 Opus 4.8 支持最高 128K 的 `max_tokens`，但 SDK 要求对如此大的值使用流式传输以避免 HTTP 超时。使用 `.stream()` 配合 `.get_final_message()` / `.finalMessage()`。
- **工具调用 JSON 解析（4.6/4.7/4.8 系列）：** Opus 4.6、Opus 4.7、Opus 4.8 和 Sonnet 4.6 可能在工具调用 `input` 字段中生成不同的 JSON 字符串转义（例如 Unicode 或正斜杠转义）。始终使用 `json.loads()` / `JSON.parse()` 解析工具输入——切勿对序列化输入进行原始字符串匹配。
- **结构化输出（所有模型）：** 在 `messages.create()` 上使用 `output_config: {format: {...}}` 替代已弃用的 `output_format` 参数。这是一个通用的 API 变更，不是 4.6 特有的。
- **不要重新实现 SDK 功能：** SDK 提供了高级辅助方法——请使用它们而不是从头构建。具体来说：使用 `stream.finalMessage()` 替代包装 `.on()` 事件在 `new Promise()` 中；使用类型化异常类（`Anthropic.RateLimitError` 等）替代字符串匹配错误消息；使用 SDK 类型（`Anthropic.MessageParam`、`Anthropic.Tool`、`Anthropic.Message` 等）替代重新定义等效接口。
- **不要为 SDK 数据结构定义自定义类型：** SDK 导出了所有 API 对象的类型。消息使用 `Anthropic.MessageParam`，工具定义使用 `Anthropic.Tool`，工具结果使用 `Anthropic.ToolUseBlock` / `Anthropic.ToolResultBlockParam`，响应使用 `Anthropic.Message`。定义自己的 `interface ChatMessage { role: string; content: unknown }` 重复了 SDK 已提供的内容并失去了类型安全性。
- **报告和文档输出：** 对于生成报告、文档或可视化效果的任务，代码执行沙箱预装了 `python-docx`、`python-pptx`、`matplotlib`、`pillow` 和 `pypdf`。Claude 可以生成格式化文件（DOCX、PDF、图表）并通过 Files API 返回它们——对于"报告"或"文档"类型的请求，请考虑此方式，而不是纯文本的 stdout 输出。
