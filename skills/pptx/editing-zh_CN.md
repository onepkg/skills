# 编辑演示文稿

## 基于模板的工作流程

当使用现有演示文稿作为模板时：

1. **分析现有幻灯片**：
   ```bash
   python scripts/thumbnail.py template.pptx
   python -m markitdown template.pptx
   ```
   查看 `thumbnails.jpg` 以了解布局，查看 markitdown 输出以了解占位文本。

2. **规划幻灯片映射**：为每个内容区块选择合适的模板幻灯片。

   ⚠️ **使用多样化的布局** — 单调的演示文稿是常见的失败模式。不要默认使用基本标题加项目符号的幻灯片。主动寻找：
   - 多列布局（2 列、3 列）
   - 图片加文字组合
   - 全出血图片配文字覆盖
   - 引用或标注幻灯片
   - 章节分隔页
   - 统计数据/数字标注
   - 图标网格或图标加文字行

   **避免：** 为每张幻灯片重复使用相同的文本密集型布局。

   将内容类型与布局风格相匹配（例如，关键点 → 项目符号幻灯片，团队信息 → 多列布局，客户评价 → 引用幻灯片）。

3. **解包**：`python scripts/office/unpack.py template.pptx unpacked/`

4. **构建演示文稿**（由你自己完成，不要使用子代理）：
   - 删除不需要的幻灯片（从 `<p:sldIdLst>` 中移除）
   - 复制要重复使用的幻灯片（`add_slide.py`）
   - 在 `<p:sldIdLst>` 中重新排序幻灯片
   - **在步骤 5 之前完成所有结构更改**

5. **编辑内容**：更新每个 `slide{N}.xml` 中的文本。
   **如果可用，在此处使用子代理** — 幻灯片是独立的 XML 文件，因此子代理可以并行编辑。

6. **清理**：`python scripts/clean.py unpacked/`

7. **打包**：`python scripts/office/pack.py unpacked/ output.pptx --original template.pptx`

---

## 脚本

| 脚本 | 用途 |
|--------|---------|
| `unpack.py` | 解压并美化打印 PPTX |
| `add_slide.py` | 复制幻灯片或从布局创建 |
| `clean.py` | 移除孤立文件 |
| `pack.py` | 重新打包并验证 |
| `thumbnail.py` | 创建幻灯片视觉网格 |

### unpack.py

```bash
python scripts/office/unpack.py input.pptx unpacked/
```

解压 PPTX，美化打印 XML，转义智能引号。

### add_slide.py

```bash
python scripts/add_slide.py unpacked/ slide2.xml      # Duplicate slide
python scripts/add_slide.py unpacked/ slideLayout2.xml # From layout
```

打印 `<p:sldId>` 以在所需位置添加到 `<p:sldIdLst>`。

### clean.py

```bash
python scripts/clean.py unpacked/
```

移除不在 `<p:sldIdLst>` 中的幻灯片、未引用的媒体、孤立的关联文件。

### pack.py

```bash
python scripts/office/pack.py unpacked/ output.pptx --original input.pptx
```

验证、修复、精简 XML，重新编码智能引号。

### thumbnail.py

```bash
python scripts/thumbnail.py input.pptx [output_prefix] [--cols N]
```

创建带有幻灯片文件名标签的 `thumbnails.jpg`。默认 3 列，每个网格最多 12 张。

**仅用于模板分析**（选择布局）。对于视觉质量检查，使用 `soffice` + `pdftoppm` 创建全分辨率单张幻灯片图像——请参阅 SKILL.md。

---

## 幻灯片操作

幻灯片顺序在 `ppt/presentation.xml` → `<p:sldIdLst>` 中。

**重新排序**：重新排列 `<p:sldId>` 元素。

**删除**：移除 `<p:sldId>`，然后运行 `clean.py`。

