# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: tools.py
@time: 2025-06-25 12:00
@desc: 将 scraper 子模块中的转换器函数注册为 LangChain/LangGraph 工具。
"""

from typing import List
from langchain_core.tools import tool

# 导入底层的转换逻辑
from .pdf_converter import convert_pdf_to_markdown
from .epub_converter import convert_epub_to_markdown
from .web_scraper import scrape_urls_to_markdown


@tool
def pdf_to_markdown_tool(file_path: str) -> str:
    """
    Converts a single PDF file from a local path into clean, readable Markdown text.
    Use this tool when you need to read and process the content of a local PDF document.
    
    Args:
        file_path (str): The local file path to the PDF document.
    """
    return convert_pdf_to_markdown(file_path)


@tool
def epub_to_markdown_tool(file_path: str) -> str:
    """
    Converts a single EPUB file from a local path into clean, readable Markdown text.
    Use this tool when you need to read and process the content of a local EPUB e-book.
    
    Args:
        file_path (str): The local file path to the EPUB document.
    """
    return convert_epub_to_markdown(file_path)


@tool
async def web_urls_to_markdown_tool(urls: List[str]) -> List[str]:
    """
    Scrapes the content of one or more web URLs and returns a list of clean Markdown strings.
    Use this tool when you need to read and process the content from web pages.
    
    Args:
        urls (List[str]): A list of one or more URLs to be scraped.
    """
    # 注意：这是一个异步工具，调用它的 LangGraph Agent 必须能够处理异步操作。
    return await scrape_urls_to_markdown(urls)


# 将所有工具收集到一个列表中，方便 Agent 绑定和使用
all_scraper_tools = [
    pdf_to_markdown_tool,
    epub_to_markdown_tool,
    web_urls_to_markdown_tool,
] 