# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: IterativeReadingLoop.py
@time: 2024-07-26 15:00
@desc: DeepReader 主动式阅读循环的核心节点
"""
import logging
import asyncio
import json
from typing import Dict, Any

from gpt_researcher.deepreader.backend.read_state import DeepReaderState
from gpt_researcher.deepreader.backend.graph.actions.docparsing_actions import structure_document_action
from gpt_researcher.deepreader.backend.graph.actions.reading_knowledge_actions import (
    reading_agent_action,
    summary_agent_action,
    key_info_agent_action,
)
from ..actions.rag_actions import chat_with_retriever
from thefuzz import fuzz

def _get_full_content_and_mark_read(node: Dict[str, Any]) -> str:
    """
    递归地获取一个节点及其所有子节点的完整内容，并将它们全部标记为 'read'。
    返回拼接后的完整文本内容。
    """
    # 标记当前节点为已读
    node['status'] = 'read'
    
    # 获取当前节点的内容
    content_parts = [node.get('content', '')]
    
    # 递归处理子节点
    for child in node.get('children', []):
        content_parts.append(_get_full_content_and_mark_read(child))
        
    return "\\n\\n".join(filter(None, content_parts))

async def iterative_reading_node(state: DeepReaderState) -> Dict[str, Any]:
    """
    主动式阅读循环的控制器节点。

    该节点负责:
    1.  首次运行时，对文档进行结构化。
    2.  按顺序遍历 reading_snippets，调用 agents 进行分析。
    3.  管理和更新循环过程中的状态，包括跨片段的上下文。
    """
    logging.info("--- 迭代式阅读节点开始 ---")
    
    # --- 步骤 1: 首次运行时进行文档结构化和状态初始化 ---
    # 检查 'reading_snippets' 和 'table_of_contents' 是否都未被填充
    if not state.get("reading_snippets") and not state.get("table_of_contents"):
        logging.info("首次进入，开始文档结构化...")
        structured_state = await structure_document_action(state)
        # 确保关键状态字段已初始化
        structured_state.setdefault("snippet_analysis_history", [])
        structured_state.setdefault("raw_reviewer_outputs", [])
        structured_state.setdefault("chapter_summaries", {})
        structured_state.setdefault("key_information", [])
        structured_state.setdefault("active_memory", {
            "background_summary": "这是文档的开端。",
            "last_data_item_context": ""
        })
        return structured_state

    # --- 步骤 2: 确定当前要阅读的片段 ---
    user_question = state.get("user_core_question", "No specific question provided.")
    active_memory = state.get("active_memory", {})
    background_memory = active_memory.get("background_summary", "This is the beginning of the document.")
    last_data_item_context = active_memory.get("last_data_item_context", "")
    research_role = state.get("research_role", "scholarly research assistant")
    db_name = state.get("db_name")

    # 寻找下一个未读的片段
    next_snippet = None
    snippet_index = -1
    for i, snippet in enumerate(state["reading_snippets"]):
        if snippet.get("status", "unread") == "unread":
            next_snippet = snippet
            snippet_index = i
            break
            
    if not next_snippet:
        logging.info("所有片段已阅读完毕。")
        return {"reading_completed": True}
        
    logging.info(f"正在阅读片段 {snippet_index + 1}/{len(state['reading_snippets'])}")
    current_chunk = next_snippet.get("content", "")
    
    if not current_chunk:
        logging.warning(f"片段 {snippet_index + 1} 内容为空，跳过。")
        next_snippet["status"] = "read"
        return {
            "reading_snippets": state["reading_snippets"],
            "reading_completed": False
        }

    # --- 步骤 3: 准备跨片段上下文 ---
    previous_chapters_context = "无。这是第一个片段。"
    history = state.get("snippet_analysis_history", [])
    if history:
        # 获取上一个片段的分析结果（取最后两个章节作参考）
        last_snippet_analysis = history[-1]
        context_chapters = last_snippet_analysis[-2:]
        if context_chapters:
            context_parts = [
                f"- 标题: {ch.get('title', 'N/A')}\\n- 摘要: {ch.get('chapter_summary', 'N/A')}"
                for ch in context_chapters
            ]
            previous_chapters_context = "来自上一片段的分析参考：\\n" + "\\n".join(context_parts)

    # --- 步骤 4: Agent 协作分析 ---
    # ReadingAgent 和 KeyInfoAgent 并行执行
    agent_results = await asyncio.gather(
        reading_agent_action(
            current_chunk, user_question, background_memory, research_role, previous_chapters_context
        ),
        key_info_agent_action(
            current_chunk,
            user_question,
            background_memory,
            research_role,
            last_data_item_context,
        )
    )
    reading_result_list, key_info_result_list = agent_results

    # 从返回的列表中收集问题和摘要
    all_questions = []
    all_summaries = []
    for result in reading_result_list:
        # V2.1: 为每个章节分析结果添加一个用于存储已审核答案的列表
        result["reviewed_answers"] = [] 
        if "error" in result:
            logging.error(f"ReadingAgent为片段{snippet_index+1}返回错误: {result['error']}")
            continue 
        all_questions.extend(result.get("questions", []))
        all_summaries.append(result.get("chapter_summary", ""))

    # ReviewerAgent
    reviewed_answers_list = await chat_with_retriever(all_questions, db_name, user_question)
    
    # --- V2.2 优化：模糊匹配并将结构化答案回填到 reading_result_list ---
    # V2.3 新增：将原始 reviewer 输出存入 state
    raw_reviewer_outputs_history = state.get("raw_reviewer_outputs", [])
    raw_reviewer_outputs_history.append(reviewed_answers_list)

    for answer_obj in reviewed_answers_list:
        if "error" in answer_obj:
            continue
        
        answered_question = answer_obj.get("question", "")
        best_match_score = -1
        best_match_result = None
        best_match_original_question = None

        # 在所有原始问题中寻找最佳匹配
        for result in reading_result_list:
            if "error" in result: continue
            for original_question in result.get("questions", []):
                score = fuzz.ratio(answered_question, original_question)
                if score > best_match_score:
                    best_match_score = score
                    best_match_result = result
                    best_match_original_question = original_question
        
        # 如果找到一个足够好的匹配（阈值降低到85），则回填答案
        if best_match_score > 85 and best_match_result:
            best_match_result["reviewed_answers"].append({
                "question": best_match_original_question,
                "answer": answer_obj.get("content_retrieve_answer")
            })

    # SummaryAgent
    # 为 SummaryAgent 准备纯文本的答案列表
    all_answers_text = [a.get("content_retrieve_answer", "") for a in reviewed_answers_list if "error" not in a]
    newly_generated_summaries = "\\n".join(filter(None, all_summaries))
    new_background_memory = background_memory # 默认继承
    if newly_generated_summaries:
        new_background_memory = await summary_agent_action(newly_generated_summaries, all_answers_text)

    # --- 步骤 5: 更新状态 ---
    # A. 标记当前片段为已读
    next_snippet["status"] = "read"
    
    # B. 将本轮详细分析结果附加到历史记录
    history.append(reading_result_list)
    
    # C. 更新顶层的 chapter_summaries 字典 (为了方便快速查找)
    chapter_summaries = state.get("chapter_summaries", {})
    for result in reading_result_list:
        if "error" not in result:
            title = result.get("title", f"片段_{snippet_index+1}_未知标题")
            chapter_summaries[title] = result.get("chapter_summary", "")
        
    # D. 更新关键信息历史和跨片段上下文
    key_information_history = state.get("key_information", [])
    key_information_history.extend(key_info_result_list)
    new_last_data_context = ""
    if key_info_result_list and "error" not in key_info_result_list[-1]:
        new_last_data_context = json.dumps(key_info_result_list[-1], ensure_ascii=False)
        
    # E. 更新活动记忆和最终返回的状态
    updated_state = {
        "active_memory": {
            "background_summary": new_background_memory,
            "last_data_item_context": new_last_data_context
        },
        "chapter_summaries": chapter_summaries,
        "snippet_analysis_history": history,
        "raw_reviewer_outputs": raw_reviewer_outputs_history,
        "key_information": key_information_history,
        "reading_snippets": state["reading_snippets"],
        "reading_completed": False # 只要读了一个片段，就还没完成
    }

    logging.info(f"--- 片段 {snippet_index + 1} 阅读完成 ---")
    return updated_state
