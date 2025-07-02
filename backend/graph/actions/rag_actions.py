from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from gpt_researcher.deepreader.backend.components.vector_store import DeepReaderVectorStore
from typing import List, Dict, Any
from gpt_researcher.deepreader.backend.prompts import REVIEWER_AGENT_PROMPT
from gpt_researcher.deepreader.backend.components.llm import call_fast_llm, call_search_llm
import logging
import json
from json_repair import loads as json_repair_loads
import asyncio

def chunk_document(markdown_content: str, source_id: str) -> List[Dict[str, Any]]:
    """
    使用 RecursiveCharacterTextSplitter 将 Markdown 文档分块。
    """
    # 设定一个合理的块大小和重叠
    text_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.MARKDOWN,
        chunk_size=1000,
        chunk_overlap=200, # 稍微减小重叠以获得更好的上下文连续性
    )
    
    chunks = text_splitter.split_text(markdown_content)
    
    # 为每个块附上元数据
    chunk_objects = []
    for i, chunk in enumerate(chunks):
        chunk_objects.append({
            "content": chunk,
            "metadata": {
                "source_id": source_id,
                "chunk_index": i
            }
        })
    return chunk_objects

def persist_chunks(chunk_objects: List[Dict[str, Any]], db_name: str = None, db_path: str = None):
    """
    将分块后的文档持久化到 RAG 数据库。
    """
    if not chunk_objects:
        print("没有可持久化的块。")
        return

    # 同时支持 db_name 和 db_path
    vector_store = DeepReaderVectorStore(db_name=db_name, db_path=db_path)
    
    contents = [obj['content'] for obj in chunk_objects]
    metadatas = [obj['metadata'] for obj in chunk_objects]
    
    vector_store.add_texts(texts=contents, metadatas=metadatas)

async def _answer_single_question(
    question: str, 
    vector_store: DeepReaderVectorStore, 
    user_question: str
) -> Dict[str, Any]:
    """
    (内部函数) 异步处理单个问题。
    """
    # 1. 在全书范围内检索相关片段
    retrieved_docs = vector_store.similarity_search(question, k=10)
    context = "\\n\\n---\\n\\n".join([doc.page_content for doc in retrieved_docs])

    # 2. 将上下文和问题喂给 LLM
    prompt = REVIEWER_AGENT_PROMPT.format(
        question=question, 
        context=context,
        user_question=user_question
    )
    
    for attempt in range(3):
        logging.info(f"--- ReviewerAgent 回答问题 (尝试 {attempt + 1}/3): {question[:50]}... ---")
        response_json_str = await call_fast_llm(prompt)
        
        # 3. 解析 LLM 返回的 JSON
        try:
            if response_json_str.strip().startswith("```json"):
                response_json_str = response_json_str.strip()[7:-3].strip()
            
            parsed_obj = json_repair_loads(response_json_str)

            if not isinstance(parsed_obj, dict) or not all(k in parsed_obj for k in ["question", "content_retrieve_answer"]):
                    raise ValueError("ReviewerAgent 返回的 JSON 对象缺少必需的键。")

            return parsed_obj # 成功解析并验证后，返回结果
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"ReviewerAgent JSON 解析失败 (尝试 {attempt + 1}/3): {e}\\n原始响应: {response_json_str}")
            if attempt == 2: # 最后一次尝试失败
                logging.error(f"ReviewerAgent 对问题 '{question[:50]}...' 的回答在所有重试后解析失败: {e}")
                return {
                    "question": question,
                    "content_retrieve_answer": f"Error parsing answer after retries: {e}",
                    "error": str(e)
                }
    # 理论上不会执行到这里
    return {"question": question, "content_retrieve_answer": "Unexpected error after retry loop.", "error": "Unexpected flow exit."}


async def chat_with_retriever(
    questions: List[str], 
    db_name: str, 
    user_question: str
) -> List[Dict[str, Any]]:
    """
    针对一系列问题，在文档内部的 RAG 存储中进行检索并生成结构化的 JSON 答案。
    (该函数现在并行处理所有问题)

    Args:
        questions: ReadingAgent 生成的问题列表。
        db_name: 当前文档对应的数据库名称。
        user_question: 用户的核心研究问题，用于为 ReviewerAgent 提供聚焦。

    Returns:
        一个包含每个问题及其答案的字典列表。
        e.g., [{'question': '...', 'content_retrieve_answer': '...'}]
    """
    if not questions:
        return []

    logging.info(f"--- ReviewerAgent 开始并行回答 {len(questions)} 个问题 ---")
    
    # 加载 RAG 存储
    vector_store = DeepReaderVectorStore(db_name=db_name)
    
    # 为每个问题创建一个异步任务
    tasks = [
        _answer_single_question(question, vector_store, user_question)
        for question in questions
    ]
    
    # 并发执行所有任务
    answers = await asyncio.gather(*tasks)
    
    logging.info(f"--- ReviewerAgent 已完成所有问题的回答 ---")
    return answers 


async def retrieve_rag_context(query: str, db_name: str, k: int = 10) -> str:
    """
    直接从向量数据库中检索与查询相关的上下文片段。

    此函数执行一个纯粹的 RAG 检索，不经过 LLM 进行二次处理。
    它用于为写作环节提供原始素材。

    Args:
        query: 用于检索的查询字符串 (例如章节标题和简介)。
        db_name: 数据库名称。
        k: 要检索的文档数量。

    Returns:
        一个包含所有检索到的片段内容的、用分隔符拼接起来的字符串。
    """
    logging.info(f"--- RAG Context Retrieval start, query: {query[:70]}... ---")
    try:
        # 加载 RAG 存储
        vector_store = DeepReaderVectorStore(db_name=db_name)

        # 1. 在全书范围内检索相关片段
        retrieved_docs = vector_store.similarity_search(query, k=k)
        
        # 2. 拼接内容
        context = "\\n\\n---\\n\\n".join([doc.page_content for doc in retrieved_docs])
        
        logging.info(f"--- RAG Context Retrieval finished, retrieved {len(retrieved_docs)} chunks. ---")
        return context
    except Exception as e:
        logging.error(f"RAG Context Retrieval failed: {e}")
        return f"Error during RAG context retrieval: {e}" 