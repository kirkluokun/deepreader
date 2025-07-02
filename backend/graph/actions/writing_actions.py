# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: writing_actions.py
@time: 2025-06-28 10:00
@desc: DeepReader 写作研讨会的核心业务动作
"""
import logging
import json
from typing import Dict, Any, List, Optional
from thefuzz import process, fuzz
from json_repair import loads as json_repair_loads

from gpt_researcher.deepreader.backend.prompts import (
    ANALYZE_NARRATIVE_FLOW_PROMPT,
    EXTRACT_THEMES_PROMPT,
    CRITIQUE_THEMES_PROMPT,
    GENERATE_FINAL_OUTLINE_PROMPT,
    WRITE_REPORT_SECTION_PROMPT,
    SELECT_RELEVANT_SUMMARIES_PROMPT,
    SELECT_RELEVANT_KEY_INFO_PROMPT,
)
from gpt_researcher.deepreader.backend.components.llm import call_smart_llm, call_writer_llm, call_fast_llm
from gpt_researcher.utils.google_llm import call_google_llm
from gpt_researcher.deepreader.backend.graph.actions.rag_actions import chat_with_retriever
from gpt_researcher.deepreader.backend.config import deep_reader_config


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def _robust_json_parser(json_string: str) -> Any:
    """A robust utility to clean and parse JSON from LLM outputs using json_repair."""
    if json_string.strip().startswith("```json"):
        json_string = json_string.strip()[7:-3].strip()
    return json_repair_loads(json_string)


async def analyze_narrative_flow_action(chapter_summaries: Dict[str, str]) -> str:
    """
    脉络分析师 Action: 对全书摘要进行梳理，形成主题驱动的叙事脉络。
    """
    logging.info("--- 脉络分析师开始工作 ---")
    prompt = ANALYZE_NARRATIVE_FLOW_PROMPT.format(
        all_chapter_summaries=json.dumps(chapter_summaries, ensure_ascii=False, indent=2)
    )
    narrative_outline = await call_smart_llm(prompt)
    logging.info(f"脉络分析师生成的内容: {narrative_outline}")
    logging.info("--- 脉络分析师完成工作 ---")
    return narrative_outline


async def extract_themes_action(
    chapter_summaries: Dict[str, str], 
    feedback_from_critic: Optional[str] = None
) -> Dict[str, str]:
    """
    主题思想家 Action: 提炼书籍的核心思想、结论和证据。
    如果收到批判者的反馈，则在此基础上进行优化。
    """
    logging.info("--- 主题思想家开始工作 ---")
    feedback_section = ""
    if feedback_from_critic:
        logging.info("收到批判者反馈，正在进行优化...")
        feedback_section = f"""
