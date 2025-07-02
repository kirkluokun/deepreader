# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: read_graph.py
@time: 2025-06-25 15:00
@desc: 定义并编译 DeepReader 的核心 LangGraph 流程
"""
import logging
from typing import Literal

from langgraph.graph import END, StateGraph

# 导入核心状态对象和节点函数
from .read_state import DeepReaderState
from .graph.nodes.RAGPersistenceNode import rag_persistence_node
from .graph.nodes.IterativeReadingLoop import iterative_reading_node
from .graph.nodes.ReportGenerationNode import report_generation_node

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def rag_parse_has_error(state: DeepReaderState) -> Literal["error", "continue"]:
    """
    检查 RAG 解析和持久化节点是否返回了错误。
    """
    if state.get("error"):
        logging.error(f"RAG 解析节点出现错误，终止流程: {state['error']}")
        return "error"
    logging.info("RAG 解析节点成功，继续流程。")
    return "continue"

def should_continue_reading(state: DeepReaderState) -> Literal["continue", "end"]:
    """
    根据 'reading_completed' 标志或错误状态决定是否继续阅读循环。
    """
    # 优先检查是否存在错误，如果存在则终止循环
    if state.get("error"):
        logging.error(f"条件判断：检测到错误，终止阅读循环。错误: {state.get('error')}")
        return "end"
        
    if state.get("reading_completed"):
        logging.info("条件判断：阅读完成，流程结束。")
        return "end"
    else:
        logging.info("条件判断：继续阅读下一章节/片段。")
        return "continue"

def create_deepreader_graph(test_until_reading_node: bool = False) -> StateGraph:
    """
    创建并配置 DeepReader 的 LangGraph 实例。

    Args:
        test_until_reading_node (bool): 如果为 True，图将在 reading_loop 后结束，用于测试。
    """
    graph = StateGraph(DeepReaderState)

    # 注册节点
    graph.add_node("rag_parser", rag_persistence_node)
    graph.add_node("reading_loop", iterative_reading_node)
    
    if not test_until_reading_node:
        graph.add_node("report_generation", report_generation_node)

    # --- 定义图的流程 ---
    graph.set_entry_point("rag_parser")
    
    # RAG 解析后，进行条件判断
    graph.add_conditional_edges(
        "rag_parser",
        rag_parse_has_error,
        {
            "error": END,
            "continue": "reading_loop",
        }
    )
    
    # 在阅读循环节点后添加条件边
    end_destination = END if test_until_reading_node else "report_generation"
    graph.add_conditional_edges(
        "reading_loop",
        should_continue_reading,
        {
            "continue": "reading_loop",  # 如果需要继续，则再次调用自己
            "end": end_destination,
        },
    )

    if not test_until_reading_node:
        # 报告生成后，流程结束
        graph.add_edge("report_generation", END)

    if test_until_reading_node:
        logging.info("DeepReader Graph 定义完成 (测试模式：在 reading_loop 后结束)。")
    else:
        logging.info("DeepReader Graph 定义完成。")
    return graph


# 编译图
app = create_deepreader_graph().compile()

logging.info("DeepReader Graph 已编译并可供使用。")
