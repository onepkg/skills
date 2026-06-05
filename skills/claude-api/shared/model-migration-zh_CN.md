# 模型迁移指南

如何将现有代码迁移到更新的 Claude 模型。涵盖重大变更、已弃用的参数，以及已退役模型的直接替代方案。

如需最新、权威的版本（包含所有支持语言的代码示例），请使用 WebFetch 获取 `shared/live-sources.md` 中的**迁移指南** URL。本文件用作整合的技能本地参考；当模型发布或重大变更改变情况时，请回退到在线文档。

**本文件较大。** 使用下方的章节名称跳转（或使用 Grep 搜索本文件中的标题文本）。首先阅读步骤 0 和步骤 1——它们适用于每次迁移。然后只阅读你正在迁移的目标模型对应的章节。

| 章节 | 何时需要 |
|---|---|
| 步骤 0：确认迁移范围 | 始终——在任何编辑之前 |
| 步骤 1：对每个文件分类 | 始终——决定是替换、并行添加还是跳过 |
| 各 SDK 语法参考 | 将本指南中的 Python 示例翻译为 TypeScript / Go / Ruby / Java / C# / PHP |
| 目标模型 / 已退役模型替换方案 | 选择目标模型 |
| 按源模型划分的重大变更 | 迁移到 Opus 4.6 / Sonnet 4.6 |
| 迁移到 Opus 4.7 | 迁移到 Opus 4.7（重大变更、静默默认值变更、行为变化） |
| Opus 4.7 迁移清单 | 4.7 的必需项与可选项，标记为 `[BLOCKS]` / `[TUNE]` |
| 迁移到 Opus 4.8 | 迁移到 Opus 4.8（无新增重大变更；会话中系统提示；行为重新调优） |
| Opus 4.8 迁移清单 | 4.8 的必需项与可选项，标记为 `[BLOCKS]` / `[TUNE]` |
| 验证迁移 | 编辑后——运行时抽查 |

**TL;DR：** 更改模型 ID 字符串。如果你之前使用 `budget_tokens`，切换到 `thinking: {type: "adaptive"}`。如果你之前使用 assistant prefills，它们在 Opus 4.6 和 Sonnet 4.6 上都会返回 400——切换到替代方案（最常见的是 `output_config.format`；详见"按源模型划分的重大变更"中的表格）。如果你正从 Sonnet 4.5 迁移到 Sonnet 4.6，显式设置 `effort`——4.6 默认为 `high`。移除 `effort-2025-11-24` 和 `fine-grained-tool-streaming-2025-05-14` 这两个 beta 头部（在 4.6 上已正式发布）；一旦切换到 adaptive thinking，移除 `interleaved-thinking-2025-05-14`（仅在过渡期使用 `budget_tokens` 逃生舱时保留它）。然后将 `client.beta.messages.create` 降级回 `client.messages.create`。调低任何激进的"CRITICAL: YOU MUST"工具指令；4.6 更严格地遵循系统提示。

---

## 步骤 0：确认迁移范围

**在任何 Write、Edit 或 MultiEdit 调用之前，确认范围。** 如果用户的请求没有明确指定单个文件、特定目录或显式的文件列表，**先询问——不要开始编辑**。这是不可协商的：即使是听起来命令式的请求，如"迁移我的代码库"、"将我的项目迁移到 X"、"升级到 Sonnet 4.6"或单纯的"迁移到 Opus 4.7"，范围都是模糊的，需要澄清性问题。"我的项目"、"我的代码"、"我的代码库"、"整个项目"、"所有地方"或"整个仓库"等措辞都是**模糊的，而非指令性的**——它们告诉你要做什么，但没说**在哪里**操作。先询问，再操作。

明确提供常见的范围选项，并等待回答后再触碰任何文件：

1. 整个工作目录
2. 特定子目录（例如 `src/`、`app/`、`services/billing/`）
3. 特定文件或文件列表

将其作为单个澄清性问题提出，以便用户可以在一个轮次中回答。**仅当范围已经明确无误时才无需询问直接进行**——用户已指定确切文件（"迁移 `extract.py` 到 Sonnet 4.6"）、指向特定目录（"将 `services/billing/` 下的所有内容迁移到 Opus 4.6"）、列出了特定文件（"更新 `a.py` 和 `b.py`"）或已在之前轮次回答了范围问题。如果你能仅凭提示就精确回答"此变更将涉及哪些文件？"，那就直接进行。否则，先询问。

**工作示例。** 如果用户说*"将我的项目迁移到 Opus 4.6。我希望所有适当的地方都使用 adaptive thinking。"*你无法知道"我的项目"是指整个工作目录、仅 `src/`、仅生产代码还是其他——`all` 使意图清楚（更新*范围内*的每个调用点），但范围本身仍未定义。不要开始编辑。回复：

> 在我开始编辑之前，您能确认一下范围吗？我可以迁移：
> 1. 工作目录中的每个 `.py` 文件
> 2. 仅 `src/` 下的文件（生产代码）
> 3. 您指定的特定子目录或文件列表
>
> 选哪个？

然后等待回答。*"迁移到 Opus 4.7"* 和单纯的*"帮我升级到 Sonnet 4.6"* 同理——先询问再编辑。

**范围问题的规模评估（大型仓库）。** 在询问之前，获取每个目录的计数，以便用户具体选择：

```sh
rg -l "<old-model-id>" --type-not md | cut -d/ -f1 | sort | uniq -c | sort -rn
```

在范围问题中展示分类数据（例如*"找到 217 个引用，分布在 3 个目录：api/（130 个）、api-go/（62 个）、routing/（25 个）。迁移哪些？"*）。还要在调查之前确认 `git status` 是干净的——意外的修改意味着存在并发进程；先停下来调查，再继续。

---

## 步骤 1：对每个文件分类

并非每个包含旧模型 ID 的文件都是 API 的**调用者**。在编辑之前，将每个文件分类到以下桶之一——正确的操作有所不同：

| # | 桶 | 特征 | 操作 |
|---|---|---|---|
| 1 | **调用 API/SDK** | `client.messages.create(model=…)`、`anthropic.Anthropic()`、请求 payload | 替换模型 ID **并**应用目标版本的重大变更清单（见下文）。 |
| 2 | **定义或提供模型** | 模型注册表、OpenAPI 规范、路由/队列配置、模型策略枚举、生成的目录 | 旧条目**保留**（模型仍在提供服务）。询问是 (a) 并行添加新模型、(b) 保持不变、还是 (c) 退役旧模型——绝不盲目替换。**如果无法询问，默认选择 (a)：并行添加新模型并标记它**——替换会注销仍在生产中的模型。 |
| 3 | **将 ID 作为不透明字符串引用** | UI 回退常量、能力门控子串检查、通用测试夹具、标签解析器、环境变量默认值 | 通常替换字符串，并验证任何解析器/正则/子串匹配能否处理新 ID——但先检查下面的子情况。 |
| 4 | **带后缀的变体 ID** | `claude-<model>-<suffix>` 如 `-fast`、`-1024k`、`-200k`、`[1m]`、带日期的快照 | 这些是部署/路由标识符，而非公共模型 ID。**不要假定存在新模型的等价物。** 先在注册表中验证；如果不存在，保持字符串不变并标记它。 |

**桶 3 子情况——在替换字符串引用之前，检查：**

- **能力门控**（例如 `if 'opus-4-6' in model_id:` 启用某个功能）→ **并行添加新 ID**，不要替换。旧模型仍在提供服务且仍具有该能力，因此替换会静默地使任何仍流经此门控的旧模型流量失去该功能。如果你知道不会有旧模型流量命中此门控（完全迁移的单一调用者代码库），替换是可以的；如果不确定，并行添加。
- **注册表断言测试**（例如 `assert "claude-X" in supported_models`、`test_X_has_N_clusters`）→ **为新模型添加断言，保留旧断言。** 旧模型仍在提供服务，因此其断言仍然有效——但注册表也应包含新模型，所以也要断言。启发式判断：如果测试在列表中引用了多个模型版本，那是注册表测试；如果一个结构体中的模型仅与自身比较，那是通用夹具。
- **冻结/生成的快照** → **重新生成**，不要手动编辑。
- **与定义者耦合**（例如集成测试通过共享的 `conftest` 种子列表传递模型授权，或断言计费层级/速率限制组枚举、生成的 SKU/定价目录）→ **先验证定义者是否有新模型条目。** 如果没有，添加一个种子条目（重用最接近的现有层级作为占位符）；如果你无法自信地做到这一点，询问用户如何填充定义者。**不要跳过测试。** 不填充定义者而进行替换会使测试在运行时失败。

迁移测试时特别注意：破坏性参数（`temperature`、`top_p`、`budget_tokens`）通常不存在——测试夹具很少在占位符模型上设置采样参数。仍需进行重大变更扫描，但预计大部分结果都是干净的。

**首先查找有意标记的同步点。** 许多代码库使用注释标记（如 `MODEL LAUNCH`、`KEEP IN SYNC`、`@model-update` 或类似标记）来标记每次模型发布时必须更改的位置。在全局模型 ID 搜索之前，先使用 Grep 搜索仓库使用的任何约定——这些标记指向关键性变更。

---

## 各 SDK 语法参考

本指南中的代码示例为 Python。**相同的字段存在于每个官方 Anthropic SDK 中**——Stainless 从同一份 OpenAPI 规范生成了全部 7 个 SDK，因此 JSON 字段名仅存在大小写约定的差异，映射关系为 1:1。使用下表将 Python 示例翻译为你正在迁移的 SDK 对应的语法。

> **在将类型和方法名写入客户代码之前，请对照 SDK 源码验证。** 使用 WebFetch 从 `shared/live-sources.md` 中的 SDK 源代码表（每个 SDK 对应一行）获取相关仓库，并确认确切的符号——特别是对于类型化 SDK（Go、Java、C#），其联合/构建器名称可能与 JSON 形状不同。不要猜测下表中或 `<lang>/claude-api/README.md` 中未包含的类型名称。


