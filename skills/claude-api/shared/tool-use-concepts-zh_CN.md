# 工具使用概念

本文件介绍 Claude API 工具使用的概念基础。有关特定语言的代码示例，请参阅 `python/`、`typescript/` 或其他语言文件夹。有关暴露哪些工具、如何在长期运行的智能体中管理上下文以及缓存策略的决策启发式方法，请参阅 `agent-design.md`。

## 用户定义工具

### 工具定义结构

> **注意：** 使用 Tool Runner（测试版）时，工具架构会自动从您的函数签名（Python）、Zod 架构（TypeScript）、带注解的类（Java）、`jsonschema` 结构标签（Go）或 `BaseTool` 子类（Ruby）生成。下面的原始 JSON Schema 格式适用于手动方法 — 包括 PHP 的 `BetaRunnableTool`，它将运行闭包包装在手写架构周围 — 或适用于没有工具运行器支持的 SDK。

每个工具都需要名称、描述和输入的 JSON Schema：

```json
{
  "name": "get_weather",
  "description": "获取某个位置的当前天气",
  "input_schema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "城市和州，例如 San Francisco, CA"
      },
      "unit": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "温度单位"
      }
    },
    "required": ["location"]
  }
}
```

**工具定义最佳实践：**

- 使用清晰、描述性的名称（例如 `get_weather`、`search_database`、`send_email`）
- 编写详细描述 — Claude 使用这些来决定何时使用工具。**关于*何时*调用它要有规定性**，而不仅仅是它做什么（例如"当用户询问当前价格或最近事件时调用此工具"）。在更保守地使用工具的最新 Opus 模型上，描述中的触发条件在应该调用率上给出可测量的提升。
- 为每个属性包含描述
- 对具有固定值集的参数使用 `enum`
- 在 `required` 中标记真正必需的参数；使其他参数可选并带有默认值

---

### 工具选择选项

控制 Claude 何时使用工具：

| 值                             | 行为                                      |
| ------------------------------ | ----------------------------------------- |
| `{"type": "auto"}`             | Claude 决定是否使用工具（默认）          |
| `{"type": "any"}`              | Claude 必须使用至少一个工具               |
| `{"type": "tool", "name": "..."}` | Claude 必须使用指定的工具               |
| `{"type": "none"}`             | Claude 不能使用工具                       |

任何 `tool_choice` 值还可以包含 `"disable_parallel_tool_use": true` 以强制 Claude 在每个响应中最多使用一个工具。默认情况下，Claude 可能在单个响应中请求多个工具调用。

---

### 工具运行器 vs 手动循环

**工具运行器（推荐）：** SDK 的工具运行器自动处理智能体循环 — 它调用 API、检测工具使用请求、执行您的工具函数、将结果反馈给 Claude 并重复，直到 Claude 停止调用工具。在 Python、TypeScript、Java、Go、Ruby 和 PHP SDK（测试版）中可用。Python SDK 还提供 MCP 转换助手（`anthropic.lib.tools.mcp`）来转换 MCP 工具、提示和资源以与工具运行器一起使用 — 有关详细信息，请参阅 `python/claude-api/tool-use.md`。

**手动智能体循环：** 当您需要对循环进行细粒度控制时使用（例如自定义日志记录、条件工具执行、人机在环批准）。循环直到 `stop_reason == "end_turn"`，始终追加完整的 `response.content` 以保留 tool_use 块，并确保每个 `tool_result` 包含匹配的 `tool_use_id`。

**服务器端工具的停止原因：** 使用服务器端工具（代码执行、网络搜索等）时，API 运行服务器端采样循环。如果此循环达到其 10 次迭代的默认限制，响应将具有 `stop_reason: "pause_turn"`。要继续，请重新发送用户消息和助手响应并发出另一个 API 请求 — 服务器将从中断处继续。不要添加像"继续"这样的额外用户消息 — API 会检测尾随的 `server_tool_use` 块并知道自动恢复。