**添加**：使用 `add_slide.py`。切勿手动复制幻灯片文件——该脚本会处理手动复制遗漏的备注引用、Content_Types.xml 和关系 ID。

---

## 编辑内容

**子代理：** 如果可用，在此处使用它们（在完成步骤 4 之后）。每张幻灯片都是一个独立的 XML 文件，因此子代理可以并行编辑。在给子代理的提示中，包含：
- 要编辑的幻灯片文件路径
- **"对所有更改使用 Edit 工具"**
- 下面的格式规则和常见陷阱

对于每张幻灯片：
1. 读取幻灯片的 XML
2. 识别所有占位内容——文本、图片、图表、图标、标题
3. 用最终内容替换每个占位内容

**使用 Edit 工具，而不是 sed 或 Python 脚本。** Edit 工具要求明确指定要替换的内容和位置，从而提高可靠性。

### 格式规则

- **将所有标题、副标题和内联标签加粗**：在 `<a:rPr>` 上使用 `b="1"`。这包括：
  - 幻灯片标题
  - 幻灯片内的章节标题
  - 行首的内联标签（例如："Status："、"Description："）
- **永远不要使用 unicode 项目符号（•）**：使用 `<a:buChar>` 或 `<a:buAutoNum>` 进行正确的列表格式化
- **项目符号一致性**：让项目符号从布局继承。仅指定 `<a:buChar>` 或 `<a:buNone>`。

---

## 常见陷阱

### 模板适配

当源内容条目少于模板时：
- **完全移除多余的元素**（图片、形状、文本框），不要仅仅清除文本
- 清除文本内容后检查是否有孤立的视觉元素
- 运行视觉质量检查以发现数量不匹配

当用不同长度的内容替换文本时：
- **较短的替换**：通常安全
- **较长的替换**：可能会溢出或意外换行
- 文本更改后通过视觉质量检查进行测试
- 考虑截断或拆分内容以适应模板的设计约束

**模板插槽 ≠ 源条目**：如果模板有 4 个团队成员但源有 3 个用户，则删除第 4 个成员的整个组（图片加文本框），而不仅仅是文本。

### 多项内容

如果源有多个项目（编号列表、多个区块），为每个项目创建单独的 `<a:p>` 元素——**切勿将它们拼接成一个字符串**。

**❌ 错误** — 所有项目放在一个段落中：
```xml
<a:p>
  <a:r><a:rPr .../><a:t>Step 1: Do the first thing. Step 2: Do the second thing.</a:t></a:r>
</a:p>
```

**✅ 正确** — 用加粗标题分隔的独立段落：
```xml
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="en-US" sz="2799" b="1" .../><a:t>Step 1</a:t></a:r>
</a:p>
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="en-US" sz="2799" .../><a:t>Do the first thing.</a:t></a:r>
</a:p>
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="en-US" sz="2799" b="1" .../><a:t>Step 2</a:t></a:r>
</a:p>
<!-- continue pattern -->
```

复制原始段落中的 `<a:pPr>` 以保留行间距。在标题上使用 `b="1"`。

### 智能引号

由解包/打包脚本自动处理。但 Edit 工具会将智能引号转换为 ASCII。

**在添加带引号的新文本时，使用 XML 实体：**

```xml
<a:t>the &#x201C;Agreement&#x201D;</a:t>
```

| 字符 | 名称 | Unicode | XML 实体 |
|-----------|------|---------|------------|
| `“` | 左双引号 | U+201C | `&#x201C;` |
| `”` | 右双引号 | U+201D | `&#x201D;` |
| `‘` | 左单引号 | U+2018 | `&#x2018;` |
| `’` | 右单引号 | U+2019 | `&#x2019;` |

### 其他

- **空白字符**：在带有前导/尾随空格的 `<a:t>` 上使用 `xml:space="preserve"`
- **XML 解析**：使用 `defusedxml.minidom`，而不是 `xml.etree.ElementTree`（会破坏命名空间）