### `thinking` — `budget_tokens` → adaptive

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

（在 Opus 4.7 上完全移除该字段；在 Claude 4.x 上最多保留 `temperature` 或 `top_p` 中的一个。）

| SDK | 要移除的字段 |
|---|---|
| Python | `temperature=…`、`top_p=…`、`top_k=…` |
| TypeScript | `temperature: …`、`top_p: …`、`top_k: …` |
| Go | `Temperature: anthropic.Float(…)`、`TopP: anthropic.Float(…)`、`TopK: anthropic.Int(…)` |
| Ruby | `temperature: …`、`top_p: …`、`top_k: …` |
| Java | `.temperature(…)`、`.topP(…)`、`.topK(…)` |
| C# | `Temperature = …`、`TopP = …`、`TopK = …` |
| PHP | `temperature: …`、`topP: …`、`topK: …` |

### Prefill 替代方案 — 通过 `output_config.format` 实现结构化输出

| SDK | 移除（最后一个 assistant 轮次） | 添加 |
|---|---|---|
| Python | `{"role": "assistant", "content": "…"}` | `output_config={"format": {"type": "json_schema", "schema": SCHEMA}}` |
| TypeScript | `{ role: 'assistant', content: '…' }` | `output_config: { format: { type: 'json_schema', schema: SCHEMA } }` |
| Go | 末尾的 `anthropic.MessageParam{Role: "assistant", …}` | `OutputConfig: anthropic.OutputConfigParam{Format: anthropic.JSONOutputFormatParam{…}}` |
| Ruby | `{ role: "assistant", content: "…" }` | `output_config: { format: { type: "json_schema", schema: SCHEMA } }` |
| Java | 末尾的 `Message.builder().role(ASSISTANT)…` | `.outputConfig(OutputConfig.builder().format(JsonOutputFormat.builder()…build()).build())` |
| C# | 末尾的 `new Message { Role = "assistant", … }` | `OutputConfig = new OutputConfig { Format = new JsonOutputFormat { … } }` |
| PHP | 末尾的 `['role' => 'assistant', 'content' => '…']` | `outputConfig: ['format' => ['type' => 'json_schema', 'schema' => $SCHEMA]]` |

### `thinking.display` — 选择恢复摘要推理（Opus 4.7）

| SDK | 添加 |
|---|---|
| Python | `thinking={"type": "adaptive", "display": "summarized"}` |
| TypeScript | `thinking: { type: 'adaptive', display: 'summarized' }` |
| Go | `Thinking: anthropic.ThinkingConfigParamUnion{OfAdaptive: &anthropic.ThinkingConfigAdaptiveParam{Display: anthropic.ThinkingConfigAdaptiveDisplaySummarized}}` |
| Ruby | `thinking: { type: "adaptive", display: "summarized" }`（或直接构建模型类时使用 `display_:`） |
| Java | `.thinking(ThinkingConfigAdaptive.builder().display(ThinkingConfigAdaptive.Display.SUMMARIZED).build())` |
| C# | `Thinking = new ThinkingConfigAdaptive { Display = Display.Summarized }` |
| PHP | `thinking: ['type' => 'adaptive', 'display' => 'summarized']` |

对于这些表格中未包含的任何字段，Python 示例中的 JSON 键直接翻译：Python/TypeScript/Ruby 使用 `snake_case`，PHP 使用 `camelCase` 命名参数，Go/C# 使用 `PascalCase` 结构体字段，Java 使用 `camelCase` 构建器方法。

---

## 解释你所做的每一次更改

迁移编辑对于未阅读发布说明的用户来说常常看起来随意——一个被删除的 `temperature`、一个被删除的 prefill、一句被改写的系统提示语句。**对于每次编辑，告诉用户你更改了什么以及为什么更改**，并将其与具体 API 或行为变更关联起来。在工作的过程中就进行总结性说明，而不是仅在最后才做。

对**系统提示编辑**要特别明确。用户有充分理由保护他们的提示，而提示调优更改是判断性调用（而非硬性 API 要求）。对于任何提示编辑：

- 引用编辑前后的文本。
- 说明驱动该编辑的行为变化（例如*"Opus 4.7 会根据任务复杂度调整回复长度，因此我添加了显式的长度指令"*，或*"4.6 更严格地遵循指令，因此 'CRITICAL: YOU MUST use the search tool' 现在会过度触发——已弱化为 'Use the search tool when…'"*）。
- 明确哪些提示编辑是**可选调优**（语气、长度、子代理指导），哪些代码编辑是**避免 400 错误所必需的**（采样参数、`budget_tokens`、prefills）。切勿将可选的提示更改呈现为强制性更改。

如果你一次应用多个提示调优编辑，将其作为简短列表提供，让用户可以逐一接受或拒绝，而不是静默重写他们的系统提示。

---

## 迁移之前

1. **确认目标模型 ID。** 仅使用 `shared/models.md` 中的确切字符串——不要在别名后添加日期后缀（使用 `claude-opus-4-6`，而非 `claude-opus-4-6-20251101`）。猜测 ID 会导致 404 错误。
2. **用以下清单检查你的代码使用了哪些功能：**
   - `thinking: {type: "enabled", budget_tokens: N}` → 在 Opus 4.6 / Sonnet 4.6 上迁移到 adaptive thinking（仍可运行但已弃用）
   - Assistant 轮次 prefills（`messages` 以 `role: "assistant"` 结尾）→ 在 Opus 4.6 / Sonnet 4.6 上必须更改（返回 400）
   - `messages.create()` 上的 `output_format` 参数 → 在所有模型上必须更改（API 范围弃用）
   - `max_tokens > ~16000` → 在任何模型上必须使用流式传输（超过约 16K 有 SDK HTTP 超时风险）。使用流式传输时，Sonnet 4.6 / Haiku 4.5 上限为 64K，Opus 4.6 上限为 128K
   - Beta 头部 `effort-2025-11-24`、`fine-grained-tool-streaming-2025-05-14`、`interleaved-thinking-2025-05-14` → 在 4.6 上已正式发布，移除它们并从 `client.beta.messages.create` 切换到 `client.messages.create`
   - 从 Sonnet 4.5 迁移到 Sonnet 4.6 但未设置 `effort`→ 4.6 默认为 `high`，这可能会改变你的延迟/成本特征
   - 包含 `CRITICAL`、`MUST`、`If in doubt, use X` 等措辞的系统提示 → 在 4.6 上可能过度触发（参见提示行为变更）
   - 从 3.x / 4.0 / 4.1 迁移：还要检查采样参数（`temperature` + `top_p`）、工具版本（`text_editor_20250728`）、`refusal` 和 `model_context_window_exceeded` 停止原因、尾随换行符的工具参数处理
3. **先对单个请求进行测试。** 对新模型运行一次调用，检查响应，然后再推广。

---

## 目标模型（推荐目标）

| 如果你当前使用… | 迁移到 | 原因 |
|---|---|---|
| Opus 4.7 | `claude-opus-4-8` | 最强大的模型；与 4.7 相同的 API 表面（无新增重大变更）——主要是提示重新调优；参见迁移到 Opus 4.8 |
| Opus 4.6 | `claude-opus-4-8` | 先应用 Opus 4.7 的重大变更，然后进行 4.8 的重新调优 |
| Opus 4.0 / 4.1 / 4.5 / Opus 3 | `claude-opus-4-8` | 按顺序应用 4.6 → 4.7 → 4.8（adaptive thinking、移除采样参数、然后重新调优） |
| Sonnet 4.0 / 4.5 / 3.7 / 3.5 | `claude-sonnet-4-6` | 最佳的推理速度/智能平衡；adaptive thinking；64K 输出 |
| Haiku 3 / 3.5 | `claude-haiku-4-5` | 最快且最具成本效益 |

除非用户明确选择了其他模型，否则默认使用调用方层级最新的 Opus。Opus 迁移分层：如果你当前使用 Opus 4.6 或更早版本，按顺序应用每个版本的章节直到达到目标（例如 4.5 → 4.8 意味着依次应用 4.6、4.7 和 4.8 章节）。4.7 → 4.8 的迁移没有新的重大变更——参见下面的迁移到 Opus 4.8。

---

## 已退役模型替换方案

这些模型返回 404——立即更新：

| 已退役模型 | 退役日期 | 直接替代方案 |
|---|---|---|
| `claude-3-7-sonnet-20250219` | 2026 年 2 月 19 日 | `claude-sonnet-4-6` |
| `claude-3-5-haiku-20241022` | 2026 年 2 月 19 日 | `claude-haiku-4-5` |
| `claude-3-opus-20240229` | 2026 年 1 月 5 日 | `claude-opus-4-8` |
| `claude-3-5-sonnet-20241022` | 2025 年 10 月 28 日 | `claude-sonnet-4-6` |
| `claude-3-5-sonnet-20240620` | 2025 年 10 月 28 日 | `claude-sonnet-4-6` |
| `claude-3-sonnet-20240229` | 2025 年 7 月 21 日 | `claude-sonnet-4-6` |
| `claude-2.1`、`claude-2.0` | 2025 年 7 月 21 日 | `claude-sonnet-4-6` |

## 已弃用模型（即将退役）

| 模型 | 退役日期 | 替代方案 |
|---|---|---|
| `claude-3-haiku-20240307` | 2026 年 4 月 19 日 | `claude-haiku-4-5` |
| `claude-opus-4-20250514` | 2026 年 6 月 15 日 | `claude-opus-4-8` |
| `claude-sonnet-4-20250514` | 2026 年 6 月 15 日 | `claude-sonnet-4-6` |

---

## 按源模型划分的重大变更

