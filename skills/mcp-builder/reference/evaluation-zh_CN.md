# MCP 服务器评估指南

## 概述

本文档提供了为 MCP 服务器创建全面评估的指导。评估测试 LLM 是否能够仅使用所提供的工具，有效利用您的 MCP 服务器来回答真实、复杂的问题。

---

## 快速参考

### 评估要求
- 创建 10 个人类可读的问题
- 问题必须是只读的、独立的、非破坏性的
- 每个问题需要多次工具调用（可能数十次）
- 答案必须是单一的、可验证的值
- 答案必须是稳定的（不会随时间变化）

### 输出格式
```xml
<evaluation>
   <qa_pair>
      <question>Your question here</question>
      <answer>Single verifiable answer</answer>
   </qa_pair>
</evaluation>
```

---

## 评估的目的

衡量 MCP 服务器质量的标准，并不在于服务器实现工具的好坏或全面程度，而在于这些实现（输入/输出模式、文档字符串/描述、功能）如何使 LLM 在没有任何其他上下文、且仅能访问 MCP 服务器的情况下，回答真实且困难的问题。

## 评估概述

创建 10 个人类可读的问题，仅需要只读的、独立的、非破坏性的和幂等的操作即可回答。每个问题应具备：
- 真实性
- 清晰简洁
- 无歧义
- 复杂性，可能需要数十次工具调用或步骤
- 可回答为一个单一的、可验证的、您预先确定的值

## 问题编写指南

### 核心要求

1. **问题必须是独立的**
   - 每个问题不应依赖于任何其他问题的答案
   - 不应假设处理其他问题时已执行过写入操作

2. **问题只能要求使用非破坏性和幂等的工具**
   - 不应指示或要求通过修改状态来得出正确答案

3. **问题必须是真实、清晰、简洁且复杂的**
   - 必须要求另一个 LLM 使用多个（可能数十个）工具或步骤来回答

### 复杂性与深度

4. **问题需要深入探索**
   - 考虑需要多个子问题和连续工具调用的多跳问题
   - 每一步都应受益于前序问题中发现的信息

5. **问题可能需要大量分页**
   - 可能需要翻越多个结果页面
   - 可能需要查询旧数据（1-2 年前的）以找到冷门信息
   - 问题必须是困难的

6. **问题需要深刻理解**
   - 而非表面知识
   - 可以将复杂观点设置为需要证据支持的真/假问题
   - 可以采用多项选择形式，让 LLM 搜索不同假设

7. **问题不能通过简单的关键词搜索解决**
   - 不要包含目标内容中的特定关键词
   - 使用同义词、相关概念或释义
   - 需要多次搜索、分析多个相关条目、提取上下文，然后推导出答案

### 工具测试

8. **问题应对工具返回值进行压力测试**
   - 可以引发工具返回大型 JSON 对象或列表，使 LLM 不堪重负
   - 应要求理解多种数据模态：
     - ID 和名称
     - 时间戳和日期时间（月、日、年、秒）
     - 文件 ID、名称、扩展名和 MIME 类型
     - URL、GID 等
   - 应测试工具返回所有有用数据形式的能力

9. **问题应大部分反映真实的人类使用场景**
   - 人类借助 LLM 所关心的信息检索任务类型

10. **问题可能需要数十次工具调用**
    - 这对上下文有限的 LLM 构成挑战
    - 鼓励 MCP 服务器工具减少返回的信息量

11. **包含有歧义的问题**
    - 可以存在歧义，或需要在调用哪些工具上做出困难决策
    - 迫使 LLM 可能犯错或误判
    - 确保尽管存在歧义，仍然存在一个单一可验证的答案

### 稳定性

12. **问题必须设计为答案不会变化**
    - 不要问依赖于动态"当前状态"的问题
    - 例如，不要计数：
      - 帖子的反应数量
      - 线程的回复数量
      - 频道的成员数量

