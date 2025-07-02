# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: docparsing_actions.py
@time: 2024-07-25 14:00
@desc: DeepReader 的文档解析和元数据提取核心动作
"""
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.json import JsonOutputParser
from pydantic import BaseModel, Field

from gpt_researcher.deepreader.backend.scraper.pdf_converter import (
    convert_pdf_to_markdown,
)
from gpt_researcher.deepreader.backend.scraper.epub_converter import (
    convert_epub_to_markdown,
)
from gpt_researcher.deepreader.backend.scraper.web_scraper import (
    scrape_urls_to_markdown,
)
from gpt_researcher.deepreader.backend.components.llm import call_smart_llm
from gpt_researcher.deepreader.backend.config import deep_reader_config
from thefuzz import fuzz
from json_repair import loads as json_repair_loads
from gpt_researcher.deepreader.backend.graph.actions.rag_actions import chunk_document


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def route_and_parse(document_path: str) -> str:
    """
    根据输入路径智能路由到合适的解析工具，并返回纯净的 MarkdownRESTRUCTURE_MD_PROMPT 文本。

    Args:
        document_path: 文档的本地路径或 URL。

    Returns:
        转换后的 Markdown 文本。
    """
    logging.info(f"开始路由和解析: {document_path}")
    
    # 优先处理 ArXiv 链接，因为它可能不包含 .pdf 后缀但应被视为 PDF
    if "arxiv.org/pdf/" in document_path or document_path.lower().endswith('.pdf'):
        logging.info("路由到 PDF 解析器。")
        return convert_pdf_to_markdown(document_path)
    
    elif document_path.lower().endswith('.epub'):
        logging.info("路由到 EPUB 解析器。")
        return convert_epub_to_markdown(document_path)
    
    elif document_path.lower().endswith('.md'):
        logging.info(f"直接读取 Markdown 文件: {document_path}")
        try:
            with open(document_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logging.error(f"读取 Markdown 文件时出错: {e}")
            raise ValueError(f"无法读取 Markdown 文件: {document_path}") from e
    
    elif document_path.lower().startswith('http'):
        logging.info("路由到 Web Scraper。")
        # Web scraper 工具需要一个 URL 列表并返回一个内容列表
        results: List[str] = await scrape_urls_to_markdown([document_path])
        return results[0] if results else ""
        
    else:
        logging.error(f"不支持的文件类型或路径: {document_path}")
        raise ValueError(f"不支持的文档来源: {document_path}")


class DocumentMetadata(BaseModel):
    """用于定义从文档中提取的元数据的 Pydantic 模型。"""
    title: Optional[str] = Field(None, description="文档的标题")
    author: Optional[List[str]] = Field(None, description="一个包含所有作者姓名的列表")
    creation_date: Optional[str] = Field(None, description="文档的创建日期 (例如 YYYY-MM-DD)")


async def extract_metadata(content_preview: str) -> Dict[str, Any]:
    """
    使用 LLM 从文本预览中提取结构化的元数据。

    Args:
        content_preview: 文本的前 1000 个字符。

    Returns:
        包含元数据的字典。
    """
    if not content_preview:
        return {"title": None, "author": [], "creation_date": None}

    logging.info("开始使用 LLM 提取元数据...")
    
    parser = JsonOutputParser(pydantic_object=DocumentMetadata)
    
    # 使用英文 Prompt 指导 LLM
    prompt = ChatPromptTemplate.from_template(
        """You are an expert librarian. Your task is to extract structured metadata from the beginning of a document.
        Analyze the following text and extract the 'title', 'author', and 'creation_date'.
        The 'author' field should be a list of strings, even if there is only one author.
        The values may be in Chinese.
        If a value for a field cannot be found, please return null for that field.
        Respond with a JSON object that strictly follows the provided schema.

        Document Preview:
        {preview}

        {format_instructions}
        """,
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    # 建议使用性能和成本更优的模型
    model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    
    chain = prompt | model | parser
    
    try:
        # Pydantic 解析器会自动将输出转换为字典
        metadata = await chain.ainvoke({"preview": content_preview})
        logging.info(f"成功提取元数据: {metadata}")
        return metadata
    except Exception as e:
        logging.error(f"提取元数据时发生错误: {e}")
        # 在失败时返回一个安全的默认值
        return {"title": "Unknown", "author": [], "creation_date": "Unknown"}


def _find_best_match_location(title: str, text: str, search_start_index: int = 0) -> Optional[Dict[str, Any]]:
    """在文本中为标题找到最佳模糊匹配位置。"""
    # 移除特殊字符进行更可靠的匹配
    clean_title = re.sub(r'[\*\_#"\\-]', '', title).strip()
    if not clean_title:
        return None

    best_ratio = 90  # 设置一个较高的初始阈值以确保匹配质量
    best_match = None

    # 简单的滑动窗口进行搜索
    # 注意：这可以被更高效的算法替代，但对于文档处理是足够的
    for match in re.finditer(re.escape(clean_title[0]), text[search_start_index:], re.IGNORECASE):
        start_pos = search_start_index + match.start()
        # 提取一个稍长的窗口以进行模糊匹配
        end_pos = start_pos + len(title) + 50  # 增加窗口大小以应对 slight LLM hallucinations
        window_text = text[start_pos:end_pos]
        
        # 为了更鲁棒地匹配，同样清理窗口文本中的特殊字符
        clean_window_text = re.sub(r'[\\*\\_#"\\\\-]', '', window_text)

        # 在窗口内进行模糊匹配
        ratio = fuzz.partial_ratio(clean_title, clean_window_text)
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = {
                "title": title,
                "matched_text": window_text.strip(),
                "start": start_pos,
                "end": end_pos,
                "ratio": ratio
            }
            if ratio > 98: # 如果几乎完美匹配，就停止搜索
                break

    return best_match


async def restructure_markdown_with_llm(markdown_text: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    使用LLM和模糊匹配来智能地重构Markdown文本的标题结构。

    Returns:
        一个包含 (重构后的Markdown文本, LLM生成的语义TOC) 的元组。
        如果失败，TOC 部分可能为 None。
    """
    logging.info("--- 开始使用 LLM 和模糊匹配进行 Markdown 智能重构 ---")
    
    semantic_toc = None
    # 步骤 1: 使用LLM提取语义目录 (TOC)
    llm_output = ""
    try:
        # 使用 f-string 代替 .format()，以避免 markdown 内容中的花括号导致格式化错误
        prompt = f"{RESTRUCTURE_MD_PROMPT}".replace("{markdown_content}", markdown_text)
        
        llm_output = await call_smart_llm(prompt)
        
        # 如果 LLM 调用失败（返回空字符串），则直接返回原文
        if not llm_output:
            logging.error("LLM 调用返回空结果，重构中止。")
            return markdown_text, None

        # 清理LLM可能返回的 markdown 代码块包装
        cleaned_llm_output = re.sub(r'^```(json)?\\s*|s*```$', '', llm_output, flags=re.DOTALL).strip()
        
        # 使用 json_repair 增加对不规范JSON的鲁棒性
        semantic_toc = json_repair_loads(cleaned_llm_output)
    except Exception as e:
        logging.error(f"LLM 提纲提取或JSON解析失败: {e}")
        logging.error(f"LLM 原始输出 (前500字符):\\n{llm_output[:500]}")
        return markdown_text, None # 失败则返回原文和 None

    # 步骤 2: 递归展平TOC并进行模糊匹配定位
    flat_toc = []
    def flatten_toc(nodes, level=1):
        for node in nodes:
            node['level'] = level # 确保level正确
            flat_toc.append(node)
            if node.get('children'):
                flatten_toc(node['children'], level + 1)

    flatten_toc(semantic_toc.get("toc", []))

    matched_titles = []
    current_search_pos = 0
    for item in flat_toc:
        title_text = item.get("title")
        if not title_text:
            continue
        
        # 清理标题中可能存在的换行符，确保标题是单行
        title_text = title_text.replace('\\n', ' ').replace('\n', ' ').strip()
        
        match_location = _find_best_match_location(title_text, markdown_text, current_search_pos)
        
        if match_location:
            # 更新搜索位置，避免重复匹配
            current_search_pos = match_location['start'] + 1
            matched_titles.append({
                "title": title_text,
                "level": item.get("level", 1),
                "start": match_location['start'],
            })

    if not matched_titles:
        logging.warning("未能从LLM生成的TOC中匹配到任何标题，返回原文。")
        return markdown_text, semantic_toc

    # 步骤 3: 基于定位的标题重构Markdown
    # 按 start 位置排序以确保正确顺序
    matched_titles.sort(key=lambda x: x['start'])
    
    reconstructed_parts = []
    last_pos = 0
    
    # 首先处理文档根目录到第一个标题的内容
    if matched_titles[0]['start'] > 0:
        content_before_first_title = markdown_text[0:matched_titles[0]['start']].strip()
        if content_before_first_title:
             reconstructed_parts.append(content_before_first_title)

    for i, match in enumerate(matched_titles):
        # 添加带新标记的标题
        header = f"{'#' * match['level']} {match['title']}"
        reconstructed_parts.append(header)
        
        # 提取并添加标题后的内容
        content_start = markdown_text.find('\n', match['start']) + 1 # 从标题的下一行开始
        if content_start == 0: # find returns -1 if not found, +1 makes it 0
            content_start = match['start'] + len(match['title'])

        # 计算内容结束位置，确保在下一个标题的行首结束，以避免切断标题标记
        next_title_start_pos = matched_titles[i + 1]['start'] if i + 1 < len(matched_titles) else len(markdown_text)
        # 从下一个标题的位置向前找到最近的换行符，那里才是真正应该结束的地方
        content_end = markdown_text.rfind('\n', 0, next_title_start_pos)
        if content_end == -1: # 如果找不到换行符（比如标题在文件最开头）
            content_end = next_title_start_pos

        content = markdown_text[content_start:content_end].strip()
        if content:
            reconstructed_parts.append(content)

    # 使用正确的换行符 `\n\n` 来连接各个部分，而不是 `\\n\\n`
    final_markdown = "\n\n".join(reconstructed_parts)
    logging.info("--- Markdown 智能重构完成 ---")
    return final_markdown, semantic_toc


