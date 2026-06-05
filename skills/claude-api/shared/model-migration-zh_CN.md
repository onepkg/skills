# 模型迁移指南

如何将现有代码迁移到更新的 Claude 模型。涵盖破坏性变更、已弃用参数以及已停用模型的直接替代品。

如需最新、权威版本（包含所有支持语言的代码示例），请从 `shared/live-sources.md` 中 WebFetch **迁移指南** URL。本文件用于整合的、驻留在技能中的参考；当模型发布或破坏性变更可能改变情况时，请回退到实时文档。

**本文件很大。** 使用下面的章节名称跳转（或在文件中 `grep` 标题文本）。先阅读步骤 0 和步骤 1 — 它们适用于每次迁移。然后只阅读您要迁移到的目标模型的对应章节。

| 章节 | 何时需要 |
|---|---|
| 步骤 0：确认迁移范围 | 总是 — 在任何编辑之前 |
| 步骤 1：对每个文件分类 | 总是 — 决定是交换、并排添加还是跳过 |
| 各 SDK 语法参考 | 将本指南中的 Python 示例翻译成 TypeScript / Go / Ruby / Java / C# / PHP |
| 目标模型 / 已停用模型替代品 | 选择目标模型 |
| 按源模型列出的破坏性变更 | 迁移到 Opus 4.6 / Sonnet 4.6 |
| 迁移到 Opus 4.7 | 迁移到 Opus 4.7（破坏性变更、静默默认值、行为转变） |
| Opus 4.7 迁移检查清单 | 4.7 的必选与可选项目，标记为 `[BLOCKS]` / `[TUNE]` |
| 迁移到 Opus 4.8 | 迁移到 Opus 4.8（无新的破坏性变更；会话中系统提示；行为重新调优） |
| Opus 4.8 迁移检查清单 | 4.8 的必选与可选项目，标记为 `[BLOCKS]` / `[TUNE]` |
| 验证迁移 | 编辑后 — 运行时抽查 |

**要点：** 更改模型 ID 字符串。如果您在使用 `budget_tokens`，请切换到 `thinking: {type: "adaptive"}`。如果您在使用助手预填充，它们在 Opus 4.6 和 Sonnet 4.6 上都会返回 400 — 请切换到预填充替代品之一（最常见的是 `output_config.format`；请参阅按源模型列出的破坏性变更中的表格）。如果您从 Sonnet 4.5 迁移到 Sonnet 4.6，请显式设置 `effort` — 4.6 默认为 `high`。移除 `effort-2025-11-24` 和 `fine-grained-tool-streaming-2025-05-14` beta 头（在 4.6 上已正式发布）；一旦使用自适应思考，移除 `interleaved-thinking-2025-05-14`（仅在使用过渡性的 `budget_tokens` 逃生舱时保留）。然后从 `client.beta.messages.create` 回退到 `client.messages.create`。减少任何激进的"CRITICAL: YOU MUST"工具指令；4.6 会更紧密地遵循系统提示。

---

## 步骤 0：确认迁移范围

**在任何 Write、Edit 或 MultiEdit 调用之前，请确认范围。** 如果用户的请求没有明确命名单个文件、特定目录或明确的文件列表，**先问清楚 — 不要开始编辑**。这是不可协商的：即使是听起来很命令式的请求，如"迁移我的代码库"、"将我的项目移到 X"、"升级到 Sonnet 4.6"或裸的"迁移到 Opus 4.7"都留下了模棱两可的范围，需要一个澄清问题。像"我的项目"、"我的代码"、"我的代码库"、"整个事情"、"到处"或"跨仓库"这样的短语是**模棱两可的，不是指令性的** — 它们告诉您要做什么，但不告诉您在哪里做。做之前先问。

明确提供常见选项并等待答案，然后再接触任何文件：

1. 整个工作目录
2. 特定子目录（例如 `src/`、`app/`、`services/billing/`）
3. 特定文件或文件列表

将此作为单个澄清问题提出，以便用户可以在一次轮次中回答。**只有在范围已经明确时才无需询问进行** — 用户命名了确切的文件（"将 `extract.py` 迁移到 Sonnet 4.6"），指向了特定目录（"将 `services/billing/` 下的所有内容迁移到 Opus 4.6"），列出了特定文件（"更新 `a.py` 和 `b.py`"），或者已经在之前的轮次中回答了范围问题。如果您可以仅通过提示就能回答"这个变更会触及哪些文件？"这个问题并有精确列表，就继续。否则，询问。

**实际示例。** 如果用户说*"将我的项目移到 Opus 4.6。我希望在合理的地方都使用自适应思考。"* 您不知道"我的项目"是指整个工作目录、只是 `src/`、只是生产代码还是其他什么 — "到处"使得意图明确（更新范围内的每个调用点），但范围本身仍未定义。不要开始编辑。回复：

> 在我开始编辑之前，您能确认范围吗？我可以迁移：
> 1. 工作目录中的每个 `.py` 文件
> 2. 只迁移 `src/` 下的文件（生产代码）
> 3. 您命名的特定子目录或文件列表
>
> 选哪一个？

然后等待答案。同样适用于*"迁移到 Opus 4.7"*和裸的*"帮我升级到 Sonnet 4.6"* — 编辑前先问。

**估算范围问题的大小（大型仓库）。** 在询问之前，获取每个目录的计数，以便用户可以具体选择：

```sh
rg -l "<旧模型ID>" --type-not md | cut -d/ -f1 | sort | uniq -c | sort -rn
```

在您的范围问题中呈现细目（例如 *"在 3 个目录中找到 217 个引用：api/（130）、api-go/（62）、routing/（25）。迁移哪个？"*）。还要在调查前确认 `git status` 是干净的 — 意外的修改意味着并发进程；继续前停止并调查。

---

## 步骤 1：对每个文件分类

并非每个包含旧模型 ID 的文件都是 API 的**调用者**。在编辑之前，将每个文件分类到这些桶之一 — 正确的操作会有所不同：

| # | 桶 | 看起来像什么 | 操作 |
|---|---|---|---|
| 1 | **调用 API/SDK** | `client.messages.create(model=...)`、`anthropic.Anthropic()`、请求负载 | 交换模型 ID **并** 应用目标版本的破坏性变更检查清单（见下文）。 |
| 2 | **定义或服务模型** | 模型注册表、OpenAPI 规范、路由/队列配置、模型策略枚举、生成的目录 | 旧条目**保留**（模型仍在服务中）。询问是否（a）并排添加新模型、（b）保持不变或（c）淘汰旧模型 — 永远不要盲目替换。**如果不能问，默认选择（a）：并排添加新模型并标记它** — 替换会注销仍在生产中的模型。 |
| 3 | **将 ID 引用为不透明字符串** | UI 回退常量、能力门控子字符串检查、通用测试夹具、标签解析器、环境默认值 | 通常交换字符串并验证任何解析器/正则表达式/子字符串匹配都能处理新 ID — 但首先检查下面的子情况。 |
| 4 | **带后缀的变体 ID** | `claude-<model>-<suffix>`，如 `-fast`、`-1024k`、`-200k`、`[1m]`、带日期的快照 | 这些是部署/路由标识符，不是公共模型 ID。**不要假设存在等效的新模型。** 先在注册表中验证；如果不存在，请保持字符串不变并标记它。 |

**桶 3 子情况 — 在交换字符串引用之前，请检查：**

- **能力门控**（例如 `if 'opus-4-6' in model_id:` 启用功能）→ **并排添加新 ID**，不要替换。旧模型仍在服务中且仍具有该能力，因此替换会静默禁用仍在流动的任何旧模型流量的该功能。如果您知道没有旧模型流量会命中此门控（单一调用者代码库完全迁移），则替换没问题；如果不确定，请并排添加。
- **注册表断言测试**（例如 `assert "claude-X" in supported_models`、`test_X_has_N_clusters`）→ **为新模型并排添加断言；保留旧的。** 旧模型仍在服务中，因此其断言仍然有效 — 但注册表也应包含新模型，因此也要断言。启发式：如果测试在列表中引用多个模型版本，那就是注册表测试；如果一个结构体中的一个模型只与自身比较，那就是通用夹具。
- **冻结 / 生成的快照** → **重新生成**，不要手动编辑。
- **耦合到定义器**（例如通过共享的 `conftest` 种子列表传递模型授权的集成测试，或断言计费层 / 速率限制组枚举或生成的 SKU/定价目录）→ **先验证定义器有新模型条目。** 如果没有，添加种子条目（重用最近的现有层作为占位符）；如果您不能自信地这样做，请询问用户如何填充定义器。**不要跳过测试。** 不填充定义器就交换会使测试在运行时失败。

特别是迁移测试时：已弃用的参数（`temperature`、`top_p`、`budget_tokens`）通常不存在 — 测试夹具很少在占位符模型上设置采样参数。破坏性变更扫描仍然是必需的，但期望大部分结果是干净的。

**首先查找故意标记的同步点。** 许多代码库用注释标记标记每次模型发布时必须更改的位置，如 `MODEL LAUNCH`、`KEEP IN SYNC`、`@model-update` 或类似内容。在广泛的模型 ID grep 之前 **先** grep 仓库使用的任何约定 — 这些标记指向承载负载的变更。

---

## 各 SDK 语法参考

本指南中的代码示例是 Python。**相同的字段存在于每个官方 Anthropic SDK 中** — Stainless 从相同的 OpenAPI 规范生成所有 7 个 SDK，因此 JSON 字段名称 1:1 映射，只有大小写约定不同。使用下面的行将 Python 示例翻译成您正在迁移的 SDK。

> **在写入客户代码之前，请对照 SDK 源验证类型和方法名称。** 从 `shared/live-sources.md` 中的 SDK 源代码表（每个 SDK 一行）WebFetch 相关仓库并确认确切的符号 — 特别是对于类型化的 SDK（Go、Java、C#），其中联合/构建器名称可能与 JSON 形状不同。不要猜测不在下表或 `<lang>/claude-api/README.md` 中的类型名称。

### `thinking` — `budget_tokens` → 自适应