13. **不要让 MCP 服务器限制您创建问题的类型**
    - 创建具有挑战性和复杂性的问题
    - 有些问题可能无法用现有的 MCP 服务器工具解决
    - 问题可能需要特定的输出格式（日期时间 vs 纪元时间，JSON vs MARKDOWN）
    - 问题可能需要数十次工具调用才能完成

## 答案编写指南

### 可验证性

1. **答案必须可通过直接字符串比较进行验证**
   - 如果答案可以用多种格式重写，请在问题中明确指定输出格式
   - 示例："使用 YYYY/MM/DD 格式。""回答 True 或 False。""回答 A、B、C 或 D，不要其他内容。"
   - 答案应为单一可验证的值，例如：
     - 用户 ID、用户名、显示名、名、姓
     - 频道 ID、频道名称
     - 消息 ID、消息字符串
     - URL、标题
     - 数值数量
     - 时间戳、日期时间
     - 布尔值（用于真/假问题）
     - 电子邮件地址、电话号码
     - 文件 ID、文件名、文件扩展名
     - 多项选择答案
   - 答案不得需要特殊格式或复杂的结构化输出
   - 答案将使用直接字符串比较进行验证

### 可读性

2. **答案通常应优先使用人类可读的格式**
   - 例如：名称、名、姓、日期时间、文件名、消息字符串、URL、是/否、真/假、a/b/c/d
   - 而非不透明的 ID（尽管 ID 也是可接受的）
   - 绝大多数答案应是人类可读的

### 稳定性

3. **答案必须是稳定/不变的**
   - 查看旧内容（例如，已结束的对话、已启动的项目、已回答的问题）
   - 基于"已封闭"的概念创建问题，这些概念将始终返回相同的答案
   - 问题可以要求考虑固定的时间窗口，以规避非稳态答案
   - 依赖不太可能变化的上下文
   - 示例：如果查找论文名称，要足够具体，以免与后来发表的论文混淆

4. **答案必须清晰且无歧义**
   - 问题应设计为有单一、清晰的答案
   - 答案应可通过使用 MCP 服务器工具推导得出

### 多样性

5. **答案必须多样化**
   - 答案应以多样化的模态和格式呈现为单一可验证的值
   - 用户概念：用户 ID、用户名、显示名、名、姓、电子邮件地址、电话号码
   - 频道概念：频道 ID、频道名称、频道主题
   - 消息概念：消息 ID、消息字符串、时间戳、月、日、年

6. **答案不得是复杂结构**
   - 不能是值列表
   - 不能是复杂对象
   - 不能是 ID 或字符串列表
   - 不能是自然语言文本
   - 除非答案可以通过直接字符串比较直接验证
   - 并且可以真实地复现
   - LLM 以任何其他顺序或格式返回相同列表的可能性应很小

## 评估流程

### 第 1 步：文档检查

阅读目标 API 的文档以了解：
- 可用的端点和功能
- 如果存在歧义，从网上获取额外信息
- 尽可能并行进行此步骤
- 确保每个子代理仅从文件系统或网络上查阅文档

### 第 2 步：工具检查

列出 MCP 服务器中可用的工具：
- 直接检查 MCP 服务器
- 了解输入/输出模式、文档字符串和描述
- 在此阶段不要调用工具本身

### 第 3 步：加深理解

重复第 1 步和第 2 步，直到您有良好的理解：
- 多次迭代
- 思考您想要创建的任务类型
- 完善您的理解
- 在任何阶段都不应阅读 MCP 服务器实现的代码本身
- 运用您的直觉和理解来创建合理、真实但非常具有挑战性的任务

### 第 4 步：只读内容检查

在了解 API 和工具后，使用 MCP 服务器工具：
- 仅使用只读和非破坏性操作检查内容
- 目标：识别用于创建真实问题的特定内容（例如用户、频道、消息、项目、任务）
- 不应调用任何会修改状态的工具
- 不会阅读 MCP 服务器实现的代码本身
- 让各个子代理独立探索，并行进行此步骤
- 确保每个子代理仅执行只读、非破坏性和幂等的操作
- 注意：某些工具可能返回大量数据，导致上下文耗尽
- 进行增量、小型且有针对性的工具调用以进行探索
- 在所有工具调用请求中，使用 `limit` 参数限制结果（<10）
- 使用分页