**Feedback from the Critical Thinker (You MUST address this):**
{feedback_from_critic}
"""
    prompt = EXTRACT_THEMES_PROMPT.format(
        all_chapter_summaries=json.dumps(chapter_summaries, ensure_ascii=False, indent=2),
        feedback_section=feedback_section
    )
    
    for attempt in range(3): # 重试3次
        logging.info(f"--- 主题思想家提炼中 (尝试 {attempt + 1}/3) ---")
        response_json_str = await call_smart_llm(prompt)
        try:
            themes = _robust_json_parser(response_json_str)
            if not isinstance(themes, dict) or not all(k in themes for k in ["key_idea", "key_conclusion", "key_evidence"]):
                raise ValueError("JSON object is missing required keys.")
            logging.info("--- 主题思想家完成工作 ---")
            return themes
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"主题思想家 JSON 解析失败 (尝试 {attempt + 1}/3): {e}\\n原始响应: {response_json_str}")
            if attempt == 2: # 最后一次尝试失败
                logging.error(f"主题思想家 JSON 解析在所有重试后失败: {e}")
                return {
                    "key_idea": f"Error parsing response after retries: {e}",
                    "key_conclusion": "",
                    "key_evidence": ""
                }

    # 如果循环结束仍未返回，则返回错误（理论上不会执行到这里）
    return {"key_idea": "An unexpected error occurred in extract_themes_action.", "key_conclusion": "", "key_evidence": ""}


async def critique_and_refine_action(
    current_keys: Dict[str, str],
    raw_reviewer_outputs: List[List[Dict[str, Any]]],
    background_summary: str
) -> str:
    """
    批判者 Action: 对主题思想家的提炼结果提出质疑和改进建议。
    """
    logging.info("--- 批判者开始工作 ---")
    prompt = CRITIQUE_THEMES_PROMPT.format(
        key_idea=current_keys.get("key_idea", ""),
        key_conclusion=current_keys.get("key_conclusion", ""),
        key_evidence=current_keys.get("key_evidence", ""),
        background_summary=background_summary,
        raw_reviewer_outputs=json.dumps(raw_reviewer_outputs, ensure_ascii=False, indent=2)
    )
    feedback = await call_smart_llm(prompt)
    logging.info("--- 批判者完成工作 ---")
    return feedback


async def generate_final_outline_action(
    narrative_outline: str, 
    final_keys: Dict[str, str],
    user_core_question: str
) -> List[Dict[str, Any]]:
    """
    总编辑 Action: 整合脉络和核心思想，创建最终的报告大纲。
    """
    logging.info("--- 总编辑开始工作 ---")
    
    # 根据配置生成大纲约束
    max_top = deep_reader_config.get_setting('outline_max_top_level')
    max_second = deep_reader_config.get_setting('outline_max_second_level')

    if max_top == "unlimited":
        outline_constraints = "- The number of top-level and second-level sections is not limited. Focus on logical depth and comprehensiveness."
    else:
        outline_constraints = f"""- The number of top-level sections (一级标题) MUST NOT exceed {max_top}.