| SDK | 之前 | 之后 |
|---|---|---|
| Python | `thinking={"type": "enabled", "budget_tokens": N}` | `thinking={"type": "adaptive"}` |
| TypeScript | `thinking: { type: 'enabled', budget_tokens: N }` | `thinking: { type: 'adaptive' }` |
| Go | `Thinking: anthropic.ThinkingConfigParamOfEnabled(N)` | `Thinking: anthropic.ThinkingConfigParamUnion{OfAdaptive: &anthropic.ThinkingConfigAdaptiveParam{}}` |
| Ruby | `thinking: { type: "enabled", budget_tokens: N }` | `thinking: { type: "adaptive" }` |
| Java | `.thinking(ThinkingConfigEnabled.builder().budgetTokens(N).build())` | `.thinking(ThinkingConfigAdaptive.builder().build())` |
| C# | `Thinking = new ThinkingConfigEnabled { BudgetTokens = N }` | `Thinking = new ThinkingConfigAdaptive()` |
| PHP | `thinking: ['type' => 'enabled', 'budget_tokens' => N]` | `thinking: ['type' => 'adaptive']` |

### 采样参数 — `temperature` / `top_p` / `top_k`

（在 Opus 4.7 上完全移除该字段；在 Claude 4.x 上最多保留 `temperature` 或 `top_p` 之一。）

| SDK | 要移除的字段 |
|---|---|
| Python | `temperature=...`、`top_p=...`、`top_k=...` |
| TypeScript | `temperature: ...`、`top_p: ...`、`top_k: ...` |
| Go | `Temperature: anthropic.Float(...)`、`TopP: anthropic.Float(...)`、`TopK: anthropic.Int(...)` |
| Ruby | `temperature: ...`、`top_p: ...`、`top_k: ...` |
| Java | `.temperature(...)`、`.topP(...)`、`.topK(...)` |
| C# | `Temperature = ...`、`TopP = ...`、`TopK = ...` |
| PHP | `temperature: ...`、`topP: ...`、`topK: ...` |

### 预填充替换 — 通过 `output_config.format` 进行结构化输出

| SDK | 移除（最后一个助手轮次） | 添加 |
|---|---|---|
| Python | `{"role": "assistant", "content": "..."}` | `output_config={"format": {"type": "json_schema", "schema": SCHEMA}}` |
| TypeScript | `{ role: 'assistant', content: '...' }` | `output_config: { format: { type: 'json_schema', schema: SCHEMA } }` |
| Go | 尾部的 `anthropic.MessageParam{Role: "assistant", ...}` | `OutputConfig: anthropic.OutputConfigParam{Format: anthropic.JSONOutputFormatParam{...}}` |
| Ruby | `{ role: "assistant", content: "..." }` | `output_config: { format: { type: "json_schema", schema: SCHEMA } }` |
| Java | 尾部的 `Message.builder().role(ASSISTANT)...` | `.outputConfig(OutputConfig.builder().format(JsonOutputFormat.builder()...build()).build())` |
| C# | 尾部的 `new Message { Role = "assistant", ... }` | `OutputConfig = new OutputConfig { Format = new JsonOutputFormat { ... } }` |
| PHP | 尾部的 `['role' => 'assistant', 'content' => '...']` | `outputConfig: ['format' => ['type' => 'json_schema', 'schema' => $SCHEMA]]` |

### `thinking.display` — 选择回到摘要推理（Opus 4.7）

| SDK | 添加 |
|---|---|
| Python | `thinking={"type": "adaptive", "display": "summarized"}` |
| TypeScript | `thinking: { type: 'adaptive', display: 'summarized' }` |
| Go | `Thinking: anthropic.ThinkingConfigParamUnion{OfAdaptive: &anthropic.ThinkingConfigAdaptiveParam{Display: anthropic.ThinkingConfigAdaptiveDisplaySummarized}}` |
| Ruby | `thinking: { type: "adaptive", display: "summarized" }`（或直接构造模型类时使用 `display_:`） |
| Java | `.thinking(ThinkingConfigAdaptive.builder().display(ThinkingConfigAdaptive.Display.SUMMARIZED).build())` |
| C# | `Thinking = new ThinkingConfigAdaptive { Display = Display.Summarized }` |
| PHP | `thinking: ['type' => 'adaptive', 'display' => 'summarized']` |

对于不在这些表中的任何字段，Python 示例中的 JSON 键直接转换：Python/TypeScript/Ruby 用 `snake_case`，PHP 用 `camelCase` 命名参数，Go/C# 用 `PascalCase` 结构字段，Java 用 `camelCase` 构建器方法。

---

## 解释您所做的每项变更

迁移编辑对于未阅读发行说明的用户来说通常看起来是任意的 — 移除的 `temperature`、删除的预填充、重写的系统提示句子。**对于每次编辑，告诉用户您更改了什么以及为什么**，并与激发它的特定 API 或行为变更相关联。在工作时在您的摘要中执行此操作，而不仅仅是在最后。

对于**系统提示编辑**要特别明确。用户理所当然地会保护他们的提示，而提示调优变更属于判断调用（不是硬性 API 要求）。对于任何提示编辑：

- 引用之前和之后的文本。
- 说明激发它的行为转变（例如 *"Opus 4.7 根据任务复杂性校准响应长度，因此我添加了明确的长度指令"*，或 *"4.6 更字面地遵循指令，因此'CRITICAL: YOU MUST use the search tool' 现在会过度触发 — 已软化为'当...时使用搜索工具'"*）。
- 明确哪些提示编辑是**可选调优**（语气、长度、子代理指导），哪些代码编辑是**避免 400 所需的**（采样参数、`budget_tokens`、预填充）。永远不要将可选的提示变更呈现为强制性的。

如果您一次应用多个提示调优编辑，请将它们作为用户可以逐项接受或拒绝的简短列表提供，而不是静默重写他们的系统提示。

---

## 迁移前

1. **确认目标模型 ID。** 仅使用 `shared/models.md` 中的确切字符串 — 不要向别名附加日期后缀（`claude-opus-4-6`，不是 `claude-opus-4-6-20251101`）。猜测 ID 会返回 404。
2. **检查您的代码使用哪些功能** 使用此清单：
   - `thinking: {type: "enabled", "budget_tokens: N}` → 在 Opus 4.6 / Sonnet 4.6 上迁移到自适应思考（仍可用但已弃用）
   - 助手轮次预填充（以 `role: "assistant"` 结尾的 `messages`）→ 在 Opus 4.6 / Sonnet 4.6 上必须更改（返回 400）
   - `messages.create()` 上的 `output_format` 参数 → 在所有模型上必须更改（全 API 弃用）
   - `max_tokens > ~16000` → 在任何模型上必须流式传输（超过 ~16K 有 SDK HTTP 超时风险）。流式传输时，Sonnet 4.6 / Haiku 4.5 上限为 64K，Opus 4.6 上限为 128K
   - Beta 头 `effort-2025-11-24`、`fine-grained-tool-streaming-2025-05-14`、`interleaved-thinking-2025-05-14` → 在 4.6 上已正式发布，移除它们并从 `client.beta.messages.create` 切换到 `client.messages.create`
   - 将 Sonnet 4.5 → Sonnet 4.6 且未设置 `effort` → 4.6 默认为 `high`，这可能会改变您的延迟/成本概况
   - 带有 `CRITICAL`、`MUST`、`If in doubt, use X` 语言的系统提示 → 在 4.6 上可能过度触发（请参阅提示行为变更）
   - 从 3.x / 4.0 / 4.1 迁移：还要检查采样参数（`temperature` + `top_p`）、工具版本（`text_editor_20250728`）、`refusal` + `model_context_window_exceeded` 停止原因、尾随换行符工具参数处理
3. **先在单个请求上测试。** 对新模型运行一次调用，检查响应，然后推出。

---

## 目标模型（推荐目标）

| 如果您在...上                     | 迁移到         | 为什么                                               |
| --------------------------------- | -------------- | --------------------------------------------------- |
| Opus 4.7                          | `claude-opus-4-8` | 最强大的模型；与 4.7 相同的 API 表面（无新的破坏性变更）— 主要是提示重新调优；请参阅迁移到 Opus 4.8 |
| Opus 4.6                          | `claude-opus-4-8` | 应用 Opus 4.7 的破坏性变更，然后进行 4.8 的重新调优 |
| Opus 4.0 / 4.1 / 4.5 / Opus 3     | `claude-opus-4-8` | 按顺序应用 4.6 → 4.7 → 4.8（自适应思考、删除采样参数，然后重新调优） |
| Sonnet 4.0 / 4.5 / 3.7 / 3.5      | `claude-sonnet-4-6` | 最佳速度 / 智能平衡；自适应思考；64K 输出 |
| Haiku 3 / 3.5                     | `claude-haiku-4-5` | 最快且最具成本效益 |

默认使用调用者层级的最新 Opus，除非他们明确选择其他方式。Opus 迁移分层：如果您在 Opus 4.6 或更早版本，请按顺序应用每个版本的章节直到您的目标（例如 4.5 → 4.8 意味着依次应用 4.6、4.7 和 4.8 章节）。4.7 → 4.8 移动没有新的破坏性变更 — 请参阅下面的迁移到 Opus 4.8。

---

## 已停用模型替代品

这些模型返回 404 — 立即更新：

| 已停用模型                    | 停用日期       | 直接替代品         |
| ----------------------------- | ------------- | ------------------ |
| `claude-3-7-sonnet-20250219`  | 2026年2月19日  | `claude-sonnet-4-6` |
| `claude-3-5-haiku-20241022`   | 2026年2月19日  | `claude-haiku-4-5`  |
| `claude-3-opus-20240229`      | 2026年1月5日   | `claude-opus-4-8`   |
| `claude-3-5-sonnet-20241022`  | 2025年10月28日 | `claude-sonnet-4-6` |
| `claude-3-5-sonnet-20240620`  | 2025年10月28日 | `claude-sonnet-4-6` |
| `claude-3-sonnet-20240229`    | 2025年7月21日  | `claude-sonnet-4-6` |
| `claude-2.1`、`claude-2.0`    | 2025年7月21日  | `claude-sonnet-4-6` |

