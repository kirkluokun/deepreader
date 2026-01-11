import faiss
import sqlite3
import numpy as np
import json
import os
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document
from typing import List, Dict, Any, Iterable, Optional, Type

# 禁用 FAISS 的 OpenMP 多线程，避免与 gRPC 并发冲突
# 这是导致 "OMP: Error #179: Function pthread_mutex_init failed" 的根本原因
faiss.omp_set_num_threads(1)

class DeepReaderVectorStore(VectorStore):
    """
    一个基于 FAISS 和 SQLite 的自定义向量存储，与 LangChain 集成。
    """
    def __init__(self, db_name: str = None, db_path: str = None, embedding_model_name: str = "text-embedding-3-large", **kwargs: Any):
        # 1. 确定文件路径
        if db_path:
            # 如果提供了db_path，直接使用它（不加扩展名）
            base_path, _ = os.path.split(db_path)
            self.db_path = f"{db_path}.sqlite"
            self.faiss_path = f"{db_path}.faiss"
        elif db_name:
            # 否则，使用旧的逻辑，保持向后兼容
            # 基于当前文件路径计算 deepreader 根目录
            current_file = Path(__file__).resolve()
            deepreader_root = current_file.parent.parent.parent  # backend/components/../.. -> deepreader/
            base_path = deepreader_root / "backend/memory"
            self.db_path = str(base_path / f"{db_name}.sqlite")
            self.faiss_path = str(base_path / f"{db_name}.faiss")
        else:
            raise ValueError("必须提供 db_name 或 db_path")
        
        # 确保目录存在
        if hasattr(self, 'db_path'):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # 2. 初始化 Embedding 模型
        self.embedding_model = OpenAIEmbeddings(model=embedding_model_name, api_key=os.environ.get("OPENAI_API_KEY"))
        self.dimension = 3072  # text-embedding-3-large 的维度

        # 3. 加载或创建数据库和 FAISS 索引
        self._load_or_create_db()

    def _load_or_create_db(self):
        # 初始化 SQLite，只确保表存在
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                metadata TEXT
            )
        """)
        conn.commit()
        conn.close()

        # 初始化 FAISS
        if os.path.exists(self.faiss_path):
            try:
                self.index = faiss.read_index(self.faiss_path)
            except Exception as e:
                print(f"无法加载 FAISS 索引，将创建新索引: {e}")
                index = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIDMap(index)
        else:
            index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(index)

    def add_texts(self, texts: Iterable[str], metadatas: Optional[List[dict]] = None, **kwargs: Any) -> List[str]:
        """
        将文本和元数据添加到向量存储中。
        支持大文档批量处理，避免超过 OpenAI API 的 token 限制（单次请求最大 300k tokens）。
        """
        texts_list = list(texts)
        if not texts_list:
            return []

        # 确保 metadatas 列表长度与 texts_list 匹配
        if metadatas is None:
            metadatas = [{} for _ in texts_list]
        
        # 1. 批量向量化（分批处理以避免超过 API 限制）
        batch_size = 100  # 每批最多 100 个块，保守估计确保不超过 300k token
        all_embeddings = []
        
        print(f"开始向量化 {len(texts_list)} 个文本块...")
        
        for i in range(0, len(texts_list), batch_size):
            batch_texts = texts_list[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(texts_list) + batch_size - 1) // batch_size
            
            print(f"  正在向量化第 {batch_num}/{total_batches} 批 ({len(batch_texts)} 个块)...")
            
            try:
                batch_embeddings = self.embedding_model.embed_documents(batch_texts)
                all_embeddings.extend(batch_embeddings)
                print(f"  ✅ 第 {batch_num} 批完成")
            except Exception as e:
                print(f"  ❌ 第 {batch_num} 批向量化失败: {e}")
                raise
        
        embeddings_np = np.array(all_embeddings, dtype='float32')

        # 2. 将文本和元数据存入 SQLite，并获取 ID
        print(f"正在存储文本块到 SQLite...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        chunk_ids = []
            
        for content, meta in zip(texts_list, metadatas):
            cursor.execute("INSERT INTO chunks (content, metadata) VALUES (?, ?)", 
                                (content, json.dumps(meta)))
            chunk_ids.append(cursor.lastrowid)
        conn.commit()
        conn.close()

        # 3. 将向量存入 FAISS
        print(f"正在存储向量到 FAISS 索引...")
        ids_np = np.array(chunk_ids, dtype='int64')
        self.index.add_with_ids(embeddings_np, ids_np)
        
        # 4. 保存 FAISS 索引
        faiss.write_index(self.index, self.faiss_path)
        print(f"✅ 成功添加 {len(texts_list)} 个块到 RAG 存储。")
        
        return [str(cid) for cid in chunk_ids]

    def similarity_search(self, query: str, k: int = 10, **kwargs: Any) -> List[Document]:
        """
        根据查询向量，在 FAISS 中进行相似度搜索。
        """
        import logging
        import sys
        import traceback
        
        try:
            # 步骤1: Embedding
            logging.debug(f"[VectorStore] 开始 embed_query...")
            sys.stdout.flush()
            
            query_embedding = self.embedding_model.embed_query(query)
            
            logging.debug(f"[VectorStore] embed_query 完成，维度: {len(query_embedding)}")
            sys.stdout.flush()
            
            query_embedding_np = np.array([query_embedding], dtype='float32')

            # 步骤2: FAISS 搜索
            logging.debug(f"[VectorStore] 开始 FAISS index.search...")
            sys.stdout.flush()
            
            distances, chunk_ids = self.index.search(query_embedding_np, k)
            
            logging.debug(f"[VectorStore] FAISS search 完成，找到 {len(chunk_ids[0])} 个结果")
            sys.stdout.flush()

            # 步骤3: 从 SQLite 获取内容
            logging.debug(f"[VectorStore] 开始从 SQLite 获取内容...")
            sys.stdout.flush()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            results = []
            for i in chunk_ids[0]:
                if i == -1: continue # FAISS 在结果不足k个时会返回-1
                
                cursor.execute("SELECT content, metadata FROM chunks WHERE id = ?", (int(i),))
                res = cursor.fetchone()
                if res:
                    metadata = json.loads(res[1]) if res[1] else {}
                    results.append(Document(page_content=res[0], metadata=metadata))
            conn.close()
            
            logging.debug(f"[VectorStore] similarity_search 完成，返回 {len(results)} 个文档")
            sys.stdout.flush()
            
            return results
            
        except Exception as e:
            logging.critical(f"[VectorStore] !!! similarity_search 发生异常 !!!")
            logging.critical(f"异常类型: {type(e).__name__}")
            logging.critical(f"异常信息: {e}")
            logging.critical(f"调用栈:\n{traceback.format_exc()}")
            sys.stdout.flush()
            raise

    @classmethod
    def from_texts(
        cls: Type["DeepReaderVectorStore"],
        texts: List[str],
        embedding: OpenAIEmbeddings,
        metadatas: Optional[List[dict]] = None,
        db_path: Optional[str] = None,
        db_name: Optional[str] = "default_from_texts_db",
        **kwargs: Any,
    ) -> "DeepReaderVectorStore":
        """
        从文本列表创建 DeepReaderVectorStore。
        注意: 此实现忽略了传入的 embedding 对象，并使用内部创建的实例。
        """
        # 通过 kwargs 传递初始化参数
        init_kwargs = {"db_path": db_path, "db_name": db_name, **kwargs}
        store = cls(**init_kwargs)
        store.add_texts(texts=texts, metadatas=metadatas)
        return store

    def _select_relevance_score_fn(self):
        # 这是 VectorStore 中的一个抽象方法，需要一个虚拟实现
        pass
