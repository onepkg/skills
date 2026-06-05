# 工具使用概念

本文档涵盖了使用 Claude API 进行工具使用的概念基础。有关特定语言的代码示例，请参阅 `python/`、`typescript/` 或其他语言文件夹。有关暴露哪些工具的决策启发式、如何在长时间运行的代理中管理上下文以及缓存策略，请参阅 `agent-design.md`。

## 用户定义工具

### 工具定义结构

> **注意：** 使用 Tool Runner（测试版）时，工具模式会根据您的函数签名（Python）、Zod 模式（TypeScript）、带注解的类（Java）、`jsonschema` 结构体标签（Go）或 `BaseTool` 子类（Ruby）自动生成。下面的原始 JSON 模式格式适用于手动方式——包括 PHP 的 `BetaRunnableTool`，它将运行闭包包裹在手动编写的模式中——或未提供工具运行器的 SDK。

每个工具需要名称、描述及其输入的 JSON Schema：

```json
{
  "name": "get_weather",
  "description": "Get current weather for a location",
  "input_schema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "City and state, e.g., San Francisco, CA"
      },
      "unit": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "Temperature unit"
      }
    },
    "required": ["location"]
  }
}
```

**工具定义的最佳实践：**

- 使用清晰、描述性的名称（例如：`get_weather`、`search_database`、`send_email`）
- 编写详细的描述——Claude 使用这些描述来决定何时使用该工具。要 **明确说明 *何时* 调用它**，而不仅仅是它做什么（例如："当用户询问当前价格或近期事件时调用此工具"）。在最近的 Opus 模型上，调用工具更加保守，描述中的触发条件在调用率方面带来了可衡量的提升。
- 为每个属性包含描述
- 对具有固定值集合的参数使用 `enum`
- 在 `required` 中标记真正必需的参数；其他参数设为可选并带有默认值

---

### 工具选择选项

控制 Claude 何时使用工具：

| 值                                | 行为                                      |
| --------------------------------- | --------------------------------------------- |
| `{"type": "auto"}`                | Claude 决定是否使用工具（默认） |
| `{"type": "any"}`                 | Claude 必须使用至少一个工具             |
| `{"type": "tool", "name": "..."}` | Claude 必须使用指定的工具            |
| `{"type": "none"}`                | Claude 不能使用工具                       |

任何 `tool_choice` 值也可以包含 `"disable_parallel_tool_use": true`，以强制 Claude 每次响应最多使用一个工具。默认情况下，Claude 可以在单次响应中请求多个工具调用。

---

### Tool Runner 与手动循环

**Tool Runner（推荐）：** SDK 的工具运行器自动处理代理循环——它调用 API、检测工具使用请求、执行您的工具函数、将结果反馈给 Claude，并重复直到 Claude 停止调用工具。可在 Python、TypeScript、Java、Go、Ruby 和 PHP SDK 中使用（测试版）。Python SDK 还提供了 MCP 转换辅助函数（`anthropic.lib.tools.mcp`），用于将 MCP 工具、提示和资源转换为与工具运行器一起使用——详情请参阅 `python/claude-api/tool-use.md`。

**手动代理循环：** 当需要对循环进行精细控制时使用（例如：自定义日志记录、条件工具执行、人机协同审批）。循环直到 `stop_reason == "end_turn"`，始终追加完整的 `response.content` 以保留 `tool_use` 块，并确保每个 `tool_result` 包含匹配的 `tool_use_id`。

**服务端工具的停止原因：** 使用服务端工具（代码执行、网络搜索等）时，API 运行一个服务端采样循环。如果此循环达到其默认限制 10 次迭代，响应将包含 `stop_reason: "pause_turn"`。要继续，重新发送用户消息和助手响应并发出另一个 API 请求——服务端将从中断处继续。**不要**添加额外的用户消息如"继续。"——API 会检测尾部的 `server_tool_use` 块并知道自动恢复。