- The number of second-level sections (二级标题) per top-level section MUST NOT exceed {max_second}.
- The outline must have exactly two levels of depth."""

    prompt = GENERATE_FINAL_OUTLINE_PROMPT.format(
        user_core_question=user_core_question,
        narrative_outline=narrative_outline,
        final_key_idea=final_keys.get("key_idea", ""),
        final_key_conclusion=final_keys.get("key_conclusion", ""),
        final_key_evidence=final_keys.get("key_evidence", ""),
        outline_constraints=outline_constraints
    )
    for attempt in range(3):
        logging.info(f"--- 总编辑生成大纲中 (尝试 {attempt + 1}/3) ---")
        response_json_str = await call_writer_llm(prompt)
        try:
            final_outline = _robust_json_parser(response_json_str)
            if not isinstance(final_outline, list):
                 raise ValueError("LLM did not return a list for the outline.")
            logging.info("--- 总编辑完成工作 ---")
            return final_outline
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"总编辑 JSON 解析失败 (尝试 {attempt + 1}/3): {e}\\n原始响应: {response_json_str}")
            if attempt == 2:
                logging.error(f"总编辑 JSON 解析在所有重试后失败: {e}")
                return [{"title": f"Error parsing outline after retries: {e}", "content_brief": "", "children": []}]
    return [{"title": "An unexpected error occurred in generate_final_outline_action.", "content_brief": "", "children": []}]


async def write_section_action(
    final_keys: Dict[str, str],
    full_outline: List[Dict[str, Any]],
    current_section_title: str,
    current_section_brief: str,
    rag_context: str,
    key_info_context: str,
    all_summaries: Dict[str, str],
    previous_part_summary: str,
    user_core_question: str
) -> (List[str], str):
    """
    Writer Action: 根据多源上下文，撰写指定的报告段落。

    Returns:
        一个元组 (written_part, part_summary)
        - written_part: 一个包含段落字符串的列表。
        - part_summary: 对该段落的总结，用于指导下一段写作。
    """
    logging.info(f"--- Writer 开始撰写章节: {current_section_title} ---")
    prompt = WRITE_REPORT_SECTION_PROMPT.format(
        user_core_question=user_core_question,
        final_key_idea=final_keys.get("key_idea", ""),
        final_key_conclusion=final_keys.get("key_conclusion", ""),
        final_key_evidence=final_keys.get("key_evidence", ""),
        full_outline=json.dumps(full_outline, ensure_ascii=False, indent=2),
        all_summaries=json.dumps(all_summaries, ensure_ascii=False, indent=2),
        previous_part_summary=previous_part_summary,
        rag_context=rag_context,
        key_info_context=key_info_context,
        current_section_title=current_section_title,
        current_section_brief=current_section_brief
    )
    
    for attempt in range(3):
        logging.info(f"--- Writer 撰写章节: {current_section_title} (尝试 {attempt + 1}/3) ---")
        response_json_str = await call_writer_llm(prompt)
        try:
            data = _robust_json_parser(response_json_str)
            if not isinstance(data, dict) or not all(k in data for k in ["written_part", "part_summary"]):
                raise ValueError("JSON object is missing 'written_part' or 'part_summary'.")
            
            written_part = data.get("written_part", [])
            part_summary = data.get("part_summary", "")

            if not isinstance(written_part, list):
                 raise ValueError("'written_part' should be a list of strings (paragraphs).")
            
            logging.info(f"--- Writer 完成撰写章节: {current_section_title} ---")
            return written_part, part_summary
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"Writer JSON 解析失败 (尝试 {attempt + 1}/3): {e}\\n原始响应: {response_json_str}")
            if attempt == 2:
                logging.error(f"Writer JSON 解析在所有重试后失败: {e}")
                error_text = f"Error during generation of section '{current_section_title}' after retries: {e}"
                return [error_text], error_text
    
    error_text = f"An unexpected error occurred in write_section_action for section '{current_section_title}'."
    return [error_text], error_text


async def select_and_retrieve_summaries_action(
    all_chapter_titles: List[str],
    current_section_title: str,
    current_section_brief: str,
    user_core_question: str,
    chapter_summaries: Dict[str, str]
) -> str:
    """
    一个Action，用于动态选择并检索与当前写作任务最相关的章节摘要。
    """
    logging.info(f"--- 为 '{current_section_title}' 动态筛选相关摘要 ---")
    
    prompt = SELECT_RELEVANT_SUMMARIES_PROMPT.format(
        user_core_question=user_core_question,
        current_section_title=current_section_title,
        current_section_brief=current_section_brief,
        all_chapter_titles=json.dumps(all_chapter_titles, ensure_ascii=False)
    )

    for attempt in range(3):
        logging.info(f"--- 为 '{current_section_title}' 动态筛选相关摘要 (尝试 {attempt + 1}/3) ---")
        response_json_str = await call_fast_llm(prompt)
        try:
            suggested_titles = _robust_json_parser(response_json_str)
            if not isinstance(suggested_titles, list):
                logging.warning("LLM未能返回一个标题列表。将重试...")
                raise ValueError("LLM did not return a list.")

            # 模糊匹配并提取摘要
            focused_summaries = []
            if not chapter_summaries: # 添加一个检查，以防 chapter_summaries 为空
                 logging.warning("章节摘要为空，无法进行模糊匹配。")
                 return "No summaries available to select from."

            for title in suggested_titles:
                # a. 寻找最匹配的原始标题
                best_match, score = process.extractOne(title, chapter_summaries.keys(), scorer=fuzz.token_sort_ratio)
                # b. 如果匹配度足够高，则提取摘要
                if score > 85: # 设置一个合理的相似度阈值
                    summary_content = chapter_summaries.get(best_match)
                    if summary_content:
                        focused_summaries.append(f"## Relevant Summary: {best_match}\\n\\n{summary_content}")

            if not focused_summaries:
                return "No highly relevant summaries found for this section."
            
            logging.info(f"成功筛选出 {len(focused_summaries)} 个相关摘要。")
            return "\\n\\n---\\n\\n".join(focused_summaries)

        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"筛选相关摘要时解析JSON失败 (尝试 {attempt + 1}/3): {e}\\n响应: {response_json_str}")
            if attempt == 2:
                 logging.error(f"筛选相关摘要时在所有重试后失败: {e}")
                 return f"Error selecting summaries after retries: {e}"
    
    return "An unexpected error occurred in select_and_retrieve_summaries_action."


async def select_and_retrieve_key_info_action(
    all_key_information: List[Dict[str, Any]],
    full_outline: List[Dict[str, Any]],
    current_section_title: str,
    current_section_brief: str,
    user_core_question: str
) -> str:
    """
    一个Action，用于动态选择并检索与当前写作任务最相关的关键信息。
    """
    logging.info(f"--- 为 '{current_section_title}' 动态筛选相关关键信息 ---")

    if not all_key_information:
        return "No key information available to select from."

    # 准备给LLM的列表，只包含名称和描述
    key_info_for_prompt = [
        {"data_name": item.get("data_name"), "description": item.get("description")}
        for item in all_key_information
    ]
    
    prompt = SELECT_RELEVANT_KEY_INFO_PROMPT.format(
        user_core_question=user_core_question,
        full_outline=json.dumps(full_outline, ensure_ascii=False, indent=2),
        current_section_title=current_section_title,
        current_section_brief=current_section_brief,
        all_key_info_list=json.dumps(key_info_for_prompt, ensure_ascii=False, indent=2)
    )

    for attempt in range(3):
        logging.info(f"--- 筛选关键信息 (尝试 {attempt + 1}/3) ---")
        response_json_str = await call_smart_llm(prompt)
        try:
            suggested_data_names = _robust_json_parser(response_json_str)
            if not isinstance(suggested_data_names, list):
                raise ValueError("LLM did not return a list.")

            # 创建一个从 data_name 到完整信息的映射，用于快速查找
            key_info_map = {item.get("data_name"): item for item in all_key_information}
            
            # 模糊匹配并提取完整信息
            focused_key_info = []
            for name in suggested_data_names:
                # 使用thefuzz进行模糊查找，因为LLM可能不会返回完全精确的名称
                best_match, score = process.extractOne(name, key_info_map.keys(), scorer=fuzz.token_sort_ratio)
                if score > 85: # 设置相似度阈值
                    info_item = key_info_map.get(best_match)
                    if info_item:
                        focused_key_info.append(f"### Relevant Key Information: {info_item.get('data_name')}\\n\\n**Description:** {info_item.get('description')}\\n\\n**Raw Data:**\\n```json\\n{json.dumps(info_item.get('rawdata'), ensure_ascii=False, indent=2)}\\n```")

            if not focused_key_info:
                return "No highly relevant key information found for this section."
            
            logging.info(f"成功筛选出 {len(focused_key_info)} 条相关关键信息。")
            return "\\n\\n---\\n\\n".join(focused_key_info)

        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"筛选关键信息时解析JSON失败 (尝试 {attempt + 1}/3): {e}\\n响应: {response_json_str}")
            if attempt == 2:
                 logging.error(f"筛选关键信息时在所有重试后失败: {e}")
                 return f"Error selecting key information after retries: {e}"
    
    return "An unexpected error occurred in select_and_retrieve_key_info_action."


async def rag_chat_action(query: str, db_name: str, user_question: str) -> str:
    """
    RAG Agent Action: 根据查询，在书籍的向量数据库中检索相关内容。
    This action is a simplified wrapper. It retrieves context for a single query.
    """
    logging.info(f"--- RAG Agent 开始检索，查询: {query} ---")
    try:
        answer_objects = await chat_with_retriever([query], db_name, user_question)
        
        if not answer_objects or "error" in answer_objects[0]:
            logging.warning(f"RAG检索未找到内容或出错: {answer_objects[0].get('error', 'No content found')}")
            return "No relevant context found in the document for this query."
        
        rag_context = answer_objects[0].get("content_retrieve_answer", "No content found.")
        
        logging.info("--- RAG Agent 完成检索 ---")
        return rag_context
    except Exception as e:
        logging.error(f"RAG Agent Action 出现异常: {e}")
        return f"An error occurred during RAG retrieval: {e}"


async def search_with_google_action(query: str) -> str:
    """
    互联网搜索 Action: 使用 Google 搜索来验证或丰富内容。
    """
    logging.info(f"--- 互联网搜索 Agent 开始搜索，查询: {query} ---")
    try:
        search_result = await call_google_llm(query)
        logging.info("--- 互联网搜索 Agent 完成搜索 ---")
        return search_result
    except Exception as e:
        logging.error(f"互联网搜索 Action 出现异常: {e}")
        return f"An error occurred during Google search: {e}"
