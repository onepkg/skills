---
name: xlsx
description: "当电子表格文件是主要输入或输出时，任何时候都使用此技能。这意味着用户想要：打开、读取、编辑或修复现有的 .xlsx、.xlsm、.csv 或 .tsv 文件（例如，添加列、计算公式、格式化、图表、清理杂乱数据）；从头开始或从其他数据源创建新电子表格；或在表格文件格式之间转换。特别是当用户按名称或路径引用电子表格文件时触发 - 即使是随意的（如"我下载文件夹中的 xlsx"）- 并且想要对其执行某些操作或从中生成某些内容。还用于将杂乱的表格数据文件（格式错误的行、错位的标题、垃圾数据）清理或重组为适当的电子表格。交付物必须是电子表格文件。当主要交付物是 Word 文档、HTML 报告、独立 Python 脚本、数据库管道或 Google Sheets API 集成时，即使涉及表格数据，也不要触发。"
license: Proprietary. LICENSE.txt has complete terms
---

# 输出要求

## 所有 Excel 文件

### 专业字体
- 除非用户另有指示，否则对所有交付物使用一致、专业的字体（例如 Arial、Times New Roman）

### 零公式错误
- 每个 Excel 模型必须以零公式错误（#REF!、#DIV/0!、#VALUE!、#N/A、#NAME?）交付

### 保留现有模板（更新模板时）
- 修改文件时研究并精确匹配现有格式、样式和约定
- 永远不要将有标准格式强加于具有既定模式的文件
- 现有模板约定始终优先于这些指南

## 财务模型

### 颜色编码标准
除非用户或现有模板另有说明

#### 行业标准颜色约定
- **蓝色文本（RGB: 0,0,255）**：硬编码输入，以及用户将更改场景的数字
- **黑色文本（RGB: 0,0,0）**：所有公式和计算
- **绿色文本（RGB: 0,128,0）**：从同一工作簿中的其他工作表链接
- **红色文本（RGB: 255,0,0）**：指向其他文件的外部链接
- **黄色背景（RGB: 255,255,0）**：需要注意的关键假设或需要更新的单元格

### 数字格式标准

#### 必需格式规则
- **年份**：格式为文本字符串（例如，"2024" 而不是 "2,024"）
- **货币**：使用 $#,##0 格式；始终在标题中指定单位（"Revenue ($mm)"）
- **零**：使用数字格式使所有零显示为 "-"，包括百分比（例如，"$#,##0;($#,##0);-"）
- **百分比**：默认为 0.0% 格式（一位小数）
- **倍数**：格式为 0.0x 用于估值倍数（EV/EBITDA、P/E）
- **负数**：使用括号 (123) 而不是减号 -123

### 公式构建规则

#### 假设放置
- 将所有假设（增长率、利润率、倍数等）放在单独的假设单元格中
- 在公式中使用单元格引用而不是硬编码值
- 示例：使用 =B5*(1+$B$6) 而不是 =B5*1.05

#### 公式错误预防
- 验证所有单元格引用是否正确
- 检查范围中的差一错误
- 确保所有预测期间的公式一致
- 使用边缘情况测试（零值、负数）
- 验证没有意外的循环引用

#### 硬编码的文档要求
- 注释或在旁边的单元格中（如果在表格末尾）。格式："Source: [System/Document], [Date], [Specific Reference], [URL if applicable]"
- 示例：
  - "Source: Company 10-K, FY2024, Page 45, Revenue Note, [SEC EDGAR URL]"
  - "Source: Company 10-Q, Q2 2025, Exhibit 99.1, [SEC EDGAR URL]"
  - "Source: Bloomberg Terminal, 8/15/2025, AAPL US Equity"
  - "Source: FactSet, 8/20/2025, Consensus Estimates Screen"

# XLSX 创建、编辑和分析

## 概述

用户可能要求您创建、编辑或分析 .xlsx 文件的内容。您可以使用不同的工具和_workflow_来完成不同的任务。

## 重要要求

