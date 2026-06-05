# 实时文档来源

本文件包含用于从 platform.claude.com 和 Agent SDK 仓库获取最新信息的 WebFetch 网址。当用户需要自缓存内容上次更新以来可能已发生变化的最新数据时，请使用这些网址。

## 何时使用 WebFetch

- 用户明确要求提供"最新"或"当前"信息
- 缓存数据看起来不正确
- 用户询问缓存内容中未涵盖的功能
- 用户需要特定的 API 细节或示例

## Claude API 文档网址

### 模型与定价

| 主题           | 网址                                                                        | 提取提示                                                                 |
| --------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 模型概览 | `https://platform.claude.com/docs/en/about-claude/models/overview.md`        | "提取所有 Claude 模型的当前模型 ID、上下文窗口和定价" |
| 迁移指南 | `https://platform.claude.com/docs/en/about-claude/models/migration-guide.md` | "提取迁移到较新 Claude 模型时的破坏性变更、已弃用参数和按模型的迁移步骤" |
| 定价         | `https://platform.claude.com/docs/en/pricing.md`                             | "提取当前每百万 token 的输入和输出定价"               |

### 核心功能

| 主题             | 网址                                                                          | 提取提示                                                                 |
| ----------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 扩展思考 | `https://platform.claude.com/docs/en/build-with-claude/extended-thinking.md` | "提取扩展思考参数、budget_tokens 要求和使用示例" |
| 自适应思考 | `https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking.md` | "提取自适应思考设置、努力级别和 Claude Opus 4.8 使用示例"         |
| 努力参数  | `https://platform.claude.com/docs/en/build-with-claude/effort.md`            | "提取努力级别、成本-质量权衡以及与思考的交互"        |
| 工具使用          | `https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md`  | "提取工具定义模式、tool_choice 选项和处理工具结果"       |
| 流式传输         | `https://platform.claude.com/docs/en/build-with-claude/streaming.md`         | "提取流式事件类型、SDK 示例和最佳实践"                      |
| 提示缓存    | `https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md`    | "提取 cache_control 用法、定价优势及实现示例"           |

### 媒体与文件

| 主题       | 网址                                                                    | 提取提示                                                 |
| ----------- | ---------------------------------------------------------------------- | --------------------------------------------------------- |
| 视觉      | `https://platform.claude.com/docs/en/build-with-claude/vision.md`      | "提取支持的图像格式、大小限制和代码示例" |
| PDF 支持 | `https://platform.claude.com/docs/en/build-with-claude/pdf-support.md` | "提取 PDF 处理能力、限制和示例"         |

### API 操作

| 主题            | 网址                                                                         | 提取提示                                                                                       |
| ---------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 批处理 | `https://platform.claude.com/docs/en/build-with-claude/batch-processing.md` | "提取批量 API 端点、请求格式和轮询结果"                                  |
| Files API        | `https://platform.claude.com/docs/en/build-with-claude/files.md`            | "提取文件上传、下载及在消息中引用，包括支持的类型和 beta 标头" |
| Token 计数   | `https://platform.claude.com/docs/en/build-with-claude/token-counting.md`   | "提取 token 计数 API 用法和示例"                                                         |
| 速率限制      | `https://platform.claude.com/docs/en/api/rate-limits.md`                    | "提取按层级和模型划分的当前速率限制"                                                         |
| 错误           | `https://platform.claude.com/docs/en/api/errors.md`                         | "提取 HTTP 错误码、含义和重试指南"                                                |

### 工具

| 主题          | 网址                                                                                    | 提取提示                                                                        |
| -------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 代码执行 | `https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool.md` | "提取代码执行工具设置、文件上传、容器复用和响应处理" |
| 计算机使用   | `https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use.md`        | "提取计算机使用工具设置、功能和实现示例"             |
| Bash 工具      | `https://platform.claude.com/docs/en/agents-and-tools/tool-use/bash-tool.md`           | "提取 bash 工具模式、参考实现和安全注意事项"        |
| 文本编辑器    | `https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool.md`    | "提取文本编辑器工具命令、模式和参考实现"                |
| 记忆工具    | `https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool.md`         | "提取记忆工具命令、目录结构和实现模式"         |
| 工具搜索    | `https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool.md`    | "提取工具搜索设置、使用时机和缓存交互"                          |
| 编程式工具调用 | `https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling.md` | "提取 PTC 设置、脚本执行模型和从代码调用工具"    |
| 技能         | `https://platform.claude.com/docs/en/agents-and-tools/skills.md`                       | "提取技能文件夹结构、SKILL.md 格式和加载行为"                  |