### 第 5 步：任务生成

检查内容后，创建 10 个人类可读的问题：
- LLM 应能使用 MCP 服务器回答这些问题
- 遵循上述所有问题和答案编写指南

## 输出格式

每个问答对包含一个问题和一个答案。输出应为具有以下结构的 XML 文件：

```xml
<evaluation>
   <qa_pair>
      <question>Find the project created in Q2 2024 with the highest number of completed tasks. What is the project name?</question>
      <answer>Website Redesign</answer>
   </qa_pair>
   <qa_pair>
      <question>Search for issues labeled as "bug" that were closed in March 2024. Which user closed the most issues? Provide their username.</question>
      <answer>sarah_dev</answer>
   </qa_pair>
   <qa_pair>
      <question>Look for pull requests that modified files in the /api directory and were merged between January 1 and January 31, 2024. How many different contributors worked on these PRs?</question>
      <answer>7</answer>
   </qa_pair>
   <qa_pair>
      <question>Find the repository with the most stars that was created before 2023. What is the repository name?</question>
      <answer>data-pipeline</answer>
   </qa_pair>
</evaluation>
```

## 评估示例

### 好问题的示例

**示例 1：需要深入探索的多跳问题（GitHub MCP）**
```xml
<qa_pair>
   <question>Find the repository that was archived in Q3 2023 and had previously been the most forked project in the organization. What was the primary programming language used in that repository?</question>
   <answer>Python</answer>
</qa_pair>
```

该问题之所以好是因为：
- 需要多次搜索才能找到已归档的仓库
- 需要识别归档前拥有最多 fork 的仓库
- 需要查看仓库详情以确定编程语言
- 答案是简单且可验证的值
- 基于不会改变的历史（已封闭）数据

**示例 2：无需关键词匹配即可理解上下文（项目管理 MCP）**
```xml
<qa_pair>
   <question>Locate the initiative focused on improving customer onboarding that was completed in late 2023. The project lead created a retrospective document after completion. What was the lead's role title at that time?</question>
   <answer>Product Manager</answer>
</qa_pair>
```

该问题之所以好是因为：
- 未使用具体项目名称（"专注于改善客户引导的倡议"）
- 需要从特定时间范围内找到已完成的项目
- 需要识别项目负责人及其职位
- 需要从回顾文档中理解上下文
- 答案是人类可读且稳定的
- 基于已完成的工作（不会改变）

**示例 3：需要多个步骤的复杂聚合（问题跟踪器 MCP）**
```xml
<qa_pair>
   <question>Among all bugs reported in January 2024 that were marked as critical priority, which assignee resolved the highest percentage of their assigned bugs within 48 hours? Provide the assignee's username.</question>
   <answer>alex_eng</answer>
</qa_pair>
```

该问题之所以好是因为：
- 需要按日期、优先级和状态过滤错误
- 需要按处理人分组并计算解决率
- 需要理解时间戳以确定 48 小时窗口
- 测试分页（可能需要处理大量错误）
- 答案是单一用户名
- 基于特定时间段的历史数据

**示例 4：需要跨多种数据类型进行综合分析（CRM MCP）**
```xml
<qa_pair>
   <question>Find the account that upgraded from the Starter to Enterprise plan in Q4 2023 and had the highest annual contract value. What industry does this account operate in?</question>
   <answer>Healthcare</answer>
</qa_pair>
```

该问题之所以好是因为：
- 需要了解订阅层级变更
- 需要在特定时间范围内识别升级事件
- 需要比较合同价值
- 必须访问账户行业信息
- 答案简单且可验证
- 基于已完成的历史交易

### 差问题的示例

**示例 1：答案随时间变化**
```xml
<qa_pair>
   <question>How many open issues are currently assigned to the engineering team?</question>
   <answer>47</answer>
</qa_pair>
```

