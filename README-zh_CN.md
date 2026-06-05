> **注意：** 本仓库包含 Anthropic 为 Claude 实现的 skills。有关 Agent Skills 标准的信息，请参阅 [agentskills.io](http://agentskills.io)。

[![skills.sh](https://skills.sh/b/anthropics/skills)](https://skills.sh/anthropics/skills)

# Skills

Skills 是指令、脚本和资源的文件夹集合，Claude 会动态加载它们以提高在特定任务上的性能。Skills 教导 Claude 如何以可重复的方式完成特定任务，无论是按照公司的品牌指南创建文档、使用组织的特定工作流程分析数据，还是自动化个人任务。

更多信息，请查看：
- [什么是 skills？](https://support.claude.com/en/articles/12512176-what-are-skills)
- [在 Claude 中使用 skills](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
- [如何创建自定义 skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)
- [使用 Agent Skills 为现实世界的代理配备能力](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

# 关于本仓库

本仓库包含的 skills 展示了 Claude 的 skills 系统能够实现的功能。这些技能涵盖了从创意应用（艺术、音乐、设计）到技术任务（Web 应用测试、MCP 服务器生成）再到企业工作流（通信、品牌等）的各种场景。

每个 skill 都自包含在其自己的文件夹中，其中包含一个 `SKILL.md` 文件，该文件包含了 Claude 使用的指令和元数据。浏览这些 skills 可以为您的 own skills 获取灵感，或了解不同的模式和方法。

本仓库中的许多 skills 都是开源的（Apache 2.0）。我们还在 [`skills/docx`](./skills/docx)、[`skills/pdf`](./skills/pdf)、[`skills/pptx`](./skills/pptx) 和 [`skills/xlsx`](./skills/xlsx) 子文件夹中包含了支持 [Claude 文档功能](https://www.anthropic.com/news/create-files) 的文档创建和编辑 skills。这些是源代码可用的，但不是开源的，但我们希望与开发者分享这些内容，作为在生产 AI 应用中积极使用的更复杂 skills 的参考。

## 免责声明

**这些 skills 仅用于演示和教育目的。** 虽然 Claude 中可能提供其中一些功能，但您从 Claude 获得的实现和行为可能与这些 skills 中显示的不同。这些 skills 旨在说明模式和可能性。在将 skills 用于关键任务之前，请务必在您自己的环境中进行全面测试。

# Skill 集合
- [./skills](./skills)：Creative & Design、Development & Technical、Enterprise & Communication 和 Document Skills 的 skill 示例
- [./spec](./spec)：Agent Skills 规范
- [./template](./template)：Skill 模板

# 在 Claude Code、Claude.ai 和 API 中试用

## Claude Code

您可以通过在 Claude Code 中运行以下命令，将此仓库注册为 Claude Code 插件市场：
```
/plugin marketplace add anthropics/skills
```

然后，安装特定的 skill 集合：
1. 选择 `Browse and install plugins`
2. 选择 `anthropic-agent-skills`
3. 选择 `document-skills` 或 `example-skills`
4. 选择 `Install now`

或者，直接通过以下方式安装任一插件：
```
/plugin install document-skills@anthropic-agent-skills
/plugin install example-skills@anthropic-agent-skills
```

安装插件后，您可以通过提及它来使用 skill。例如，如果您从市场安装了 `document-skills` 插件，您可以要求 Claude Code 执行类似的操作："Use the PDF skill to extract the form fields from `path/to/some-file.pdf`"

## Claude.ai

这些示例 skills 都已经在 Claude.ai 的付费计划中可用。

要使用此仓库中的任何 skill 或上传自定义 skills，请按照 [在 Claude 中使用 skills](https://support.claude.com/en/articles/12512180-using-skills-in-claude#h_a4222fa77b) 中的说明操作。

## Claude API

您可以通过 Claude API 使用 Anthropic 的预构建 skills 并上传自定义 skills。有关更多信息，请参阅 [Skills API 快速入门](https://docs.claude.com/en/api/skills-guide#creating-a-skill)。

# 创建基础 Skill

Skills 的创建非常简单 - 只需一个包含 `SKILL.md` 文件的文件夹，该文件包含 YAML frontmatter 和指令。您可以使用本仓库中的 **template-skill** 作为起点：

```markdown
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[在此处添加 Claude 在此 skill 激活时将遵循的指令]

## 示例
- 示例用法 1
- 示例用法 2

## 指南
- 指南 1
- 指南 2
```

Frontmatter 只需要两个字段：
- `name` - skill 的唯一标识符（小写，用连字符代替空格）
- `description` - 对 skill 功能和使用时机的完整描述

下面的 markdown 内容包含 Claude 将遵循的指令、示例和指南。有关更多详细信息，请参阅 [如何创建自定义 skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)。

# 合作伙伴 Skills

Skills 是让 Claude 更好地掌握使用特定软件的绝佳方式。当我们看到合作伙伴提供的出色 skill 示例时，我们可能会在此处突出显示其中一些：

- **Notion** - [Notion Skills for Claude](https://www.notion.so/notiondevs/Notion-Skills-for-Claude-28da4445d27180c7af1df7d8615723d0)