```python
# 在您的智能体循环中处理 pause_turn
if response.stop_reason == "pause_turn":
    messages = [
        {"role": "user", "content": user_query},
        {"role": "assistant", "content": response.content},
    ]
    # 发出另一个 API 请求 — 服务器自动恢复
    response = client.messages.create(
        model="claude-opus-4-8", messages=messages, tools=tools
    )
```

设置 `max_continuations` 限制（例如 5）以防止无限循环。有关完整指南，请参阅：`https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons`

> **安全性：** 工具运行器每当 Claude 请求时都会自动执行您的工具函数。对于具有副作用的工具（发送电子邮件、修改数据库、金融交易），请在您的工具函数中验证输入并考虑要求对破坏性操作进行确认。如果您需要在每次工具执行前获得人机在环批准，请使用手动智能体循环。

---

### 处理工具结果

当 Claude 使用工具时，响应包含 `tool_use` 块。您必须：

1. 使用提供的输入执行工具
2. 在 `tool_result` 消息中发回结果
3. 继续对话

**工具结果中的错误处理：** 当工具执行失败时，设置 `"is_error": true` 并提供信息性错误消息。Claude 通常会确认错误并尝试不同的方法或要求澄清。

**多个工具调用：** Claude 可以在单个响应中请求多个工具。全部处理后再继续 — 在单个 `user` 消息中发回所有结果。

---

## 服务器端工具：代码执行

代码执行工具让 Claude 在安全的沙箱容器中运行代码。与用户定义的工具不同，服务器端工具在 Anthropic 的基础设施上运行 — 您不需要在客户端执行任何操作。只需包含工具定义，Claude 会处理其余部分。

### 关键事实

- 在隔离容器中运行（1 个 CPU、5 GiB RAM、5 GiB 磁盘）
- 无互联网访问（完全沙箱化）
- Python 3.11，预先安装了数据科学库
- 容器持续 30 天，可以跨请求重用
- 与网络搜索/网络获取工具一起使用时免费；否则每个组织每月 1,550 个免费小时后为 0.05 美元/小时

### 工具定义

该工具不需要架构 — 只需在 `tools` 数组中声明它：

```json
{
  "type": "code_execution_20260120",
  "name": "code_execution"
}
```

Claude 自动获得对 `bash_code_execution`（运行 shell 命令）和 `text_editor_code_execution`（创建/查看/编辑文件）的访问权限。

### 预安装的 Python 库

- **数据科学**：pandas、numpy、scipy、scikit-learn、statsmodels
- **可视化**：matplotlib、seaborn
- **文件处理**：openpyxl、xlsxwriter、pillow、pypdf、pdfplumber、python-docx、python-pptx
- **数学**：sympy、mpmath
- **实用工具**：tqdm、python-dateutil、pytz、sqlite3

可以在运行时通过 `pip install` 安装额外的包。

### 支持上传的文件类型

| 类型   | 扩展名                             |
| ------ | ---------------------------------- |
| 数据   | CSV、Excel (.xlsx/.xls)、JSON、XML |
| 图像   | JPEG、PNG、GIF、WebP               |
| 文本   | .txt、.md、.py、.js 等             |

### 容器重用

跨请求重用容器以维护状态（文件、已安装的包、变量）。从第一个响应中提取 `container_id` 并将其传递给后续请求。

### 响应结构

响应包含交错的文本和工具结果块：

- `text` — Claude 的解释
- `server_tool_use` — Claude 正在做什么
- `bash_code_execution_tool_result` — 代码执行输出（检查 `return_code` 以确定成功/失败）
- `text_editor_code_execution_tool_result` — 文件操作结果

> **安全性：** 在将下载的文件写入磁盘之前，始终使用 `os.path.basename()` / `path.basename()` 清理文件名以防止路径遍历攻击。将文件写入专用的输出目录。

---

## 服务器端工具：网络搜索和网络获取

