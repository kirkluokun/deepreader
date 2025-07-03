#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown转PDF使用示例

展示如何使用md2pdf模块将markdown文件转换为PDF
"""

import os
from pathlib import Path
from md2pdf import MarkdownToPDFConverter


def example_convert_file():
    """示例：转换markdown文件为PDF"""
    print("=== 示例1: 转换markdown文件为PDF ===")
    
    # 创建转换器
    converter = MarkdownToPDFConverter()
    
    # 示例markdown文件路径
    input_file = "../input/sample.md"  # 替换为你的markdown文件路径
    output_file = "../output/sample.pdf"  # 输出PDF文件路径
    
    if os.path.exists(input_file):
        # 转换文件
        success = converter.convert_file(input_file, output_file)
        
        if success:
            print(f"✅ 转换成功! PDF文件已生成: {output_file}")
        else:
            print("❌ 转换失败!")
    else:
        print(f"⚠️  输入文件不存在: {input_file}")


def example_convert_content():
    """示例：转换markdown内容为PDF"""
    print("\n=== 示例2: 转换markdown内容为PDF ===")
    
    # 示例markdown内容
    markdown_content = """
# 测试文档

这是一个**测试文档**，用于演示markdown转PDF功能。

## 功能特点

1. **支持中文**: 完全支持中文字符和格式
2. **表格支持**: 可以转换表格内容
3. **代码高亮**: 支持代码块语法高亮
4. **自定义样式**: 可以自定义CSS样式

## 代码示例

```python
def hello_world():
    print("Hello, 世界!")
    return "成功"
```

## 表格示例

| 功能 | 支持 | 说明 |
|------|------|------|
| 中文 | ✅ | 完全支持 |
| 表格 | ✅ | 样式美观 |
| 代码 | ✅ | 语法高亮 |

## 引用示例

> 这是一个引用示例
> 支持多行引用内容

---

**结论**: 这个工具可以很好地将markdown转换为PDF格式。
"""
    
    # 创建转换器
    converter = MarkdownToPDFConverter()
    
    # 输出文件路径
    output_file = "../output/content_sample.pdf"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 转换内容
    success = converter.convert_content(markdown_content, output_file)
    
    if success:
        print(f"✅ 转换成功! PDF文件已生成: {output_file}")
    else:
        print("❌ 转换失败!")


def example_custom_css():
    """示例：使用自定义CSS样式"""
    print("\n=== 示例3: 使用自定义CSS样式 ===")
    
    # 自定义CSS样式
    custom_css = """
    @page {
        size: A4;
        margin: 1.5cm;
    }
    
    body {
        font-family: "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
        font-size: 14pt;
        line-height: 1.8;
        color: #2c3e50;
    }
    
    h1 {
        color: #e74c3c;
        font-size: 28pt;
        border-bottom: 3px solid #e74c3c;
        padding-bottom: 0.5em;
    }
    
    h2 {
        color: #3498db;
        font-size: 22pt;
        border-left: 4px solid #3498db;
        padding-left: 0.5em;
    }
    
    code {
        background-color: #ecf0f1;
        color: #c0392b;
        padding: 0.3em 0.5em;
        border-radius: 4px;
        font-family: "Monaco", "Consolas", monospace;
    }
    
    blockquote {
        border-left: 4px solid #f39c12;
        background-color: #fdf6e3;
        padding: 1em;
        margin: 1em 0;
        font-style: italic;
    }
    """
    
    # 创建使用自定义CSS的转换器
    converter = MarkdownToPDFConverter(css_style=custom_css)
    
    # 示例内容
    markdown_content = """
# 自定义样式示例

这个文档使用了**自定义CSS样式**。

## 特点

- 红色的一级标题
- 蓝色的二级标题  
- 自定义的代码样式：`print("Hello World")`

> 这是一个使用自定义样式的引用块
> 具有不同的背景色和边框
"""
    
    # 输出文件
    output_file = "../output/custom_style_sample.pdf"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 转换
    success = converter.convert_content(markdown_content, output_file)
    
    if success:
        print(f"✅ 转换成功! 自定义样式PDF已生成: {output_file}")
    else:
        print("❌ 转换失败!")


def create_sample_markdown():
    """创建示例markdown文件"""
    print("\n=== 创建示例markdown文件 ===")
    
    sample_content = """# 示例文档

这是一个用于测试的示例markdown文档。

## 基本格式

### 文本样式
- **粗体文本**
- *斜体文本*
- `行内代码`
- ~~删除线~~

### 列表
1. 有序列表项1
2. 有序列表项2
   - 嵌套无序列表
   - 另一个嵌套项

### 链接和图片
[这是一个链接](https://example.com)

## 代码块

```python
def greet(name):
    '''问候函数'''
    return f"你好, {name}!"

# 调用函数
message = greet("世界")
print(message)
```

## 表格

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 数据1 | 数据2 | 数据3 |
| 中文 | English | 123 |
| ✅ | ❌ | ⚠️ |

## 引用

> 这是一个引用块
> 
> 可以包含多行内容
> 
> —— 作者

## 分割线

---

## 总结

这个示例展示了markdown的各种基本语法，转换为PDF后应该保持良好的格式。
"""
    
    # 确保目录存在
    input_dir = "../input"
    os.makedirs(input_dir, exist_ok=True)
    
    # 写入示例文件
    sample_file = os.path.join(input_dir, "sample.md")
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    print(f"✅ 示例markdown文件已创建: {sample_file}")
    return sample_file


def main():
    """主函数：运行所有示例"""
    print("🚀 Markdown转PDF示例程序")
    print("=" * 50)
    
    # 创建示例markdown文件
    create_sample_markdown()
    
    # 运行示例
    example_convert_file()
    example_convert_content()
    example_custom_css()
    
    print("\n" + "=" * 50)
    print("✨ 所有示例执行完成!")
    print("\n📋 使用说明:")
    print("1. 确保已安装依赖: pip install weasyprint")
    print("2. 如果weasyprint安装失败，可以使用: brew install wkhtmltopdf (MacOS)")
    print("3. 查看生成的PDF文件在 ../output/ 目录中")


if __name__ == '__main__':
    main() 