# -*- coding: utf-8 -*-
"""
dynamic-gptr/gpt_researcher/utils/google_llm.py

封装了调用 Google GenAI 原生 SDK 的特定逻辑。
"""
import asyncio
from google import genai
from google.genai.types import Tool, GoogleSearch, GenerateContentConfig


async def call_google_llm(prompt: str, model_name: str) -> str:
    """
    使用 Google 原生 SDK 调用 Generative AI 模型，并启用 Google 搜索工具。

    Args:
        prompt (str): 发送给模型的提示。
        model_name (str): 要使用的模型名称 (例如 "gemini-1.5-flash-latest")。

    Returns:
        str: 模型返回的文本响应。
        
    Raises:
        ImportError: 如果必要的 google-genai 库没有安装。
        Exception: 捕获并重新抛出任何在API调用期间发生的未知错误。
    """
    print(f"--- 正在通过原生封装调用 Google GenAI SDK: {model_name} ---")
    try:
        # 1. 初始化原生客户端
        # SDK 会自动从环境变量 GOOGLE_API_KEY 读取密钥
        client = genai.Client()

        # 2. 创建搜索工具和生成配置
        google_search_tool = Tool(google_search=GoogleSearch())
        generation_config = GenerateContentConfig(tools=[google_search_tool])

        # 3. 异步生成内容
        # 在一个线程中运行同步的SDK调用，以避免阻塞异步事件循环
        response_object = await asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents=prompt,
            config=generation_config
        )
        
        # 4. 从返回对象中提取文本内容
        print("--- Google GenAI 原生SDK调用成功 ---")
        return response_object.text

    except ImportError:
        print("错误: 无法导入 'google-genai'。请确保 'google-genai' 已正确安装在虚拟环境中。")
        raise
    except Exception as e:
        print(f"错误: 使用Google GenAI原生SDK时发生未知错误: {e}")
        raise