网络搜索和网络获取让 Claude 搜索网络并检索页面内容。它们在服务器端运行 — 只需包含工具定义，Claude 就会自动处理查询、获取和结果处理。

### 工具定义

```json
[
  { "type": "web_search_20260209", "name": "web_search" },
  { "type": "web_fetch_20260209", "name": "web_fetch" }
]
```

### 动态过滤（Opus 4.8 / Opus 4.7 / Opus 4.6 / Sonnet 4.6）

`web_search_20260209` 和 `web_fetch_20260209` 版本支持**动态过滤** — Claude 编写并执行代码以在搜索结果到达上下文窗口之前过滤它们，提高准确性和令牌效率。动态过滤内置于这些工具版本中并自动激活；您不需要单独声明 `code_execution` 工具或传递任何测试版头。

```json
{
  "tools": [
    { "type": "web_search_20260209", "name": "web_search" },
    { "type": "web_fetch_20260209", "name": "web_fetch" }
  ]
}
```

如果没有动态过滤，也可以使用之前的 `web_search_20250305` 版本。

> **注意：** 仅当您的应用程序需要独立于网络搜索的代码执行（数据分析、文件处理、可视化）时，才包含独立的 `code_execution` 工具。将其与 `_20260209` 网络工具一起包含会创建第二个执行环境，这可能会混淆模型。

---

## 服务器端工具：程序化工具调用

使用标准工具使用时，每个工具调用都是一次往返：Claude 调用，结果进入 Claude 的上下文，Claude 推理，然后调用下一个工具。链式调用会累积延迟和令牌 — 大多数中间数据永远不再需要。

程序化工具调用让 Claude 将这些调用组合成一个脚本。脚本在代码执行容器中运行；当它调用工具时，容器暂停，调用执行，结果返回到正在运行的代码（而不是 Claude 的上下文）。脚本使用正常控制流处理它。只有最终输出返回给 Claude。当链接许多工具调用或中间结果很大且在到达上下文窗口之前应该过滤时，请使用它。

有关完整文档，请使用 WebFetch：

- URL：`https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling`

---

## 服务器端工具：工具搜索

工具搜索工具让 Claude 从大型库中动态发现工具，而无需将所有定义加载到上下文窗口中。当您有许多工具但只有少数工具与任何给定请求相关时，请使用它。发现的工具架构附加到请求，而不是交换进去 — 这保留了提示缓存（请参阅 `agent-design.md` § 智能体缓存）。

有关完整文档，请使用 WebFetch：

- URL：`https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool`

---

## 技能

技能打包特定于任务的指令，Claude 仅在相关时加载。每个技能是一个包含 `SKILL.md` 文件的文件夹。技能的简短描述默认位于上下文中；当当前任务需要时，Claude 读取完整文件。使用技能将专门化指令保留在基础系统提示之外，同时保持可发现性。

有关完整文档，请使用 WebFetch：

- URL：`https://platform.claude.com/docs/en/agents-and-tools/skills`

---

## 工具使用示例

您可以直接在工具定义中提供示例工具调用，以演示使用模式并减少参数错误。这有助于 Claude 了解如何正确格式化工具输入，特别是对于具有复杂架构的工具。

有关完整文档，请使用 WebFetch：

- URL：`https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use`

---

## 服务器端工具：计算机使用

计算机使用让 Claude 与桌面环境交互（屏幕截图、鼠标、键盘）。它可以是 Anthropic 托管的（服务器端，如代码执行）或自托管的（您提供环境并在客户端执行操作）。

有关完整文档，请使用 WebFetch：

- URL：`https://platform.claude.com/docs/en/agents-and-tools/computer-use/overview`

---

## 上下文编辑

随着长期运行的智能体累积轮次，上下文编辑会从转录中清除过时的工具结果和思考块。与压缩（摘要）不同，上下文编辑是修剪 — 清除的内容被移除，而不是被替换。当旧工具输出不再相关并且您希望保持转录精简而不丢失对话结构时，请使用它。清除内容的阈值是可配置的。