该问题之所以差是因为：
- 答案会随着问题的创建、关闭或重新分配而变化
- 不是基于稳定/不变的数据
- 依赖于动态的"当前状态"

**示例 2：通过关键词搜索过于简单**
```xml
<qa_pair>
   <question>Find the pull request with title "Add authentication feature" and tell me who created it.</question>
   <answer>developer123</answer>
</qa_pair>
```

该问题之所以差是因为：
- 可以通过对确切标题进行简单的关键词搜索来解决
- 不需要深入探索或理解
- 无需综合分析或分析

**示例 3：答案格式有歧义**
```xml
<qa_pair>
   <question>List all the repositories that have Python as their primary language.</question>
   <answer>repo1, repo2, repo3, data-pipeline, ml-tools</answer>
</qa_pair>
```

该问题之所以差是因为：
- 答案是一个列表，可能以任何顺序返回
- 难以通过直接字符串比较进行验证
- LLM 可能以不同格式输出（JSON 数组、逗号分隔、换行分隔）
- 最好询问特定的聚合值（计数）或最高级（最多星标）

## 验证流程

创建评估后：

1. **检查 XML 文件**以了解模式
2. **加载每个任务指令**，并使用 MCP 服务器和工具并行地尝试自行解决问题，以确定正确答案
3. **标记任何需要写入或破坏性操作**的操作
4. **汇总所有正确答案**，并替换文档中的任何错误答案
5. **移除任何需要写入或破坏性操作**的 `<qa_pair>`

请记住并行地解决问题，以避免上下文耗尽，然后在最后汇总所有答案并对文件进行修改。

## 创建高质量评估的技巧

1. **在生成任务前认真思考并提前规划**
2. **在有机会时并行处理**以加快速度并管理上下文
3. **关注真实的使用场景**，即人类实际想要完成的任务
4. **创建具有挑战性的问题**，测试 MCP 服务器能力的极限
5. **确保稳定性**，使用历史数据和已封闭的概念
6. **验证答案**，亲自使用 MCP 服务器工具解决问题
7. **根据过程中的发现**进行迭代和完善

---

# 运行评估

创建评估文件后，您可以使用提供的评估框架来测试您的 MCP 服务器。

## 设置

1. **安装依赖项**

   ```bash
   pip install -r scripts/requirements.txt
   ```

   或手动安装：
   ```bash
   pip install anthropic mcp
   ```

2. **设置 API 密钥**

   ```bash
   export ANTHROPIC_API_KEY=your_api_key_here
   ```

## 评估文件格式

评估文件使用包含 `<qa_pair>` 元素的 XML 格式：

```xml
<evaluation>
   <qa_pair>
      <question>Find the project created in Q2 2024 with the highest number of completed tasks. What is the project name?</question>
      <answer>Website Redesign</answer>
   </qa_pair>
   <qa_pair>
      <question>Search for issues labeled as "bug" that were closed in March 2024. Which user closed the most issues? Provide their username.</question>
      <answer>sarah_dev</answer>
   </qa_pair>
</evaluation>
```

## 运行评估

评估脚本（`scripts/evaluation.py`）支持三种传输类型：

**重要提示：**
- **stdio 传输**：评估脚本会自动为您启动和管理 MCP 服务器进程。请勿手动运行服务器。
- **sse/http 传输**：您必须在运行评估之前单独启动 MCP 服务器。脚本会连接到指定 URL 上已在运行的服务器。

### 1. 本地 STDIO 服务器

对于本地运行的 MCP 服务器（脚本会自动启动服务器）：

```bash
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a my_mcp_server.py \
  evaluation.xml
```

使用环境变量：
```bash
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a my_mcp_server.py \
  -e API_KEY=abc123 \
  -e DEBUG=true \
  evaluation.xml
```

### 2. 服务器发送事件（SSE）

对于基于 SSE 的 MCP 服务器（您必须先启动服务器）：