def parse_markdown_to_json_toc(markdown_text: str) -> Dict[str, Any]:
    """
    使用正则表达式解析 Markdown 文本，根据标题（#, ##, ...）构建一个嵌套的 JSON 目录结构 (TOC)。

    每个节点包含:
    - title: 章节标题
    - level: 标题级别 (1 for #, 2 for ##, etc.)
    - content: 从当前标题到下一个同级或更高级别标题之间的文本内容。
    - children: 一个包含子章节节点的列表。

    Args:
        markdown_text: 完整的 Markdown 文本。

    Returns:
        一个代表整个文档结构的嵌套字典。如果无法解析或没有标题，则返回空字典。
    """
    lines = markdown_text.split('\n')
    toc = {'title': 'Document Root', 'level': 0, 'content': [], 'children': []}
    path = [toc]

    for line in lines:
        match = re.match(r'^(#+)\s+(.*)', line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            
            node = {'title': title, 'level': level, 'content': [], 'children': []}
            
            while path[-1]['level'] >= level:
                path.pop()
            
            path[-1]['children'].append(node)
            path.append(node)
        else:
            path[-1]['content'].append(line)

    def finalize_content(node):
        node['content'] = '\n'.join(node['content']).strip()
        for child in node['children']:
            finalize_content(child)

    finalize_content(toc)
    
    if not toc['children']:
        logging.info("未在文本中找到任何 Markdown 标题，无法生成 TOC。")
        return {}
        
    return toc


def chunk_text_by_size(markdown_text: str, chunk_size: int = 5000, overlap_ratio: float = 0.15) -> List[str]:
    """
    当 Markdown 文本中没有标题时，将其按指定的字数阈值进行弹性切分，并支持片段间的重叠。

    Args:
        markdown_text: 完整的 Markdown 文本。
        chunk_size: 每个片段的目标字数。
        overlap_ratio: 片段间的重叠比例 (0.0 to 1.0)。

    Returns:
        一个包含文本片段的列表。
    """
    if not markdown_text:
        return []

    if not (0 <= overlap_ratio < 1):
        logging.warning(f"重叠比例必须在 0.0 和 1.0 之间，收到的值为 {overlap_ratio}。将使用 0.0。")
        overlap_ratio = 0.0

    overlap_size = int(chunk_size * overlap_ratio)
    step_size = chunk_size - overlap_size
    
    # 确保 step_size 大于 0，防止无限循环
    if step_size <= 0:
        logging.error("chunk_size 和 overlap_ratio 的设置导致步长小于等于0，无法分片。")
        return []

    logging.info(f"开始按尺寸（{chunk_size}字）和重叠（{overlap_size}字）对文本进行分片...")
    text_length = len(markdown_text)
    
    chunks = [markdown_text[i:i + chunk_size] for i in range(0, text_length, step_size)]
    
    # 如果最后一个片段为空，则移除（当文本长度恰好是步长的倍数时可能发生）
    if chunks and not chunks[-1]:
        chunks.pop()

    logging.info(f"文本被切分为 {len(chunks)} 个片段。")
    return chunks


async def structure_document_action(state: "DeepReaderState") -> Dict[str, Any]:
    """
    根据原始 Markdown 内容和配置策略，决定并执行文档结构化。
    - 如果策略是 'snippet'，则直接按字数分片。
    - 如果策略是 'chapter'，则优先尝试LLM重构，失败则回退到正则解析。
    """
    logging.info("--- 开始文档结构化解析 ---")
    markdown_content = state.get("raw_markdown_content")
    if not markdown_content:
        logging.error("文档结构化失败：'raw_markdown_content' 为空。")
        return {"error": "Cannot structure document: raw_markdown_content is empty."}

    # 根据配置策略决定执行路径
    if deep_reader_config.PARSING_STRATEGY == 'snippet':
        logging.info(f"配置策略为 'snippet'，直接按字数分片（大小: {deep_reader_config.SNIPPET_CHUNK_SIZE}）。")
        snippets_text = chunk_text_by_size(
            markdown_content,
            chunk_size=deep_reader_config.SNIPPET_CHUNK_SIZE
        )
        snippets_structured = [
            {"content": text, "status": "unread"} for text in snippets_text
        ]
        return {"table_of_contents": None, "reading_snippets": snippets_structured}

    # # --- 'chapter' 策略的执行流程 ---
    # logging.info("配置策略为 'chapter'，开始执行章节解析流程。")
    # # 优先尝试LLM智能重构
    # logging.info("步骤 1: 尝试使用 LLM 进行智能结构化...")
    # restructured_md, semantic_toc = await restructure_markdown_with_llm(markdown_content)
    
    # 检查重构是否成功 (例如，内容是否显著改变)
    # 这是一个简单的检查，可以根据需要变得更复杂
    if restructured_md and len(restructured_md) > len(markdown_content) * 0.5:
        logging.info("LLM 智能重构成功，现在基于重构后的内容进行解析。")
        markdown_to_parse = restructured_md
    else:
        logging.warning("LLM 智能重构失败或返回空内容，将使用原始文本进行解析。")
        markdown_to_parse = markdown_content
        
    # 任务 1.1: 尝试按标题解析
    toc = parse_markdown_to_json_toc(markdown_to_parse)

    if toc:
        logging.info("成功将文档解析为层级目录 (TOC)。现在添加 'status' 字段...")
        
        # 递归函数，为每个节点添加 status
        def add_status_recursively(node):
            node['status'] = 'unread'
            for child in node.get('children', []):
                add_status_recursively(child)
        
        add_status_recursively(toc)
        
        return {"table_of_contents": toc, "reading_snippets": None}
    else:
        # 任务 1.2: 备用方案，按字数分片
        logging.info("文档无标题结构，将按字数进行弹性分片。")
        snippets_text = chunk_text_by_size(markdown_to_parse)
        # 确保每个 snippet 都是一个带有 content 和 status 的字典
        snippets_structured = [
            {"content": text, "status": "unread"} for text in snippets_text
        ]
        return {"table_of_contents": None, "reading_snippets": snippets_structured}