**LibreOffice 必需用于公式重新计算**：您可以假设 LibreOffice 已安装，用于使用 `scripts/recalc.py` 脚本重新计算公式值。该脚本在首次运行时自动配置 LibreOffice，包括在 Unix 套接字受限的沙盒环境中（由 `scripts/office/soffice.py` 处理）

## 读取和分析数据

### 使用 pandas 进行数据分析
对于数据分析、可视化和基本操作，使用 **pandas**，它提供强大的数据操作功能：

```python
import pandas as pd

# 读取 Excel
df = pd.read_excel('file.xlsx')  # 默认：第一张表
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)  # 所有表作为字典

# 分析
df.head()      # 预览数据
df.info()      # 列信息
df.describe()  # 统计

# 写入 Excel
df.to_excel('output.xlsx', index=False)
```

## Excel 文件工作流

## 关键：使用公式，而不是硬编码值

**始终使用 Excel 公式而不是在 Python 中计算值并硬编码它们。** 这确保电子表格保持动态和可更新。

### ❌ 错误 - 硬编码计算值
```python
# 不好：在 Python 中计算并硬编码结果
total = df['Sales'].sum()
sheet['B10'] = total  # 硬编码 5000

# 不好：在 Python 中计算增长率
growth = (df.iloc[-1]['Revenue'] - df.iloc[0]['Revenue']) / df.iloc[0]['Revenue']
sheet['C5'] = growth  # 硬编码 0.15

# 不好：Python 计算平均值
avg = sum(values) / len(values)
sheet['D20'] = avg  # 硬编码 42.5
```

### ✅ 正确 - 使用 Excel 公式
```python
# 好：让 Excel 计算总和
sheet['B10'] = '=SUM(B2:B9)'

# 好：增长率作为 Excel 公式
sheet['C5'] = '=(C4-C2)/C2'

# 好：使用 Excel 函数计算平均值
sheet['D20'] = '=AVERAGE(D2:D19)'
```

这适用于所有计算 - 总计、百分比、比率、差异等。当源数据更改时，电子表格应该能够重新计算。

## 常见工作流
1. **选择工具**：pandas 用于数据，openpyxl 用于公式/格式化
2. **创建/加载**：创建新工作簿或加载现有文件
3. **修改**：添加/编辑数据、公式和格式化
4. **保存**：写入文件
5. **重新计算公式（如果使用公式则强制）**：使用 scripts/recalc.py 脚本
   ```bash
   python scripts/recalc.py output.xlsx
   ```
6. **验证并修复任何错误**：
   - 脚本返回带有错误详细信息的 JSON
   - 如果 `status` 是 `errors_found`，检查 `error_summary` 获取特定错误类型和位置
   - 修复识别的错误并再次重新计算
   - 要修复的常见错误：
     - `#REF!`：无效的单元格引用
     - `#DIV/0!`：除以零
     - `#VALUE!`：公式中的数据类型错误
     - `#NAME?`：无法识别的公式名称

### 创建新 Excel 文件

```python
# 使用 openpyxl 进行公式和格式化
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
sheet = wb.active

# 添加数据
sheet['A1'] = 'Hello'
sheet['B1'] = 'World'
sheet.append(['Row', 'of', 'data'])

# 添加公式
sheet['B2'] = '=SUM(A1:A10)'

# 格式化
sheet['A1'].font = Font(bold=True, color='FF0000')
sheet['A1'].fill = PatternFill('solid', start_color='FFFF00')
sheet['A1'].alignment = Alignment(horizontal='center')

# 列宽
sheet.column_dimensions['A'].width = 20

wb.save('output.xlsx')
```

### 编辑现有 Excel 文件

```python
# 使用 openpyxl 保留公式和格式化
from openpyxl import load_workbook

# 加载现有文件
wb = load_workbook('existing.xlsx')
sheet = wb.active  # 或 wb['SheetName'] 用于特定表

# 使用多个表
for sheet_name in wb.sheetnames:
    sheet = wb[sheet_name]
    print(f"Sheet: {sheet_name}")

# 修改单元格
sheet['A1'] = 'New Value'
sheet.insert_rows(2)  # 在位置 2 插入行
sheet.delete_cols(3)  # 删除第 3 列

# 添加新表
new_sheet = wb.create_sheet('NewSheet')
new_sheet['A1'] = 'Data'

wb.save('modified.xlsx')
```