有关完整文档，请使用 WebFetch：

- URL：`https://platform.claude.com/docs/en/build-with-claude/context-editing`

---

## 客户端工具：记忆

记忆工具使 Claude 能够通过记忆文件目录跨对话存储和检索信息。Claude 可以创建、读取、更新和删除在会话之间保持不变的文件。

### 关键事实

- 客户端工具 — 您通过实现控制存储
- 支持命令：`view`、`create`、`str_replace`、`insert`、`delete`、`rename`
- 对 `/memories` 目录中的文件进行操作
- Python、TypeScript 和 Java SDK 提供用于实现记忆后端的帮助程序类/函数

> **安全性：** 永远不要在记忆文件中存储 API 密钥、密码、令牌或其他秘密。对个人身份信息（PII）要谨慎 — 在持久化用户数据之前检查数据隐私法规（GDPR、CCPA）。参考实现没有内置访问控制；在多用户系统中，在工具处理程序中实现每用户记忆目录和认证。

有关完整实现示例，请使用 WebFetch：

- 文档：`https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool.md`

---

## 结构化输出

结构化输出约束 Claude 的响应遵循特定的 JSON 架构，保证有效、可解析的输出。这不是一个单独的工具 — 它增强了 Messages API 响应格式和/或工具参数验证。

有两个功能可用：

- **JSON 输出**（`output_config.format`）：控制 Claude 的响应格式
- **严格工具使用**（`strict: true`）：保证有效的工具参数架构

**支持的模型：** Claude Opus 4.8、Claude Sonnet 4.6 和 Claude Haiku 4.5。传统模型（Claude Opus 4.5、Claude Opus 4.1）也支持结构化输出。

> **推荐：** 使用 `client.messages.parse()`，它会自动根据您的架构验证响应。当直接使用 `messages.create()` 时，使用 `output_config: {format: {...}}`。`output_format` 便利参数也被一些 SDK 方法接受（例如 `.parse()`），但 `output_config.format` 是规范的 API 级参数。

### JSON Schema 限制

**支持：**

- 基本类型：object、array、string、integer、number、boolean、null
- `enum`、`const`、`anyOf`、`allOf`、`$ref`/`$def`
- 字符串格式：`date-time`、`time`、`date`、`duration`、`email`、`hostname`、`uri`、`ipv4`、`ipv6`、`uuid`
- `additionalProperties: false`（所有对象都需要）

**不支持：**

- 递归架构
- 数值约束（`minimum`、`maximum`、`multipleOf`）
- 字符串约束（`minLength`、`maxLength`）
- 复杂数组约束
- `additionalProperties` 设置为 `false` 以外的任何值

Python 和 TypeScript SDK 通过从发送到 API 的架构中移除它们并在客户端验证它们来自动处理不支持的约束。

### 重要说明

- **首次请求延迟：** 新架构会产生一次性编译成本。具有相同架构的后续请求使用 24 小时缓存。
- **拒绝：** 如果 Claude 出于安全原因拒绝（`stop_reason: "refusal"`），输出可能与您的架构不匹配。
- **令牌限制：** 如果 `stop_reason: "max_tokens"`，输出可能不完整。增加 `max_tokens`。
- **不兼容：** 引用（返回 400 错误）、消息预填充。
- **兼容：** 批处理 API、流式传输、令牌计数、扩展思考。

---

## 有效工具使用的技巧

1. **提供详细描述：** Claude 严重依赖描述来了解何时以及如何使用工具
2. **使用特定的工具名称：** `get_current_weather` 比 `weather` 更好
3. **验证输入：** 始终在执行前验证工具输入
4. **优雅地处理错误：** 返回信息性错误消息以便 Claude 可以适应
5. **限制工具数量：** 太多工具可能会混淆模型 — 保持集合有针对性
6. **测试工具交互：** 验证 Claude 在各种场景中正确使用工具

有关详细的工具使用文档，请使用 WebFetch：

- URL：`https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview`
