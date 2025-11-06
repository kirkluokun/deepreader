# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: token_counter.py
@time: 2025-11-06
@desc: 全局 Token 计数器，用于跟踪所有 LLM 调用的 token 消耗
"""
import tiktoken
import logging
from typing import Dict, Any
from threading import Lock


class TokenCounter:
    """全局 Token 计数器，线程安全"""
    
    def __init__(self):
        self._lock = Lock()
        self.stats = {
            # 按模型类型分类
            "fast_llm": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0},
            "smart_llm": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0},
            "writer_llm": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0},
            "search_llm": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0},
            # 总计
            "total": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}
        }
        
        # 使用 cl100k_base 编码器（适用于 GPT-3.5/4 和 Gemini）
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logging.warning(f"无法加载 tiktoken 编码器: {e}，将使用简单估算")
            self.encoder = None
    
    def count_tokens(self, text: str) -> int:
        """计算文本的 token 数量"""
        if not text:
            return 0
        
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                logging.warning(f"Token 计数失败: {e}，使用简单估算")
        
        # 简单估算：中文约1.5字符/token，英文约4字符/token
        # 混合文本平均约2.5字符/token
        return int(len(text) / 2.5)
    
    def add_call(self, llm_type: str, prompt: str, response: str):
        """
        记录一次 LLM 调用
        
        Args:
            llm_type: LLM 类型（fast_llm, smart_llm, writer_llm, search_llm）
            prompt: 输入的 prompt
            response: LLM 的响应
        """
        prompt_tokens = self.count_tokens(prompt)
        completion_tokens = self.count_tokens(response)
        total_tokens = prompt_tokens + completion_tokens
        
        with self._lock:
            if llm_type not in self.stats:
                logging.warning(f"未知的 LLM 类型: {llm_type}，将记录到 total")
                llm_type = "total"
            
            # 更新对应类型的统计
            self.stats[llm_type]["prompt_tokens"] += prompt_tokens
            self.stats[llm_type]["completion_tokens"] += completion_tokens
            self.stats[llm_type]["total_tokens"] += total_tokens
            self.stats[llm_type]["calls"] += 1
            
            # 更新总计
            self.stats["total"]["prompt_tokens"] += prompt_tokens
            self.stats["total"]["completion_tokens"] += completion_tokens
            self.stats["total"]["total_tokens"] += total_tokens
            self.stats["total"]["calls"] += 1
            
            logging.debug(
                f"Token计数: {llm_type} - "
                f"输入:{prompt_tokens}, 输出:{completion_tokens}, 总计:{total_tokens}"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取当前统计数据"""
        with self._lock:
            return dict(self.stats)
    
    def get_summary(self) -> str:
        """获取格式化的统计摘要"""
        stats = self.get_stats()
        
        lines = []
        lines.append("=" * 80)
        lines.append("📊 Token 使用统计")
        lines.append("=" * 80)
        
        for llm_type, data in stats.items():
            if llm_type == "total":
                lines.append("-" * 80)
            
            if data["calls"] > 0:
                type_name = {
                    "fast_llm": "Fast LLM (gemini-2.0-flash)",
                    "smart_llm": "Smart LLM (gemini-2.5-flash)",
                    "writer_llm": "Writer LLM (gemini-2.5-pro)",
                    "search_llm": "Search LLM (gemini-2.0-flash)",
                    "total": "总计"
                }.get(llm_type, llm_type)
                
                lines.append(f"{type_name}:")
                lines.append(f"  调用次数: {data['calls']:,} 次")
                lines.append(f"  输入 Tokens: {data['prompt_tokens']:,}")
                lines.append(f"  输出 Tokens: {data['completion_tokens']:,}")
                lines.append(f"  总计 Tokens: {data['total_tokens']:,}")
                lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def reset(self):
        """重置所有统计数据"""
        with self._lock:
            for key in self.stats:
                self.stats[key] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}


# 全局单例实例
_global_token_counter = TokenCounter()


def get_token_counter() -> TokenCounter:
    """获取全局 token 计数器实例"""
    return _global_token_counter

