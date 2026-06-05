---
name: web-artifacts-builder
description: 用于使用现代前端 Web 技术（React、Tailwind CSS、shadcn/ui）创建精致的多组件 claude.ai HTML 制品的工具套件。用于需要状态管理、路由或 shadcn/ui 组件的复杂制品 - 不用于简单的单文件 HTML/JSX 制品。
license: Complete terms in LICENSE.txt
---

# Web 制品构建器

要构建强大的前端 claude.ai 制品，请遵循以下步骤：
1. 使用 `scripts/init-artifact.sh` 初始化前端仓库
2. 通过编辑生成的代码开发您的制品
3. 使用 `scripts/bundle-artifact.sh` 将所有代码捆绑到单个 HTML 文件中
4. 向用户显示制品
5. （可选）测试制品

**技术栈**：React 18 + TypeScript + Vite + Parcel（捆绑）+ Tailwind CSS + shadcn/ui

## 设计和样式指南

非常重要：为避免通常被称为"AI slop"的东西，避免使用过多的居中布局、紫色渐变、统一的圆角和 Inter 字体。

## 快速入门

### 步骤 1：初始化项目

运行初始化脚本以创建新的 React 项目：
```bash
bash scripts/init-artifact.sh <project-name>
cd <project-name>
```

这将创建一个完全配置的项目，包括：
- ✅ React + TypeScript（通过 Vite）
- ✅ Tailwind CSS 3.4.1 带有 shadcn/ui 主题系统
- ✅ 配置了路径别名（`@/`）
- ✅ 预安装了 40+ shadcn/ui 组件
- ✅ 包含所有 Radix UI 依赖项
- ✅ 配置了 Parcel 用于捆绑（通过 .parcelrc）
- ✅ Node 18+ 兼容性（自动检测并固定 Vite 版本）

### 步骤 2：开发您的制品

要构建制品，请编辑生成的文件。有关指导，请参阅下面的**常见开发任务**。

### 步骤 3：捆绑到单个 HTML 文件

要将 React 应用捆绑到单个 HTML 制品中：
```bash
bash scripts/bundle-artifact.sh
```

这将创建 `bundle.html` - 一个自包含的制品，其中所有 JavaScript、CSS 和依赖项都内联。此文件可以直接在 Claude 对话中作为制品共享。

**要求**：您的项目必须在根目录中有一个 `index.html`。

**脚本执行的操作**：
- 安装捆绑依赖项（parcel、@parcel/config-default、parcel-resolver-tspaths、html-inline）
- 创建带有路径别名支持的 `.parcelrc` 配置
- 使用 Parcel 构建（没有源映射）
- 使用 html-inline 将所有资产内联到单个 HTML 中

### 步骤 4：与用户共享制品

最后，在与用户的对话中共享捆绑的 HTML 文件，以便他们可以作为制品查看它。

### 步骤 5：测试/可视化制品（可选）

注意：这是一个完全可选的步骤。仅在必要或请求时执行。

要测试/可视化制品，请使用可用工具（包括其他技能或内置工具如 Playwright 或 Puppeteer）。一般来说，避免在前端测试制品，因为它会在请求和可以看到完成的制品之间增加延迟。在呈现制品后，如果请求或出现问题，再进行测试。

## 参考

- **shadcn/ui 组件**：https://ui.shadcn.com/docs/components
