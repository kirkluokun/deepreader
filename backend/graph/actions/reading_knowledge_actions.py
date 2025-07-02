# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: reading_knowledge_actions.py
@time: 2025-06-26 11:00
@desc: DeepReader 主动式阅读循环的核心业务动作
"""
import logging
from typing import Dict, Any, List
import json
from json_repair import loads as json_repair_loads

from gpt_researcher.deepreader.backend.read_state import DeepReaderState
from gpt_researcher.deepreader.backend.prompts import (
    READING_AGENT_PROMPT, 
    SUMMARY_AGENT_PROMPT, 
    KEY_INFO_AGENT_PROMPT
)
from gpt_researcher.deepreader.backend.components.llm import call_fast_llm, call_smart_llm
from gpt_researcher.deepreader.backend.config import deep_reader_config


async def reading_agent_action(
    current_chunk: str,
    user_question: str,
    previous_summary: str,
    research_role: str,
    previous_chapters_context: str
) -> List[Dict[str, Any]]:
    """
    实现 ReadingAgent 的核心逻辑，对文本片段进行总结、提问，并感知上下文。

    Args:
        current_chunk: 当前要分析的文本片段。
        user_question: 用户的核心探索问题。
        previous_summary: 截至目前的全局背景记忆。
        research_role: 研究角色。
        previous_chapters_context: 上一个片段结尾1-2个章节的分析摘要。

    Returns:
        一个包含本片段内各章节分析结果的列表，每个元素是一个字典。
        e.g., [{'title': '...', 'chapter_summary': '...', 'questions': []}]
    """
    logging.info("--- ReadingAgent 开始分析片段 ---")
    
    # 从配置中获取提问数量
    max_questions = deep_reader_config.get_setting('reading_agent_questions')

    prompt = READING_AGENT_PROMPT.format(
        research_role=research_role,
        chapter_content=current_chunk,
        user_question=user_question,
        background_memory=previous_summary,
        previous_chapters_context=previous_chapters_context,
        max_questions=max_questions
    )
    
    for attempt in range(3):
        logging.info(f"--- ReadingAgent 分析片段 (尝试 {attempt + 1}/3) ---")
        response_json_str = await call_fast_llm(prompt)
        try:
            # 清理并解析 LLM 返回的 JSON 字符串
            if response_json_str.strip().startswith("```json"):
                response_json_str = response_json_str.strip()[7:-3].strip()
            
            data = json_repair_loads(response_json_str)

            # 新的验证逻辑：确保返回的是一个列表，且列表内元素结构正确
            if not isinstance(data, list):
                raise ValueError("LLM 返回的不是一个 JSON 列表。")
            
            for item in data:
                if not isinstance(item, dict) or not all(k in item for k in ["title", "chapter_summary", "questions"]):
                    raise ValueError("JSON 列表中的对象缺少 'title', 'chapter_summary', 或 'questions' 键。")
                
            logging.info("--- ReadingAgent 分析完成 ---")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"ReadingAgent JSON 解析或验证失败 (尝试 {attempt + 1}/3): {e}\\n原始响应: {response_json_str}")
            if attempt == 2:
                logging.error(f"ReadingAgent 在所有重试后仍然失败: {e}")
                return [{
                    "title": "Parsing Error",
                    "chapter_summary": f"Failed to parse summary from LLM response after retries. Error: {e}",
                    "questions": [],
                    "error": str(e)
                }]
                
    # 理论上不会执行到这里
    return [{"title": "Unexpected Error", "chapter_summary": "An unexpected error occurred in reading_agent_action.", "questions": [], "error": "Unexpected flow exit."}]


async def summary_agent_action(
    newly_generated_summaries: str, 
    reviewed_answers: list[str]
) -> str:
    """
    实现 SummaryAgent 的逻辑，将当前片段的新总结和问答回顾整合成增量背景记忆。

    Args:
        newly_generated_summaries: 当前片段产出的所有章节摘要的拼接字符串。
        reviewed_answers: ReviewerAgent 对相关问题的回答列表。

    Returns:
        一个精炼的、可用于更新全局背景记忆的字符串。
    """
    logging.info("--- SummaryAgent 开始生成增量背景记忆 ---")
    
    # 将答案列表格式化为字符串
    answers_str = "\\n- ".join(reviewed_answers) if reviewed_answers else "无"
    
    prompt = SUMMARY_AGENT_PROMPT.format(
        newly_generated_summaries=newly_generated_summaries,
        reviewed_answers=answers_str
    )
    
    background_memory = await call_smart_llm(prompt)
    logging.info("--- SummaryAgent 背景记忆生成完毕 ---")
    return background_memory


async def key_info_agent_action(
    current_chunk: str,
    user_question: str,
    background_memory: str,
    research_role: str,
    last_data_item_context: str
) -> List[Dict[str, Any]]:
    """
    实现 KeyInfoAgent 的核心逻辑，精准提取有价值的数据和论断。

    Args:
        current_chunk: 当前要分析的文本片段。
        user_question: 用户的核心探索问题。
        background_memory: 截至目前的全局背景记忆。
        research_role: 研究角色。
        last_data_item_context: 上一个片段结尾可能未完成的数据项上下文。

    Returns:
        一个包含本片段内所有关键信息分析结果的列表，每个元素是一个字典。
        e.g., [{'data_name': '...', 'description': '...', 'rawdata': {}, 'originfrom': '...'}]
    """
    logging.info("--- KeyInfoAgent 开始提取关键信息 ---")
    prompt = KEY_INFO_AGENT_PROMPT.format(
        research_role=research_role,
        chapter_content=current_chunk,
        user_question=user_question,
        background_memory=background_memory,
        last_data_item_context=last_data_item_context
    )

    for attempt in range(3):
        logging.info(f"--- KeyInfoAgent 提取信息 (尝试 {attempt + 1}/3) ---")
        response_str = await call_fast_llm(prompt)

        try:
            if response_str.strip().startswith("```json"):
                response_str = response_str.strip()[7:-3].strip()
            
            data = json_repair_loads(response_str)

            # 检查是否为 "无有价值数据" 的特定JSON响应
            if isinstance(data, list) and len(data) > 0 and data[0].get("data_name") == "无有价值数据":
                logging.info("--- KeyInfoAgent 未在本片段发现有价值数据 (JSON格式) ---")
                return []

            if not isinstance(data, list):
                raise ValueError("LLM 返回的不是一个 JSON 列表。")
            
            for item in data:
                if not isinstance(item, dict) or not all(k in item for k in ["data_name", "description", "rawdata", "originfrom"]):
                    raise ValueError("JSON 列表中的对象缺少 'data_name', 'description', 'rawdata', 或 'originfrom' 键。")
                
            logging.info("--- KeyInfoAgent 关键信息提取完成 ---")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"KeyInfoAgent JSON 解析或验证失败 (尝试 {attempt + 1}/3): {e}\\n原始响应: {response_str}")
            if attempt == 2:
                logging.error(f"KeyInfoAgent 在所有重试后仍然失败: {e}")
                return [{
                    "data_name": "Parsing Error",
                    "description": f"Failed to parse key information from LLM response after retries. Error: {e}",
                    "rawdata": {},
                    "originfrom": "N/A",
                    "error": str(e)
                }]
                
    return [{"data_name": "Unexpected Error", "description": "An unexpected error occurred in key_info_agent_action.", "rawdata": {}, "originfrom": "N/A", "error": "Unexpected flow exit."}]


# 后续将在此处添加具体的业务 action 函数，例如:
# async def structure_document_action(state: DeepReaderState) -> Dict[str, Any]:
#     ...
