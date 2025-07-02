# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: llm.py
@time: 2024-07-29 11:00
@desc: 封装了 DeepReader 项目中所有与 LLM 调用相关的功能
"""
import logging
from gpt_researcher.config import Config, config
from .google_llm import call_google_llm
from gpt_researcher.utils.llm import create_chat_completion

import numpy as np


# 初始化一个全局配置实例，方便在所有 action 中访问模型等设置
# Config 类会自动从 .env 和/或 config.py 加载配置
try:
    config = Config()
except ImportError as e:
    logging.error(f"无法导入或初始化 Config 类: {e}。请确保 gpt_researcher/config/config.py 存在且正确。")
    config = None



async def call_writer_llm(prompt: str) -> str:
    """
    封装对 'smart_llm' 的调用，用于需要联网搜索的文本生成任务，如总结、提问等。
    """
    if not config:
        raise RuntimeError("Config 未被正确初始化，无法调用 LLM。")
    
    llm_provider = config.strategic_llm_provider
    llm_model = config.strategic_llm_model
    
    logging.info(f"--- 正在使用 Strategic LLM ({llm_provider}) 调用模型: {llm_model} ---")
    
    messages = [{"role": "user", "content": prompt}]
    
    try:
        return await create_chat_completion(
            messages=messages,
            model=llm_model,
            llm_provider=llm_provider,
            temperature= 0.5,
            llm_kwargs=config.llm_kwargs.copy(),
        )
    except Exception as e:
        logging.error(f"调用 Strategic LLM 时发生错误: {e}")
        return f"Error calling Strategic LLM: {e}"




async def call_smart_llm(prompt: str) -> str:
    """
    封装对 'smart_llm' 的调用，用于需要联网搜索的文本生成任务，如总结、提问等。
    """
    if not config:
        raise RuntimeError("Config 未被正确初始化，无法调用 LLM。")
    
    llm_provider = config.smart_llm_provider
    llm_model = config.smart_llm_model
    
    logging.info(f"--- 正在使用 Smart LLM ({llm_provider}) 调用模型: {llm_model} ---")
    
    messages = [{"role": "user", "content": prompt}]
    
    try:
        return await create_chat_completion(
            messages=messages,
            model=llm_model,
            llm_provider=llm_provider,
            temperature= 0.5,
            llm_kwargs=config.llm_kwargs.copy(),
        )
    except Exception as e:
        logging.error(f"调用 Smart LLM 时发生错误: {e}")
        return f"Error calling Smart LLM: {e}"



async def call_fast_llm(prompt: str) -> str:
    """
    封装对 'fast_llm' 的调用，用于快速、成本较低的文本生成任务，如总结、提问等。

    Args:
        prompt (str): 发送给模型的提示。

    Returns:
        str: 模型返回的文本响应。
    """
    # 安全检查: 直接检查导入的 config 对象是否有效
    if not config:
        raise RuntimeError(
            "Config 对象未被正确初始化。请确保在程序的入口点执行了 `Config()`。"
        )

    llm_provider = config.fast_llm_provider
    llm_model = config.fast_llm_model

    logging.info(f"--- 正在使用 Fast LLM ({llm_provider}) 调用模型: {llm_model} ---")
    messages = [{"role": "user", "content": prompt}]
    
    try:
        return await create_chat_completion(
            messages=messages,
            model=llm_model,
            llm_provider=llm_provider,
            temperature=0.5,
            llm_kwargs=config.llm_kwargs.copy(),
        )
    except Exception as e:
        import traceback
        logging.error(f"调用 Fast LLM 时发生严重错误: {e}")
        logging.error(f"错误类型: {type(e).__name__}")
        logging.error(f"完整追溯信息:\\n{traceback.format_exc()}")
        return ""


async def call_search_llm(prompt: str) -> str:
    """
    封装需要联网搜索的LLM调用，优先使用Google原生SDK。
    
    Args:
        prompt (str): 发送给模型的提示。

    Returns:
        str: 模型返回的文本响应，可能包含实时搜索结果。
    """
    if not config:
        raise RuntimeError("Config 未被正确初始化，无法调用 LLM。")

    llm_provider = config.search_llm_provider
    llm_model = config.search_llm_model

    logging.info(f"--- 正在使用 Search LLM ({llm_provider}) 调用模型: {llm_model} ---")

    if llm_provider == "google_genai":
        try:
            return await call_google_llm(prompt, llm_model)
        except Exception as e:
            logging.error(f"调用 Google Search LLM 时发生错误: {e}")
            return f"Error calling Google Search LLM: {e}"
    else:
        # 如果配置了其他搜索模型，则使用标准 chat completion 流程
        logging.warning(f"Search LLM 提供商 '{llm_provider}' 不是 'google_genai'，将作为标准 LLM 调用。")
        messages = [{"role": "user", "content": prompt}]
        try:
            return await create_chat_completion(
                messages=messages,
                model=llm_model,
                llm_provider=llm_provider,
                temperature=config.temperature,
                llm_kwargs=config.llm_kwargs.copy(),
            )
        except Exception as e:
            logging.error(f"调用 Search LLM ({llm_provider}) 时发生错误: {e}")
            return f"Error calling Search LLM: {e}"
