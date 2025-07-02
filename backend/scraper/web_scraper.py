# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: web_scraper.py
@time: 2024-07-25 11:00
@desc: 一个服务于 deepreader 的网页抓取工具，使用 Crawl4AI 提取内容。
"""
import asyncio
import logging
from typing import List, Optional

# 复用现有的 Crawl4AI 爬虫组件
from gpt_researcher.scraper.craw4ai_scraper.c4ai import Crawl4AIScraper

# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class WebScraper:
    """
    一个为 deepreader 组件设计的简化版爬虫，
    它使用 Crawl4AI 将指定 URL 的内容获取并转换为干净的 Markdown。
    """

    def __init__(self, urls: List[str]):
        """
        初始化 WebScraper。

        Args:
            urls (List[str]): 一个包含待抓取 URL 的列表。
        """
        if not isinstance(urls, list):
            raise TypeError("urls 必须是一个字符串列表。")
        self.urls = urls
        self.logger = logging.getLogger(__name__)

    async def _scrape_single_url(self, url: str) -> Optional[str]:
        """
        使用 Crawl4AIScraper 抓取单个 URL。

        Args:
            url (str): 要抓取的 URL。

        Returns:
            Optional[str]: 页面转换后的 Markdown 内容，如果抓取失败则返回 None。
        """
        self.logger.info(f"开始抓取 URL: {url}")
        try:
            scraper_instance = Crawl4AIScraper(link=url)
            # Crawl4AIScraper 的 scrape 方法返回 (内容, 图片链接列表, 标题)
            content, _, title = await scraper_instance.scrape()

            if content:
                self.logger.info(f"成功抓取 URL: {url} (标题: {title})")
                return content
            else:
                self.logger.warning(f"URL 未返回有效内容: {url}")
                return None
        except Exception as e:
            self.logger.error(f"抓取 {url} 时发生错误: {e}", exc_info=True)
            return None

    async def run(self) -> List[str]:
        """
        异步抓取在初始化时提供的所有 URL。

        Returns:
            List[str]: 一个包含已抓取 Markdown 内容的列表，抓取失败的 URL 会被忽略。
        """
        self.logger.info(f"为 {len(self.urls)} 个 URL 开始抓取任务。")
        tasks = [self._scrape_single_url(url) for url in self.urls]
        results = await asyncio.gather(*tasks)
        
        # 过滤掉抓取失败返回的 None
        successful_results = [res for res in results if res is not None]
        
        self.logger.info(f"抓取任务完成。成功抓取 {len(successful_results)} 个 URL。")
        return successful_results

async def scrape_urls_to_markdown(urls: List[str]) -> List[str]:
    """
    一个便捷函数，用于快速抓取 URL 列表并返回 Markdown 内容。

    Args:
        urls (List[str]): 需要抓取的 URL 列表。

    Returns:
        List[str]: 包含已抓取 Markdown 内容的列表。
    """
    scraper = WebScraper(urls)
    return await scraper.run()
