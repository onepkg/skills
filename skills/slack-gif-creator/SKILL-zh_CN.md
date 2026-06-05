---
name: slack-gif-creator
description: 用于创建针对 Slack 优化的动画 GIF 的知识和工具。提供约束条件、验证工具和动画概念。当用户请求为 Slack 创建动画 GIF（例如"帮我制作一个关于 X 做 Y 的 Slack GIF"）时使用。
license: 完整条款见 LICENSE.txt
---

# Slack GIF 创建工具

提供用于创建针对 Slack 优化的动画 GIF 的工具包和知识。

## Slack 要求

**尺寸：**
- 表情符号 GIF：128x128（推荐）
- 消息 GIF：480x480

**参数：**
- 帧率：10-30（越低文件越小）
- 颜色数：48-128（越少文件越小）
- 时长：表情符号 GIF 控制在 3 秒以内

## 核心工作流

```python
from core.gif_builder import GIFBuilder
from PIL import Image, ImageDraw

# 1. Create builder
builder = GIFBuilder(width=128, height=128, fps=10)

# 2. Generate frames
for i in range(12):
    frame = Image.new('RGB', (128, 128), (240, 248, 255))
    draw = ImageDraw.Draw(frame)

    # Draw your animation using PIL primitives
    # (circles, polygons, lines, etc.)

    builder.add_frame(frame)

# 3. Save with optimization
builder.save('output.gif', num_colors=48, optimize_for_emoji=True)
```

## 绘制图形

### 处理用户上传的图片
如果用户上传了图片，请考虑他们是否希望：
- **直接使用**（例如"给这个做动画"、"拆分成帧"）
- **作为灵感参考**（例如"做类似的东西"）

使用 PIL 加载和处理图片：
```python
from PIL import Image

uploaded = Image.open('file.png')
# Use directly, or just as reference for colors/style
```

### 从头绘制
从头绘制图形时，使用 PIL ImageDraw 基本图形：

```python
from PIL import ImageDraw

draw = ImageDraw.Draw(frame)

# Circles/ovals
draw.ellipse([x1, y1, x2, y2], fill=(r, g, b), outline=(r, g, b), width=3)

# Stars, triangles, any polygon
points = [(x1, y1), (x2, y2), (x3, y3), ...]
draw.polygon(points, fill=(r, g, b), outline=(r, g, b), width=3)

# Lines
draw.line([(x1, y1), (x2, y2)], fill=(r, g, b), width=5)

# Rectangles
draw.rectangle([x1, y1, x2, y2], fill=(r, g, b), outline=(r, g, b), width=3)
```

**不要使用：**表情符号字体（跨平台不可靠）或假定此技能中存在预置图形。

### 让图形更具视觉效果

图形应精致且富有创意，而非过于简单。具体方法如下：

**使用较粗线条** - 始终将轮廓线和线条设置为 `width=2` 或更高。细线条（width=1）看起来粗糙且业余。

**增加视觉层次感**：
- 使用渐变制作背景（`create_gradient_background`）
- 叠加多个形状增加复杂度（例如，大星星内部嵌套小星星）

**让形状更有趣**：
- 不要只画一个普通的圆——添加高光、环或图案
- 星星可以添加发光效果（在背后绘制更大的半透明版本）
- 组合多种形状（星星+闪烁、圆形+环）

**注意颜色搭配**：
- 使用鲜艳、互补的颜色
- 增加对比度（浅色形状上使用深色轮廓，深色形状上使用浅色轮廓）
- 考虑整体构图

**对于复杂形状**（心形、雪花等）：
- 使用多边形和椭圆组合
- 仔细计算点以保证对称
- 添加细节（心形可以有高光曲线，雪花可以有复杂的枝杈）

要有创意和细节！一个好的 Slack GIF 应该看起来精致，而不是像占位图形。

## 可用工具

### GIFBuilder（`core.gif_builder`）
组装帧并针对 Slack 优化：
```python
builder = GIFBuilder(width=128, height=128, fps=10)
builder.add_frame(frame)  # Add PIL Image
builder.add_frames(frames)  # Add list of frames
builder.save('out.gif', num_colors=48, optimize_for_emoji=True, remove_duplicates=True)
```

