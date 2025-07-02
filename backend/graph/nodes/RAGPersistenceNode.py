# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: RAGPersistenceNode.py
@time: 2025-06-25 14:15
@desc: 一个多功能的 LangGraph 节点，负责文档的完整预处理和持久化流程。
"""
import logging
import os
import hashlib
from pathlib import Path
from typing import Dict, Any

from ..actions import rag_actions, docparsing_actions
# from ..state import DeepReaderState  # 假设的状态对象，用于类型提示


async def rag_persistence_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    一个异步的 LangGraph 节点，负责执行以下一系列操作：
    1. 检查基于文档路径哈希的缓存是否存在，如果存在则跳过。
    2. 如果缓存不存在，则根据输入路径智能解析文档（PDF, EPUB, URL）。
    3. 使用 LLM 从文档内容中提取元数据。
    4. 将解析后的文本内容分块。
    5. 将分块持久化到以文档哈希命名的 RAG 向量数据库中。
    6. 返回所有产出，以更新图的核心状态。
    """
    logging.info("--- 进入增强型 RAG 持久化节点 ---")

    document_path = state.get("document_path")
    if not document_path:
        logging.error("错误: 在 state 中未找到 'document_path'。")
        return {"error": "Missing document_path in state"}

    # 1. 生成基于路径哈希的唯一数据库名
    db_name_hash = hashlib.md5(document_path.encode()).hexdigest()
    # 基于当前文件路径计算 deepreader 根目录
    current_file = Path(__file__).resolve()
    deepreader_root = current_file.parent.parent.parent.parent  # backend/graph/nodes/../../../.. -> deepreader/
    db_base_path = deepreader_root / "backend/memory"
    # 我们只需要 db_name 传递给 vector_store，它会自动处理路径和扩展名
    
    # 2. 检查缓存是否存在
    # vector_store 内部会判断文件是否存在，但我们在这里提前检查可以避免不必要的实例化
    faiss_path = db_base_path / f"{db_name_hash}.faiss"
    sqlite_path = db_base_path / f"{db_name_hash}.sqlite"

    if faiss_path.exists() and sqlite_path.exists():
        logging.info(f"发现文档 '{document_path}' 的现有数据库 '{db_name_hash}'。跳过处理。")
        return {
            "db_name": db_name_hash,
            "rag_status": "Skipped: Exists",
            "error": None
        }

    # 3. 如果缓存不存在，执行完整流程
    logging.info(f"未找到缓存，开始为 '{document_path}' 执行完整处理流程。")
    try:
        # 3.1. 优先使用 state中的内容，否则路由解析，获取原始 Markdown
        raw_markdown_content = state.get("raw_markdown_content")
        if raw_markdown_content:
            logging.info("在 state 中发现现有 Markdown 内容，将直接使用。")
        else:
            logging.info("State 中无 Markdown 内容，将从路径解析。")
            raw_markdown_content = await docparsing_actions.route_and_parse(document_path)

        if not raw_markdown_content:
            logging.error(f"文档解析失败或内容为空: {document_path}")
            return {"error": f"Failed to parse document or document is empty: {document_path}"}
        
        logging.info(f"文档内容已准备好，长度: {len(raw_markdown_content)}")

        # 3.2. 提取元数据 (仅当元数据不存在时)
        document_metadata = state.get("document_metadata")
        if not document_metadata:
             document_metadata = await docparsing_actions.extract_metadata(raw_markdown_content[:1500])
        else:
            logging.info("在 state 中发现现有元数据，将直接使用。")

        # 3.3. 内容分块
        chunks = rag_actions.chunk_document(raw_markdown_content, source_id=document_path)
        logging.info(f"内容分块完成，共 {len(chunks)} 个块。")

        # 3.4. 持久化分块，使用哈希作为 db_name
        rag_actions.persist_chunks(chunk_objects=chunks, db_name=db_name_hash)

        # 3.5. 返回所有要更新到 state 的字段
        logging.info(f"--- RAG 持久化节点成功完成，新数据库: '{db_name_hash}' ---")
        return {
            "db_name": db_name_hash,
            "raw_markdown_content": raw_markdown_content,
            "document_metadata": document_metadata,
            "chunks": chunks,
            "rag_status": "Completed: New DB Created",
            "error": None
        }

    except Exception as e:
        logging.error(f"在 RAG 持久化节点中发生严重错误: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred in RAGPersistenceNode: {str(e)}"}
