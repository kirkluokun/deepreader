# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: config.py
@time: 2025-06-26 11:00
@desc: DeepReader backend configuration settings
"""
from typing import Literal, Dict, Any


class DeepReaderConfig:
    """
    用于配置 DeepReader 文档处理流程的设置。
    """
    # =================================================================
    # LLM 配置
    # =================================================================
    
    # Fast LLM - 用于快速、成本较低的任务
    FAST_LLM_PROVIDER: str = "google_genai"
    FAST_LLM_MODEL: str = "gemini-3-flash-preview"
    
    # Smart LLM - 用于需要较高质量的文本生成任务
    SMART_LLM_PROVIDER: str = "google_genai"
    SMART_LLM_MODEL: str = "gemini-3-flash-preview"
    
    # Strategic LLM - 用于最复杂、最重要的任务
    STRATEGIC_LLM_PROVIDER: str = "google_genai"
    STRATEGIC_LLM_MODEL: str = "gemini-3-pro-preview"
    
    # Search LLM - 用于需要联网搜索的任务
    SEARCH_LLM_PROVIDER: str = "google_genai"
    SEARCH_LLM_MODEL: str = "gemini-3-flash-preview"
    
    # LLM 通用参数
    TEMPERATURE: float = 0.5
    LLM_KWARGS: Dict[str, Any] = {}

    # =================================================================
    # 文档解析配置
    # =================================================================
    
    # 定义文档的解析策略
    # - 'chapter': 优先尝试使用LLM和正则表达式按章节/标题结构化文档。
    # - 'snippet': 强制跳过章节解析，直接按固定字数将文档切分为片段。
    PARSING_STRATEGY: Literal['chapter', 'snippet'] = 'snippet'

    # 当 PARSING_STRATEGY 设置为 'snippet' 时，每个文本片段的目标字数。
    # 这个数值越大，阅读速度越快，但是阅读精度可能有一定程度下降。类似于“一目十行”速度越快。
    SNIPPET_CHUNK_SIZE: int = 6000

    # =================================================================
    # 报告生成模式配置
    # =================================================================

    # 定义研报生成的模式
    # - 'test': 测试模式，用于快速调试，生成最精简的报告。
    # - 'concise': 精简模式，默认选项，平衡速度与报告深度。
    # - 'deep': 深度模式，生成最全面、深入的报告，耗时最长。
    MODE: Literal['test', 'concise', 'deep'] = 'concise'

    # 定义不同模式下的具体参数
    MODE_SETTINGS: Dict[str, Dict[str, Any]] = {
        'test': {
            'reading_agent_questions': 1,  # ReadingAgent 提问数量
            'debate_rounds': 1,            # 写作研讨会辩论轮次
            'outline_max_top_level': 2,    # 大纲一级标题最大数量
            'outline_max_second_level': 2  # 大纲二级标题最大数量
        },
        'concise': {
            'reading_agent_questions': 3,
            'debate_rounds': 2,
            'outline_max_top_level': 4,
            'outline_max_second_level': 5
        },
        'deep': {
            'reading_agent_questions': 5,
            'debate_rounds': 5,
            'outline_max_top_level': "unlimited",  # 不限制
            'outline_max_second_level': "unlimited" # 不限制
        }
    }

    def get_setting(self, key: str) -> Any:
        """
        根据当前设置的 MODE，获取对应的配置值。
        
        Args:
            key (str): The key for the setting to retrieve.

        Returns:
            Any: The value of the setting for the current mode.
        """
        return self.MODE_SETTINGS[self.MODE].get(key)

    # =================================================================
    # LLM 配置属性访问方法
    # =================================================================
    
    @property
    def fast_llm_provider(self) -> str:
        """获取Fast LLM提供商"""
        return self.FAST_LLM_PROVIDER
    
    @property
    def fast_llm_model(self) -> str:
        """获取Fast LLM模型"""
        return self.FAST_LLM_MODEL
    
    @property
    def smart_llm_provider(self) -> str:
        """获取Smart LLM提供商"""
        return self.SMART_LLM_PROVIDER
    
    @property
    def smart_llm_model(self) -> str:
        """获取Smart LLM模型"""
        return self.SMART_LLM_MODEL
    
    @property
    def strategic_llm_provider(self) -> str:
        """获取Strategic LLM提供商"""
        return self.STRATEGIC_LLM_PROVIDER
    
    @property
    def strategic_llm_model(self) -> str:
        """获取Strategic LLM模型"""
        return self.STRATEGIC_LLM_MODEL
    
    @property
    def search_llm_provider(self) -> str:
        """获取Search LLM提供商"""
        return self.SEARCH_LLM_PROVIDER
    
    @property
    def search_llm_model(self) -> str:
        """获取Search LLM模型"""
        return self.SEARCH_LLM_MODEL
    
    @property
    def temperature(self) -> float:
        """获取温度参数"""
        return self.TEMPERATURE
    
    @property
    def llm_kwargs(self) -> Dict[str, Any]:
        """获取LLM额外参数"""
        return self.LLM_KWARGS.copy()


# 实例化配置以供其他模块导入和使用
deep_reader_config = DeepReaderConfig()
