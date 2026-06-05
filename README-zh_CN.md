> **Note:** 本仓库包含 Anthropic 为 Claude 实现的 skills。有关 Agent Skills 标准的信息，请参阅 [agentskills.io](http://agentskills.io)。

[![skills.sh](https://skills.sh/b/anthropics/skills)](https://skills.sh/anthropics/skills)

# Skills
Skills 是指令、脚本和资源的文件夹，Claude 会动态加载它们以提升在专业任务上的表现。Skills 教会 Claude 如何以可重复的方式完成特定任务，无论是根据公司品牌指南创建文档、使用组织的特定工作流分析数据，还是自动化个人任务。

更多信息请查看：
- [什么是 skills？](https://support.claude.com/en/articles/12512176-what-are-skills)
- [在 Claude 中使用 skills](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
- [如何创建自定义 skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)
- [使用 Agent Skills 为现实世界装备智能体](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

# 关于本仓库

本仓库包含了一系列 skills，展示了 Claude 的 skills 系统所能实现的功能。这些 skills 涵盖创意应用（艺术、音乐、设计）、技术任务（测试 Web 应用、MCP 服务器生成）以及企业工作流（通信、品牌推广等）。

每个 skill 都独立存放在各自的文件夹中，包含一个 `SKILL.md` 文件，其中含有 Claude 使用的指令和元数据。浏览这些 skills 可以为您创建自己的 skills 提供灵感，或帮助您理解不同的模式和方法。

本仓库中的许多 skills 都是开源的（Apache 2.0）。我们还在 [`skills/docx`](./skills/docx)、[`skills/pdf`](./skills/pdf)、[`skills/pptx`](./skills/pptx) 和 [`skills/xlsx`](./skills/xlsx) 子文件夹中包含了驱动 [Claude 文档功能](https://www.anthropic.com/news/create-files) 的文档创建与编辑 skills。这些是源代码可用（source-available）但不属于开源，但我们希望与开发者分享这些内容，作为在生产级 AI 应用中积极使用的更复杂 skills 的参考。

## 免责声明

**这些 skills 仅供演示和教育目的。** 虽然其中某些功能可能在 Claude 中可用，但您从 Claude 获得的实现和行为可能与这些 skills 中展示的有所不同。这些 skills 旨在说明各种模式与可能性。在将其用于关键任务之前，请始终在您自己的环境中充分测试这些 skills。

# Skill 分类
- [./skills](./skills): 创意与设计、开发与技术、企业与沟通以及文档技能（Skill）示例
- [./spec](./spec): Agent Skills 规范
- [./template](./template): Skill 模板

# 在 Claude Code、Claude.ai 和 API 中尝试

## Claude Code
您可以通过在 Claude Code 中运行以下命令，将此仓库注册为 Claude Code 插件市场：
```
/plugin marketplace add anthropics/skills
```

然后，要安装特定的 skill 集合：
1. 选择 `Browse and install plugins`
2. 选择 `anthropic-agent-skills`
3. 选择 `document-skills` 或 `example-skills`
4. 选择 `Install now`

或者，直接通过以下命令安装任一插件：
```
/plugin install document-skills@anthropic-agent-skills
/plugin install example-skills@anthropic-agent-skills
```

安装插件后，您只需提及该 skill 即可使用。例如，如果您从市场安装了 `document-skills` 插件，可以要求 Claude Code 执行类似操作："Use the PDF skill to extract the form fields from `path/to/some-file.pdf`"

## Claude.ai

这些示例 skills 在 Claude.ai 上已全部面向付费计划开放。

要使用本仓库中的任何 skill 或上传自定义 skills，请按照 [在 Claude 中使用 skills](https://support.claude.com/en/articles/12512180-using-skills-in-claude#h_a4222fa77b) 中的说明操作。

## Claude API

您可以通过 Claude API 使用 Anthropic 预构建的 skills，并上传自定义 skills。更多信息请参阅 [Skills API 快速入门](https://docs.claude.com/en/api/skills-guide#creating-a-skill)。

# 创建基本 Skill

创建 skills 非常简单——只需要一个文件夹，其中包含一个带有 YAML 前置元数据和指令的 `SKILL.md` 文件。您可以使用本仓库中的 **template-skill** 作为起点：

```markdown
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[Add your instructions here that Claude will follow when this skill is active]

## Examples
- Example usage 1
- Example usage 2

## Guidelines
- Guideline 1
- Guideline 2
```

前置元数据只需要两个字段：
- `name` - 您的 skill 的唯一标识符（小写，空格用连字符代替）
- `description` - 对该 skill 的功能及使用时机的完整描述

下方的 markdown 内容包含 Claude 将遵循的指令、示例和指南。更多详情请参阅 [如何创建自定义 skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)。

# 合作伙伴 Skills

Skills 是教会 Claude 更好地使用特定软件的有效方式。当我们看到合作伙伴提供的优秀示例 skills 时，我们会在此展示其中一些：

- **Notion** - [Notion Skills for Claude](https://www.notion.so/notiondevs/Notion-Skills-for-Claude-28da4445d27180c7af1df7d8615723d0)
