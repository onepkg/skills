---
name: pptx
description: "任何时候只要涉及 .pptx 文件，无论是作为输入、输出还是两者兼有，都使用此技能。这包括：创建幻灯片组、推介幻灯片或演示文稿；读取、解析或从任何 .pptx 文件中提取文本（即使提取的内容将用于其他地方，如电子邮件或摘要）；编辑、修改或更新现有演示文稿；合并或拆分裂片文件；使用模板、布局、演讲者注释或注释。当用户提及'deck'、'slides'、'presentation'或引用 .pptx 文件名时触发，无论他们计划之后对内容做什么。如果需要打开、创建或触及 .pptx 文件，请使用此技能。"
license: Proprietary. LICENSE.txt has complete terms
---

# PPTX 技能

## 快速参考

| 任务 | 指南 |
|------|-------|
| 读取/分析内容 | `python -m markitdown presentation.pptx` |
| 编辑或从模板创建 | 阅读 [editing.md](editing.md) |
| 从头创建 | 阅读 [pptxgenjs.md](pptxgenjs.md) |

---

## 读取内容

```bash
# 文本提取
python -m markitdown presentation.pptx

# 视觉概览
python scripts/thumbnail.py presentation.pptx

# 原始 XML
python scripts/office/unpack.py presentation.pptx unpacked/
```

---

## 编辑工作流

**阅读 [editing.md](editing.md) 获取完整详细信息。**

1. 使用 `thumbnail.py` 分析模板
2. 解包 → 操作幻灯片 → 编辑内容 → 清理 → 打包

---

## 从头创建

**阅读 [pptxgenjs.md](pptxgenjs.md) 获取完整详细信息。**

当没有模板或参考演示文稿时使用。

---

## 设计思路

**不要创建无聊的幻灯片。** 白色背景上的普通项目符号不会给任何人留下深刻印象。为每张幻灯片考虑此列表中的想法。

### 开始之前

- **选择一个大胆的、内容驱动的调色板**：调色板应该感觉是为 THIS 主题设计的。如果将您的颜色交换到完全不同的演示文稿中仍然"有效"，那么您还没有做出足够具体的选择。
- **主导性胜过平等**：一种颜色应该占主导地位（60-70% 视觉权重），配以 1-2 种支持色调和一种锐利的强调色。永远不要让所有颜色具有相同的权重。
- **深色/浅色对比**：标题 + 结论幻灯片使用深色背景，内容使用浅色（"三明治"结构）。或者始终使用深色以获得高级感。
- **致力于视觉主题**：选择一个独特的元素并重复它 — 圆形图像框架、彩色圆圈中的图标、厚单侧边框。在每张幻灯片上携带它。

### 调色板

选择与您的主题匹配的颜色 — 不要默认为通用蓝色。使用这些调色板作为灵感：

| 主题 | 主要 | 次要 | 强调 |
|-------|---------|-----------|--------|
| **Midnight Executive** | `1E2761`（海军蓝） | `CADCFC`（冰蓝） | `FFFFFF`（白色） |
| **Forest & Moss** | `2C5F2D`（森林绿） | `97BC62`（苔藓绿） | `F5F5F5`（奶油色） |
| **Coral Energy** | `F96167`（珊瑚色） | `F9E795`（金色） | `2F3C7E`（海军蓝） |
| **Warm Terracotta** | `B85042`（赤陶色） | `E7E8D1`（沙色） | `A7BEAE`（鼠尾草绿） |
| **Ocean Gradient** | `065A82`（深蓝色） | `1C7293`（青色） | `21295C`（午夜蓝） |
| **Charcoal Minimal** | `36454F`（木炭色） | `F2F2F2`（灰白色） | `212121`（黑色） |
| **Teal Trust** | `028090`（青色） | `00A896`（海沫绿） | `02C39A`（薄荷绿） |
| **Berry & Cream** | `6D2E46`（浆果色） | `A26769`（尘玫瑰色） | `ECE2D0`（奶油色） |
| **Sage Calm** | `84B59F`（鼠尾草绿） | `69A297`（桉树绿） | `50808E`（石板蓝） |
| **Cherry Bold** | `990011`（樱桃红） | `FCF6F5`（灰白色） | `2F3C7E`（海军蓝） |

### 每张幻灯片

**每张幻灯片都需要一个视觉元素** — 图像、图表、图标或形状。纯文本幻灯片容易被遗忘。

**布局选项：**
- 两列（左侧文本，右侧插图）
- 图标 + 文本行（彩色圆圈中的图标，粗体标题，下方描述）
- 2x2 或 2x3 网格（一侧图像，另一侧内容块网格）
- 半出血图像（全左或右侧）带内容叠加

**数据显示：**
- 大统计标注（大数字 60-72pt，下方小标签）
- 比较列（前后、优缺点、并排选项）
- 时间线或流程（编号步骤、箭头）

**视觉润色：**
- 部分标题旁边的小彩色圆圈中的图标
- 关键统计或标语的斜体强调文本

