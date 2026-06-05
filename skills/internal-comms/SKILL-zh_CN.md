---
name: internal-comms
description: 一套资源，帮助我编写各种内部沟通内容，使用公司喜欢的格式。当被要求编写某种内部沟通内容（状态报告、领导层更新、3P 更新、公司新闻通讯、FAQ、事件报告、项目更新等）时，Claude 应使用此技能。
license: Complete terms in LICENSE.txt
---

## 何时使用此技能

要编写内部沟通内容，请为此技能用于：
- 3P 更新（Progress、Plans、Problems）
- 公司新闻通讯
- FAQ 回复
- 状态报告
- 领导层更新
- 项目更新
- 事件报告

## 如何使用此技能

要编写任何内部沟通内容：

1. **从请求中识别沟通类型**
2. **从 `examples/` 目录加载适当的指南文件**：
    - `examples/3p-updates.md` - 用于 Progress/Plans/Problems 团队更新
    - `examples/company-newsletter.md` - 用于公司范围的新闻通讯
    - `examples/faq-answers.md` - 用于回答常见问题
    - `examples/general-comms.md` - 用于任何其他不显式匹配上述内容的情况
3. **遵循该文件中的具体说明**以获取格式、语气和内容收集

如果沟通类型与任何现有指南不匹配，请询问澄清或更多关于所需格式的上下文。

## 关键词
3P 更新、公司新闻通讯、公司沟通、每周更新、FAQ、常见问题、更新、内部沟通
