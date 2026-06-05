**重要：你必须按顺序完成这些步骤。不要跳过步骤直接编写代码。**

如果你需要填写PDF表单，首先检查该PDF是否包含可填写的表单字段。从该文件所在目录运行以下脚本：
 `python scripts/check_fillable_fields <file.pdf>`，然后根据结果进入"可填写字段"或"不可填写字段"部分并按照相应说明操作。

# 可填写字段

如果PDF包含可填写的表单字段：
- 从该文件所在目录运行以下脚本：`python scripts/extract_form_field_info.py <input.pdf> <field_info.json>`。它将创建一个JSON文件，包含字段列表，格式如下：
```
[
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "rect": ([left, bottom, right, top] bounding box in PDF coordinates, y=0 is the bottom of the page),
    "type": ("text", "checkbox", "radio_group", or "choice"),
  },
  // Checkboxes have "checked_value" and "unchecked_value" properties:
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "type": "checkbox",
    "checked_value": (Set the field to this value to check the checkbox),
    "unchecked_value": (Set the field to this value to uncheck the checkbox),
  },
  // Radio groups have a "radio_options" list with the possible choices.
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "type": "radio_group",
    "radio_options": [
      {
        "value": (set the field to this value to select this radio option),
        "rect": (bounding box for the radio button for this option)
      },
      // Other radio options
    ]
  },
  // Multiple choice fields have a "choice_options" list with the possible choices:
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "type": "choice",
    "choice_options": [
      {
        "value": (set the field to this value to select this option),
        "text": (display text of the option)
      },
      // Other choice options
    ],
  }
]
```
- 使用以下脚本将PDF转换为PNG（每页一张图片）（从该文件所在目录运行）：
`python scripts/convert_pdf_to_images.py <file.pdf> <output_directory>`
然后分析图片以确定每个表单字段的用途（确保将边界框的PDF坐标转换为图片坐标）。
- 创建一个`field_values.json`文件，格式如下，包含每个字段要填入的值：
```
[
  {
    "field_id": "last_name", // Must match the field_id from `extract_form_field_info.py`
    "description": "The user's last name",
    "page": 1, // Must match the "page" value in field_info.json
    "value": "Simpson"
  },
  {
    "field_id": "Checkbox12",
    "description": "Checkbox to be checked if the user is 18 or over",
    "page": 1,
    "value": "/On" // If this is a checkbox, use its "checked_value" value to check it. If it's a radio button group, use one of the "value" values in "radio_options".
  },
  // more fields
]
```
- 从该文件所在目录运行`fill_fillable_fields.py`脚本以创建已填写的PDF：
`python scripts/fill_fillable_fields.py <input pdf> <field_values.json> <output pdf>`
该脚本会验证你提供的字段ID和值是否有效；如果打印出错误信息，请修正相应字段后重试。

# 不可填写字段

如果PDF没有可填写的表单字段，你将添加文本注释。首先尝试从PDF结构中提取坐标（更精确），如有需要再回退到视觉估算。

## 第一步：首先尝试结构提取

运行以下脚本提取文本标签、线条和复选框及其精确的PDF坐标：
`python scripts/extract_form_structure.py <input.pdf> form_structure.json`

这将创建一个JSON文件，包含：
- **labels**：每个文本元素及其精确坐标（PDF点坐标中的x0、top、x1、bottom）
- **lines**：定义行边界的水平线
- **checkboxes**：作为复选框的小方形矩形（含中心坐标）
- **row_boundaries**：从水平线计算得出的行顶部/底部位置

**检查结果**：如果`form_structure.json`包含有意义的标签（与表单字段对应的文本元素），请使用**方法A：基于结构的坐标**。如果PDF是扫描/基于图片的，且标签很少或没有，请使用**方法B：视觉估算**。

---

## 方法A：基于结构的坐标（首选）

当`extract_form_structure.py`在PDF中找到了文本标签时使用此方法。

### A.1：分析结构

读取form_structure.json并识别：

1. **标签组**：组成单个标签的相邻文本元素（例如"Last"+"Name"）
2. **行结构**：具有相似`top`值的标签位于同一行
3. **字段列**：输入区域在标签结束后开始（x0 = label.x1 + gap）
4. **复选框**：直接从结构中使用复选框坐标

**坐标系**：PDF坐标，其中y=0在页面顶部，y向下递增。

### A.2：检查遗漏元素

结构提取可能无法检测到所有表单元素。常见情况：
- **圆形复选框**：只有方形矩形被检测为复选框
- **复杂图形**：装饰性元素或非标准表单控件
- **褪色或浅色元素**：可能无法被提取

如果在PDF图片中看到了form_structure.json中未包含的表单字段，则需要对这些特定字段使用**视觉分析**（参见下面的"混合方法"）。

### A.3：使用PDF坐标创建fields.json

对于每个字段，从提取的结构中计算输入坐标：

**文本字段：**
- entry x0 = label x1 + 5（标签后的小间距）
- entry x1 = 下一个标签的x0，或行边界
- entry top = 与标签top相同
- entry bottom = 下方的行边界线，或label bottom + row_height

**复选框：**
- 直接从form_structure.json中使用复选框矩形坐标
- entry_bounding_box = [checkbox.x0, checkbox.top, checkbox.x1, checkbox.bottom]