### Validators（`core.validators`）
检查 GIF 是否符合 Slack 要求：
```python
from core.validators import validate_gif, is_slack_ready

# Detailed validation
passes, info = validate_gif('my.gif', is_emoji=True, verbose=True)

# Quick check
if is_slack_ready('my.gif'):
    print("Ready!")
```

### 缓动函数（`core.easing`）
平滑运动而非线性运动：
```python
from core.easing import interpolate

# Progress from 0.0 to 1.0
t = i / (num_frames - 1)

# Apply easing
y = interpolate(start=0, end=400, t=t, easing='ease_out')

# Available: linear, ease_in, ease_out, ease_in_out,
#           bounce_out, elastic_out, back_out
```

### 帧辅助函数（`core.frame_composer`）
满足常见需求的便捷函数：
```python
from core.frame_composer import (
    create_blank_frame,         # Solid color background
    create_gradient_background,  # Vertical gradient
    draw_circle,                # Helper for circles
    draw_text,                  # Simple text rendering
    draw_star                   # 5-pointed star
)
```

## 动画概念

### 抖动/振动
通过振荡偏移对象位置：
- 使用 `math.sin()` 或 `math.cos()` 配合帧索引
- 添加小幅随机变化以获得自然感
- 应用于 x 和/或 y 位置

### 脉冲/心跳
有节奏地缩放对象尺寸：
- 使用 `math.sin(t * frequency * 2 * math.pi)` 实现平滑脉冲
- 心跳效果：两次快速脉冲后暂停（调整正弦波）
- 在基础尺寸的 0.8 到 1.2 之间缩放

### 弹跳
物体下落并弹跳：
- 使用 `interpolate()` 配合 `easing='bounce_out'` 实现着陆
- 使用 `easing='ease_in'` 实现下落（加速）
- 通过每帧增加 y 速度来模拟重力

### 旋转
围绕中心旋转对象：
- PIL：`image.rotate(angle, resample=Image.BICUBIC)`
- 晃动效果：使用正弦波而非线性变化控制角度

### 淡入/淡出
逐渐出现或消失：
- 创建 RGBA 图像，调整 alpha 通道
- 或使用 `Image.blend(image1, image2, alpha)`
- 淡入：alpha 从 0 到 1
- 淡出：alpha 从 1 到 0

### 滑动
将对象从屏幕外移动到指定位置：
- 起始位置：帧边界之外
- 结束位置：目标位置
- 使用 `interpolate()` 配合 `easing='ease_out'` 实现平滑停止
- 过冲效果：使用 `easing='back_out'`

### 缩放
缩放和定位以实现缩放效果：
- 放大：从 0.1 缩放到 2.0，裁剪中心
- 缩小：从 2.0 缩放到 1.0
- 可添加运动模糊增加戏剧效果（PIL 滤镜）

### 爆炸/粒子爆发
创建向外辐射的粒子：
- 生成具有随机角度和速度的粒子
- 更新每个粒子：`x += vx`，`y += vy`
- 添加重力：`vy += gravity_constant`
- 随时间淡出粒子（降低 alpha）

## 优化策略

仅在要求缩小文件大小时，实施以下几种方法：

1. **减少帧数** - 降低帧率（10 而非 20）或缩短时长
2. **减少颜色数** - 使用 `num_colors=48` 而非 128
3. **缩小尺寸** - 128x128 而非 480x480
4. **去除重复帧** - 在 save() 中设置 `remove_duplicates=True`
5. **表情符号模式** - `optimize_for_emoji=True` 自动优化

```python
# Maximum optimization for emoji
builder.save(
    'emoji.gif',
    num_colors=48,
    optimize_for_emoji=True,
    remove_duplicates=True
)
```

## 理念

此技能提供：
- **知识**：Slack 的要求和动画概念
- **工具**：GIFBuilder、验证器、缓动函数
- **灵活性**：使用 PIL 基本图形创建动画逻辑

它不提供：
- 固定的动画模板或预制函数
- 表情符号字体渲染（跨平台不可靠）
- 内置于技能中的预置图形库

**关于用户上传的说明**：此技能不包含预置图形，但如果用户上传了图片，请使用 PIL 加载和处理——根据他们的请求判断是直接使用还是仅作为灵感参考。

发挥创意！结合各种概念（弹跳+旋转、脉冲+滑动等），充分利用 PIL 的全部功能。

## 依赖

```bash
pip install pillow imageio numpy
```