```python
# Handle pause_turn in your agentic loop
if response.stop_reason == "pause_turn":
    messages = [
        {"role": "user", "content": user_query},
        {"role": "assistant", "content": response.content},
    ]
    # Make another API request — server resumes automatically
    response = client.messages.create(
        model="claude-opus-4-8", messages=messages, tools=tools
    )
```

设置 `max_continuations` 限制（例如：5）以防止无限循环。完整指南请参阅：`https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons`

> **安全：** 每当 Claude 请求您的工具函数时，Tool Runner 会自动执行它们。对于具有副作用（发送邮件、修改数据库、金融交易）的工具，请在工具函数内验证输入，并考虑对破坏性操作要求确认。如果在每次工具执行前需要人机协同审批，请使用手动代理循环。

---

### 处理工具结果

当 Claude 使用工具时，响应包含一个 `tool_use` 块。您必须：

1. 使用提供的输入执行工具
2. 将结果通过 `tool_result` 消息发送回来
3. 继续对话

**工具结果中的错误处理：** 当工具执行失败时，设置 `"is_error": true` 并提供包含信息的错误消息。Claude 通常会确认错误，然后尝试不同的方法或要求澄清。

**多个工具调用：** Claude 可以在单次响应中请求多个工具。先处理所有工具再继续——将所有结果通过单条 `user` 消息发送回来。

---

## 服务端工具：代码执行

代码执行工具让 Claude 在安全的沙箱容器中运行代码。与用户定义工具不同，服务端工具在 Anthropic 的基础设施上运行——您无需在客户端执行任何操作。只需包含工具定义，Claude 会处理其余部分。

### 关键信息

- 在隔离的容器中运行（1 CPU、5 GiB RAM、5 GiB 磁盘）
- 无互联网访问（完全沙箱化）
- Python 3.11，预装数据科学库
- 容器可持续 30 天，可在多个请求间重用
- 与网络搜索/网络获取工具一起使用时免费；否则，每个组织每月 1,550 小时免费使用后为 $0.05/小时

### 工具定义

该工具不需要模式——只需在 `tools` 数组中声明：

```json
{
  "type": "code_execution_20260120",
  "name": "code_execution"
}
```

Claude 将自动获得 `bash_code_execution`（运行 shell 命令）和 `text_editor_code_execution`（创建/查看/编辑文件）的访问权限。

### 预装 Python 库

- **数据科学**：pandas、numpy、scipy、scikit-learn、statsmodels
- **可视化**：matplotlib、seaborn
- **文件处理**：openpyxl、xlsxwriter、pillow、pypdf、pdfplumber、python-docx、python-pptx
- **数学**：sympy、mpmath
- **工具**：tqdm、python-dateutil、pytz、sqlite3

额外的包可以通过 `pip install` 在运行时安装。

### 支持上传的文件类型

| 类型   | 扩展名                         |
| ------ | ---------------------------------- |
| 数据   | CSV、Excel (.xlsx/.xls)、JSON、XML |
| 图片 | JPEG、PNG、GIF、WebP               |
| 文本   | .txt、.md、.py、.js 等          |

### 容器重用

跨请求重用容器以保持状态（文件、已安装的包、变量）。从第一个响应中提取 `container_id` 并将其传递给后续请求。

### 响应结构

响应包含交错的文本和工具结果块：

- `text` — Claude 的解释
- `server_tool_use` — Claude 正在执行的操作
- `bash_code_execution_tool_result` — 代码执行输出（检查 `return_code` 以了解成功/失败）
- `text_editor_code_execution_tool_result` — 文件操作结果

> **安全：** 在将下载的文件写入磁盘之前，始终使用 `os.path.basename()` / `path.basename()` 对文件名进行清理，以防止路径遍历攻击。将文件写入专用输出目录。

---

## 服务端工具：网络搜索和网络获取

网络搜索和网络获取让 Claude 搜索网络并检索页面内容。它们在服务端运行——只需包含工具定义，Claude 会自动处理查询、获取和结果处理。