使用`pdf_width`和`pdf_height`创建fields.json（表示PDF坐标）：
```json
{
  "pages": [
    {"page_number": 1, "pdf_width": 612, "pdf_height": 792}
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Last name entry field",
      "field_label": "Last Name",
      "label_bounding_box": [43, 63, 87, 73],
      "entry_bounding_box": [92, 63, 260, 79],
      "entry_text": {"text": "Smith", "font_size": 10}
    },
    {
      "page_number": 1,
      "description": "US Citizen Yes checkbox",
      "field_label": "Yes",
      "label_bounding_box": [260, 200, 280, 210],
      "entry_bounding_box": [285, 197, 292, 205],
      "entry_text": {"text": "X"}
    }
  ]
}
```

**重要**：直接从form_structure.json使用`pdf_width`/`pdf_height`和坐标。

### A.4：验证边界框

在填写之前，检查边界框是否有错误：
`python scripts/check_bounding_boxes.py fields.json`

这会检查相交的边界框以及对于字体大小来说过小的输入框。在填写前修复所有报告的错误。

---

## 方法B：视觉估算（备选方案）

当PDF是扫描/图片格式且结构提取未找到可用的文本标签（例如，所有文本显示为"(cid:X)"模式）时使用此方法。

### B.1：将PDF转换为图片

`python scripts/convert_pdf_to_images.py <input.pdf> <images_dir/>`

### B.2：初始字段识别

检查每页图片以识别表单区域并获取字段位置的**粗略估计**：
- 表单字段标签及其大致位置
- 输入区域（用于文本输入的行、框或空白区域）
- 复选框及其大致位置

对于每个字段，记下大致像素坐标（尚不需要精确）。

### B.3：缩放精化（对准确性至关重要）

对于每个字段，裁剪估计位置周围的区域以精确精化坐标。

**使用ImageMagick创建缩放裁剪：**
```bash
magick <page_image> -crop <width>x<height>+<x>+<y> +repage <crop_output.png>
```

其中：
- `<x>, <y>` = 裁剪区域的左上角（使用你的粗略估计减去边距）
- `<width>, <height>` = 裁剪区域的大小（字段区域加上每侧约50px边距）

**示例：** 为了精化估计在(100, 150)附近的"Name"字段：
```bash
magick images_dir/page_1.png -crop 300x80+50+120 +repage crops/name_field.png
```

（注意：如果`magick`命令不可用，请尝试使用相同参数的`convert`）。

**检查裁剪后的图片**以确定精确坐标：
1. 确定输入区域开始的确切像素位置（标签之后）
2. 确定输入区域结束的位置（下一个字段或边缘之前）
3. 确定输入行/框的顶部和底部

**将裁剪坐标转换回完整图片坐标：**
- full_x = crop_x + crop_offset_x
- full_y = crop_y + crop_offset_y

示例：如果裁剪起始于(50, 120)且输入框在裁剪内起始于(52, 18)：
- entry_x0 = 52 + 50 = 102
- entry_top = 18 + 120 = 138

**对每个字段重复此过程**，尽可能将附近字段分组到单个裁剪中。

### B.4：使用精化坐标创建fields.json

使用`image_width`和`image_height`创建fields.json（表示图片坐标）：
```json
{
  "pages": [
    {"page_number": 1, "image_width": 1700, "image_height": 2200}
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Last name entry field",
      "field_label": "Last Name",
      "label_bounding_box": [120, 175, 242, 198],
      "entry_bounding_box": [255, 175, 720, 218],
      "entry_text": {"text": "Smith", "font_size": 10}
    }
  ]
}
```

**重要**：使用`image_width`/`image_height`和来自缩放分析的精化像素坐标。

### B.5：验证边界框

在填写之前，检查边界框是否有错误：
`python scripts/check_bounding_boxes.py fields.json`

这会检查相交的边界框以及对于字体大小来说过小的输入框。在填写前修复所有报告的错误。

---

## 混合方法：结构+视觉

当结构提取对大多数字段有效但遗漏了某些元素（例如圆形复选框、非标准表单控件）时使用此方法。

1. **使用方法A**处理form_structure.json中检测到的字段
2. **将PDF转换为图片**以便对缺失字段进行视觉分析
3. **使用缩放精化**（来自方法B）处理缺失字段
4. **合并坐标**：对于来自结构提取的字段，使用`pdf_width`/`pdf_height`。对于视觉估算的字段，必须将图片坐标转换为PDF坐标：
   - pdf_x = image_x * (pdf_width / image_width)
   - pdf_y = image_y * (pdf_height / image_height)
5. **在fields.json中使用单一坐标系** - 将所有坐标转换为带有`pdf_width`/`pdf_height`的PDF坐标

---

## 第二步：填写前验证

**在填写前始终验证边界框：**
`python scripts/check_bounding_boxes.py fields.json`

这会检查：
- 相交的边界框（会导致文本重叠）
- 对指定字体大小来说过小的输入框

在继续之前修复fields.json中报告的所有错误。

## 第三步：填写表单

填充脚本会自动检测坐标系并处理转换：
`python scripts/fill_pdf_form_with_annotations.py <input.pdf> fields.json <output.pdf>`

## 第四步：验证输出

将已填写的PDF转换为图片并验证文本位置：
`python scripts/convert_pdf_to_images.py <output.pdf> <verify_images/>`

如果文本位置不正确：
- **方法A**：检查是否使用了来自form_structure.json的PDF坐标以及`pdf_width`/`pdf_height`
- **方法B**：检查图片尺寸是否匹配且坐标是精确像素
- **混合方法**：确保视觉估算字段的坐标转换正确
