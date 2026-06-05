#!/usr/bin/env python3
"""
批量翻译Markdown文件的脚本
将所有.md文件翻译成中文，并保存为*-zh_CN.md格式
"""

import os
import re
from pathlib import Path

def should_skip_translation(filepath):
    """判断是否应该跳过翻译此文件"""
    # 跳过已经是中文版本的文件
    if filepath.endswith('-zh_CN.md'):
        return True
    
    # 跳过第三方许可声明文件（法律文档不应翻译）
    if 'THIRD_PARTY_NOTICES' in filepath:
        return True
    
    # 跳过LICENSE文件
    if 'LICENSE' in filepath.upper():
        return True
    
    return False

def translate_markdown_content(content, filepath):
    """
    翻译markdown内容
    注意：这是一个简化的版本，实际使用时需要集成翻译API
    这里只提供框架和规则
    """
    
    # 保留的代码块不翻译
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f'__CODE_BLOCK_{len(code_blocks)-1}__'
    
    # 保存代码块
    content = re.sub(r'```[\s\S]*?```', save_code_block, content)
    
    # 保留的行内代码不翻译
    inline_codes = []
    def save_inline_code(match):
        inline_codes.append(match.group(0))
        return f'__INLINE_CODE_{len(inline_codes)-1}__'
    
    content = re.sub(r'`[^`]+`', save_inline_code, content)
    
    # 保留URL链接
    urls = []
    def save_url(match):
        urls.append(match.group(0))
        return f'__URL_{len(urls)-1}__'
    
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', save_url, content)
    
    # 保留图片链接
    images = []
    def save_image(match):
        images.append(match.group(0))
        return f'__IMAGE_{len(images)-1}__'
    
    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', save_image, content)
    
    # 保留HTML标签
    html_tags = []
    def save_html_tag(match):
        html_tags.append(match.group(0))
        return f'__HTML_TAG_{len(html_tags)-1}__'
    
    content = re.sub(r'<[^>]+>', save_html_tag, content)
    
    # 在这里添加实际的翻译逻辑
    # 由于这是示例，我们只返回原始内容
    # 实际使用时应该调用翻译API
    
    print(f"警告: 文件 {filepath} 需要翻译，但尚未实现自动翻译功能")
    print("请手动翻译或使用翻译API")
    
    # 恢复占位符
    for i, code in enumerate(code_blocks):
        content = content.replace(f'__CODE_BLOCK_{i}__', code)
    
    for i, code in enumerate(inline_codes):
        content = content.replace(f'__INLINE_CODE_{i}__', code)
    
    for i, url in enumerate(urls):
        content = content.replace(f'__URL_{i}__', url)
    
    for i, image in enumerate(images):
        content = content.replace(f'__IMAGE_{i}__', image)
    
    for i, tag in enumerate(html_tags):
        content = content.replace(f'__HTML_TAG_{i}__', tag)
    
    return content

def process_markdown_files(root_dir):
    """处理目录中的所有markdown文件"""
    root_path = Path(root_dir)
    
    # 查找所有.md文件
    md_files = list(root_path.rglob('*.md'))
    
    print(f"找到 {len(md_files)} 个markdown文件")
    
    translated_count = 0
    skipped_count = 0
    
    for md_file in md_files:
        filepath = str(md_file)
        
        # 检查是否应该跳过
        if should_skip_translation(filepath):
            skipped_count += 1
            continue
        
        # 读取文件内容
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"读取文件失败 {filepath}: {e}")
            continue
        
        # 生成新文件名
        new_filepath = filepath.replace('.md', '-zh_CN.md')
        
        # 如果目标文件已存在，跳过
        if os.path.exists(new_filepath):
            print(f"跳过已存在的文件: {new_filepath}")
            skipped_count += 1
            continue
        
        # 翻译内容
        translated_content = translate_markdown_content(content, filepath)
        
        # 写入新文件
        try:
            with open(new_filepath, 'w', encoding='utf-8') as f:
                f.write(translated_content)
            translated_count += 1
            print(f"✓ 已处理: {filepath} -> {new_filepath}")
        except Exception as e:
            print(f"写入文件失败 {new_filepath}: {e}")
    
    print(f"\n完成!")
    print(f"已翻译: {translated_count} 个文件")
    print(f"已跳过: {skipped_count} 个文件")

if __name__ == '__main__':
    # 设置根目录
    root_directory = '/var/www/volumes/github/onepkg/skills/skills'
    
    print("开始批量翻译Markdown文件...")
    print(f"根目录: {root_directory}\n")
    
    process_markdown_files(root_directory)