### 字体排版

**选择有趣的字体配对** — 不要默认为 Arial。选择有个性的标题字体并与干净的正文配对。

| 标题字体 | 正文字体 |
|-------------|-----------|
| Georgia | Calibri |
| Arial Black | Arial |
| Calibri | Calibri Light |
| Cambria | Calibri |
| Trebuchet MS | Calibri |
| Impact | Arial |
| Palatino | Garamond |
| Consolas | Calibri |

| 元素 | 大小 |
|---------|------|
| 幻灯片标题 | 36-44pt 粗体 |
| 部分标题 | 20-24pt 粗体 |
| 正文 | 14-16pt |
| 说明文字 | 10-12pt  muted |

### 间距

- 最小边距 0.5"
- 内容块之间 0.3-0.5"
- 留出呼吸空间 — 不要填满每一英寸

### 避免（常见错误）

- **不要重复相同的布局** — 在幻灯片间变化列、卡片和标注
- **不要居中正文** — 左对齐段落和列表；仅居中标题
- **不要吝啬大小对比** — 标题需要 36pt+ 以从 14-16pt 正文中脱颖而出
- **不要默认为蓝色** — 选择反映特定主题的颜色
- **不要随机混合间距** — 选择 0.3" 或 0.5" 间隙并一致使用
- **不要只样式化一张幻灯片而让其余保持朴素** — 要么完全投入，要么始终保持简单
- **不要创建纯文本幻灯片** — 添加图像、图标、图表或视觉元素；避免纯标题 + 项目符号
- **不要忘记文本框填充** — 当将线条或形状与文本边缘对齐时，在文本框上设置 `margin: 0` 或偏移形状以考虑填充
- **不要使用低对比度元素** — 图标 AND 文本需要与背景形成强烈对比；避免浅色背景上的浅色文本或深色背景上的深色文本
- **切勿在标题下使用强调线** — 这些是 AI 生成幻灯片的标志；改用空白或背景颜色

---

## QA（必需）

**假设有问题。您的工作是找到它们。**

您的第一次渲染几乎从不正确。将 QA 视为 bug 狩猎，而不是确认步骤。如果您在第一次检查中发现零问题，那么您看得不够仔细。

### 内容 QA

```bash
python -m markitdown output.pptx
```

检查缺失内容、拼写错误、错误顺序。

**使用模板时，检查剩余的占位符文本：**

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

如果 grep 返回结果，请在宣布成功之前修复它们。

### 视觉 QA

**⚠️ 使用子代理** — 即使是 2-3 张幻灯片。您一直盯着代码，会看到您期望看到的，而不是实际存在的。子代理有新鲜的眼睛。

将幻灯片转换为图像（参见[转换为图像](#converting-to-images)），然后使用此提示：

```
 visually inspect these slides. Assume there are issues — find them.

Look for:
- Overlapping elements (text through shapes, lines through words, stacked elements)
- Text overflow or cut off at edges/box boundaries
- Decorative lines positioned for single-line text but title wrapped to two lines
- Source citations or footers colliding with content above
- Elements too close (< 0.3" gaps) or cards/sections nearly touching
- Uneven gaps (large empty area in one place, cramped in another)
- Insufficient margin from slide edges (< 0.5")
- Columns or similar elements not aligned consistently
- Low-contrast text (e.g., light gray text on cream-colored background)
- Low-contrast icons (e.g., dark icons on dark backgrounds without a contrasting circle)
- Text boxes too narrow causing excessive wrapping
- Leftover placeholder content

For each slide, list issues or areas of concern, even if minor.

Read and analyze these images:
1. /path/to/slide-01.jpg (Expected: [brief description])
2. /path/to/slide-02.jpg (Expected: [brief description])

Report ALL issues found, including minor ones.
```

### 验证循环

1. 生成幻灯片 → 转换为图像 → 检查
2. **列出发现的问题**（如果未发现问题，请更严格地再次查看）
3. 修复问题
4. **重新验证受影响的幻灯片** — 一个修复通常会创建另一个问题
5. 重复直到完整传递未发现新问题

**在完成至少一次修复和验证循环之前，不要宣布成功。**

---

## 转换为图像

将演示文稿转换为单独的幻灯片图像以进行视觉检查：

```bash
python scripts/office/soffice.py --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

这将创建 `slide-01.jpg`、`slide-02.jpg` 等。

要在修复后重新渲染特定幻灯片：

```bash
pdftoppm -jpeg -r 150 -f N -l N output.pdf slide-fixed
```

---

## 依赖项

- `pip install "markitdown[pptx]"` - 文本提取
- `pip install Pillow` - 缩略图网格
- `npm install -g pptxgenjs` - 从头创建
- LibreOffice (`soffice`) - PDF 转换（通过 `scripts/office/soffice.py` 为沙盒环境自动配置）
- Poppler (`pdftoppm`) - PDF 到图像