### 从 Sonnet 4.5 迁移到 Sonnet 4.6（effort 默认值变更）

Sonnet 4.5 没有 `effort` 参数；Sonnet 4.6 默认为 `high`。如果你只切换模型字符串而不做其他更改，可能会看到延迟和 token 使用量显著增加。显式设置 `effort`。

**推荐起点：**

| 工作负载 | 起始值 | 说明 |
|---|---|---|
| 聊天、分类、内容生成 | `low` | 配合 `thinking: {"type": "disabled"}`，你将会看到与 Sonnet 4.5 无思考模式相似或更好的性能 |
| 大多数应用程序（平衡） | `medium` | 质量与成本的默认最佳平衡点 |
| 智能编码、工具密集型工作流 | `medium` | 配合 adaptive thinking 和较大的 `max_tokens`（使用流式传输时最高 64K——Sonnet 4.6 的上限） |
| 自主多步骤代理、长周期循环 | `high` | 如果延迟/token 成为问题，可降级到 `medium` |
| 计算机使用代理 | `high` + adaptive | Sonnet 4.6 在 adaptive + high 上获得最佳计算机使用准确率 |

对于非思考聊天工作负载，具体如下：

```python
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8192,
    thinking={"type": "disabled"},
    output_config={"effort": "low"},
    messages=[{"role": "user", "content": "..."}],
)
```

**何时改用 Opus 4.6：** 最困难、最长周期的问题——大型代码迁移、深度研究、长时间自主工作。Sonnet 4.6 在快速响应和成本效率方面更胜一筹。

### 迁移到 Opus 4.6 / Sonnet 4.6（从任何旧模型）

**1. 手动扩展思考已弃用——改用 adaptive thinking。**

`thinking: {type: "enabled", budget_tokens: N}`（具有固定 token 预算的手动扩展思考）在 Opus 4.6 和 Sonnet 4.6 上已弃用。将其替换为 `thinking: {type: "adaptive"}`，这允许 Claude 自行决定何时思考以及思考多少。Adaptive thinking 还会自动启用交错思考（无需 beta 头部）。

```python
# 旧方式（在旧模型上仍有效，在 4.6 上已弃用）
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 8000},
    messages=[...]
)

# 新方式（Opus 4.6 / Sonnet 4.6）
response = client.messages.create(
    model="claude-opus-4-6",  # 或 "claude-sonnet-4-6"
    max_tokens=16000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},  # 可选：low | medium | high | max
    messages=[...]
)
```

Adaptive thinking 是长期目标，在内部评估中其表现优于手动扩展思考。请在条件允许时进行迁移。

**过渡期逃生舱：** 手动扩展思考在 Opus 4.6 和 Sonnet 4.6 上仍然*功能可用*（已弃用，将在未来版本中移除）。如果迁移过程中你需要一个硬性上限——例如，在调优 `effort` 之前限制失控工作负载的 token 消耗——你可以在显式设置 `effort` 的同时保留 `budget_tokens`，然后在后续更新中移除。`budget_tokens` 必须严格小于 `max_tokens`：

```python
# 仅用于过渡——已弃用，计划移除
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 8192},  # 必须 < max_tokens
    output_config={"effort": "medium"},
    messages=[...],
)
```

如果用户要求在 4.6 上设置"思考预算"，首选答案是 `effort`——使用 `low`、`medium`、`high` 或 `max`（仅 Opus 层级——Sonnet 或 Haiku 不可用），而不是 token 计数。

**2. Effort 参数（仅 Opus 4.5、Opus 4.6、Sonnet 4.6）。**

控制思考深度和总 token 消耗。位于 `output_config` 内部，而非顶层。默认为 `high`。`max` 仅 Opus 层级可用（Opus 4.6 及之后——Sonnet 或 Haiku 不可用）。在 Sonnet 4.5 和 Haiku 4.5 上会报错。

```python
output_config={"effort": "medium"}  # 通常是最佳成本/质量平衡
```

### 迁移到 4.6 系列（Opus 4.6 和 Sonnet 4.6）

**3. Assistant 轮次 prefills 返回 400（Opus 4.6 和 Sonnet 4.6）。**

Opus 4.6 和 Sonnet 4.6 均不再支持在最后一个 assistant 轮次中预填充响应——两者都会返回 400。在对话中*其他位置*添加 assistant 消息（例如用于少样本示例）仍然有效。根据 prefill 的作用选择替代方案：

| Prefill 用于 | 替代方案 |
|---|---|
| 强制 JSON / YAML / schema 输出 | `output_config.format` 配合 `json_schema`——参见下方示例 |
| 强制分类标签 | 包含有效标签枚举字段的工具，或结构化输出 |
| 跳过开场白（`以下是摘要：\n`） | 系统提示指令：*"直接回复，无需开场白。不要以'以下是...'或'基于...'等短语开头。"* |
| 规避错误拒绝 | 通常不再需要——4.6 的拒绝行为更加恰当。仅使用用户轮次提示即可。 |
| 继续被中断的回复 | 将延续内容放入用户轮次：*"您之前的回复被中断，结尾为`[最后文本]`。请从那里继续。"* |
| 注入提醒/上下文的补充 | 改为注入到用户轮次中。对于复杂的代理框架，通过工具调用或在压缩期间公开上下文。 |

```python
# 旧方式（在 Opus 4.6 / Sonnet 4.6 上失败）——prefill 强制 JSON 形状
messages=[
    {"role": "user", "content": "提取名称。"},
    {"role": "assistant", "content": "{\"name\": \""},
]

# 新方式——结构化输出替代 prefill
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    output_config={"format": {"type": "json_schema", "schema": {...}}},
    messages=[{"role": "user", "content": "提取名称。"}],
)
```

**4. 当 `max_tokens > ~16K` 时使用流式传输（所有模型）；Opus 4.6 独有可达 128K。**

非流式传输请求在高 `max_tokens` 时会遇到 SDK HTTP 超时，无论模型如何——对于约 16K 以上的输出，使用流式传输。可流式传输的上限因模型而异：Sonnet 4.6 和 Haiku 4.5 上限为 64K，Opus 4.6 独有可达 128K。

```python
with client.messages.stream(model="claude-opus-4-6", max_tokens=64000, ...) as stream:
    message = stream.get_final_message()
```

**5. 工具调用的 JSON 转义可能不同（Opus 4.6 和 Sonnet 4.6）。**

这两个 4.6 模型可能生成包含 Unicode 或正斜杠转义的工具调用 `input` 字段。始终使用 `json.loads()` / `JSON.parse()` 进行解析——切勿对序列化输入进行原始字符串匹配。

### 所有模型

**6. `output_format` → `output_config.format`（API 范围）。**

`messages.create()` 上旧的顶层 `output_format` 参数已弃用。请改用 `output_config.format`。这不是 4.6 特有的——适用于每个模型。

---

## 在 4.6 上应移除的 Beta 头部

在 4.5 上必需的几个 beta 头部在 4.6 上已正式发布，应将其移除。保留它们无害但具有误导性；移除它们还可以让你从 `client.beta.messages.create(...)` 回到 `client.messages.create(...)`。

| 头部 | 在 4.6 上的状态 | 操作 |
|---|---|---|
| `effort-2025-11-24` | Effort 参数已正式发布 | 移除 |
| `fine-grained-tool-streaming-2025-05-14` | 已正式发布 | 移除 |
| `interleaved-thinking-2025-05-14` | Adaptive thinking 会自动启用交错思考 | 在使用 adaptive thinking 时移除；在 Sonnet 4.6 上*配合*手动扩展思考仍可运行，但该路径已弃用 |
| `token-efficient-tools-2025-02-19` | 已内置于所有 Claude 4+ 模型 | 移除（无效果） |
| `output-128k-2025-02-19` | 已内置于 Claude 4+ 模型 | 移除（无效果） |

移除所有这些头部并完成迁移到 adaptive thinking 后，你可以将 SDK 调用点从 beta 命名空间切换回普通命名空间：

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

## 从 3.x / 4.0 / 4.1 迁移到 4.6 时的额外变更

如果你从 Opus 4.1、Sonnet 4、Sonnet 3.7 或更旧的 Claude 3.x 模型直接跳到 4.6，请应用以上所有内容*以及*本节中的项目。已在 Opus 4.5 / Sonnet 4.5 上的用户可以跳过本节。

**1. 采样参数：使用 `temperature` 或 `top_p`，不可同时使用。**

同时传递两者会在所有 Claude 4+ 模型上报错：

```python
# 旧方式（仅 3.x——在 4+ 上报错）
client.messages.create(temperature=0.7, top_p=0.9, ...)

# 新方式
client.messages.create(temperature=0.7, ...)  # 或 top_p，不可同时使用
```

**2. 更新工具版本。**

旧版工具版本在 4+ 上不受支持。**`type` 和 `name` 字段都会变化**——`text_editor_20250728` 和 `str_replace_based_edit_tool` 是一对；只更新其中一个而不更新另一个会返回 400。同时从文本编辑器集成中移除 `undo_edit` 命令：

| 旧版 | 新版 |
|---|---|
| `text_editor_20250124` + `str_replace_editor` | `text_editor_20250728` + `str_replace_based_edit_tool` |
| `code_execution_*`（早期版本） | `code_execution_20250825` |
| `undo_edit` 命令 | *（不再支持——删除调用点）* |

```python
# 之前
tools = [{"type": "text_editor_20250124", "name": "str_replace_editor"}]

# 之后——两个字段都更改
tools = [{"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}]
```

**3. 处理 `refusal` 停止原因。**

Claude 4+ 可能在响应中返回 `stop_reason: "refusal"`。如果你的代码只处理 `end_turn` / `tool_use` / `max_tokens`，请添加分支：

```python
if response.stop_reason == "refusal":
    # 向用户展示拒绝信息；不要使用相同的提示重试
    ...
```

