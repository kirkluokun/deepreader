# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: clean_rule.py
@time: 2025-06-29 12:00
@desc: 通用的 Markdown 文本清洗函数，用于移除各种不需要的格式和标签。
"""
import re


def clean_markdown_text(markdown_text: str) -> str:
    """
    一个通用的 Markdown 文本清洗函数，移除各种不需要的格式和标签。
    旨在提供纯净的文本内容，用于后续的自然语言处理。
    
    清洗规则包括:
    - 移除 Markdown 图片和链接
    - 移除所有 HTML 标签
    - 移除 PDF 转换产生的伪标题 (如 '# 图表 ...')
    - 移除 HTML 实体引用
    - 移除 marker 工具特有的 content-ref 标签
    - 移除 Markdown 的强调符号 (如 * 和 **)
    - 移除所有空行并标准化空白字符
    """
    if not isinstance(markdown_text, str):
        return ""
        
    cleaned_text = markdown_text

    # 1. 移除 Markdown 格式的图片和链接
    cleaned_text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", cleaned_text)
    cleaned_text = re.sub(r"\[[^\]]*\]\([^)]*\)", "", cleaned_text)

    # 2. 移除 HTML 图片标签
    cleaned_text = re.sub(r"<img[^>]*>", "", cleaned_text, flags=re.IGNORECASE)

    # 3. 移除各种 span 标签
    cleaned_text = re.sub(r"<span id=\"page-\d+-\d+\"></span>", "", cleaned_text)
    cleaned_text = re.sub(r"<span id=\"[^\"]*\"></span>", "", cleaned_text)
    cleaned_text = re.sub(r"<span class=\"[^\"]*\"></span>", "", cleaned_text)
    cleaned_text = re.sub(r"<span[^>]*></span>", "", cleaned_text)

    # 4. 移除伪标题
    cleaned_text = re.sub(r"^#+\s*<span[^>]*></span>\s*", "", cleaned_text, flags=re.MULTILINE)
    cleaned_text = re.sub(r"^(#+\s+)(?=图)", "", cleaned_text, flags=re.MULTILINE)
    cleaned_text = re.sub(r"^(#+\s+)(?=表)", "", cleaned_text, flags=re.MULTILINE)

    # 5. 移除其他常见的HTML标签
    cleaned_text = re.sub(r"</?div[^>]*>", "", cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"</?p[^>]*>", "", cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"<br[^>]*>", "", cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"<a[^>]*>(.*?)</a>", r"\\1", cleaned_text, flags=re.IGNORECASE | re.DOTALL)
    cleaned_text = re.sub(r"<!--.*?-->", "", cleaned_text, flags=re.DOTALL)
    cleaned_text = re.sub(r"<style[^>]*>.*?</style>", "", cleaned_text, flags=re.IGNORECASE | re.DOTALL)
    cleaned_text = re.sub(r"<script[^>]*>.*?</script>", "", cleaned_text, flags=re.IGNORECASE | re.DOTALL)
    # 通用规则，移除所有剩余的HTML标签
    cleaned_text = re.sub(r'<[^>]*>', '', cleaned_text)

    # 6. 移除 HTML 实体引用
    cleaned_text = re.sub(r"&nbsp;", " ", cleaned_text)
    cleaned_text = re.sub(r"&amp;", "&", cleaned_text)
    cleaned_text = re.sub(r"&lt;", "<", cleaned_text)
    cleaned_text = re.sub(r"&gt;", ">", cleaned_text)
    cleaned_text = re.sub(r"&quot;", '"', cleaned_text)
    cleaned_text = re.sub(r"&#\d+;", "", cleaned_text)
    cleaned_text = re.sub(r"&[a-zA-Z]+;", "", cleaned_text)

    # 7. 移除 marker 特有的 content-ref 标签
    cleaned_text = re.sub(r"<content-ref[^>]*>.*?</content-ref>", "", cleaned_text, flags=re.IGNORECASE | re.DOTALL)
    cleaned_text = re.sub(r"<content-ref[^>]*/>", "", cleaned_text, flags=re.IGNORECASE)

    # 8. 移除 Markdown 强调符号
    cleaned_text = re.sub(r"\*", "", cleaned_text)
    
    # 9. 清理空白字符并移除所有空行
    cleaned_text = re.sub(r" +", " ", cleaned_text) # 合并多个连续空格
    lines = cleaned_text.split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    cleaned_text = '\n'.join(non_empty_lines)

    return cleaned_text