### 高级功能

| 主题              | 网址                                                                           | 提取提示                                   |
| ------------------ | ----------------------------------------------------------------------------- | --------------------------------------------------- |
| 结构化输出 | `https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md` | "提取 output_config.format 用法和模式强制"                           |
| 压缩         | `https://platform.claude.com/docs/en/build-with-claude/compaction.md`         | "提取压缩设置、触发配置和带压缩的流式传输"             |
| 上下文编辑    | `https://platform.claude.com/docs/en/build-with-claude/context-editing.md`    | "提取上下文编辑阈值、清除内容及配置"            |
| 引用          | `https://platform.claude.com/docs/en/build-with-claude/citations.md`          | "提取引用格式和实现"        |
| 上下文窗口    | `https://platform.claude.com/docs/en/build-with-claude/context-windows.md`    | "提取上下文窗口大小和 token 管理" |

### 托管代理

当托管代理的绑定、行为或传输层细节未在缓存的 `shared/managed-agents-*.md` 概念文件或 `{lang}/managed-agents/README.md` 中涵盖时，请使用这些网址。

| 主题                 | 网址                                                                              | 提取提示                                                                               |
| --------------------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 概览              | `https://platform.claude.com/docs/en/managed-agents/overview.md`                 | "提取高层架构以及代理/会话/环境/保管库如何协同工作" |
| 快速入门            | `https://platform.claude.com/docs/en/managed-agents/quickstart.md`               | "提取最小端到端代理 → 环境 → 会话 → 流式代码路径"              |
| 代理设置           | `https://platform.claude.com/docs/en/managed-agents/agent-setup.md`              | "提取代理创建/更新/版本列表/归档生命周期和参数"                   |
| 定义成果       | `https://platform.claude.com/docs/en/managed-agents/define-outcomes.md`          | "提取成果定义、评估钩子和成功标准配置"             |
| 会话              | `https://platform.claude.com/docs/en/managed-agents/sessions.md`                 | "提取会话生命周期、状态转换、空闲/已终止语义和恢复规则"    |
| 环境          | `https://platform.claude.com/docs/en/managed-agents/environments.md`             | "提取环境配置（云/网络）、管理端点和复用模型"          |
| 自托管沙箱 | `https://platform.claude.com/docs/en/managed-agents/self-hosted-sandboxes.md`    | "提取 config:{type:self_hosted}、ANTHROPIC_ENVIRONMENT_KEY、EnvironmentWorker.run/run_one、beta_agent_toolset、ant beta:worker poll/run、webhook 驱动唤醒" |
| 自托管沙箱 — 安全 | `https://platform.claude.com/docs/en/managed-agents/self-hosted-sandboxes-security.md` | "提取客户负责的内容（加固、出口流量、密钥保管、信任边界）与 Anthropic 无法执行的操作" |
| 事件和流式传输  | `https://platform.claude.com/docs/en/managed-agents/events-and-streaming.md`     | "提取事件流类型、流优先排序、重连/去重和控制模式"    |
| 工具                 | `https://platform.claude.com/docs/en/managed-agents/tools.md`                    | "提取内置工具集、自定义工具定义和工具结果传输格式"                |
| 文件                 | `https://platform.claude.com/docs/en/managed-agents/files.md`                    | "提取文件上传、挂载路径、会话资源以及列出/下载会话输出"  |
| 权限策略   | `https://platform.claude.com/docs/en/managed-agents/permission-policies.md`      | "提取权限策略类型（允许/拒绝/确认）和按工具配置"                     |
| 多代理           | `https://platform.claude.com/docs/en/managed-agents/multi-agent.md`              | "提取多代理组合模式、子代理调用和结果交接"            |
| 可观测性         | `https://platform.claude.com/docs/en/managed-agents/observability.md`            | "提取托管代理暴露的日志、追踪和使用遥测"                       |
| Webhooks              | `https://platform.claude.com/docs/en/managed-agents/webhooks.md`                 | "提取 webhook 端点注册、HMAC 签名验证、支持的事件类型和投递语义" |
| GitHub                | `https://platform.claude.com/docs/en/managed-agents/github.md`                   | "提取 github_repository 资源结构、多仓库挂载和 token 轮换"             |
| MCP 连接器         | `https://platform.claude.com/docs/en/managed-agents/mcp-connector.md`            | "提取代理上的 MCP 服务器声明与会话时基于保管库的凭证注入"     |
| 保管库                | `https://platform.claude.com/docs/en/managed-agents/vaults.md`                   | "提取保管库创建、凭证添加/轮换、OAuth 刷新结构和归档"                 |
| 技能                | `https://platform.claude.com/docs/en/managed-agents/skills.md`                   | "提取托管代理的技能打包和加载模型"                                  |
| 记忆                | `https://platform.claude.com/docs/en/managed-agents/memory.md`                   | "提取记忆资源结构、作用域和生命周期"                                         |
| 引导            | `https://platform.claude.com/docs/en/managed-agents/onboarding.md`               | "提取首次运行设置、前提条件和账户/区域要求"                      |
| 云容器      | `https://platform.claude.com/docs/en/managed-agents/cloud-containers.md`         | "提取云容器运行时、镜像配置和网络/存储选项"                     |
| 迁移             | `https://platform.claude.com/docs/en/managed-agents/migration.md`                | "提取从早期 API/预览形态到 GA 托管代理的迁移路径"                 |