### 工具定义

```json
[
  { "type": "web_search_20260209", "name": "web_search" },
  { "type": "web_fetch_20260209", "name": "web_fetch" }
]
```

### 动态过滤（Opus 4.8 / Opus 4.7 / Opus 4.6 / Sonnet 4.6）

`web_search_20260209` 和 `web_fetch_20260209` 版本支持**动态过滤**——Claude 编写并执行代码来过滤搜索结果，在它们进入上下文窗口之前，从而提高准确性和 Token 效率。动态过滤内置于这些工具版本中并自动激活；您无需单独声明 `code_execution` 工具或传递任何测试版标头。

```json
{
  "tools": [
    { "type": "web_search_20260209", "name": "web_search" },
    { "type": "web_fetch_20260209", "name": "web_fetch" }
  ]
}
```

无动态过滤的情况下，之前的 `web_search_20250305` 版本也可用。

> **注意：** 仅在您的应用程序需要独立于网络搜索的代码执行用于自身目的（数据分析、文件处理、可视化）时，才包含独立的 `code_execution` 工具。将其与 `_20260209` 网络工具一起包含会创建第二个执行环境，这可能会混淆模型。

---

## 服务端工具：编程式工具调用

在标准工具使用中，每次工具调用都是一次往返：Claude 调用，结果进入 Claude 的上下文，Claude 进行推理，然后调用下一个工具。链式调用会累积延迟和 Token——这些中间数据大部分不再需要。

编程式工具调用让 Claude 将这些调用组合成一个脚本。该脚本在代码执行容器中运行；当它调用工具时，容器暂停，调用执行，结果返回到正在运行的代码（而不是 Claude 的上下文）。脚本使用正常的控制流处理结果。只有最终输出返回给 Claude。当链式调用多个工具或中间结果很大且需要在到达上下文窗口之前进行过滤时，请使用此功能。

完整文档请使用 WebFetch：

- URL: `https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling`

---

## 服务端工具：工具搜索

工具搜索工具让 Claude 从大型库中动态发现工具，而无需将所有定义加载到上下文窗口中。当您有很多工具但只有少数与给定请求相关时使用。发现的工具模式会追加到请求中，而不是替换——这保留了提示缓存（请参阅 `agent-design.md` §代理缓存）。

完整文档请使用 WebFetch：

- URL: `https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool`

---

## 技能

技能将特定任务的指令打包，Claude 仅在相关时加载这些指令。每个技能是一个包含 `SKILL.md` 文件的文件夹。技能的简短描述默认存在于上下文中；Claude 在当前任务需要时读取完整文件。使用技能可以将专门的指令保留在基础系统提示之外，同时不失去可发现性。

完整文档请使用 WebFetch：

- URL: `https://platform.claude.com/docs/en/agents-and-tools/skills`

---

## 工具使用示例

您可以直接在工具定义中提供示例工具调用，以演示使用模式并减少参数错误。这有助于 Claude 理解如何正确格式化工具输入，特别是对于具有复杂模式的工具。

完整文档请使用 WebFetch：

- URL: `https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use`

---

## 服务端工具：计算机使用

计算机使用让 Claude 与桌面环境交互（截图、鼠标、键盘）。它可以是 Anthropic 托管的（服务端，类似于代码执行）或自托管的（您提供环境并在客户端执行操作）。

完整文档请使用 WebFetch：

- URL: `https://platform.claude.com/docs/en/agents-and-tools/computer-use/overview`

---

## 上下文编辑

上下文编辑在长时间运行的代理累积对话轮次时，从转录中清除过时的工具结果和思考块。与压缩（进行总结）不同，上下文编辑进行修剪——清除的内容被移除，而不是替换。当旧的工具输出不再相关且您希望在保持转录精简的同时不丢失对话结构时使用此功能。清除阈值是可配置的。

完整文档请使用 WebFetch：

