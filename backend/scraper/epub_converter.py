# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: epub_converter.py
@time: 2024-07-29 12:00
@desc: 使用 ebooklib 实现 EPUB 到纯净 Markdown 的转换
"""
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import logging
from pathlib import Path
from gpt_researcher.deepreader.backend.scraper.clean_rule import clean_markdown_text
import sys

def convert_epub_to_markdown(file_path: str) -> str:
    """
    将 EPUB 文件转换为干净的 Markdown 文本。
    
    Args:
        file_path (str): EPUB 文件的路径。
        
    Returns:
        str: 转换后的 Markdown 文本。
    """
    try:
        book = epub.read_epub(file_path)
        full_text = []

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                # 提取所有文本，并用双换行符作为分隔，以保留段落结构
                text = soup.get_text(separator='\n\n', strip=True)
                full_text.append(text)
        
        # 将所有部分合并成一个单一的文本
        raw_markdown = "\n\n".join(full_text)
        
        # 使用统一的清洗函数进行深度清洗
        cleaned_markdown = clean_markdown_text(raw_markdown)
        
        logging.info(f"EPUB 文件 '{file_path}' 已成功转换为 Markdown 并清洗。")
        return cleaned_markdown

    except Exception as e:
        logging.error(f"处理 EPUB 文件 '{file_path}' 时发生错误: {e}", exc_info=True)
        return ""

if __name__ == "__main__":
    # 配置日志记录以进行测试
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 从命令行参数获取 EPUB 文件路径
    if len(sys.argv) < 2:
        print("用法: python gpt_researcher/deepreader/backend/scraper/epub_converter.py <epub文件的绝对路径>")
        sys.exit(1)
    
    test_epub_path = sys.argv[1]
    
    if not Path(test_epub_path).exists():
        logging.error(f"测试文件未找到: {test_epub_path}")
        logging.error("请提供一个有效的EPUB文件路径作为命令行参数。")
    else:
        logging.info(f"开始测试 EPUB 转换: {test_epub_path}")
        try:
            markdown_output = convert_epub_to_markdown(test_epub_path)
            logging.info("EPUB 转换和清洗成功完成。")
            
            # 生成与源文件同名、同目录的 .md 文件路径
            output_file = Path(test_epub_path).with_suffix('.md')
            output_file.write_text(markdown_output, encoding='utf-8')
            
            logging.info(f"转换后的 Markdown (前500字符):\n---")
            print(markdown_output[:500])
            logging.info(f"---\n完整输出已保存到: {output_file.resolve()}")
            
        except Exception as e:
            logging.error(f"在测试转换过程中发生错误: {e}", exc_info=True)