### Anthropic CLI

`ant` CLI 提供对 Claude API 的终端访问。每个 API 资源都作为子命令公开。它是从版本控制的 YAML 创建代理、环境、会话和其他资源，以及交互式检查响应的一种便捷方式。

| 主题         | 网址                                                     | 提取提示                                                                                  |
| ------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Anthropic CLI | `https://platform.claude.com/docs/en/api/sdks/cli.md`   | "提取 CLI 安装、认证、命令结构以及 beta:agents/environments/sessions 命令" |

---

## Claude API SDK 仓库

当某个绑定（类、方法、命名空间、字段）未在缓存的 `{lang}/` 技能文件或上述托管代理文档中涵盖时，请使用 WebFetch 访问这些仓库。SDK 包含针对 `/v1/agents`、`/v1/sessions`、`/v1/environments` 及相关资源的 beta 托管代理支持 — 在仓库中搜索 `BetaManagedAgents`、`beta.agents`、`beta.sessions` 或该语言的等效命名空间。

| SDK        | 网址                                                      | 提取提示                                                                                                       |
| ---------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Python     | `https://github.com/anthropics/anthropic-sdk-python`     | "提取 beta 托管代理命名空间、类和方法签名（`client.beta.agents`、`client.beta.sessions`）" |
| TypeScript | `https://github.com/anthropics/anthropic-sdk-typescript` | "提取 beta 托管代理命名空间、类和方法签名（`client.beta.agents`、`client.beta.sessions`）" |
| Java       | `https://github.com/anthropics/anthropic-sdk-java`       | "提取 beta 托管代理类、构建器和方法签名（`client.beta().agents()`、`BetaManagedAgents*`）" |
| Go         | `https://github.com/anthropics/anthropic-sdk-go`         | "提取 beta 托管代理类型和方法签名（`client.Beta.Agents`、`BetaManagedAgents*` 事件类型）"      |
| Ruby       | `https://github.com/anthropics/anthropic-sdk-ruby`       | "提取 beta 托管代理方法和参数结构（`client.beta.agents`、`client.beta.sessions`）"               |
| C#         | `https://github.com/anthropics/anthropic-sdk-csharp`     | "提取 beta 托管代理类和方法签名（NuGet 包、`BetaManagedAgents*` 类型）"                 |
| PHP        | `https://github.com/anthropics/anthropic-sdk-php`        | "提取 beta 托管代理类和方法签名（`$client->beta->agents`、`BetaManagedAgents*` 参数）"      |

---

## 备用策略

如果 WebFetch 失败（网络问题、网址已变更）：

1. 使用语言特定文件中的缓存内容（注意缓存日期）
2. 告知用户数据可能已过时
3. 建议用户直接查看 platform.claude.com 或 GitHub 仓库