## 已弃用模型（即将停用）

| 模型                          | 停用日期       | 替代品             |
| ----------------------------- | ------------- | ------------------ |
| `claude-3-haiku-20240307`     | 2026年4月19日  | `claude-haiku-4-5`  |
| `claude-opus-4-20250514`      | 2026年6月15日  | `claude-opus-4-8`   |
| `claude-sonnet-4-20250514`    | 2026年6月15日  | `claude-sonnet-4-6` |

---

## 按源模型列出的破坏性变更

### 从 Sonnet 4.5 迁移到 Sonnet 4.6（effort 默认值变更）

Sonnet 4.5 没有 `effort` 参数；Sonnet 4.6 默认为 `high`。如果您只是切换模型字符串而不做其他任何事情，您可能会看到明显更高的延迟和令牌使用量。请显式设置 `effort`。

**推荐起点：**

| 工作负载                                          | 起始值       | 备注                                                                                                    |
| ------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------- |
| 聊天、分类、内容生成                              | `low`        | 配合 `thinking: {"type": "disabled"}`，您将看到与 Sonnet 4.5 无思考相比类似或更好的性能                  |
| 大多数应用程序（平衡）                            | `medium`     | 质量与成本的最佳平衡点                                                                                  |
| 智能体编码、工具密集型工作流                      | `medium`     | 配合自适应思考和慷慨的 `max_tokens`（流式传输时最多 64K — Sonnet 4.6 的上限）                              |
| 自主多步骤智能体、长周期循环                      | `high`       | 如果延迟/令牌成为问题，请缩减到 `medium`                                                                 |
| 计算机使用智能体                                  | `high` + 自适应 | Sonnet 4.6 最佳的计算机使用准确度是在自适应 + high 时                                                |

特别是对于非思考聊天工作负载：

```python
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8192,
    thinking={"type": "disabled"},
    output_config={"effort": "low"},
    messages=[{"role": "user", "content": "..."}],
)
```

**何时改用 Opus 4.6：** 最困难和最长周期的问题 — 大型代码重构、深度研究、扩展自主工作。Sonnet 4.6 在快速周转和成本效率方面胜出。

### 迁移到 Opus 4.6 / Sonnet 4.6（从任何旧模型）

**1. 手动扩展思考已弃用 — 使用自适应思考。**

`thinking: {type: "enabled", "budget_tokens: N}`（具有固定令牌预算的手动扩展思考）在 Opus 4.6 和 Sonnet 4.6 上已弃用。将其替换为 `thinking: {type: "adaptive"}`，让 Claude 决定何时思考以及思考多少。自适应思考还会自动启用交错思考（不需要 beta 头）。

```python
# 旧（在旧模型上仍有效，在 4.6 上已弃用）
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 8000},
    messages=[...]
)

# 新（Opus 4.6 / Sonnet 4.6）
response = client.messages.create(
    model="claude-opus-4-6",  # 或 "claude-sonnet-4-6"
    max_tokens=16000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},  # 可选：low | medium | high | max
    messages=[...]
)
```

自适应思考是长期目标，并且在内部评估中它优于手动扩展思考。能迁移时就迁移。

**过渡性逃生舱：** 手动扩展思考在 Opus 4.6 和 Sonnet 4.6 上仍然**可用**（已弃用，将在未来版本中移除）。如果您在迁移时需要硬上限 — 例如，在调优 `effort` 之前限制失控工作负载的令牌消耗 — 您可以保留 `budget_tokens` 以及显式的 `effort` 值，然后在后续步骤中移除它。`budget_tokens` 必须严格小于 `max_tokens`：

```python
# 仅过渡 — 已弃用，计划移除
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 8192},  # 必须 < max_tokens
    output_config={"effort": "medium"},
    messages=[...],
)
```

如果用户在 4.6 上要求"思考预算"，首选答案是 `effort` — 使用 `low`、`medium`、`high` 或 `max`（仅 Opus 层级 — 不是 Sonnet 或 Haiku），而不是令牌计数。

**2. Effort 参数（仅限 Opus 4.5、Opus 4.6、Sonnet 4.6）。**

控制思考深度和整体令牌消耗。位于 `output_config` 内，不是顶级。默认值为 `high`。`max` 仅适用于 Opus 层级（Opus 4.6 及更高版本 — 不是 Sonnet 或 Haiku）。在 Sonnet 4.5 和 Haiku 4.5 上会出错。

```python
output_config={"effort": "medium"}  # 通常是最佳的成本 / 质量平衡
```

### 迁移到 4.6 系列（Opus 4.6 和 Sonnet 4.6）

**3. 助手轮次预填充返回 400（Opus 4.6 和 Sonnet 4.6）。**

在最后一个助手轮次上的预填充响应在 Opus 4.6 和 Sonnet 4.6 上都不再受支持 — 两者都返回 400。在对话的**其他地方**添加助手消息（例如，用于少量示例）仍然有效。选择与预填充用途匹配的替代品：

| 预填充用于                               | 替代品                                                                                                                               |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 强制 JSON / YAML / schema 输出           | 带有 `json_schema` 的 `output_config.format` — 请参阅下面的示例                                                                       |
| 强制分类标签                             | 包含有效标签的枚举字段的工具，或结构化输出                                                                                            |
| 跳过前言（`Here is the summary:\n`）      | 系统提示指令：*"直接回应，不要前言。不要以'这是...'或'基于...'等短语开头。"*                                                          |
| 绕过糟糕的拒绝                           | 通常不再需要 — 4.6 的拒绝更恰当。普通用户轮次提示就足够了。                                                                           |
| 继续中断的响应                           | 移动到用户轮次：*"您之前的响应被中断并以 `[最后文本]` 结束。从那里继续。"*                                                           |
| 注入提醒 / 上下文水化                     | 改为注入到用户轮次。对于复杂的智能体 harness，通过工具调用或在压缩期间暴露上下文。                                                    |

```python
# 旧（在 Opus 4.6 / Sonnet 4.6 上失败）— 预填充强制 JSON 形状
messages=[
    {"role": "user", "content": "Extract the name."},
    {"role": "assistant", "content": "{\"name\": \""},
]

# 新 — 结构化输出替换预填充
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    output_config={"format": {"type": "json_schema", "schema": {...}}},
    messages=[{"role": "user", "content": "Extract the name."}],
)
```

**4. `max_tokens > ~16K` 时流式传输（所有模型）；仅 Opus 4.6 达到 128K。**

无论模型如何，非流式请求在高 `max_tokens` 时都会遇到 SDK HTTP 超时 — 超过 ~16K 输出的任何内容都要流式传输。可流式传输的上限因模型而异：Sonnet 4.6 和 Haiku 4.5 上限为 64K，仅 Opus 4.6 达到 128K。

```python
with client.messages.stream(model="claude-opus-4-6", max_tokens=64000, ...) as stream:
    message = stream.get_final_message()
```

**5. 工具调用 JSON 转义可能不同（Opus 4.6 和 Sonnet 4.6）。**

两个 4.6 模型都可以生成带有 Unicode 或斜杠转义的工具调用 `input` 字段。始终使用 `json.loads()` / `JSON.parse()` 解析 — 永远不要对序列化的输入进行原始字符串匹配。

### 所有模型

**6. `output_format` → `output_config.format`（全 API）。**

`messages.create()` 上旧的顶级 `output_format` 参数已弃用。请改用 `output_config.format`。这不是 4.6 特有的 — 适用于每个模型。

---

## 在 4.6 上要移除的 Beta 头

在 4.5 上需要的几个 beta 头现在在 4.6 上已正式发布，应该移除。保留它们是无害的但会误导；移除它们还可以让您从 `client.beta.messages.create(...)` 移回 `client.messages.create(...)`。

| 头                                        | 在 4.6 上的状态                                              | 操作                                                  |
| ----------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------- |
| `effort-2025-11-24`                       | Effort 参数已正式发布                                       | 移除                                                  |
| `fine-grained-tool-streaming-2025-05-14`  | 已正式发布                                                 | 移除                                                  |
| `interleaved-thinking-2025-05-14`         | 自适应思考自动启用交错思考                                  | 使用自适应思考时移除；在 Sonnet 4.6 上与手动扩展思考一起使用时仍然有效，但该路径已弃用 |
| `token-efficient-tools-2025-02-19`        | 内置于所有 Claude 4+ 模型                                   | 移除（无效果）                                        |
| `output-128k-2025-02-19`                  | 内置于 Claude 4+ 模型                                       | 移除（无效果）                                        |

一旦您移除所有这些并完成向自适应思考的迁移，您就可以将 SDK 调用点从 beta 命名空间切换回常规命名空间：

```python
# 之前
response = client.beta.messages.create(
    model="claude-opus-4-5",
    betas=["interleaved-thinking-2025-05-14", "effort-2025-11-24"],
    ...
)

# 之后
response = client.messages.create(
    model="claude-opus-4-6",
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},
    ...
)
```

---

## 从 3.x / 4.0 / 4.1 → 4.6 迁移时的额外变更

如果您从 Opus 4.1、Sonnet 4、Sonnet 3.7 或较旧的 Claude 3.x 模型直接跳到 4.6，请应用上面的所有内容 **加上** 本节中的项目。已经在 Opus 4.5 / Sonnet 4.5 上的用户可以跳过此。

**1. 采样参数：`temperature` 或 `top_p`，不是两者都有。**

传递两者会在每个 Claude 4+ 模型上出错：

```python
# 旧（仅 3.x — 在 4+ 上出错）
client.messages.create(temperature=0.7, top_p=0.9, ...)

# 新
client.messages.create(temperature=0.7, ...)  # 或 top_p，不是两者都有
```

**2. 更新工具版本。**

传统工具版本在 4+ 上不受支持。**`type` 和 `name` 字段都改变了** — `text_editor_20250728` 和 `str_replace_based_edit_tool` 是一对；只更新一个而不更新另一个会返回 400。还要从文本编辑器集成中移除 `undo_edit` 命令：