- URL: `https://platform.claude.com/docs/en/build-with-claude/context-editing`

---

## 客户端工具：记忆

记忆工具使 Claude 能够通过记忆文件目录跨对话存储和检索信息。Claude 可以创建、读取、更新和删除跨会话持续存在的文件。

### 关键信息

- 客户端工具——您通过自己的实现控制存储
- 支持的命令：`view`、`create`、`str_replace`、`insert`、`delete`、`rename`
- 在 `/memories` 目录中的文件上操作
- Python、TypeScript 和 Java SDK 提供了用于实现记忆后端的辅助类/函数

> **安全：** 切勿在记忆文件中存储 API 密钥、密码、Token 或其他机密信息。谨慎处理个人身份信息（PII）——在持久化用户数据之前检查数据隐私法规（GDPR、CCPA）。参考实现没有内置的访问控制；在多用户系统中，请在工具处理程序中实现每个用户的记忆目录和认证。

有关完整的实现示例，请使用 WebFetch：

- 文档：`https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool.md`

---

## 结构化输出

结构化输出约束 Claude 的响应以遵循特定的 JSON Schema，保证有效、可解析的输出。这不是一个单独的工具——它增强了 Messages API 响应格式和/或工具参数验证。

提供两个功能：

- **JSON 输出**（`output_config.format`）：控制 Claude 的响应格式
- **严格的工具使用**（`strict: true`）：保证有效的工具参数模式

**支持的模型：** Claude Opus 4.8、Claude Sonnet 4.6 和 Claude Haiku 4.5。旧版模型（Claude Opus 4.5、Claude Opus 4.1）也支持结构化输出。

> **推荐：** 使用 `client.messages.parse()`，它会自动根据您的模式验证响应。直接使用 `messages.create()` 时，请使用 `output_config: {format: {...}}`。某些 SDK 方法（例如：`.parse()`）也接受 `output_format` 便捷参数，但 `output_config.format` 是规范的 API 级别参数。

### JSON Schema 限制

**支持：**

- 基本类型：object、array、string、integer、number、boolean、null
- `enum`、`const`、`anyOf`、`allOf`、`$ref`/`$def`
- 字符串格式：`date-time`、`time`、`date`、`duration`、`email`、`hostname`、`uri`、`ipv4`、`ipv6`、`uuid`
- `additionalProperties: false`（所有对象必需）

**不支持：**

- 递归模式
- 数值约束（`minimum`、`maximum`、`multipleOf`）
- 字符串约束（`minLength`、`maxLength`）
- 复杂数组约束
- 设置为 `false` 以外的 `additionalProperties`

Python 和 TypeScript SDK 通过从发送至 API 的模式中移除不支持的约束并在客户端进行验证，自动处理不支持的约束。

### 重要说明

- **首次请求延迟**：新模式会产生一次性编译成本。后续使用相同模式的请求将使用 24 小时缓存。
- **拒绝响应**：如果 Claude 因安全原因拒绝（`stop_reason: "refusal"`），输出可能与您的模式不匹配。
- **Token 限制**：如果 `stop_reason: "max_tokens"`，输出可能不完整。请增加 `max_tokens`。
- **不兼容**：引用（返回 400 错误）、消息预填充。
- **兼容**：批量 API、流式传输、Token 计数、扩展思考。

---

## 有效使用工具的提示

1. **提供详细的描述**：Claude 在很大程度上依赖描述来理解何时以及如何使用工具
2. **使用具体的工具名称**：`get_current_weather` 优于 `weather`
3. **验证输入**：在执行前始终验证工具输入
4. **优雅地处理错误**：返回包含信息的错误消息，以便 Claude 能够适应
5. **限制工具数量**：过多的工具可能会混淆模型——保持集合集中
6. **测试工具交互**：验证 Claude 在各种场景中正确使用工具

有关详细的工具使用文档，请使用 WebFetch：

- URL: `https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview`