## 重新计算公式

由 openpyxl 创建或修改的 Excel 文件包含公式作为字符串，但不包含计算值。使用提供的 `scripts/recalc.py` 脚本重新计算公式：

```bash
python scripts/recalc.py <excel_file> [timeout_seconds]
```

示例：
```bash
python scripts/recalc.py output.xlsx 30
```

该脚本：
- 在首次运行时自动设置 LibreOffice 宏
- 重新计算所有表中的所有公式
- 扫描所有单元格的 Excel 错误（#REF!、#DIV/0! 等）
- 返回带有详细错误位置和计数的 JSON
- 在 Linux 和 macOS 上工作

## 公式验证清单

快速检查以确保公式正常工作：

### 基本验证
- [ ] **测试 2-3 个示例引用**：在构建完整模型之前验证它们是否拉取正确的值
- [ ] **列映射**：确认 Excel 列匹配（例如，第 64 列 = BL，而不是 BK）
- [ ] **行偏移**：记住 Excel 行是 1 索引的（DataFrame 第 5 行 = Excel 第 6 行）

### 常见陷阱
- [ ] **NaN 处理**：使用 `pd.notna()` 检查空值
- [ ] **最右侧列**：FY 数据通常在第 50+ 列
- [ ] **多个匹配**：搜索所有出现，而不仅仅是第一个
- [ ] **除以零**：在使用 `/` 之前检查分母（#DIV/0!）
- [ ] **错误引用**：验证所有单元格引用指向预期的单元格（#REF!）
- [ ] **跨表引用**：使用正确的格式（Sheet1!A1）链接表

### 公式测试策略
- [ ] **从小处开始**：在广泛应用之前在 2-3 个单元格上测试公式
- [ ] **验证依赖项**：检查公式中引用的所有单元格是否存在
- [ ] **测试边缘情况**：包括零、负数和非常大的值

### 解释 scripts/recalc.py 输出
该脚本返回带有错误详细信息的 JSON：
```json
{
  "status": "success",           // 或 "errors_found"
  "total_errors": 0,              // 错误总数
  "total_formulas": 42,           // 文件中的公式数量
  "error_summary": {              // 仅在发现错误时存在
    "#REF!": {
      "count": 2,
      "locations": ["Sheet1!B5", "Sheet1!C10"]
    }
  }
}
```

## 最佳实践

### 库选择
- **pandas**：最适合数据分析、批量操作和简单数据导出
- **openpyxl**：最适合复杂格式化、公式和 Excel 特定功能

### 使用 openpyxl
- 单元格索引是 1 基的（row=1, column=1 指的是单元格 A1）
- 使用 `data_only=True` 读取计算值：`load_workbook('file.xlsx', data_only=True)`
- **警告**：如果用 `data_only=True` 打开并保存，公式会被值替换并永久丢失
- 对于大文件：使用 `read_only=True` 进行读取或 `write_only=True` 进行写入
- 公式被保留但不评估 - 使用 scripts/recalc.py 更新值

### 使用 pandas
- 指定数据类型以避免推断问题：`pd.read_excel('file.xlsx', dtype={'id': str})`
- 对于大文件，读取特定列：`pd.read_excel('file.xlsx', usecols=['A', 'C', 'E'])`
- 正确处理日期：`pd.read_excel('file.xlsx', parse_dates=['date_column'])`

## 代码风格指南
**重要**：在为 Excel 操作生成 Python 代码时：
- 编写简洁、简明的 Python 代码，没有不必要的注释
- 避免冗长的变量名和冗余操作
- 避免不必要的 print 语句

**对于 Excel 文件本身**：
- 向具有复杂公式或重要假设的单元格添加注释
- 记录硬编码值的数据源
- 包括关键计算和模型部分的注释