```bash
python scripts/evaluation.py \
  -t sse \
  -u https://example.com/mcp \
  -H "Authorization: Bearer token123" \
  -H "X-Custom-Header: value" \
  evaluation.xml
```

### 3. HTTP（可流式 HTTP）

对于基于 HTTP 的 MCP 服务器（您必须先启动服务器）：

```bash
python scripts/evaluation.py \
  -t http \
  -u https://example.com/mcp \
  -H "Authorization: Bearer token123" \
  evaluation.xml
```

## 命令行选项

```
usage: evaluation.py [-h] [-t {stdio,sse,http}] [-m MODEL] [-c COMMAND]
                     [-a ARGS [ARGS ...]] [-e ENV [ENV ...]] [-u URL]
                     [-H HEADERS [HEADERS ...]] [-o OUTPUT]
                     eval_file

positional arguments:
  eval_file             Path to evaluation XML file

optional arguments:
  -h, --help            Show help message
  -t, --transport       Transport type: stdio, sse, or http (default: stdio)
  -m, --model           Claude model to use (default: claude-3-7-sonnet-20250219)
  -o, --output          Output file for report (default: print to stdout)

stdio options:
  -c, --command         Command to run MCP server (e.g., python, node)
  -a, --args            Arguments for the command (e.g., server.py)
  -e, --env             Environment variables in KEY=VALUE format

sse/http options:
  -u, --url             MCP server URL
  -H, --header          HTTP headers in 'Key: Value' format
```

## 输出

评估脚本会生成一份详细的报告，包括：

- **摘要统计信息**：
  - 准确率（正确数/总数）
  - 平均任务持续时间
  - 每项任务的平均工具调用次数
  - 工具调用总数

- **每项任务的结果**：
  - 提示和预期响应
  - 代理的实际响应
  - 答案是否正确（✅/❌）
  - 持续时间和工具调用详情
  - 代理对其方法的总结
  - 代理对工具的反馈

### 将报告保存到文件

```bash
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a my_server.py \
  -o evaluation_report.md \
  evaluation.xml
```

## 完整的工作流程示例

以下是创建和运行评估的完整示例：

1. **创建评估文件**（`my_evaluation.xml`）：

```xml
<evaluation>
   <qa_pair>
      <question>Find the user who created the most issues in January 2024. What is their username?</question>
      <answer>alice_developer</answer>
   </qa_pair>
   <qa_pair>
      <question>Among all pull requests merged in Q1 2024, which repository had the highest number? Provide the repository name.</question>
      <answer>backend-api</answer>
   </qa_pair>
   <qa_pair>
      <question>Find the project that was completed in December 2023 and had the longest duration from start to finish. How many days did it take?</question>
      <answer>127</answer>
   </qa_pair>
</evaluation>
```

2. **安装依赖项**：

```bash
pip install -r scripts/requirements.txt
export ANTHROPIC_API_KEY=your_api_key
```

3. **运行评估**：

```bash
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a github_mcp_server.py \
  -e GITHUB_TOKEN=ghp_xxx \
  -o github_eval_report.md \
  my_evaluation.xml
```

4. **查看报告** `github_eval_report.md`，以：
   - 查看哪些问题通过/失败
   - 阅读代理对您的工具的反馈
   - 确定需要改进的领域
   - 迭代完善您的 MCP 服务器设计

## 故障排除

### 连接错误

如果出现连接错误：
- **STDIO**：验证命令和参数是否正确
- **SSE/HTTP**：检查 URL 是否可访问以及请求头是否正确
- 确保在环境变量或请求头中设置了任何必需的 API 密钥

### 准确率低

如果许多评估失败：
- 查看代理对每个任务的反馈
- 检查工具描述是否清晰且全面
- 验证输入参数是否文档齐全
- 考虑工具返回的数据是否过多或过少
- 确保错误信息具有可操作性

### 超时问题

如果任务超时：
- 使用能力更强的模型（例如 `claude-3-7-sonnet-20250219`）
- 检查工具是否返回过多数据
- 验证分页是否正常工作
- 考虑简化复杂问题
