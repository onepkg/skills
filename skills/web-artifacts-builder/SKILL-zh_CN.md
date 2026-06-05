---
name: web-artifacts-builder
description: 用于使用现代前端 Web 技术（React、Tailwind CSS、shadcn/ui）创建复杂、多组件的 claude.ai HTML 工件（artifact）的工具集。适用于需要状态管理、路由或 shadcn/ui 组件的复杂工件，而非简单的单文件 HTML/JSX 工件。
license: 完整条款见 LICENSE.txt
---

# Web Artifacts Builder

要构建强大的前端 claude.ai 工件，请按以下步骤操作：
1. 使用 `scripts/init-artifact.sh` 初始化前端仓库
2. 通过编辑生成的代码来开发你的工件
3. 使用 `scripts/bundle-artifact.sh` 将所有代码打包到单个 HTML 文件中
4. 向用户展示工件
5. （可选）测试工件

**技术栈**: React 18 + TypeScript + Vite + Parcel（打包）+ Tailwind CSS + shadcn/ui

## 设计与样式指南

非常重要：为避免常说的"AI 模板感"，请避免使用过多的居中布局、紫色渐变、统一的圆角以及 Inter 字体。

## 快速开始

### 第 1 步：初始化项目

运行初始化脚本以创建新的 React 项目：
```bash
bash scripts/init-artifact.sh <project-name>
cd <project-name>
```

这将创建一个完全配置的项目，包含：
- ✅ React + TypeScript（通过 Vite）
- ✅ Tailwind CSS 3.4.1 及 shadcn/ui 主题系统
- ✅ 路径别名（`@/`）已配置
- ✅ 预装了 40+ 个 shadcn/ui 组件
- ✅ 包含所有 Radix UI 依赖
- ✅ 已为打包配置 Parcel（通过 .parcelrc）
- ✅ Node 18+ 兼容性（自动检测并锁定 Vite 版本）

### 第 2 步：开发你的工件

要构建工件，请编辑生成的文件。有关指导，请参阅下面的**常见开发任务**。

### 第 3 步：打包到单个 HTML 文件

要将 React 应用打包为单个 HTML 工件：
```bash
bash scripts/bundle-artifact.sh
```

这将创建 `bundle.html` —— 一个自包含的工件，所有 JavaScript、CSS 和依赖项都已内联。该文件可以直接在 Claude 对话中作为工件分享。

**要求**：你的项目必须在根目录中包含 `index.html`。

**脚本功能**：
- 安装打包依赖（parcel、@parcel/config-default、parcel-resolver-tspaths、html-inline）
- 创建包含路径别名支持的 `.parcelrc` 配置
- 使用 Parcel 构建（无 source map）
- 使用 html-inline 将所有资源内联到单个 HTML 中

### 第 4 步：与用户分享工件

最后，在对话中与用户分享打包后的 HTML 文件，以便他们将其视为工件进行查看。

### 第 5 步：测试/可视化工件（可选）

注意：这是完全可选的步骤。仅在必要时或应要求时执行。

要测试/可视化工件，请使用可用的工具（包括其他技能或内置工具，如 Playwright 或 Puppeteer）。通常，避免事先测试工件，因为这会在请求与最终工件展示之间增加延迟。如遇问题或应要求，可在展示工件后再进行测试。

## 参考

- **shadcn/ui 组件**: https://ui.shadcn.com/docs/components
