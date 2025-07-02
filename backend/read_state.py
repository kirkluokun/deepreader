# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: state.py
@time: 2025-06-16 10:00
@desc: 定义 DeepReader Agent 的核心状态对象
"""

from typing import Any, Dict, List, Optional, Tuple
from typing_extensions import TypedDict


class DeepReaderState(TypedDict):
    """
    DeepReader Agent 的核心状态机。

    该状态对象在 LangGraph 的各个节点之间流转，
    记录了从文档解析到最终报告生成的整个过程中的所有数据和状态。
    """
    research_role: Optional[str]
    """(可选) 用户输入的研究角色，作为整个分析过程的最高指引。"""

    user_core_question: Optional[str]
    """(可选) 用户输入的核心研究问题，作为整个分析过程的最高指引。"""

    document_path: str
    """待分析文档的来源路径，可以是本地文件路径或网络 URL。"""

    db_name: Optional[str]
    """(可选) 用于存储本次文档解析结果的数据库名称。如果未提供，将使用默认名称。"""
    
    raw_markdown_content: str
    """从源文档（PDF, EPUB, URL）直接转换而来的、未经修改的完整 Markdown 文本。"""

    document_metadata: Dict[str, Any]
    """
    文档的元数据。
    这应该是一个必需字段，因为它在流程早期就被填充。
    例如: {'title': '...', 'author': '...', 'toc': [...]}
    """
    
    table_of_contents: Optional[Dict[str, Any]]
    """从 Markdown 标题解析出的 JSON 格式章节树。"""

    reading_snippets: Optional[List[Dict[str, Any]]]
    """当无法生成 table_of_contents 时，用于存储按字数切分的阅读片段。"""
    
    snippet_analysis_history: List[List[Dict[str, Any]]]
    """
    存储每个片段（snippet）阅读产出的历史记录。
    外层列表的每个元素代表一个片段，内层列表是该片段的分析结果（一个或多个章节的分析对象）。
    例如: [[{"title": "...", "chapter_summary": "...", "questions": []}]]
    """
    
    chunks: List[Dict[str, Any]]
    """
    结构化的文档片段列表。
    这是文档被智能解析和分块后的主要产物。
    每个片段是一个字典，例如: {'chunk_id': '...', 'chapter_id': '...', 'content': '...'}
    """

    chapter_summaries: Dict[str, str]
    """
    按章节ID索引的章节摘要。
    键是 chapter_id, 值是该章节的综合摘要内容。
    """
    
    key_information: List[Dict[str, Any]]
    """
    存储从文档中提取的所有关键信息（数据和论断）的列表。
    列表中的每个元素都是一个由 KeyInfoAgent 输出的结构化字典。
    例如: [{'data_name': '...', 'description': '...', 'rawdata': {}, 'originfrom': '...'}]
    """
    
    active_memory: Optional[Dict[str, Any]]
    """
    用于在循环中传递上下文。
    例如: {'background_summary': '...', 'last_data_item_context': '...'}
    """


    marginalia: Dict[str, List[str]]
    """
    "边栏笔记"的集合，模拟精读时的思考过程。
    键是 chunk_id, 值是该片段对应的笔记列表。
    """

    entities: List[Dict[str, Any]]
    """
    从文档中提取出的关键实体列表。
    每个实体是一个字典，例如: {'entity_id': '...', 'name': '...', 'description': '...'}
    """

    entity_relationships: List[Tuple[str, str, str]]
    """
    实体间的关系链接列表。
    每个元素是一个元组，格式为 (源实体ID, 目标实体ID, 关系描述)。
    例如: ('entity_001', 'entity_002', 'is a part of')
    """

    synthesis_report: str
    """最终生成的、围绕用户核心问题展开的综合性分析报告。"""

    rag_status: Optional[str]
    """记录 RAG 持久化节点执行状态的标志。例如: 'Completed', 'Failed'。"""
    
    raw_reviewer_outputs: List[List[Dict[str, Any]]]
    """(调试用) 存储每一轮 ReviewerAgent 返回的原始 JSON 对象列表，用于检查 LLM 输出的准确性。"""

    # --- 写作研讨会阶段字段 ---

    report_narrative_outline: Optional[str]
    """(脉络分析师产出) 对全书摘要进行梳理后，形成的非线性、主题驱动的叙事脉络。"""

    thematic_analysis: Optional[Dict[str, str]]
    """(主题思想家产出) 对书籍核心思想的初步提炼，格式为 {"key_idea": "...", "key_conclusion": "...", "key_evidence": "..."}。"""
    
    critic_consensus_log: List[str]
    """(批判者与思想家) 记录思想家与批判者之间为了达成共识的讨论日志。"""

    final_keys: Optional[Dict[str, str]]
    """(思想家+批判者共识) 经过讨论和提炼后，最终确定的核心思想、结论和证据。"""

    final_report_outline: Optional[List[Dict[str, Any]]]
    """(总编辑产出) 最终生成的、包含两级标题和草稿的完整读书笔记大纲。"""

    draft_report: Optional[List[Dict[str, Any]]]
    """(Writer产出) 最终生成的、结构与大纲一致的完整报告，内容已被填充。"""
    
    error: Optional[str]
    """
    记录图执行过程中可能发生的错误信息。
    如果流程正常，该字段为 None。
    """ 