| 旧                                                | 新                                                     |
| ------------------------------------------------- | ------------------------------------------------------- |
| `text_editor_20250124` + `str_replace_editor`     | `text_editor_20250728` + `str_replace_based_edit_tool`  |
| `code_execution_*`（早期版本）                    | `code_execution_20250825`                               |
| `undo_edit` 命令                                  | *（不再支持 — 删除调用点）*                             |

```python
# 之前
tools = [{"type": "text_editor_20250124", "name": "str_replace_editor"}]

# 之后 — 两个字段都改变了
tools = [{"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}]
```

**3. 处理 `refusal` 停止原因。**

Claude 4+ 可以在响应上返回 `stop_reason: "refusal"`。如果您的代码只处理 `end_turn` / `tool_use` / `max_tokens`，请添加分支：

```python
if response.stop_reason == "refusal":
    # 向用户显示拒绝；不要用相同的提示重试
    ...
```

**4. 处理 `model_context_window_exceeded` 停止原因（4.5+）。**

与 `max_tokens` 不同：它意味着模型达到了*上下文窗口*限制，而不是请求的输出上限。同时处理两者：

```python
if response.stop_reason == "model_context_window_exceeded":
    # 上下文窗口已耗尽 — 压缩或拆分对话
    ...
elif response.stop_reason == "max_tokens":
    # 达到请求的输出上限 — 用更高的 max_tokens 重试或流式传输
    ...
```

**5. 工具调用字符串参数中保留的尾随换行符（4.5+）。**

4.5 和 4.6 保留了旧模型剥离的尾随换行符。如果您的工具实现对工具调用 `input` 值进行精确字符串匹配（例如 `if name == "foo"`），请验证当模型发送 `"foo\n"` 时它们仍然匹配。在接收端用 `.rstrip()` 规范化通常是最简单的修复。

**6. Haiku：代际之间重置速率限制。**