**4. 处理 `model_context_window_exceeded` 停止原因（4.5+）。**

与 `max_tokens` 不同：它表示模型达到了*上下文窗口*限制，而非请求的输出上限。同时处理两者：

```python
if response.stop_reason == "model_context_window_exceeded":
    # 上下文窗口耗尽——压缩或拆分对话
    ...
elif response.stop_reason == "max_tokens":
    # 达到请求的输出上限——使用更大的 max_tokens 重试或使用流式传输
    ...
```

**5. 工具调用字符串参数中的尾随换行符被保留（4.5+）。**

4.5 和 4.6 保留了旧模型会移除的尾随换行符。如果你的工具实现对工具调用的 `input` 值进行精确字符串匹配（例如 `if name == "foo"`），请验证当模型发送 `"foo\n"` 时它们是否仍然匹配。在接收端使用 `.rstrip()` 进行规范化通常是最简单的修复方法。

**6. Haiku：速率限制在不同代际之间重置。**

Haiku 4.5 有自己独立的速率限制池，与 Haiku 3 / 3.5 分开。如果你在迁移期间增加流量，请查看你所在层级的 Haiku 4.5 限制（参见 [API rate limits](https://platform.claude.com/docs/en/api/rate-limits)）——满足 Haiku 3.5 流量的配额可能需要在 4.5 上提升层级才能支持相同的量。

---

## 提示行为变更（Opus 4.5 / 4.6、Sonnet 4.6）

这些不会破坏你的代码，但在 4.5 及更早版本上有效的提示在 4.6 上可能过度触发或触发不足。根据需要调优。

**1. 激进指令导致过度触发。** Opus 4.5 和 4.6 比早期模型更严格地遵循系统提示。为*克服*旧模型抗拒而编写的提示现在过于激进：

| 之前（在 4.0 / 4.5 上有效） | 之后（在 4.6 上使用） |
|---|---|
| `CRITICAL: You MUST use this tool when...` | `Use this tool when...` |
| `Default to using [tool]` | `Use [tool] when it would improve X` |
| `If in doubt, use [tool]` | *（删除——不再需要）* |

如果模型现在过度触发某个工具或技能，修复方法几乎总是调低语言强度，而不是添加更多防护措施。

**2. 过度思考和过度探索（Opus 4.6）。** 在较高的 `effort` 设置下，Opus 4.6 在回答之前会进行更多探索。如果这消耗了太多思考 token，先降低 `effort`（`medium` 通常是最佳平衡点），然后再添加文字指令来约束推理。

**3. 过于积极的子代理生成（Opus 4.6）。** Opus 4.6 有很强的倾向将任务委托给子代理。如果你看到它为简单的 `grep` 或 `read` 就能解决的问题生成了子代理，请添加指导：*"仅在需要并行或独立工作流时使用子代理。对于单文件读取或顺序操作，直接工作。"*

**4. 过度设计（Opus 4.5 / 4.6）。** 这两个模型可能会添加超出要求的额外文件、抽象或防御性错误处理。如果你希望最小化更改，明确提示：*"仅进行直接要求的更改。不要为不可能发生的场景添加辅助函数、抽象或错误处理。"*

**5. LaTeX 数学输出（Opus 4.6）。** Opus 4.6 默认使用 LaTeX（`\frac{}{}`、`$...$`）输出数学和技术内容。如果你需要纯文本，明确指示：*"所有数学内容格式化为纯文本——不使用 LaTeX、不使用 `$`、不使用 `\frac{}{}`。使用 `/` 表示除法，使用 `^` 表示指数。"*

**6. 省略口头摘要（4.6 系列）。** 4.6 模型更加简洁，可能跳过工具调用后的摘要段落，直接跳转到下一步操作。如果你依赖这些摘要来提高可见性，请添加：*"完成涉及工具使用的任务后，提供你做了什么简要总结。"*

**7. "思考"作为触发词（Opus 4.5 思考禁用时）。** 当 `thinking` 关闭时，Opus 4.5 对 *think* 这个词特别敏感，可能会进行超出你期望的推理。改用 `consider`、`evaluate` 或 `reason through`。

---

## 模型 ID 重命名快速参考

| 旧字符串（迁移源） | 新字符串 |
|---|---|
| `claude-opus-4-7` | `claude-opus-4-8` |
| `claude-opus-4-6` | `claude-opus-4-8` |
| `claude-opus-4-5` | `claude-opus-4-8` |
| `claude-opus-4-1` | `claude-opus-4-8` |
| `claude-opus-4-0` | `claude-opus-4-8` |
| `claude-sonnet-4-5` | `claude-sonnet-4-6` |
| `claude-sonnet-4-0` | `claude-sonnet-4-6` |

较旧的别名（`claude-opus-4-7`、`claude-opus-4-6`、`claude-opus-4-5`、`claude-sonnet-4-5` 等）仍然有效，如果需要时间进行升级，可以固定在当前版本——完整的旧版列表请参见 `shared/models.md`。

---

## 迁移清单

每个项目都已标记：**`[BLOCKS]`** 项目如果遗漏会导致 400 错误、无限循环、静默超时或错误的工具选择——将以下更改作为代码编辑应用，而非建议。**`[TUNE]`** 项目为质量/成本调整。

对于每个调用 `messages.create()` / 等同 SDK 方法的文件：

- [ ] **[BLOCKS]** 将 `model=` 字符串更新为新别名
- [ ] **[BLOCKS]** 将 `budget_tokens` 替换为 `thinking={"type": "adaptive"}`（在 Opus 4.6 / Sonnet 4.6 上已弃用）
- [ ] **[BLOCKS]** 将 `format` 从顶层 `output_format` 移到 `output_config.format` 中
- [ ] **[BLOCKS]** 如果目标是 Opus 4.6 或 Sonnet 4.6，移除所有 assistant 轮次 prefills（参见 prefill 替代方案表）
- [ ] **[BLOCKS]** 如果 `max_tokens > ~16000`，切换到流式传输（否则 SDK HTTP 超时）
- [ ] **[TUNE]** 显式设置 `output_config={"effort": "..."}`——特别是在从 Sonnet 4.5 迁移到 Sonnet 4.6 时（4.6 默认为 `high`）
- [ ] **[TUNE]** 移除已正式发布的 beta 头部：`effort-2025-11-24`、`fine-grained-tool-streaming-2025-05-14`、`token-efficient-tools-2025-02-19`、`output-128k-2025-02-19`；一旦使用 adaptive thinking，移除 `interleaved-thinking-2025-05-14`
- [ ] **[TUNE]** 移除所有 beta 后，将 `client.beta.messages.create(...)` 切换为 `client.messages.create(...)`
- [ ] **[TUNE]** 检查系统提示中是否包含激进工具语言（`CRITICAL:`、`MUST`、`If in doubt`）并适当调低

**从 3.x / 4.0 / 4.1 迁移时的额外项目：**
- [ ] **[BLOCKS]** 移除 `temperature` 或 `top_p` 之一（同时传递两者在 Claude 4+ 上返回 400）
- [ ] **[BLOCKS]** 将文本编辑器工具 `type` 更新为 `text_editor_20250728`
- [ ] **[BLOCKS]** 将文本编辑器工具 `name` 更新为 `str_replace_based_edit_tool`——**仅更改 `type` 而保留 `name: "str_replace_editor"` 会返回 400**
- [ ] **[BLOCKS]** 将代码执行工具更新为 `code_execution_20250825`
- [ ] **[BLOCKS]** 删除所有 `undo_edit` 命令调用点
- [ ] **[TUNE]** 添加对 `stop_reason == "refusal"` 的处理
- [ ] **[TUNE]** 添加对 `stop_reason == "model_context_window_exceeded"` 的处理（4.5+）
- [ ] **[TUNE]** 验证工具参数字符串匹配是否容忍尾随换行符（在 4.5+ 上被保留）
- [ ] **[TUNE]** 如果迁移到 Haiku 4.5：检查速率限制层级（与 Haiku 3.x 使用不同的池）

**验证：**
- [ ] 运行一个测试请求，检查 `response.stop_reason`、`response.usage` 以及工具使用/思考行为是否符合预期

关于缓存提示：渲染顺序和哈希输入未发生变化，因此现有的 `cache_control` 断点仍可正常工作。但是，**更改模型字符串会使现有缓存失效**——新模型上的第一个请求将重新写入缓存。

---

## 迁移到 Opus 4.7

> **模型 ID `claude-opus-4-7` 以此处编写为准。** 当用户请求迁移到 Opus 4.7 时，务必写入 `model="claude-opus-4-7"`。**不要**使用 WebFetch 验证——本指南是迁移目标 ID 的权威来源。对应条目存在于 `shared/models.md` 中。

Claude Opus 4.7 在发布时是 Anthropic 最强大的模型，现在是上一代 Opus（Opus 4.8 为当前版本——参见下面的迁移到 Opus 4.8）。它高度自主，在长周期代理工作、知识工作、视觉任务和记忆任务上表现异常出色。本节总结了 4.7 发布时的所有新特性，并且仍然是来自 Opus 4.6 或更早版本的调用者的分层重大变更路径。它叠加在上述 4.6 迁移之上——如果调用者从 Opus 4.5 或更早版本直接跳过来，请先应用 4.6 的更改，然后是本部分，最后是 4.8 部分。

**已经使用 Opus 4.6 的用户的 TL;DR：** 将模型 ID 更新为 `claude-opus-4-7`，移除任何剩余的 `budget_tokens` 和采样参数（两者在 Opus 4.7 上都返回 400），为 `max_tokens` 提供额外余量并使用 `count_tokens()` 对新模型重新基线化，如果推理内容会展示给用户则选择恢复 `thinking.display: "summarized"`，并重新调优 `effort`——它在 4.7 上比任何之前的 Opus 都更重要。

### 重大变更（在 Opus 4.7 上会返回 400）

**扩展思考已移除。**

`thinking: {type: "enabled", budget_tokens: N}` 在 Claude Opus 4.7 及更高模型上不再支持，会返回 400 错误。切换到 adaptive thinking（`thinking: {type: "adaptive"}`）并使用 effort 参数控制思考深度。Adaptive thinking 在 Claude Opus 4.7 上**默认关闭**：没有 `thinking` 字段的请求将在无思考模式下运行，与 Opus 4.6 行为一致。显式设置 `thinking: {type: "adaptive"}` 以启用它。

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

如果调用者之前没有使用扩展思考，则无需更改——思考默认关闭，或者可以显式设置为 `thinking={"type": "disabled"}`。

完全删除 `budget_tokens` 相关代码。关于替代的 `effort` 值，请参见下方的**在 Opus 4.7 上选择 effort 级别**——从 `budget_tokens` 到 `effort` 不存在精确的 1:1 映射。

**采样参数已移除。**

`temperature`、`top_p` 和 `top_k` 参数在 Claude Opus 4.7 上不再被接受。包含这些参数的请求会返回 400 错误。从请求 payload 中移除这些字段。提示（prompting）是在 Claude Opus 4.7 上引导模型行为的推荐方式。如果你之前使用 `temperature = 0` 追求确定性，请注意它从未在之前的模型上保证过相同的输出。

```python
# 之前——在 Opus 4.7 上会报错
client.messages.create(temperature=0.7, top_p=0.9, ...)

# 之后
client.messages.create(...)  # 无采样参数
```

- **如果目的是确定性**——使用 `effort: "low"` 配合更紧凑的提示。
- **如果目的是创造性差异**——提示替代方案取决于用例；**询问用户**他们希望如何激发差异。如果无法询问，添加一个适合用例的指令，例如"选择一些偏离分布且有意义的方案"——例如对于文本生成，"在回复中变化你的措辞和结构"；对于前端/设计，使用下方"设计和前端编码"下的提出四个方向的方法。

### 在 Opus 4.7 上选择 effort 级别

`budget_tokens` 控制要*思考*多少；`effort` 控制思考*和行动*的总体投入，因此不存在精确的 1:1 映射。**在编码和代理用例中使用 `xhigh` 以获得最佳效果，对于大多数对智能敏感的用例至少使用 `high`。** 尝试其他级别以进一步调优 token 使用和智能水平：

| 级别 | 使用场景 | 说明 |
|---|---|---|
| `max` | 值得在最高水平测试的智能密集型任务 | 在某些用例中可以带来提升，但可能因 token 使用量增加而出现收益递减；容易过度思考 |
| `xhigh` | **大多数编码和代理用例** | 这些场景的最佳设置；是 Claude Code 中的默认值 |
| `high` | 一般的智能敏感型用例 | 平衡 token 使用与智能；推荐作为大多数智能敏感型工作的最低水平 |
| `medium` | 需要减少 token 使用同时权衡智能的成本敏感型用例 | |
| `low` | 短小精悍的任务和延迟敏感型工作负载，对智能不敏感 | |

### 静默默认值变更（无错误，但行为不同）

**思考内容默认省略。**

在 Claude Opus 4.7 上，思考块仍然出现在响应流中，但它们的 `thinking` 字段为空，除非你显式选择加入。这是与 Claude Opus 4.6 的静默变更，之前在 4.6 上默认返回总结的思考文本。要在 Claude Opus 4.7 上恢复总结的思考内容，将 `thinking.display` 设置为 `"summarized"`。**块字段名称未变**——它仍然是 `thinking` 类型块上的 `block.thinking`；不要重命名它。

**检测方法：** 查找任何从 `thinking` 类型块读取 `block.thinking`（或等效字段）并在 UI、日志或跟踪中呈现的代码。**修复方法是请求参数，而非响应处理**——在 `thinking` 参数中添加 `display: "summarized"`：

```python
thinking={"type": "adaptive", "display": "summarized"}  # "display" 在 Opus 4.7 上是新增的；值："omitted"（默认）| "summarized"
```

默认值为 `"omitted"`。如果思考内容从未在任何地方展示，则无需更改。如果您的产品向用户流式传输推理内容，新的默认值会表现为输出开始前长时间停顿；设置 `display: "summarized"` 以在思考过程中恢复可见的进度显示。

**更新后的 token 计数。**

Claude Opus 4.7 和 Claude Opus 4.6 的 token 计数方式不同。相同的输入文本在 Claude Opus 4.7 上产生的 token 数高于 Claude Opus 4.6，并且 `/v1/messages/count_tokens` 对 Claude Opus 4.7 返回的 token 数将与 Claude Opus 4.6 不同。Claude Opus 4.7 的 token 效率可能因工作负载模式而异。提示干预、`task_budget` 和 `effort` 可以帮助控制成本并确保适当的 token 使用。请注意，这些控制措施可能会折损模型智能。**更新你的 `max_tokens` 参数以提供额外余量，包括压缩触发器。** Claude Opus 4.7 按标准 API 定价提供 1M 上下文窗口，无需长上下文溢价。

还需检查：

- 针对 4.6 校准的客户端 token 估算器（类似 tiktoken 的近似方法）
- 将 token 乘以固定每 token 费率的成本计算器
- 基于实测 token 数的速率限制重试阈值

通过在调用者的代表性提示样本上，重新对 `claude-opus-4-7` 运行 `client.messages.count_tokens()` 来重新基线化。不要应用统一乘数。对于成本敏感的工作负载，考虑将 `effort` 降低一个级别（例如 `high` → `medium`）。对于代理循环，考虑采用任务预算（见下文）。

### 新功能：任务预算（beta）

Opus 4.7 引入了**任务预算**——告诉 Claude 它在整个代理循环中有多少 token 可用（思考 + 工具调用 + 最终输出）。模型会看到一个实时倒计时，并用它来优先安排工作并在预算即将耗尽时优雅收尾。

这是**模型知晓的建议**，而非硬性上限。它不同于 `max_tokens`，后者仍然是每个响应的强制限制并且*不*向模型公开。当你希望模型自我调节时使用 `task_budget`；使用 `max_tokens` 作为硬性上限来控制使用量。

需要 beta 头部 `task-budgets-2026-03-13`：

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

为开放式代理任务设置宽松的预算，为延迟敏感型任务收紧预算。**最小 `task_budget.total` 为 20,000 token。** 如果预算对任务来说过于严格，模型可能不够彻底地完成任务，并将其预算作为约束参考。**在迁移期间不要添加 `task_budget`，除非你确定预算值是合适的**——如果你可以运行工作负载并进行测量，就这样做；否则询问用户该值而不是猜测。这是在代理工作负载上抵消 token 计数变化的杠杆。

### 能力改进

**高分辨率视觉。** Opus 4.7 是第一个支持高分辨率图像的 Claude 模型。最大图像分辨率为**长边 2576 像素**（从 Opus 4.6 及之前的 1568px 提升）。这在视觉密集型工作负载上带来了显著提升，特别是计算机使用和截图/文档/直观理解。模型返回的坐标现在与实际图像像素 1:1 映射，因此无需缩放因子计算。

高分辨率支持在 Opus 4.7 上**自动启用**——无需 beta 头部，无需客户端选择加入。模型接受更大的输入，并直接返回像素精确的坐标。

**Token 成本。** Opus 4.7 上的全分辨率图像可能使用比之前模型多约 3 倍的图像 token（每个图像最多约 4784 个 token，之前约为 1600 个 token 的上限）。如果不需要额外的保真度，在发送前在客户端进行下采样以控制成本——但**在迁移期间默认不要添加下采样**。如果你不确定管道是否需要保真度，询问用户而不是猜测。在 Opus 4.7 上使用 `count_tokens()` 对代表性图像进行重新基线化，然后再对任何测得的成本变化做出反应。

除了分辨率外，Opus 4.7 还在低级感知（指向、测量、计数）和自然图像边界框定位和检测方面有所改进。

**知识工作。** 在模型视觉验证自身输出的任务上取得了显著进展——`.docx` 修订标注、`.pptx` 编辑以及程序化的图表/图形分析（例如通过图像处理库进行像素级数据转录）。如果提示中包含如*"返回之前再次检查幻灯片布局"*的辅助结构，尝试移除并重新基线化。

**记忆。** Opus 4.7 在写入和使用基于文件系统的记忆方面表现更佳。如果代理维护跨轮次的草稿本、笔记文件或结构化记忆存储，该代理应在为自己做笔记以及在未来的任务中利用其笔记方面有所改进。

**面向用户的进度更新。** Opus 4.7 在长代理跟踪期间提供更规律、更高质量的中间更新。如果系统提示中包含如*"每 3 次工具调用后，总结进度"*的辅助结构，尝试移除以避免过多的面向用户文本。如果 Opus 4.7 更新的长度或内容对你的用例校准不佳，请在提示中明确描述这些更新应有的样貌并提供示例。

### 实时网络安全防护措施

涉及禁止或高风险主题的请求可能导致拒绝。

### 快速模式：Opus 4.7 上不可用

Opus 4.7 没有快速模式变体。**Opus 4.6 Fast 仍然受支持**。仅当调用者的代码实际使用了快速模式模型字符串时才提及此项（例如 `claude-opus-4-6-fast`）；如果代码中未出现 "fast" 一词，则不提及快速模式。

当你看到 `model="claude-opus-4-6-fast"`（或类似形式）时，**迁移编辑应为**：

```python
# Opus 4.7 没有快速模式——保持在 4.6 Fast（调用者自行选择是否切换到标准 Opus 4.7）。
model="claude-opus-4-6-fast",
```

也就是说：保持模型字符串**不变**，在其上方添加注释，并告知用户他们有两个选项——(a) 留在 Opus 4.6 Fast（仍受支持），或 (b) 将延迟容忍流量迁移到标准 Opus 4.7 以获取智能提升。**不要**自行将模型字符串改写为 `claude-opus-4-7`；那会静默地用延迟换智能，这应该是调用者的决定。

### 行为变化（可提示调优）

这些不会破坏任何东西，但为 Opus 4.6 调优的提示可能会产生不同的效果。Opus 4.7 比 4.6 更易引导，因此小的提示调整通常能消除差距。

**更字面化的指令遵循。** Claude Opus 4.7 比 Claude Opus 4.6 更字面化、更显式地解释提示，尤其是在较低的 effort 级别。它不会静默地将一个项目的指令泛化到另一个项目，也不会推断你未提出的请求。这种字面化的优点是精确性和更少的反复。对于具有精心调优提示、结构化提取以及需要可预测行为的管道 API 用例，它通常表现更好。对提示和框架进行审查可能对迁移到 Claude Opus 4.7 特别有帮助。

**详细程度根据任务复杂度校准。** Opus 4.7 根据其对任务复杂度的判断来调整响应长度，而不是默认使用固定的详细程度——简单查询时回答更短，开放式分析时回答更长。如果产品依赖特定的长度或风格，请显式调优提示。要减少详细程度：

> *"提供简洁、重点突出的回复。跳过非必要的上下文，并将示例保持在最少。"*

如果你看到特定类型的过度详细（例如过度解释），添加针对这些的目标指令。展示所需简洁程度的正面示例往往比告诉模型不该做什么的负面示例或指令更有效。**不要**假定现有的"简洁"指令应被移除——先测试。

**语气和写作风格。** Opus 4.7 更直接、更有主见，比 Opus 4.6 更温暖的风格使用更少的验证性措辞和更少的 emoji。与任何新模型一样，长篇写作中的散文风格可能发生变化。如果产品依赖特定的语气，请对照新基线重新评估风格提示。如果需要更温暖或更对话式的语气，请指定：

> *"使用温暖、协作的语气。在回答之前先认可用户的表述框架。"*

**`effort` 比任何之前的 Opus 都更重要。** Opus 4.7 更严格地遵循 `effort` 级别，尤其是在低端。在 `low` 和 `medium` 时，它将工作范围限定在被要求的内容，而不是超出——这对延迟和成本有好处，但在 `low` 级别的中等任务上存在思考不足的风险。

- 如果在复杂问题上出现浅层推理，将 `effort` 提高到 `high` 或 `xhigh`，而不是通过提示绕过。
- 如果必须将 `effort` 保持在 `low` 以控制延迟，添加有针对性的指导：*"此任务涉及多步骤推理。在回复之前仔细思考问题。"*
- **在 `xhigh` 或 `max` 时，设置较大的 `max_tokens`**，以便模型有空间在工具调用和子代理之间进行思考和行动。从 64K 开始并根据需要进行调优。（`xhigh` 是 Opus 4.7 上新增的 effort 级别，介于 `high` 和 `max` 之间。）

自适应思考的触发也是可引导的。如果模型的思考频率超出预期——这在大型或复杂系统提示下可能发生——添加：*"思考会增加延迟，仅当它能显著提高答案质量时才使用——通常适用于需要多步骤推理的问题。如果不确定，直接回复。"*

**默认较少使用工具。** Opus 4.7 倾向于比 4.6 更少使用工具，而更多使用推理。这在大多数情况下会产生更好的结果，但对于依赖工具（搜索/检索、函数调用、计算机使用步骤）的产品，可能会降低工具使用率。两个选项：

- **提高 `effort`**——`high` 或 `xhigh` 在代理搜索和编码中显示更多的工具使用，对知识工作尤其有用。
- **通过提示引导**——在工具描述或系统提示中明确说明何时以及如何使用工具，并鼓励模型倾向于更频繁地使用工具：

> *"当答案依赖于对话中不存在的信息时，你必须在回答之前调用 `search` 工具——不要凭先验知识回答。"*

**默认使用更少的子代理。** Opus 4.7 倾向于比 4.6 生成更少的子代理。这是可引导的——给出关于何时进行委托的明确指导。例如，对于编码代理：

> *"对于你可以在单个回复中直接完成的工作（例如重构一个你已经能看到的函数），不要生成子代理。在需要分头处理多个项目或读取多个文件时，才在同一轮次中生成多个子代理。"*

**设计和前端编码。** Opus 4.7 比 4.6 有更强的设计直觉，具有一致的内置风格：温暖的奶油色/米白色背景（约 `#F4F1EA`）、衬线展示字体（Georgia、Fraunces、Playfair）、斜体单词强调以及陶土色/琥珀色强调色。这对于编辑、酒店和作品集类任务效果很好，但对于仪表盘、开发工具、金融科技、医疗保健或企业应用会感觉不合适——而且它也出现在幻灯片以及网页 UI 中。

默认风格是持久的。泛泛的指令（"不要用奶油色"、"让它干净简约"）往往会使模型切换到不同的固定调色板，而不是产生多样性。两种方法可靠有效：

1. **指定具体替代方案。** 模型精确遵循显式规范——给出确切的十六进制颜色值、字体和布局约束。
2. **让模型在构建之前提出选项。** 这打破了默认模式并让用户获得控制权：

   > *"在构建之前，针对此简报提出 4 种不同的视觉方向（每种为：背景十六进制色值 / 强调色十六进制色值 / 字体——一行说明理由）。请用户选择一种，然后仅实现该方向。"*

如果调用者之前依赖 `temperature` 来获得设计多样性，使用方法 (2)——它在不同运行中会产生有意义的不同方向。

Opus 4.7 还需要比早期模型更少的前端设计提示来避免通用的"AI 千篇一律"审美。早期模型需要冗长的反千篇一律代码片段，而 Opus 4.7 用更短的提示就能生成独特、有创意的前端。以下代码片段与上述多样性方法配合良好：

> *"绝对不要使用通用的 AI 生成审美，如过度使用的字体系列（Inter、Roboto、Arial、系统字体）、陈词滥调的色彩方案（特别是白色或深色背景上的紫色渐变）、可预测的布局和组件模式，以及缺乏特定情境特色的千篇一律设计。使用独特的字体、协调的颜色和主题，以及用于效果和微交互的动画。"*

**交互式编码产品。** Opus 4.7 的 token 使用和行为在自主式、异步编码代理（单用户轮次）与交互式、同步编码代理（多用户轮次）之间可能存在差异。具体来说，它在交互式环境中倾向于使用更多 token，主要原因是在用户轮次后进行更多推理。这可以提高长周期连贯性、指令遵循以及长时间交互式编码会话中的编码能力，但也伴随着更高的 token 使用量。要在编码产品中最大化性能与 token 效率，请使用 `effort: "xhigh"` 或 `"high"`，添加自主功能（如自动模式），并减少用户所需的人工交互次数。

在限制所需用户交互时，在第一个人类轮次中预先指定任务、意图和相关约束。预先指定良好、清晰、准确的任务描述有助于最大化自主性和智能性，同时最大程度减少用户轮次后的额外 token 使用——因为 Opus 4.7 比之前的模型更自主，这种使用模式有助于最大化性能。相反，通过多个用户轮次逐步传达的模糊或未充分指定的提示往往会降低 token 效率，有时还会降低性能。

**代码审查。** Opus 4.7 在查找 bug 方面比之前的模型有显著改进，具有更高的召回率和精确度。然而，如果代码审查框架是为早期模型调优的，它最初可能显示*较低*的召回率——这很可能是框架效应，而非能力退化。当审查提示说"仅报告高严重性问题"、"保守一些"或"不要吹毛求疵"时，Opus 4.7 比早期模型更忠实地遵循该指令：它同样彻底地调查，识别 bug，然后拒绝报告其判断为低于所述标准的发现。精确度上升，但测得的召回率可能下降，尽管底层 bug 发现能力已经提高。

推荐的提示语言：

> *"报告你发现的每个问题，包括你不确定或认为严重性较低的问题。在此阶段不要按重要性或置信度进行过滤——后续会有单独的验证步骤进行过滤。你这里的目标是覆盖率：提出一个后来被过滤掉的发现也比静默遗漏一个 bug 更好。对于每个发现，包括你的置信度级别和估计的严重性，以便下游过滤器可以对它们进行排序。"*

这可以在没有实际第二步的情况下使用，但将置信度过滤移出发现阶段通常有帮助。如果框架有单独的验证/去重/排序阶段，明确告诉模型其发现阶段的任务是覆盖率，而非过滤。如果需要单遍自过滤，请具体说明标准，而不是使用"重要"等定性术语——例如*"报告任何可能导致不正确行为、测试失败或误导性结果的 bug；仅省略纯样式或命名偏好等细枝末节。"*在评估子集上迭代提示以验证召回率或 F1 收益。

**计算机使用。** 计算机使用在高达新的 2576px / 3.75MP 最大分辨率的范围内均可工作。以 **1080p** 发送图像可以在性能和成本之间取得良好平衡。对于特别成本敏感的工作负载，**720p** 或 **1366×768** 是成本更低的选择，性能仍然强劲。测试以找到适合用例的理想设置；尝试使用 `effort` 也可以帮助调优行为。

---

## Opus 4.7 迁移清单

每个项目都已标记：**`[BLOCKS]`** 项目如果遗漏会导致 400 错误、无限循环、静默截断或空输出——将以下更改作为代码编辑应用，而非建议。**`[TUNE]`** 项目为质量/成本调整——向用户展示作为建议。

以 **"If…"** 或 **"At…"** 为前缀的 `[BLOCKS]` 项目是有条件的。在逐一检查清单之前，**扫描文件**查找条件：它是否向 UI/日志呈现思考文本？它是否将 `output_config.effort` 设置为 `"x-high"` 或 `"max"`？它是否为安全工作负载？它是否为多轮次代理循环？仅应用条件匹配的项目。

- [ ] **[BLOCKS]** 将 `thinking: {type: "enabled", budget_tokens: N}` 替换为 `thinking: {type: "adaptive"}` + `output_config.effort`；完全删除 `budget_tokens` 相关代码
- [ ] **[BLOCKS]** 从请求构造中移除 `temperature`、`top_p`、`top_k`
- [ ] **[BLOCKS]** 如果思考内容向用户展示或存储在日志中：添加 `thinking.display: "summarized"`（否则渲染的文本为空）
- [ ] **[BLOCKS]** 当 `output_config.effort` 为 `xhigh` 或 `max` 时：设置 `max_tokens` ≥ 64000（否则输出在思考中途被截断）
- [ ] **[TUNE]** 为 `max_tokens` 和压缩触发器提供额外余量；重新对 `claude-opus-4-7` 运行 `count_tokens()` 对代表性提示进行重新基线化（不要使用统一乘数）
- [ ] **[TUNE]** 在对测得的成本变化做出反应*之前*，重新基线化成本和速率限制仪表盘
- [ ] **[TUNE]** 按路径重新评估 `effort`——编码/代理使用 `xhigh`，大多数智能敏感型工作至少使用 `high`；它在 4.7 上比任何之前的 Opus 都更重要
- [ ] **[TUNE]** 多轮次代理循环：采用 API 原生任务预算（`output_config.task_budget`，beta `task-budgets-2026-03-13`，最少 20k token）——这是用于限制循环中的*累积*消耗；每轮深度使用 `effort`
- [ ] **[TUNE]** 检查依赖 4.6 泛化意图的模糊或未充分指定的指令，并将其更新为更清晰或更精确——4.7 会字面化地遵循它们
- [ ] **[TUNE]** 工具使用工作负载：在工具描述中添加明确的何时/如何使用指导（4.7 较少使用工具）
- [ ] **[TUNE]** 详细程度：在更改之前测试现有的长度指令——4.7 根据任务复杂度校准长度，因此为所需的输出调优，而不是假设一个方向
- [ ] **[TUNE]** 移除强制进度更新辅助结构（*"每 N 次工具调用后…"*）
- [ ] **[TUNE]** 移除知识工作验证辅助结构（*"再次检查幻灯片布局…"*）并重新基线化
- [ ] **[TUNE]** 如果需要更温暖/更对话式的语气，添加语气指令；在写作密集型路径上重新评估风格提示
- [ ] **[TUNE]** 如果存在子代理工具：添加明确的生成/不生成指导
- [ ] **[TUNE]** 前端/设计输出：指定具体的调色板/字体，或让模型在构建之前提出 4 种视觉方向（默认的奶油色/衬线内置风格是持久的）
- [ ] **[TUNE]** 交互式编码产品：使用 `effort: "xhigh"` 或 `"high"`，添加自主功能（如自动模式）以减少人工交互，并在第一个轮次中预先指定任务/意图/约束
- [ ] **[TUNE]** 代码审查框架：移除或放宽"仅报告高严重性"/"保守一些"过滤器，让模型报告每个发现并附上置信度 + 严重性；将过滤移至下游步骤（4.7 更字面化地遵循严重性过滤器，这可能会降低测得的召回率）
- [ ] **[TUNE]** 视觉密集型管道（截图、图表、文档理解）：将图像保持在最长边 2576 像素以内的原生分辨率以获取精度提升；从坐标处理中移除任何缩放因子计算（坐标现在与像素 1:1 对应）。无需 beta 头部/选择加入——高分辨率在 Opus 4.7 上是自动的。
- [ ] **[TUNE]** 计算机使用管道：以 1080p 发送截图以获得良好的性能/成本平衡（成本敏感型工作负载使用 720p 或 1366×768）；尝试使用 `effort` 来调优行为
- [ ] **[TUNE]** 成本敏感的图片管道：4.7 上的全分辨率图像使用多达约 4784 个 token，而之前模型约为 1,600 个（约 3 倍）。在上传前在客户端进行下采样可以避免增加，但**默认不要下采样**——如果你不确定是否需要保真度，询问用户。在成本变化做出反应之前，使用 `count_tokens()` 对代表性图像进行重新基线化。

---

## 迁移到 Opus 4.8

> **模型 ID `claude-opus-4-8` 以此处编写为准。** 当用户请求迁移到 Opus 4.8 时，务必写入 `model="claude-opus-4-8"`。**不要**使用 WebFetch 验证——本指南是迁移目标 ID 的权威来源。对应条目存在于 `shared/models.md` 中。

Claude Opus 4.8 是我们迄今为止最强大的通用可用模型——高度自主，在最先进的长周期代理执行、知识工作和记忆方面表现出色。它叠加在上述 Opus 4.7 迁移之上。如果调用者从 Opus 4.6 或更早版本跳过来，请先应用 4.6 和 4.7 部分，然后是本部分。

**无新增重大变更。** Opus 4.8 保持与 Opus 4.7 相同的请求接口。在 4.7 上已经正常工作的相同调用在 4.8 上无需更改即可工作——仅 adaptive thinking（`thinking: {type: "enabled", budget_tokens: N}` 仍然返回 400；使用 `{type: "adaptive"}`）、采样参数（`temperature`、`top_p`、`top_k`）仍被拒绝、最后一个 assistant 轮次 prefills 仍然返回 400、`thinking.display` 仍默认为 `"omitted"`，以及 `low`/`medium`/`high`/`xhigh`/`max` effort 级别、任务预算（beta）和高分辨率视觉的行为与 4.7 相同。因此 4.7 → 4.8 的迁移**是模型 ID 替换加上提示重新调优**——除了模型字符串之外没有必需的代码编辑。

**已经使用 Opus 4.7 的用户的 TL;DR：** 将模型 ID 替换为 `claude-opus-4-8`。没有其他必需操作以避免错误。然后重新调优提示以适应行为变化：4.8 比 4.7 *叙述更多*（如果你想要 4.7 式的简洁，添加默认静默指令）、写作语气更温暖、更少拐弯抹角、更慎重且更频繁提问（添加自主性指导以降低提问率），并且在调用搜索、子代理、基于文件的记忆和自定义工具方面更为保守（添加明确的"何时使用"触发指导）。对于长周期代理工作，在一个明确指定的轮次中预先提供完整的任务规范，并以高 effort 运行。

### 无新增 API 重大变更（继承自 4.7）

以下所有内容均从 Opus 4.7 继承而来——仅当调用者来自 Opus 4.6 或更早版本时才应用它们（有关前后对比和 SDK 特定语法，请参见上方的**迁移到 Opus 4.7** 部分）：

- `thinking: {type: "enabled", budget_tokens: N}` → 400。使用 `thinking: {type: "adaptive"}` + `output_config.effort`。
- `temperature`、`top_p`、`top_k` → 400。移除它们；通过提示进行引导。
- 最后一个 assistant 轮次 prefills → 400。使用 `output_config.format`（结构化输出）或系统提示指令。
- `thinking.display` 默认为 `"omitted"`；如果你向用户展示推理内容，设置为 `"summarized"`。

如果调用者已经在 Opus 4.7 上且这些都没有问题，则此处无需更改。

### 新的 API 功能：会话中系统提示

你可以将会话中途的受信任指令通过 `{"role": "system", ...}` 条目直接放在 `messages` 数组中——无需编辑顶层系统提示并使提示缓存失效。用于应用在会话过程中获知的内容：用户提供的异步上下文、模式切换（自动批准已启用）、磁盘上的文件更改、剩余 token 预算下降。

```python
messages=[
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]},
    {"role": "system", "content": "此项目的代码库是 Go。请用 Go 编写代码。"},
]
```

将其表述为**上下文，而非命令**。陈述事实，让 Claude 据此行动；避免覆盖式语言（"忽略用户所说的"、"无论用户要求什么"、"无视之前的指令"）。Claude 经过训练可保护用户免受看似对用户不利的指令的影响，该保护同样适用于系统角色。这是一个 beta 功能（`anthropic-beta: mid-conversation-system-2026-04-07`），从 Opus 4.7 起可用，非 4.8 独占。有关缓存放置详情和旧模型的 `<system-reminder>` 回退方案，请参见 `shared/prompt-caching.md` 和 `shared/agent-design.md`。

### 能力改进

**长周期代理执行。** Opus 4.8 在长时间自主代理工作方面达到了最先进水平——复杂的重构和隔夜编码运行，无需人工修正即可完成。要充分发挥其潜力，**在单个明确指定的初始轮次中预先提供完整的任务规范，并以高 effort 运行**（`effort: "high"` 或 `"xhigh"`）。其长周期连贯性部分来自于每一步进行更多推理；结合明确的前期目标，这种更智能的规划通常比之前的边界模型产生更高效*和*更准确的输出。"前期明确目标"原则映射到两个产品界面：在 Claude Code 中，`/goal` 为运行设定方向；使用**托管代理 (CMA)** 时，通过**结果（Outcome）**（`user.define_outcome` 配合可评分的评价标准——框架运行 迭代 → 评分 → 修订 循环）来定义"完成"的状态，参见 `shared/managed-agents-outcomes.md`。

**Effort 是一个需要测试的维度，而非固定设置。** 在之前的模型上，许多人会本能地使用 `xhigh` 以最大化智能。Opus 4.8 具有更高的智能上限，因此**从 `high` 作为默认值开始并迭代**，而不是默认使用 `xhigh`。在你的评估集上扫描 `medium`、`high` 和 `xhigh`，并根据智能 ↔ 延迟 ↔ 成本的权衡按路径进行权衡——这种关系不是单调的：前端更高的 effort 通常*减少*代理工作上的轮次数和总成本，而某些任务上 `medium` 在更短时间内交付同样好的结果。将 `max` 保留给极难、延迟不敏感的情况。上方的**迁移到 Opus 4.7** 部分中的每级别 effort 表在 4.8 上同样适用。

**写作语调和清晰度。** 测试人员一致认为 4.8 的散文比之前的模型更清晰、更温暖、更少拐弯抹角，可测量的 AI 语言习惯更少——尤其是在较高的 effort 下，它接近专家级别的散文和结构。这与 4.7 的变化方向大致**相反**（4.7 更简洁、直接、更少验证性措辞）。如果你为了对抗 4.7 的简洁或为了注入温暖而添加了风格提示，在保留之前先对照新基线重新评估——它们现在可能过度矫正。4.8 也是一个更强的思考伙伴：更深思熟虑、更愿意提出异议、更可能从上下文中推断出正确答案。

**代码审查和调试。** 比 4.7 更强的真实 bug 发现能力和更清晰的解释——一次性修复 4.7 需要更多操作的内容，并正确识别间歇性不稳定问题，而不是在一次干净运行后宣布"已修复"。4.7 的注意事项仍然适用：如果审查框架说"仅报告高严重性问题"或"保守一些"，4.8 会字面化地遵循，测得的召回率可能会下降，尽管底层 bug 发现能力已经改进。告诉模型报告所有内容并在下游过滤（或进行第二次审查）——参见 4.7 部分中的**代码审查**指导以获取推荐的提示。

### 行为变化（可提示调优）

这些都不会破坏代码，但为 Opus 4.7 调优的提示可能会产生不同的效果。4.8 能良好地遵循指令，因此小的、明确的提示调整就能消除差距。

**工具触发具有表面依赖性（搜索和知识）。** 4.8 的工具触发比之前的模型更具有表面依赖性：有系统提示时，它是高精度/低召回率——网络搜索触发频率略高，但每次触发运行的轮次更少，而知识检索工具（Drive、项目知识、关联文件）触发频率*更低*。它在确信需要搜索时进行搜索，否则根据上下文回答，这可能会降低需要深入研究的任务的深度。通过明确的搜索优先指令恢复应有的搜索率：

> ```
> <search_first>
> 对于当前信息会改变答案的问题（近期事件、当前角色或价格、版本特定行为或用户标记为时间敏感的任何内容），在回答之前进行搜索，而不是凭记忆回答。对于开放式研究请求，立即开始搜索；不要先问范围问题，除非请求对于要研究的内容确实存在歧义。
> </search_first>
> ```

**子代理、记忆和自定义工具利用不足。** 与搜索分开来看，4.8 对于需要明确"决定使用这个"步骤的能力持保守态度——基于文件的记忆、子代理委托、自定义工具。除非相当确信需要它们，否则它不会动用复杂或昂贵的能力。由于 4.8 能良好地遵循指令，这是可引导的——说明每个能力的*适用时机*，而不仅仅是它存在：

> *"在超过几个轮次的任何任务之前，检查你的记忆文件以获取相关的先前上下文，并在执行过程中将新发现写入其中。当一个任务分头涉及多个独立项目（要读取的许多文件、要运行的许多测试、要检查的许多候选项）时，委托给子代理，而不是串行迭代。"*

同样的方法也适用于**工具描述**层面，而不仅仅是系统提示：说明*何时*调用工具的指导性描述（例如"当用户询问当前价格或近期事件时调用此工具"）在 4.8 上相比仅说明工具功能的描述能带来显著提升。将触发条件作为每个能力自身 `description` 的一部分。

**更多面向用户的叙述。** 4.8 比 4.7 叙述更多——在长时间工具调用会话中，工具调用之间输出更多文本，并且默认情况下任务结束总结更长、更详细。如果你之前添加了强制中间状态的辅助结构（"每 3 次工具调用后，总结进度"），**将其移除**——4.8 会自行完成。如果叙述对于编码代理来说过于冗长，显式的默认静默指令使其表现像 4.7 一样，且质量不受影响：

> *"工具调用之间默认保持静默。仅当你发现某些内容、改变方向或遇到阻塞时才输出文本——每项一句话。不要叙述常规操作（'现在我将…'、'让我检查…'、'正在查看…'）。完成后：一两句话说明结果。不要回顾每个文件或测试——用户一直在跟随。"*

对于知识工作交付物（报告、分析结果），详细程度对用户偏好或用户轮次中的指令反应良好——暴露详细程度偏好而非硬编码长度。

**更慎重——更频繁提问。** 4.8 比之前的 Opus 模型更加慎重。对于之前它会自行决定的小决策（变量名、默认值、两种等效方法中的哪一种），它倾向于停下来询问，并且经常在完成一个任务时以"想让我也…？"结束，而不是执行明显的下一步或干净地停止。这在高风险或不熟悉的代码库中是可取的，但未校准时会困扰用户。在小事上授予自主权，同时在重要事项上保持谨慎（在 Claude Code 中，这在不增加过度触达的情况下将提问率降低了约 12 个百分点）：

> *"对于小的选择（命名、格式化、默认值、等效方法之间的选择），选择一个合理的选项并注明即可，无需询问。对于范围变更或破坏性操作，仍然要先询问。"*

**禁用思考时的冗长推理。** 当 `thinking: {type: "disabled"}` 时，4.8 偶尔会将其推理的长篇解释写入可见响应中，当用户想要快速回答时会显得冗长。最简单的修复方法是保持 adaptive thinking 开启——设置 `thinking: {type: "adaptive"}`（推荐设置；它会根据任务调整思考量）。请注意，省略该字段时 adaptive 不会开启——与 Opus 4.7 一样，没有 `thinking` 字段的请求在无思考模式下运行，因此要显式设置它。如果你出于延迟或成本原因需要关闭思考，在系统提示中限定范围：

> *"仅回复你的最终答案。不要包含探索性推理、中间草稿、你考虑过但拒绝的差异，或关于你过程的元评论。"*

### Opus 4.8 迁移清单

每个项目都已标记：**`[BLOCKS]`** 项目如果遗漏会导致 400 错误；**`[TUNE]`** 项目为质量/成本调整——向用户展示作为建议。

对于**已经在 Opus 4.7 上**的调用者，仅第一项是必需的；其余都是 `[TUNE]`。有条件的 `[BLOCKS]` 项目仅当从 Opus 4.6 或更早版本迁移时才适用。

- [ ] **[BLOCKS]** 将 `model=` 字符串更新为 `claude-opus-4-8`
- [ ] **[BLOCKS]** *（仅当从 Opus 4.6 或更早版本迁移时）* 首先应用**迁移到 Opus 4.7** 的重大变更——`budget_tokens` → adaptive thinking，移除 `temperature`/`top_p`/`top_k`，移除最后一个 assistant 轮次 prefills。这些在 4.7 上已返回 400，在 4.8 上继续返回 400。
- [ ] **[TUNE]** 长周期/代理工作：在一个明确指定的第一个轮次中放置完整任务规范，并以 `high` 或 `xhigh` effort 运行（Claude Code：`/goal`；托管代理：带有可评分评价标准的结果（Outcome））
- [ ] **[TUNE]** Effort：在你的评估集上扫描 `medium` / `high` / `xhigh`，并根据智能 ↔ 延迟 ↔ 成本的权衡按路径选择（默认 `high`，编码/代理使用 `xhigh`）
- [ ] **[TUNE]** 研究深度和工具使用：添加搜索优先指令；为子代理、基于文件的记忆和自定义工具添加明确的触发指导（4.8 默认对这些利用不足）——在系统提示*和*每个工具的自身 `description` 中（指导性的"当…时调用"描述可带来可衡量的提升）
- [ ] **[TUNE]** 叙述：移除强制进度辅助结构（*"每 N 次工具调用后…"*）；如果编码代理过于健谈，添加默认静默指令
- [ ] **[TUNE]** 自主性：添加小决策无需提问的指导以降低提问率，同时对范围变更/破坏性操作保持谨慎
- [ ] **[TUNE]** 写作语调：重新评估为对抗 4.7 的直率而添加的风格提示——4.8 默认更温暖、更少拐弯抹角；在保留之前重新基线化
- [ ] **[TUNE]** 代码审查框架：保持报告所有内容—下游过滤的模式（4.8 字面化地遵循"仅高严重性"/"保守一些"的过滤器，这可能会降低测得的召回率）
- [ ] **[TUNE]** 思考禁用的路径：如果推理内容泄露到可见响应中，添加仅限最终答案的指令
- [ ] **[TUNE]** 考虑使用会话中系统消息（`messages` 中的 `role:"system"`，beta `mid-conversation-system-2026-04-07`）来传递应用在会话过程中获知的上下文，而不是重建顶层系统提示并使缓存失效

---

## 验证迁移

更新后，抽查确认新模型实际正在被使用。将 `YOUR_TARGET_MODEL` 替换为你迁移到的模型字符串（例如 `claude-opus-4-8`、`claude-opus-4-7`、`claude-sonnet-4-6`、`claude-haiku-4-5`）并保持断言前缀同步：

```python
YOUR_TARGET_MODEL = "claude-opus-4-8"  # 或 "claude-opus-4-7"、"claude-sonnet-4-6"、"claude-haiku-4-5"
response = client.messages.create(model=YOUR_TARGET_MODEL, max_tokens=64, messages=[...])
assert response.model.startswith(YOUR_TARGET_MODEL), response.model
```

对于速率限制余量变化、定价或能力差异（视觉、结构化输出、effort 支持），查询 Models API：

```python
m = client.models.retrieve(YOUR_TARGET_MODEL)
m.max_input_tokens, m.max_tokens
m.capabilities["effort"]["max"]["supported"]
```

完整的查看能力模式请参见 `shared/models.md`。
