# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: ReportGenerationNode.py
@time: 2025-06-28 12:00
@desc: DeepReader 写作研讨会的总控节点
"""
import logging
import json
import asyncio
from typing import Dict, Any

from backend.read_state import DeepReaderState
from backend.graph.actions.writing_actions import (
    analyze_narrative_flow_action,
    extract_themes_action,
    critique_and_refine_action,
    generate_final_outline_action,
    write_section_action,
    select_and_retrieve_summaries_action,
    select_and_retrieve_key_info_action,
)
from backend.graph.actions.rag_actions import (
    retrieve_rag_context
)
from backend.config import deep_reader_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def report_generation_node(state: DeepReaderState) -> Dict[str, Any]:
    """
    编排整个"写作研讨会"的协作流程，从分析到最终报告生成。
    """
    logging.info("--- 报告生成节点启动：写作研讨会开始 ---")
    
    # 从状态中获取阅读阶段的产出
    chapter_summaries = state.get("chapter_summaries", {})
    raw_reviewer_outputs = state.get("raw_reviewer_outputs", [])
    background_summary = state.get("active_memory", {}).get("background_summary", "")
    db_name = state.get("db_name", "default_db")
    user_core_question = state.get("user_core_question", "No core question provided.") # 提取核心问题
    key_information = state.get("key_information", []) # 提取关键信息

    # --- 1. 脉络分析师 ---
    logging.info("步骤 1/5: 脉络分析师正在梳理书籍脉络...")
    narrative_outline = await analyze_narrative_flow_action(chapter_summaries)
    logging.info("脉络分析师完成。")

    # --- 2. 主题思想家 (初稿) ---
    logging.info("步骤 2/5: 主题思想家正在提炼核心思想...")
    initial_keys = await extract_themes_action(
        chapter_summaries=chapter_summaries,
        user_core_question=user_core_question
    )
    logging.info("主题思想家完成初稿。")

    # --- 3. 批判者与思想家 (辩论与共识) ---
    logging.info("步骤 3/5: 批判者与思想家进入辩论环节...")
    current_keys = initial_keys
    discussion_log = []
    # 从配置中获取辩论轮次
    debate_rounds = deep_reader_config.get_setting('debate_rounds')

    logging.info(f"--- 写作研讨会：核心思想辩论开始（共 {debate_rounds} 轮） ---")
    
    # 辩论循环
    for i in range(debate_rounds):
        logging.info(f"辩论第 {i+1} 轮开始...")
        feedback = await critique_and_refine_action(
            current_keys=current_keys,
            raw_reviewer_outputs=raw_reviewer_outputs,
            background_summary=background_summary,
            user_core_question=user_core_question
        )
        discussion_log.append(f"Round {i+1} Critique: {feedback}")
        
        # 带着批判者的反馈，再次提炼
        logging.info("主题思想家根据反馈进行优化...")
        current_keys = await extract_themes_action(
            chapter_summaries=chapter_summaries,
            user_core_question=user_core_question,
            feedback_from_critic=feedback
        )
        discussion_log.append(f"Round {i+1} Refined Themes: {current_keys}")

    final_keys = current_keys
    logging.info(f"--- 辩论结束，最终核心思想: {final_keys} ---")

    # --- 4. 总编辑 ---
    logging.info("步骤 4/5: 总编辑正在生成最终报告大纲...")
    final_report_outline = await generate_final_outline_action(
        narrative_outline, 
        final_keys,
        user_core_question=user_core_question # 传递核心问题
    )
    logging.info("总编辑完成大纲制定。")

    # --- 5. Writer (迭代写作) ---
    logging.info("步骤 5/5: Writer 开始迭代撰写报告...")
    # 创建大纲的深拷贝，用于填充报告内容
    draft_report_structured = json.loads(json.dumps(final_report_outline))
    cumulative_summaries = ""  # 用于累积前面所有部分的摘要

    # 遍历两级大纲
    for section in draft_report_structured:
        # 使用enumerate以便在修改时能够正确索引
        for i, sub_section in enumerate(section.get('children', [])):
            section_title = sub_section.get("title", "无标题章节")
            section_brief = sub_section.get("content_brief", "")
            
            logging.info(f"  - 正在为章节 '{section_title}' 准备素材 (并行)...")
            
            # --- 并行准备素材：RAG, 动态摘要, 动态关键信息 ---
            rag_query = f"{section_title}: {section_brief}"
            
            # 创建并行任务
            tasks = {
                "rag": retrieve_rag_context(
                    query=rag_query,
                    db_name=db_name
                ),
                "summaries": select_and_retrieve_summaries_action(
                    all_chapter_titles=list(chapter_summaries.keys()),
                    current_section_title=section_title,
                    current_section_brief=section_brief,
                    user_core_question=user_core_question,
                    chapter_summaries=chapter_summaries
                ),
                "key_info": select_and_retrieve_key_info_action(
                    all_key_information=key_information,
                    full_outline=final_report_outline,
                    current_section_title=section_title,
                    current_section_brief=section_brief,
                    user_core_question=user_core_question
                )
            }

            # 执行并行任务
            results = await asyncio.gather(*tasks.values())
            
            # 解包结果
            rag_context, focused_summaries_context, focused_key_info_context = results
            
            # RAG结果现在是纯文本，无需额外处理

            logging.info(f"  - 开始撰写章节: {section_title}...")
            written_part, part_summary = await write_section_action(
                final_keys=final_keys,
                full_outline=final_report_outline,
                current_section_title=section_title,
                current_section_brief=section_brief,
                rag_context=rag_context,
                key_info_context=focused_key_info_context,
                all_summaries=focused_summaries_context,
                previous_part_summary=cumulative_summaries,
                user_core_question=user_core_question
            )
            
            # 3. 填充结构化报告: 将撰写的内容填充回去，并移除简介
            sub_section['written_content'] = written_part
            if 'content_brief' in sub_section:
                del sub_section['content_brief'] # 移除简介，因为它已被内容取代

            # 更新累积摘要，为下一次迭代做准备
            cumulative_summaries += f"\\n\\n---\\n\\nSection: {section_title}\\nSummary: {part_summary}"
    
    logging.info("Writer 完成全部章节撰写。")

    # --- 准备最终要更新到状态的字典 ---
    updated_state = {
        "report_narrative_outline": narrative_outline,
        "thematic_analysis": initial_keys,
        "critic_consensus_log": discussion_log,
        "final_keys": final_keys,
        "final_report_outline": final_report_outline,
        "draft_report": draft_report_structured, # 4. 输出结构化报告
    }
    
    logging.info("--- 报告生成节点完成 ---")
    return updated_state