Haiku 4.5 有自己的速率限制池，与 Haiku 3 / 3.5 分开。如果您在迁移时增加流量，请在 [API 速率限制](https://platform.claude.com/docs/en/api/rate-limits) 检查您层级的 Haiku 4.5 限制 — 舒适地服务 Haiku 3.5 流量的配额在 4.5 上对于相同体积可能需要层级提升。

---

## 提示行为变更（Opus 4.5 / 4.6，Sonnet 4.6）

这些不会破坏您的代码，但在 4.5 及更早版本上有效的提示在 4.6 上可能会过度触发或触发不足。根据需要调优。

**1. 激进的指令导致过度触发。** Opus 4.5 和 4.6 比早期模型更紧密地遵循系统提示。为克服旧模型的不情愿而写的提示现在过于激进：

| 之前（在 4.0 / 4.5 上有效）                | 之后（在 4.6 上使用）                        |
| ------------------------------------------- | ------------------------------------------- |
| `CRITICAL: You MUST use this tool when...`  | `Use this tool when...`                     |
| `Default to using [tool]`                   | `Use [tool] when it would improve X`        |
| `If in doubt, use [tool]`                   | *（删除 — 不再需要）*                       |

如果模型现在过度触发工具或技能，修复几乎总是缓和语言，而不是添加更多护栏。

**2. 过度思考和过度探索（Opus 4.6）。** 在更高的 `effort` 设置下，Opus 4.6 在回答之前会探索更多。如果这燃烧了太多思考令牌，首先降低 `effort`（`medium` 通常是最佳点），然后再添加散文指令来约束推理。

**3. 过度渴望的子代理生成（Opus 4.6）。** Opus 4.6 有强烈的委托给子代理的偏好。如果您看到它为直接 `grep` 或 `read` 就能解决的事情生成子代理，请添加指导：*"仅对并行或独立的工作流使用子代理。对于单文件读取或顺序操作，直接工作。"*

**4. 过度工程（Opus 4.5 / 4.6）。** 两个模型都可能添加额外的文件、抽象或防御性错误处理，超出了要求的范围。如果您想要最小的变更，请明确提示：*"只做直接要求的变更。不要为不可能发生的场景添加助手、抽象或错误处理。"*

**5. LaTeX 数学输出（Opus 4.6）。** Opus 4.6 对于数学和技术内容默认为 LaTeX（`\frac{}{}`、`$...$`）。如果您需要纯文本，请明确指示：*"将所有数学格式化为纯文本 — 不要 LaTeX，不要 `$`，不要 `\frac{}{}`。使用 `/` 表示除法，使用 `^` 表示指数。"*

**6. 跳过的口头摘要（4.6 系列）。** 4.6 模型更简洁，可能会在工具调用后跳过摘要段落，直接跳到下一个动作。如果您依赖这些摘要进行可见性，请添加：*"完成涉及工具使用的任务后，简要总结您所做的事情。"*

**7. "思考"作为触发词（禁用思考的 Opus 4.5）。** 当 `thinking` 关闭时，Opus 4.5 对"思考"这个词特别敏感，可能会比您想要的推理更多。改用"考虑"、"评估"或"通过推理"。

---

## 模型 ID 重命名快速参考

| 旧字符串（迁移源）           | 新字符串           |
| ---------------------------- | ------------------ |
| `claude-opus-4-7`            | `claude-opus-4-8`  |
| `claude-opus-4-6`            | `claude-opus-4-8`  |
| `claude-opus-4-5`            | `claude-opus-4-8`  |
| `claude-opus-4-1`            | `claude-opus-4-8`  |
| `claude-opus-4-0`            | `claude-opus-4-8`  |
| `claude-sonnet-4-5`          | `claude-sonnet-4-6`|
| `claude-sonnet-4-0`          | `claude-sonnet-4-6`|

较旧的别名（`claude-opus-4-7`、`claude-opus-4-6`、`claude-opus-4-5`、`claude-sonnet-4-5` 等）仍然有效，如果您在升级前需要时间可以固定 — 完整的旧列表请参阅 `shared/models.md`。

---

## 迁移检查清单

每个项目都有标记：**`[BLOCKS]`** 项目如果遗漏会导致 400 错误、无限循环、静默超时或错误的工具选择 — 将这些作为代码编辑应用，而不是建议。**`[TUNE]`** 项目是质量/成本调整。

对于每个调用 `messages.create()` / 等效 SDK 方法的文件：

- [ ] **[BLOCKS]** 将 `model=` 字符串更新为新别名
- [ ] **[BLOCKS]** 用 `thinking={"type": "adaptive"}` 替换 `budget_tokens`（在 Opus 4.6 / Sonnet 4.6 上已弃用）
- [ ] **[BLOCKS]** 将 `format` 从顶级 `output_format` 移到 `output_config.format`
- [ ] **[BLOCKS]** 如果目标是 Opus 4.6 或 Sonnet 4.6，移除任何助手轮次预填充（请参阅预填充替换表）
- [ ] **[BLOCKS]** 如果 `max_tokens > ~16000` 切换到流式传输（否则 SDK HTTP 超时）
- [ ] **[TUNE]** 显式设置 `output_config={"effort": "..."}` — 特别是从 Sonnet 4.5 → Sonnet 4.6 移动时（4.6 默认为 `high`）
- [ ] **[TUNE]** 移除已正式发布的 beta 头：`effort-2025-11-24`、`fine-grained-tool-streaming-2025-05-14`、`token-efficient-tools-2025-02-19`、`output-128k-2025-02-19`；一旦使用自适应思考，移除 `interleaved-thinking-2025-05-14`
- [ ] **[TUNE]** 一旦移除所有 betas，将 `client.beta.messages.create(...)` 切换为 `client.messages.create(...)`
- [ ] **[TUNE]** 审查系统提示中激进的工具语言（`CRITICAL:`、`MUST`、`If in doubt`）并调回

**从 3.x / 4.0 / 4.1 迁移时的额外项目：**
- [ ] **[BLOCKS]** 移除 `temperature` 或 `top_p`（在 Claude 4+ 上传递两者会返回 400）
- [ ] **[BLOCKS]** 将文本编辑器工具 `type` 更新为 `text_editor_20250728`
- [ ] **[BLOCKS]** 将文本编辑器工具 `name` 更新为 `str_replace_based_edit_tool` — **只更改 `type` 而保持 `name: "str_replace_editor"` 会返回 400**
- [ ] **[BLOCKS]** 将代码执行工具更新为 `code_execution_20250825`
- [ ] **[BLOCKS]** 删除任何 `undo_edit` 命令调用点
- [ ] **[TUNE]** 添加对 `stop_reason == "refusal"` 的处理
- [ ] **[TUNE]** 添加对 `stop_reason == "model_context_window_exceeded"`（4.5+）的处理
- [ ] **[TUNE]** 验证工具参数字符串匹配容忍尾随换行符（在 4.5+ 上保留）
- [ ] **[TUNE]** 如果迁移到 Haiku 4.5：检查速率限制层级（与 Haiku 3.x 分开的池）

**验证：**
- [ ] 运行一个测试请求并检查 `response.stop_reason`、`response.usage`，以及工具使用/思考行为是否符合预期

对于缓存的提示：渲染顺序和哈希输入没有改变，因此现有的 `cache_control` 断点继续工作。但是，**更改模型字符串会使现有缓存无效** — 在新模型上的第一个请求将新鲜写入缓存。

---

## 迁移到 Opus 4.7

> **模型 ID `claude-opus-4-7` 如此处所写是权威的。** 当用户要求迁移到 Opus 4.7 时，准确写入 `model="claude-opus-4-7"`。**不要** WebFetch 验证 — 本指南是迁移目标 ID 的真实来源。相应条目存在于 `shared/models.md` 中。

Claude Opus 4.7 是发布时我们最强大的模型，现在是上一代 Opus（Opus 4.8 是当前版本 — 请参阅下面的迁移到 Opus 4.8）。它高度自主，在长周期智能体工作、知识工作、视觉任务和记忆任务方面表现出色。本节总结了 4.7 发布时的所有新内容，并且仍然是从 Opus 4.6 或更早版本迁移的呼叫者的分层破坏性变更路径。它层叠在上面的 4.6 迁移之上 — 如果呼叫者从 Opus 4.5 或更早版本跳跃，请先应用 4.6 变更，然后是本节，然后是 4.8 节。

**对于已经在 Opus 4.6 上的人的要点：** 将模型 ID 更新为 `claude-opus-4-7`，去掉任何剩余的 `budget_tokens` 和采样参数（两者在 Opus 4.7 上都返回 400），给 `max_tokens` 额外的余量并用 `count_tokens()` 针对新模型重新基线，如果推理向用户显示，则选择回到 `thinking.display: "summarized"`，并重新调优 `effort` — 它在 4.7 上比任何之前的 Opus 都更重要。

### 破坏性变更（在 Opus 4.7 上会返回 400）

**扩展思考已移除。**

`thinking: {type: "enabled", "budget_tokens: N}` 在 Claude Opus 4.7 或更高版本的模型上不再支持，并返回 400 错误。切换到自适应思考（`thinking: {type: "adaptive"}`）并使用 effort 参数控制思考深度。自适应思考在 Claude Opus 4.7 上**默认关闭**：没有 `thinking` 字段的请求在没有思考的情况下运行，与 Opus 4.6 行为匹配。显式设置 `thinking: {type: "adaptive"}` 以启用它。

```python
# 之前（Opus 4.6）
client.messages.create(
    model="claude-opus-4-6",
    max_tokens=64000,
    thinking={"type": "enabled", "budget_tokens": 32000},
    messages=[{"role": "user", "content": "..."}],
)

# 之后（Opus 4.7）
client.messages.create(
    model="claude-opus-4-7",
    max_tokens=64000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},  # 或 "max"、"xhigh"、"medium"、"low"
    messages=[{"role": "user", "content": "..."}],
)
```

如果呼叫者没有使用扩展思考，则不需要更改 — 思考默认关闭，或者可以用 `thinking={"type": "disabled"}` 显式设置。

完全删除 `budget_tokens` 管道。对于替换的 `effort` 值，请参阅下面的**在 Opus 4.7 上选择 effort 级别** — 没有从 `budget_tokens` 的确切 1:1 映射。

**采样参数已移除。**

`temperature`、`top_p` 和 `top_k` 参数在 Claude Opus 4.7 上不再接受。包含它们的请求返回 400 错误。从您的请求负载中移除这些字段。提示是指导 Claude Opus 4.7 模型行为的推荐方式。如果您之前使用 `temperature = 0` 来追求确定性，请注意它在之前的模型上从未保证相同的输出。

```python
# 之前 — 在 Opus 4.7 上出错
client.messages.create(temperature=0.7, top_p=0.9, ...)

# 之后
client.messages.create(...)  # 没有采样参数
```

- **如果意图是确定性** — 使用 `effort: "low"` 配合更严格的提示。
- **如果意图是创意思维** — 提示替换取决于用例；**询问用户**他们希望如何引出方差。如果您不能问，添加一个适用于用例的指令，例如 *"选择一些偏离分布且有趣的东西"* — 例如对于文本生成，*"在响应中改变你的措辞和结构"*；对于前端/设计，使用下面**设计和前端编码**下的提议 4 方向方法。

### 在 Opus 4.7 上选择 effort 级别

`budget_tokens` 控制*思考多少*；`effort` 控制思考多少*和行动*，因此没有确切的 1:1 映射。**对于编码和智能体用例，使用 `xhigh` 获得最佳结果，对于大多数智能敏感的用例，至少使用 `high`。** 实验其他级别以进一步调优令牌使用和智能：

| 级别 | 用于何时 | 备注 |
| --- | --- | --- |
| `max` | 值得在天花板测试的智能要求高的任务 | 可以在某些用例中提供增益，但可能会因增加的令牌使用而显示收益递减；可能容易过度思考 |
| `xhigh` | **大多数编码和智能体用例** | 这些的最佳设置；在 Claude Code 中用作默认值 |
| `high` | 一般智能敏感用例 | 平衡令牌使用和智能；推荐为大多数智能敏感工作的最小值 |
| `medium` | 需要减少令牌使用同时权衡智能的成本敏感用例 | |
| `low` | 简短、范围明确的任务和对延迟不敏感的非智能敏感工作负载 | |

### 静默默认值变更（无错误，但行为不同）

**思考内容默认省略。**

思考块仍然出现在 Claude Opus 4.7 的响应流中，但它们的 `thinking` 字段是空的，除非您显式选择加入。这与 Claude Opus 4.6 的静默变更，4.6 的默认值是返回摘要思考文本。要在 Claude Opus 4.7 上恢复摘要思考内容，请将 `thinking.display` 设置为 `"summarized"`。**块字段名称不变** — 在 `thinking` 类型块上它仍然是 `block.thinking`；不要重命名它。

**检测这个：** 任何从 `thinking` 类型块读取 `block.thinking`（或等效）并在 UI、日志或跟踪中渲染它的代码。**修复是请求参数，不是响应处理** — 向 `thinking` 参数添加 `display: "summarized"`：

```python
thinking={"type": "adaptive", "display": "summarized"}  # "display" 是 Opus 4.7 上的新功能；值："omitted"（默认）| "summarized"
```

Claude Opus 4.7 上的默认值是 `"omitted"`。如果思考内容从未在任何地方显示，则无需更改。如果您的产品向用户流式传输推理，新默认值会在输出开始之前显示为长时间暂停；设置 `display: "summarized"` 以恢复思考期间的可见进度。

**更新的令牌计数。**

Claude Opus 4.7 和 Claude Opus 4.6 对令牌的计数不同。相同的输入文本在 Claude Opus 4.7 上产生比在 Claude Opus 4.6 上更高的令牌计数，并且 `/v1/messages/count_tokens` 在 Claude Opus 4.7 上返回的令牌数量与在 Claude Opus 4.6 上不同。Claude Opus 4.7 的令牌效率可能因工作负载形状而异。提示干预、`task_budget` 和 `effort` 可以帮助控制成本并确保适当的令牌使用。请记住，这些控制可能会权衡模型智能。**更新您的 `max_tokens` 参数以给予额外余量，包括压缩触发器。** Claude Opus 4.7 在标准 API 定价下提供 1M 上下文窗口，没有长上下文溢价。

还要检查什么：

- 针对 4.6 校准的客户端令牌估计器（tiktoken 风格的近似值）
- 将令牌乘以固定每令牌速率的成本计算器
- 键入测量的令牌计数的速率限制重试阈值

通过在呼叫者提示的代表性样本上针对 `claude-opus-4-7` 重新运行 `client.messages.count_tokens()` 来重新建立基线。不要应用 blanket 乘数。对于成本敏感的工作负载，考虑将 `effort` 降低一级（例如 `high` → `medium`）。对于智能体循环，考虑采用任务预算（见下文）。

### 新功能：任务预算（测试版）

Opus 4.7 引入了**任务预算** — 告诉 Claude 完整智能体循环有多少令牌（思考 + 工具调用 + 最终输出）。模型看到一个运行倒计时，并使用它来确定工作优先级并在预算耗尽时优雅地结束。

这是**模型知道的建议**，不是硬上限。它与 `max_tokens` 不同，后者仍然是强制执行的每响应限制，并且**不**向模型暴露。当您希望模型自我调节时使用 `task_budget`；当您想要硬上限以限制使用时使用 `max_tokens`。

需要 beta 头 `task-budgets-2026-03-13`：

```python
client.beta.messages.create(
    betas=["task-budgets-2026-03-13"],
    model="claude-opus-4-7",
    max_tokens=64000,
    thinking={"type": "adaptive"},
    output_config={
        "effort": "high",
        "task_budget": {"type": "tokens", "total": 128000},
    },
    messages=[...],
)
```

为开放式智能体任务设置慷慨的预算，为延迟敏感的任务收紧预算。**最小 `task_budget.total` 是 20,000 个令牌。** 如果预算对于任务来说过于严格，模型可能不那么彻底地完成它，将预算作为约束引用。**不要在迁移期间添加 `task_budget`，除非您确定预算值是正确的** — 如果您可以运行工作负载并测量，就这样做；否则询问用户该值而不是猜测。这是抵消智能体工作负载上令牌计数偏移的主要杠杆。

### 能力改进

**高分辨率视觉。** Opus 4.7 是第一个支持高分辨率图像的 Claude 模型。最大图像分辨率为**长边 2576 像素**（高于 Opus 4.6 及之前的 1568px）。这在视觉密集型工作负载上解锁了增益，特别是计算机使用和屏幕截图/工件/文档理解。模型返回的坐标现在 1:1 映射到实际图像像素，因此不需要比例因子数学。

高分辨率支持在 Opus 4.7 上**自动** — 不需要 beta 头，不需要客户端选择加入。模型接受更大的输入并开箱即用地返回像素精确的坐标。

**令牌成本。** Opus 4.7 上的全分辨率图像可以使用比先前模型多约 3 倍的图像令牌（每个图像高达约 4784 个令牌，而之前的上限约为 1,600 个令牌）。如果不需要额外的保真度，请在发送前在客户端进行下采样以控制成本 — 但**不要在迁移期间默认添加下采样**。如果您不确定管道是否需要保真度，请询问用户而不是猜测。在 Opus 4.7 上对代表性图像使用 `count_tokens()` 以在对任何测量的成本偏移做出反应之前重新建立基线。

除了分辨率之外，Opus 4.7 还改进了低级感知（指向、测量、计数）和自然图像边界框定位和检测。

**知识工作。** 在模型视觉验证自己输出的任务上有意义的增益 — `.docx` 红lining、`.pptx` 编辑和程序化图表/图形分析（例如通过图像处理库进行像素级数据转录）。如果提示有像 *"返回前仔细检查幻灯片布局"* 这样的脚手架，请尝试移除它并重新建立基线。

**记忆。** Opus 4.7 更擅长写入和使用基于文件系统的记忆。如果智能体在轮次之间维护草稿板、笔记文件或结构化记忆存储，该智能体应该更擅长向自己写下笔记并在未来的任务中利用其笔记。

**面向用户的进度更新。** Opus 4.7 在长智能体追踪期间提供更规律、更高质量的临时更新。如果系统提示有像 *"每 3 次工具调用后总结进度"* 这样的脚手架，请尝试移除它以避免过多的面向用户的文本。如果 Opus 4.7 更新的长度或内容没有很好地校准到您的用例，请在提示中明确描述这些更新应该是什么样子并提供示例。

### 实时网络安全保障

涉及禁止或高风险主题的请求可能导致拒绝。

### 快速模式：在 Opus 4.7 上不可用

Opus 4.7 没有快速模式变体。**Opus 4.6 快速模式仍然支持。** 只有在呼叫者的代码实际使用快速模式模型字符串（例如 `claude-opus-4-6-fast`）时才提出这个；如果"快速"一词没有出现在代码中，就不要说快速模式。

当您看到 `model="claude-opus-4-6-fast"`（或类似）时，**迁移编辑是**：

```python
# Opus 4.7 没有快速模式 — 保持在 4.6 快速模式（呼叫者选择切换到标准 Opus 4.7）。
model="claude-opus-4-6-fast",
```

也就是说：保持模型字符串**不变**，在其上方添加注释，并告诉用户他们的两个选择 — （a）留在 Opus 4.6 快速模式，仍然支持，或（b）将延迟容忍的流量移动到标准 Opus 4.7 以获得智能增益。**不要**自己将模型字符串重写为 `claude-opus-4-7`；那会静默地用智能交换延迟，这是呼叫者的决定。

### 行为转变（提示可调）

这些不会破坏任何东西，但为 Opus 4.6 调优的提示可能会有不同的落地效果。Opus 4.7 比 4.6 更可引导，因此小的提示微调通常会缩小差距。

**更字面的指令遵循。** Claude Opus 4.7 比 Claude Opus 4.6 更字面、更明确地解释提示，特别是在较低的 effort 级别。它不会静默地将指令从一个项目概括到另一个项目，也不会推断您没有提出的请求。这种字面主义的好处是精度和更少的折腾。对于带有仔细调优提示的 API 用例、结构化提取以及您想要可预测行为的管道，它通常表现更好。提示和 harness 审查对于迁移到 Claude Opus 4.7 可能特别有帮助。

**根据任务复杂性校准冗长。** Opus 4.7 根据它判断任务的复杂程度来缩放响应长度，而不是默认为固定的冗长 — 简单查找的答案更短，开放式分析的答案更长。如果产品依赖于特定的长度或风格，请明确调优提示。为了减少冗长：

> *"提供简洁、集中的响应。跳过非必要的上下文，保持示例最小化。"*

如果您看到特定类型的过度冗长（例如过度解释），添加针对这些的指令。显示所需简洁程度的正面示例往往比负面示例或告诉模型不要做什么的指令更有效。**不要**假设应该删除现有的"要简洁"指令 — 先测试。

**语气和写作风格。** Opus 4.7 更直接、更有主见，与 Opus 4.6 更温暖的风格相比，验证型措辞更少，表情符号更少。与任何新模型一样，长篇写作的散文风格可能会发生变化。如果产品依赖于特定的声音，请对照新基线重新评估风格提示。如果需要更温暖或更具对话性的语气，请指定：

> *"使用温暖、协作的语气。在回答之前承认用户的框架。"*

**`effort` 比任何之前的 Opus 都更重要。** Opus 4.7 更严格地尊重 `effort` 级别，特别是在低端。在 `low` 和 `medium` 时，它将工作范围限制在要求的范围内，而不是超越 — 这对延迟和成本有好处，但在 `low` 时的适度任务上存在思考不足的一些风险。

- 如果复杂问题上出现浅推理，将 `effort` 提高到 `high` 或 `xhigh`，而不是在提示周围处理。
- 如果 `effort` 必须保持 `low` 以延迟，请添加有针对性的指导：*"这个任务涉及多步骤推理。在响应之前仔细考虑问题。"*
- **在 `xhigh` 或 `max` 时，设置大的 `max_tokens`** 以便模型有空间在工具调用和子代理之间思考和行动。从 64K 开始并从那里调优。（`xhigh` 是 Opus 4.7 上的新 effort 级别，介于 `high` 和 `max` 之间。）

自适应思考触发也是可引导的。如果模型比想要的更经常思考 — 这可能发生在大型或复杂的系统提示上 — 添加：*"思考会增加延迟，应该只在它会有意义地提高回答质量时使用 — 通常用于需要多步骤推理的问题。如有疑问，直接回应。"*

**默认情况下更少使用工具。** Opus 4.7 倾向于比 4.6 更少使用工具，更多使用推理。这在大多数情况下会产生更好的结果，但对于依赖工具（搜索/检索、函数调用、计算机使用步骤）的产品，它可能会降低工具使用率。两个杠杆：

- **提高 `effort`** — `high` 或 `xhigh` 在智能体搜索和编码中显示出明显更多的工具使用，对于知识工作特别有用。
- **提示它** — 在工具描述或系统提示中明确说明何时以及如何使用该工具，并鼓励模型倾向于更频繁地使用它：

> *"当答案取决于对话中不存在的信息时，您**必须**在回答之前调用 `search` 工具 — 不要从先前的知识回答。"*

**默认情况下更少的子代理。** Opus 4.7 倾向于比 4.6 生成更少的子代理。这是可引导的 — 明确指导何时委托是可取的。例如，对于编码智能体：

> *"不要**为您可以在单个响应中直接完成的工作生成子代理（例如重构您已经可以看到的函数）。当跨项目扇出或读取多个文件时，在同一轮中生成多个子代理。"*

**设计和前端编码。** Opus 4.7 比 4.6 有更强的设计本能，具有一致的默认房屋风格：温暖的奶油/灰白色背景（约 `#F4F1EA`）、衬线显示字体（Georgia、Fraunces、Playfair）、斜体字重音和陶土/琥珀色重音。这对于社论、酒店和产品简介简档来说读起来很好，但对于仪表板、开发工具、金融科技、医疗保健或企业应用程序来说会感觉不对劲 — 它会出现在幻灯片和 Web UI 中。

默认值是持久的。通用指令（"不要使用奶油"、"让它干净最小"）倾向于将模型移动到不同的固定调色板，而不是产生多样性。两种方法可靠地工作：

1. **指定具体的替代方案。** 模型精确地遵循明确的规格 — 给出精确的十六进制值、字体和布局约束。
2. **让模型在构建之前提出选项。** 这打破了默认并给用户控制权：

   > *"在构建之前，针对此简介提出 4 个不同的视觉方向（每个为：bg 十六进制 / 重音十六进制 / 字体 — 单行理由）。询问用户选择一个，然后只实现该方向。"*

如果呼叫者之前依赖 `temperature` 来获得设计多样性，请使用方法（2）— 它在运行中产生有意义的不同方向。

Opus 4.7 与之前的模型相比，生成避免通用"AI 垃圾"美学所需的前端设计提示也更少。早期模型需要冗长的反垃圾片段，而 Opus 4.7 用短得多的推动就能生成独特、有创意的前端。此片段与上述多样性方法配合良好：

> *"永远不要使用通用的 AI 生成美学，如过度使用的字体系列（Inter、Roboto、Arial、系统字体）、陈词滥调的配色方案（特别是白色或深色背景上的紫色渐变）、可预测的布局和组件模式，以及缺乏上下文特定特征的千篇一律的设计。使用独特的字体、有凝聚力的颜色和主题，以及用于效果和微交互的动画。"*

**交互式编码产品。** Opus 4.7 的令牌使用和行为在具有单个用户轮次的自主、异步编码智能体与具有多个用户轮次的交互式、同步编码智能体之间可能不同。具体来说，它倾向于在交互式设置中使用更多令牌，主要是因为它在用户轮次后推理更多。这可以在长时间的交互式编码会话中提高长周期连贯性、指令遵循和编码能力，但也伴随着更多的令牌使用。为了在编码产品中最大化性能和令牌效率，请使用 `effort: "xhigh"` 或 `"high"`，添加自主功能（如自动模式），并减少用户所需的交互次数。

在限制所需的用户交互时，在第一个人类轮次中预先指定任务、意图和相关约束。预先明确、准确的任务描述有助于最大化自主性和智能性，同时最小化用户轮次后的额外令牌使用 — 因为 Opus 4.7 比之前的模型更自主，这种使用模式有助于最大化性能。相反，在多个用户轮次中逐渐传达的模棱两可或不明确的提示往往会降低令牌效率，有时会降低性能。

**代码审查。** Opus 4.7 在发现 bug 方面比之前的模型有意义地更好，召回率和精度都更高。但是，如果代码审查 harness 是为早期模型调优的，它最初可能显示*更低的*召回率 — 这很可能是 harness 效应，而不是能力回归。当审查提示说"只报告高严重性问题"、"保守"或"不要吹毛求疵"时，Opus 4.7 比早期模型更忠实地遵循该指令：它调查得同样彻底，识别出 bug，然后拒绝报告它判断低于所述栏的发现。精度上升，但测量的召回率可能下降，即使底层的 bug 发现已经改善。

推荐的提示语言：

> *"报告您发现的每一个问题，包括您不确定的或认为低严重性的。在此阶段不要过滤重要性或置信度 — 单独的验证步骤会这样做。您这里的目标是覆盖：出现后来被过滤掉的发现比静默丢弃 bug 更好。对于每个发现，包括您的置信度水平和估计的严重性，以便下游过滤器可以对它们进行排名。"*

这可以在没有实际第二步的情况下使用，但将置信度过滤移出发现步骤通常有帮助。如果 harness 有单独的验证/去重/排名阶段，明确告诉模型它在发现阶段的工作是覆盖，而不是过滤。如果需要单通自过滤，请具体说明栏而不是使用"重要"等定性术语 — 例如 *"报告任何可能导致不正确行为、测试失败或误导性结果的 bug；只省略纯粹风格或命名偏好之类的小问题。"* 对评估子集迭代提示以验证召回或 F1 增益。

**计算机使用。** 计算机使用适用于高达新的 2576px / 3.75MP 最大值的分辨率。以 **1080p** 发送图像提供了性能和成本的良好平衡。对于特别成本敏感的工作负载，**720p** 或 **1366×768** 是具有强大性能的低成本选项。测试以找到用例的理想设置；试验 `effort` 也可以帮助调优行为。

---

## Opus 4.7 迁移检查清单

每个项目都有标记：**`[BLOCKS]`** 项目如果遗漏会导致 400 错误、无限循环、静默截断或空输出 — 将这些作为代码编辑应用，而不是建议。**`[TUNE]`** 项目是质量/成本调整 — 将它们作为建议呈现给用户。

以 **"如果..."** 或 **"在..."** 为前缀的 `[BLOCKS]` 项目是有条件的。在处理列表之前，**扫描文件** 查找条件：它是否向 UI/日志显示思考文本？它是否将 `output_config.effort` 设置为 `"x-high"` 或 `"max"`？它是安全工作负载吗？它是多轮智能体循环吗？只应用条件匹配的项目。

- [ ] **[BLOCKS]** 用 `thinking: {type: "adaptive"}` + `output_config.effort` 替换 `thinking: {type: "enabled", budget_tokens: N}`；完全删除 `budget_tokens` 管道
- [ ] **[BLOCKS]** 从请求构造中去掉 `temperature`、`top_p`、`top_k`
- [ ] **[BLOCKS]** 如果思考内容向用户显示或存储在日志中：添加 `thinking.display: "summarized"`（否则渲染的文本是空的）
- [ ] **[BLOCKS]** 在 `output_config.effort` 为 `xhigh` 或 `max` 时：设置 `max_tokens` ≥ 64000（否则输出在思考中期截断）
- [ ] **[TUNE]** 给 `max_tokens` 和压缩触发器额外余量；在代表性提示上针对 `claude-opus-4-7` 重新运行 `count_tokens()` 以重新建立基线（无 blanket 乘数）
- [ ] **[TUNE]** 在对测量的偏移做出反应之前**先**重新建立成本和速率限制仪表板的基线
- [ ] **[TUNE]** 按路线重新评估 `effort` — 对于编码/智能体使用 `xhigh`，对于大多数智能敏感工作至少使用 `high`；它在 4.7 上比任何之前的 Opus 都更重要
- [ ] **[TUNE]** 多轮智能体循环：采用 API 原生的任务预算（`output_config.task_budget`、beta `task-budgets-2026-03-13`、最小 20k 令牌）— 这是用于限制循环中*累积*支出的；每轮深度是 `effort`
- [ ] **[TUNE]** 检查依赖 4.6 概括意图的模棱两可或不明确的指令，并更新它们以更清晰或更精确 — 4.7 字面地遵循它们
- [ ] **[TUNE]** 工具使用工作负载：向工具描述添加明确的何时/如何使用指导（4.7 更少伸手去拿工具）
- [ ] **[TUNE]** 冗长：在更改之前测试现有的长度指令 — 4.7 根据任务复杂性校准长度，因此针对所需输出调优，而不是假设方向
- [ ] **[TUNE]** 移除强制进度更新脚手架（*"每 N 次工具调用后..."*）
- [ ] **[TUNE]** 移除知识工作验证脚手架（*"仔细检查幻灯片布局..."*）并重新建立基线
- [ ] **[TUNE]** 如果需要更温暖 / 更具对话性的声音，添加语气指令；在写作繁重的路线上重新评估风格提示
- [ ] **[TUNE]** 子代理工具存在：添加明确的生成 / 不生成指导
- [ ] **[TUNE]** 前端/设计输出：指定具体的调色板/字体，或让模型在构建之前提出 4 个视觉方向（默认的奶油/衬线房屋风格是持久的）
- [ ] **[TUNE]** 交互式编码产品：使用 `effort: "xhigh"` 或 `"high"`，添加自主功能（例如自动模式）以减少人类交互，并在第一轮中预先指定任务/意图/约束
- [ ] **[TUNE]** 代码审查 harness：移除或放松"只报告高严重性" / "保守"过滤器，让模型报告每个发现并带有置信度 + 严重性；将过滤移到下游步骤（4.7 更字面地遵循严重性过滤器，这可能会压低测量的召回率）
- [ ] **[TUNE]** 视觉密集型管道（屏幕截图、图表、文档理解）：将图像保持在原生分辨率，长边最多 2576px 以获得准确度增益；从坐标处理中移除任何比例因子数学（坐标现在与像素 1:1）。不需要 beta 头 / 选择加入 — 高分辨率在 Opus 4.7 上是自动的。
- [ ] **[TUNE]** 计算机使用管道：以 1080p 发送屏幕截图以获得良好的性能/成本平衡（对于成本敏感的工作负载为 720p 或 1366×768）；试验 `effort` 以调优行为
- [ ] **[TUNE]** 成本敏感的图像管道：4.7 上的全分辨率图像使用多达约 4784 个令牌，而之前模型上约为 1,600 个（约 3 倍）。上传前在客户端下采样避免了增加，但**不要默认下采样** — 如果您不确定是否需要保真度，请询问用户。在对成本偏移做出反应之前，在代表性图像上用 `count_tokens()` 重新建立基线。

---

## 迁移到 Opus 4.8

> **模型 ID `claude-opus-4-8` 如此处所写是权威的。** 当用户要求迁移到 Opus 4.8 时，准确写入 `model="claude-opus-4-8"`。**不要** WebFetch 验证 — 本指南是迁移目标 ID 的真实来源。相应条目存在于 `shared/models.md` 中。

Claude Opus 4.8 是我们迄今为止最强大的普遍可用模型 — 高度自主，具有最先进的长周期智能体执行、知识工作和记忆。它层叠在上面的 Opus 4.7 迁移之上。如果呼叫者从 Opus 4.6 或更早版本跳跃，请先应用 4.6 和 4.7 节，然后是这一节。

**无新的破坏性变更。** Opus 4.8 保持与 Opus 4.7 相同的请求表面。已经在 4.7 上工作的相同调用在 4.8 上不变地工作 — 仅自适应思考（`thinking: {type: "enabled", budget_tokens: N}` 仍然返回 400；使用 `{type: "adaptive"}`），采样参数（`temperature`、`top_p`、`top_k`）仍然被拒绝，最后助手轮次预填充仍然返回 400，`thinking.display` 仍然默认为 `"omitted"`，以及 `low`/`medium`/`high`/`xhigh`/`max` effort 级别、任务预算（测试版）和高分辨率视觉都表现得与 4.7 上一样。因此，4.7 → 4.8 迁移是**模型 ID 交换加上提示重新调优** — 除了模型字符串之外没有必需的代码编辑。

**对于已经在 Opus 4.7 上的人的要点：** 将模型 ID 交换为 `claude-opus-4-8`。没有其他任何东西需要避免错误。然后为行为转变重新调优提示：4.8 比 4.7 *叙述更多*（如果您想要 4.7 式的简洁，添加默认静默），用更温暖、更少对冲的声音写作，更慎重并更频繁地询问（添加自治指导以收回询问率），并且对于触及搜索、子代理、基于文件的记忆和自定义工具更保守（添加明确的"何时使用此"触发）。对于长周期智能体工作，在一个明确指定的轮次中预先给出完整的任务规格，并在高 effort 下运行。

### 没有新的 API 破坏性变更（继承自 4.7）

这些都不变地从 Opus 4.7 继承 — 只有当呼叫者来自 Opus 4.6 或更早版本时才应用它们（之前/之后和 SDK 特定语法请参阅**迁移到 Opus 4.7** 部分）：

- `thinking: {type: "enabled", budget_tokens: N}` → 400。使用 `thinking: {type: "adaptive"}` + `output_config.effort`。
- `temperature`、`top_p`、`top_k` → 400。移除它们；用提示引导。
- 最后助手轮次预填充 → 400。使用 `output_config.format`（结构化输出）或系统提示指令。
- `thinking.display` 默认为 `"omitted"`；如果您向用户显示推理，请设置 `"summarized"`。

如果呼叫者已经在 Opus 4.7 上并且这些都干净，这里没有什么要改变的。

### 新 API 功能：会话中系统提示

您可以通过将 `{"role": "system", ...}` 条目直接放在 `messages` 数组中来在会话中途传递受信任的指令 — 无需编辑顶级系统提示并使您的提示缓存无效。将其用于应用程序在会话中途学习的事物：用户交付了异步上下文、模式切换（启用自动批准）、磁盘上的文件更改、剩余令牌预算下降。

```python
messages=[
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]},
    {"role": "system", "content": "这个项目的代码库是 Go。用 Go 写代码。"},
]
```

将这些表述为**上下文，不是命令**。陈述事实并让 Claude 采取行动；避免覆盖式语言（"忽略用户说的话"、"不管用户的请求如何"、"无视之前的指令"）。Claude 被训练保护用户免受看起来对他们不利的指令，并且该保护也适用于系统角色。这是一个测试版（`anthropic-beta: mid-conversation-system-2026-04-07`），可从 Opus 4.7 开始使用，不是 4.8 独有的。有关缓存放置细节和旧模型的 `<system-reminder>` 回退，请参阅 `shared/prompt-caching.md` 和 `shared/agent-design.md`。

### 能力改进

**长周期智能体执行。** Opus 4.8 在长、自主智能体工作方面是最先进的 — 无需人类纠正即可完成复杂重构和通宵编码运行。为了充分利用它，**在单个明确指定的初始轮次中预先给出完整任务规格并在高 effort 下运行**（`effort: "high"` 或 `"xhigh"`）。它的长周期连贯性部分来自每一步更多的推理；结合清晰的前期目标，这种更智能的规划通常比之前的前沿模型产生更高效*和*更准确的输出。"明确目标前期"原则映射到两个产品表面：在 Claude Code 中，`/goal` 为运行设置方向；对于**托管智能体（CMA）**，通过**结果**（`user.define_outcome` 带有可评分的 rubric — harness 运行迭代 → 评分 → 修改循环）说明"完成"是什么样子，请参阅 `shared/managed-agents-outcomes.md`。

**Effort 是要测试的维度，不是固定设置。** 在之前的模型上，许多人本能地达到 `xhigh` 以最大化智能。Opus 4.8 有更高的智能天花板，因此**从 `high` 作为默认值开始并迭代**，而不是默认为 `xhigh`。在您自己的评估集上扫描 `medium`、`high` 和 `xhigh`，并权衡每条路线的智能 ↔ 延迟 ↔ 成本权衡 — 关系不是单调的：前期更高的 effort 通常会*减少*智能体工作的轮次计数和总成本，而对于某些任务，`medium` 在更短的时间内提供同样好的结果。为极其困难、延迟不敏感的情况保留 `max`。上面的 **迁移到 Opus 4.7** 部分中的每级 effort 表在 4.8 上不变地应用。

**写作声音和清晰度。** 测试人员一致描述 4.8 的散文比之前的模型更清晰、更温暖、更少对冲，可测量的 AI 口语抽搐更少 — 特别是在更高的 effort 下，它接近专家级的散文和结构。这大致是 4.7 转变的**相反**方向（4.7 更 clipped、直接、更少验证导向）。如果您添加了风格提示来抵消 4.7 的简洁性或注入温暖，请在保留它们之前对照新基线重新评估它们 — 它们现在可能过度纠正。4.8 也是一个更强的思想伙伴：更体贴、更愿意推回、更可能从上下文推断正确答案。

**代码审查和调试。** 比 4.7 更强的真实 bug 发现和更清晰的解释 — 一次性修复，而 4.7 需要更多，并且正确识别间歇性 flakes 而不是在一次干净运行后宣布"已修复"。4.7 的警告仍然适用：如果审查 harness 说"只报告高严重性问题"或"保守"，4.8 会字面遵循它，即使底层的 bug 发现已经改善，测量的召回率也可能下降。告诉模型报告一切并在下游过滤（或第二次审查）— 有关推荐提示，请参阅 4.7 部分中的**代码审查**指导。

### 行为转变（提示可调）

这些都不会破坏代码，但为 Opus 4.7 调优的提示可能会有不同的落地效果。4.8 很好地遵循指令，因此小的、明确的推动会缩小差距。

**工具触发是表面依赖的（搜索和知识）。** 4.8 的工具触发比之前的模型更依赖表面：在系统提示存在时，它是高精度/低召回 — 网络搜索触发稍频繁但每次触发运行更少轮次，而知识检索工具（Drive、项目知识、连接的文件）触发*更少*。它在确信需要搜索时搜索，否则从上下文回答，这可能会降低需要它的任务的研究深度。用明确的搜索优先指令恢复应该搜索的速率：

> ```
> <search_first>
> 对于当前信息会改变答案的问题（最近事件、当前角色或价格、版本特定行为，或用户标记为时间敏感的任何内容）在回答之前搜索，而不是从记忆中回答。对于开放式研究请求，立即开始搜索；不要先问范围问题，除非请求对研究什么真正模棱两可。
> </search_first>
> ```

**子代理、记忆和自定义工具的利用不足。** 与搜索分开，4.8 对于需要明确"决定使用这个"步骤的能力是保守的 — 基于文件的记忆、子代理委托、自定义工具。它不会触及复杂或昂贵的能力，除非合理确定需要它们。这是可引导的，因为 4.8 很好地遵循指令 — 说明*每个能力何时适用*，而不仅仅是它存在：

> *"对于任何超过几轮的任务，检查您的记忆文件以获取相关的先前上下文，并在继续时将新发现写入其中。当任务跨独立项目扇出（许多文件要读取、许多测试要运行、许多候选要检查）时，委托给子代理，而不是串行迭代。"*

相同的杠杆在**工具描述**级别起作用，而不仅仅是系统提示：规定性描述说明*何时*调用工具（例如"当用户询问当前价格或最近事件时调用此工具"）在 4.8 上比仅说明工具做什么的描述给出有意义的提升。使触发条件成为每个能力自己的 `description` 的一部分。

**更多面向用户的叙述。** 4.8 比 4.7 叙述更多 — 在长工具调用会话中的工具调用之间有更多文本，并且默认情况下更冗长、更详细的任务结束总结。如果您之前添加了脚手架来强制临时状态（"每 3 次工具调用后，总结进度"），**删除它** — 4.8 会自己做。如果对于编码智能体来说叙述太冗长，明确的默认静默使其表现得像 4.7 而不会降低质量：

> *"默认在工具调用之间保持静默。只有在您发现某些东西、改变方向或遇到阻碍时才写文本 — 每次一句话。不要叙述常规动作（'现在我将...'、'让我检查...'、'看着...'）。完成时：关于结果的一两个句子。不要回顾每个文件或测试 — 用户一直在关注。"*

对于知识工作交付物（报告、分析读数），冗长对用户偏好或用户轮次中的指令的响应非常好 — 暴露冗长偏好而不是硬编码长度。

**更慎重 — 更频繁地询问。** 4.8 比之前的 Opus 模型更慎重。在它之前只会做出的小决定上（变量名、默认值、两个等效方法中的哪一个），它倾向于暂停并询问，并且它经常以"想让我也...吗？"而不是明显的下一步或干净地停止来关闭完成的任务。这对于高风险或不熟悉的代码库是首选，但在未校准时会惹恼用户。在小事上授予自治权，同时在重要的地方保持谨慎（在 Claude Code 测试中，这将询问率降低了约 12 个百分点，而不会增加越权）：

> *"对于小选择（命名、格式化、默认值、等效项中的哪个方法），选择一个合理的选项并注意它，而不是询问。对于范围变更或破坏性动作，仍然先询问。"*

**思考禁用时的冗长推理。** 当 `thinking: {type: "disabled"}` 时，4.8 偶尔会将其推理的更长解释写入可见响应，当用户想要快速、快速的答案时，这读起来很冗长。最简单的修复是保持自适应思考开启 — 设置 `thinking: {type: "adaptive"}`（推荐设置；它根据任务调整思考多少）。请注意，当该字段被省略时，自适应是**不**开启的 — 与 Opus 4.7 一样，没有 `thinking` 字段的请求在没有思考的情况下运行，因此请显式设置它。如果您需要关闭思考以延迟或成本，请在系统提示中限定范围：

> *"只回答您的最终答案。不要包括探索性推理、中间草稿、您考虑但拒绝的差异或关于您过程的元评论。"*

### Opus 4.8 迁移检查清单

每个项目都有标记：**`[BLOCKS]`** 项目如果遗漏会导致 400 错误；**`[TUNE]`** 项目是质量/成本调整 — 将它们作为建议呈现给用户。

对于**已经在 Opus 4.7 上**的呼叫者，只有第一项是必需的；其他一切都是 `[TUNE]`。有条件的 `[BLOCKS]` 项目仅在来自 Opus 4.6 或更早版本时适用。

- [ ] **[BLOCKS]** 将 `model=` 字符串更新为 `claude-opus-4-8`
- [ ] **[BLOCKS]** *（仅当来自 Opus 4.6 或更早版本时）* 首先应用**迁移到 Opus 4.7** 的破坏性变更 — `budget_tokens` → 自适应思考，去掉 `temperature`/`top_p`/`top_k`，移除最后助手轮次预填充。这些在 4.7 上已经返回 400，并且在 4.8 上继续返回 400。
- [ ] **[TUNE]** 长周期 / 智能体工作：将完整任务规格放在一个明确指定的第一回合中并在 `high` 或 `xhigh` effort 下运行（Claude Code：`/goal`；托管智能体：带有可评分 rubric 的结果）
- [ ] **[TUNE]** Effort：在您的评估集上扫描 `medium` / `high` / `xhigh`，并通过智能 ↔ 延迟 ↔ 成本权衡按路线选择（默认 `high`，编码/智能体用 `xhigh`）
- [ ] **[TUNE]** 研究深度和工具使用：添加搜索优先指令；为子代理、基于文件的记忆和自定义工具添加明确的触发指导（4.8 默认情况下对这些的触及不足）— 在系统提示中*和*在每个工具自己的 `description` 中（规定性的"当...时调用此"描述给出可测量的提升）
- [ ] **[TUNE]** 叙述：移除强制进度脚手架（*"每 N 次工具调用后..."*）；如果编码智能体太健谈，添加默认静默
- [ ] **[TUNE]** 自治：添加小决定不询问的指导以降低询问率，同时对范围变更 / 破坏性动作保持谨慎
- [ ] **[TUNE]** 写作声音：重新评估为抵消 4.7 的直接性而添加的风格提示 — 4.8 默认更温暖、更少对冲；在保留它们之前重新建立基线
- [ ] **[TUNE]** 代码审查 harness：保持报告一切-下游过滤模式（4.8 字面遵循"仅高严重性" / "保守"过滤器，这可能会压低测量的召回率）
- [ ] **[TUNE]** 思考禁用的路径：如果推理泄漏到可见响应中，添加仅最终答案的指令
- [ ] **[TUNE]** 考虑会话中系统消息（`messages` 中的 `role:"system"`、beta `mid-conversation-system-2026-04-07`）用于应用在会话中途学习的上下文，而不是重建顶级系统提示并使缓存无效

---

## 验证迁移

更新后，抽查新模型是否实际被使用。将 `YOUR_TARGET_MODEL` 替换为您迁移到的模型字符串（例如 `claude-opus-4-8`、`claude-opus-4-7`、`claude-sonnet-4-6`、`claude-haiku-4-5`）并保持断言前缀同步：

```python
YOUR_TARGET_MODEL = "claude-opus-4-8"  # 或 "claude-opus-4-7"、"claude-sonnet-4-6"、"claude-haiku-4-5"
response = client.messages.create(model=YOUR_TARGET_MODEL, max_tokens=64, messages=[...])
assert response.model.startswith(YOUR_TARGET_MODEL), response.model
```

对于速率限制余量变更、定价或能力 delta（视觉、结构化输出、effort 支持），查询 Models API：

```python
m = client.models.retrieve(YOUR_TARGET_MODEL)
m.max_input_tokens, m.max_tokens
m.capabilities["effort"]["max"]["supported"]
```

完整的能力查找模式请参阅 `shared/models.md`。
