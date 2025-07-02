### **DeepReader Agent - 产品需求文档 (PRD) 2.0**

#### **1. 愿景与目标**

`DeepReader` 是一个**智能阅读伙伴与知识助理**。其核心目标是模拟人类专家的沉浸式、反思式阅读过程，帮助用户在极短时间内深度理解、分析和重构任何长篇文档（书籍、论文、报告等），并根据用户特定需求生成定制化的知识产物（如摘要、逻辑图、思维导图等）。

它最终将作为 `dynamic-gptr` 项目的核心分析引擎，但首先会作为一个独立的、带前端的应用被构建和验证。

我们完全可以借鉴甚至超越现有方案，打造一个真正理解“阅读”这门艺术的智能体。

核心理念：模拟人类的“沉浸式与反思式阅读”
您的核心思想——“模拟人类的阅读过程”——是设计的黄金准则。人类专家阅读一本书，绝不是从头到尾线性处理一遍就完事。这个过程是多层次、迭代和交互的：

鸟瞰 (Skimming): 先看封面、目录、前言、结论，快速建立对全书结构的宏观认知。
精读 (Close Reading): 逐章阅读，在“空白处”做笔记、划重点、产生疑问（“这个概念是什么意思？”）、建立联系（“这和第三章的观点相呼应！”）。
反思 (Reflection): 读完几章或全书后，合上书本，回顾主线，梳理不同章节间的逻辑关系，形成对全书的整体、主题性理解。
构建 (Construction): 将书本的知识融入自己的知识体系，可能会画出思维导图、写下书评，或与他人讨论。
我们的 DeepReader Agent 就应该基于这个流程来构建，而不是一个简单的“输入 PDF -> 输出摘要”的管道。




#### **2. 核心用户流程**

1.  **上传与提问**: 用户通过 React 前端上传一份文档（PDF/EPUB/URL），并**输入一个核心问题**，即他们最希望从该文档中了解的内容。
2.  **智能分析**: `DeepReader` Agent 在后端接收任务，开始执行多阶段的自动化分析流程。
3.  **结果呈现**: 前端以交互式仪表盘的形式呈现分析结果，包括章节摘要、主题脉络、关键概念等。
4.  **对话与追问**: 用户可以在仪表盘下方的对话窗口中，针对已分析的文档内容进行追问，Agent 会利用已建立的知识库进行回答。

#### **3. 核心功能与机制**

##### **3.1. 用户意图引导 (User Intent Guidance)**

* **实现模块**: 前端界面、LangGraph 状态管理。
* **功能描述**:
    1.  前端提供一个输入框，让用户在上传文档时，可以选择输入一个"核心探索问题" (`user_core_question`)。
    2.  此问题将作为最高优先级的上下文，存入 `DeepReaderState`（Agent 的状态机）。
    3.  在后续所有分析节点（特别是 `MarginaliaNode` 和 `GlobalSynthesisNode`），LLM 的 Prompt 都会被注入此问题，以确保分析过程始终围绕用户的核心关切点进行，使结果更具相关性。
    * *Prompt 示例*: "在分析这段文字时，请特别关注它如何能回答用户最关心的问题：'{user_core_question}'"。如果没有输入就留空白即可。

核心组件：路径
dynamic-gptr/gpt_researcher/deepreader/graph/state.py：记录文档状态的 TypedDict 或 Pydantic 数据类。
dynamic-gptr/gpt_researcher/deepreader/graph/graph.py：定义和编译 LangGraph 图。
dynamic-gptr/gpt_researcher/deepreader/graph/nodes/：存放图的各个功能节点。
dynamic-gptr/gpt_researcher/deepreader/components/：存放被节点调用的具体业务逻辑组件 (替代 actions)。
dynamic-gptr/gpt_researcher/deepreader/main.py：项目的运行入口。
dynamic-gptr/gpt_researcher/deepreader/utils/：存放需要用到的工具函数。
dynamic-gptr/gpt_researcher/deepreader/context/：负责 RAG 压缩等上下文处理。
dynamic-gptr/gpt_researcher/deepreader/memory/：实现长短期记忆及信息持久化。

llm调用方法：
复用组件：dynamic-gptr/gpt_researcher/utils/llm.py，默认选择smart_llm，简单任务可以使用fastllm，复杂任务使用strategic_llm
dynamic-gptr/gpt_researcher/utils/google_llm.py，这个可以直接实现检索的googlellm



#### **4. LangGraph 架构与核心节点**

补充：每个章节、每个片段都要有id，每个外来的信息、llm生成的信息，都要有ids。通过ids建立entities的节点关系。
* **State (状态机)**: `DeepReaderState` (建议使用 TypedDict)
    * `user_core_question: str`: 用户输入的核心研究问题。
    * `document_path: str`: 被阅读文档的本地路径或URL。
    * `document_metadata: Dict[str, Any]`: 文档元数据 (如: 标题, 作者)。
    * `chunks: List[Dict[str, Any]]`: 结构化的文档块。每个块为字典，包含 `chunk_id`, `chapter_id`, `content` 等。
    * `chapter_summaries: Dict[str, str]`: 按 `chapter_id` 索引的章节摘要。
    * `marginalia: Dict[str, List[str]]`: "边栏笔记", 按 `chunk_id` 索引。
    * `entities: List[Dict[str, Any]]`: 提取的关键实体，每个实体包含 `entity_id`, `name`, `description`。
    * `entity_relationships: List[Tuple[str, str, str]]`: 实体关系链接 `(source_entity_id, target_entity_id, relationship_description)`。
    * `synthesis_report: str`: 最终生成的综合报告。
    * `error: Optional[str]`: 记录流程中可能发生的错误信息。

* **Nodes (节点)**:
    1.  `DocumentParsingNode`: 执行 3.2 的解构逻辑，产出 `structured_chunks`。
    2.  `IterativeReadingLoop`: 这是一个**子图 (subgraph)**，它会按顺序遍历 `structured_chunks`。
        * `MarginaliaNode`: 执行 3.3 的主动式阅读，生成"边栏笔记"，并可能触发外部搜索。
        * `ChapterSynthesisNode`: 当一个章节的所有片段都处理完毕后，此节点启动，将所有笔记整合成一个 `ChapterReport`。
    3.  `GlobalSynthesisNode`: 当所有章节都完成后，此节点启动。它读取所有的 `ChapterReport`，并结合 `user_core_question`，生成一份关于全书的、主题性的、高度浓缩的最终综合报告 `final_synthesis`。
    4.  `KeyEntityLinkageNode`: 执行 3.4 的简化版关系映射。
    5.  `ReportGenerationNode`: **(按需执行)** 根据用户的具体要求（例如"生成思维导图"），读取 `final_synthesis` 和 `key_entity_links`，生成特定格式的输出。

    

##### **3.2. 智能文档解构 (Intelligent Document Decomposition)**
当用户上传一本书（PDF/EPUB）时，图从这里开始。

节点 1: DocumentParsingNode (文档解析节点)
输入: PDF/EPUB 文件路径或 URL。
核心功能:
使用 PyMuPDF (处理PDF) 或 EbookLib (处理EPUB) 等库。
关键任务 1: 提取目录 (Table of Contents)。这是本书的骨架，至关重要。
关键任务 2: 将文档按章节/小节进行物理分割，形成结构化的文本块。
输出:
table_of_contents: 结构化的目录。
structured_chunks: 一个按章节组织的文本块列表。


* **实现模块**: `DocumentParsingNode` 及其核心函数 `intelligent_chunker`。
* **功能描述**: 这是 Agent 阅读的第一步，目标是将原始文档转化为一个结构化的、适合机器阅读的格式。
    1.  **格式转换**: 统一将输入的 PDF/EPUB/URL 转换为 Markdown 格式，以利用其结构化标记。使用https://github.com/datalab-to/marker的python包，具体使用方法可以参考https://github.com/datalab-to/marker/blob/master/README.md。格式转换的脚本dynamic-gptr/gpt_researcher/deepreader/backend/utils/pdf_converter.py。
    epub转换：EbookLib-一个专门用来读取和解析+markdownify: 一个能将 HTML 清理并转换为干净的 Markdown 的库。 EPUB 文件结构的强大库,纯 Python 实现，无外部软件依赖，方便部署；控制力极强，可以逐个章节处理，完美契合您的intelligent_chunker需求。markdownify: 一个能将 HTML 清理并转换为干净的 Markdown 的库。 因为 EPUB 的本质就是一个包含 XHTML 文件（每个章节一个文件）、CSS 和元数据的 ZIP 压缩包。我们的思路是：用 EbookLib 把每个章节的 XHTML 内容抽出来，再用 markdownify 把它变成 Markdown。在dynamic-gptr/gpt_researcher/deepreader/backend/utils/epub_converter.py转换为markdown。要在poetry中安装pip install EbookLib markdownify最新版本。转换的时候要注意对标题进行`#`, `##`, `###` 等标题层级进行递归切分。
    web_scraper.py：就使用crawl4ai的组件，复用
    2.  **分层解析逻辑**:dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/DocumentParsingNode.py，动作dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/doc_parser_actions.py实现功能，
        * **第一优先级：目录 (TOC)**。如果文档元数据中包含明确的目录，则严格按照目录的章节结构进行切分。【在这里要使用fastllm先识别是存在目录，也可以考虑是否使用检索关键词？有的论文没有目录，则要关注1、1.1、1.1.1等等标注】
        * **第二优先级：Markdown 标题**。如果没有TOC，则根据 Markdown 的 `#`, `##`, `###` 等标题层级进行递归切分，形成一个嵌套的章节树。优先切分到最细粒度的章节单元（例如 `###` 或 `####`）。
        * **第三优先级：LLM 辅助识别**。如果文档是纯文本，没有任何结构标记，则调用 LLM 进行"语义分块"，让其根据内容的逻辑转折点来划分章节。
    3.  **弹性分片机制 (Flexible Snippet Mechanism)**:
        * 设定一个"最佳阅读片段"字数阈值（如，3000字）。
        * 对于一个最小的章节单元：
            * **如果字数 < 阈值**: 作为一个完整的块进行处理。
            * **如果字数 > 阈值**: 将这个过长的章节，再切分为多个连贯的"片段 (Snippets)"。切分时会尽量保持句子的完整性。
    4.  rag化：把已经准备好的片段也同时rag压缩，保存在本地sqlite数据库，dynamic-gptr/gpt_researcher/deepreader/backend/memory，参考langgraph的方案

##### **3.3. 主动式阅读与外部知识增强 (Active Reading & Knowledge Enhancement)**IterativeReadingLoop

* **实现模块**: `MarginaliaNode` 、ChapterSynthesisNode(边栏笔记节点)。dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/IterativeReadingLoop.py

这是一个循环，图会遍历 structured_chunks 中的每一个章节。

节点 2.1: ChapterReadingNode (章节阅读节点)

输入: 单个章节的文本块。
核心功能: 将章节文本进一步细分为更小的段落或逻辑片段。
输出: 一个章节内的片段队列。
节点 2.2: MarginaliaNode (""边栏笔记"生成节点)

这是模拟"精读"时思维活动的核心！
输入: 单个文本片段。
核心功能: 使用 smart_llm (因为不计较消耗，我们可以用最好的模型) 并行地对文本片段进行多维度分析，生成一组""边栏笔记"：
summary: 对这段文字的简短摘要。
keywords: 关键术语。
entities: 提取出的核心实体（人名、地名、概念、理论）。
questions_raised: 这段文字引发了哪些值得思考的问题？
connections: （脑洞） "这段内容让我想起了..."，LLM可以被提示去寻找与已读章节内容的潜在联系。这需要一个简单的 RAG 机制，在已生成的章节摘要中检索相似内容。
输出: 一个结构化的 Marginalia (边栏笔记) 对象。
节点 2.3: ChapterSynthesisNode (章节综合节点)

输入: 一个章节所有的 Marginalia 对象。
核心功能: "读完一章了，总结一下"。LLM 将本章所有的""边栏笔记"进行综合，生成一个高质量的、包含多维信息的章节报告。
输出: 一个 ChapterReport 对象，包含：
本章的详细摘要。
本章核心概念列表及其解释。
本章提出的主要问题。
本章与其他章节的初步关联分析。


* **功能描述**: 模拟人类阅读时的"主动思考"过程。dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/reading_knowledge_actions.py
    1.  **序列化处理**: 为了保证对长章节内多个"片段"的连贯理解，`MarginaliaNode` 会**按顺序**处理这些片段，并将前一个片段的摘要作为上下文传递给下一个片段的处理过程。
    2.  **多维笔记**: 对每个片段生成结构化的 `Marginalia` 笔记（摘要、关键词、实体、引发的问题等）。
    3.  **工具调用：网络检索**: `MarginaliaNode` 中的agent在阅读额时候，被赋予调用工具（Tool-Using）的能力。当 LLM 在阅读中碰到一个它认为需要外部知识来补充理解的术语、历史背景或概念时（例如"什么是1929年的郁金香狂热？"），它可以在其输出中包含一个特殊的 `search_query`。后续的图逻辑会捕捉到这个查询，调用 `Tavily` 等搜索 API，将搜索结果返回，用于增强对原文的理解。
    4. agent还会及时性的生成问题，带着问题使用rag进行全文书本的检索，尝试找到关联。相当于存在一个辅助rag书本字典，随时可以当人类一样跳着翻阅书本。
    
    5. 在这里要完善数据结构命名。

##### **3.4. (已简化) 关键关系映射 (Key Relationship Mapping)**

* **实现模块**: `KeyEntityLinkageNode`。
* **功能描述**: 我们**暂缓构建完整的、复杂的知识图谱**。取而代之的是一个更轻量、更聚焦的模块。
    1.  **高频实体识别**: 在所有 `Marginalia` 笔记生成后，系统会统计所有提取出的 `entities` 的出现频率。
    2.  **聚焦核心关系**: 只选取 Top 10 或 Top 20 的最高频核心实体。
    3.  **关系提炼**: 调用 LLM，专门针对这几个核心实体，在全文范围内进行检索（通过 RAG），提炼它们之间的核心关系。
    * *Prompt 示例*: "在整篇文档中，'公司A'和'项目B'之间的主要关系是什么？请用一句话总结。"
* **目的**: 满足用户对核心逻辑提取的需求，同时避免了早期阶段陷入构建全量知识图谱的复杂性中。



RAG 的“升维”应用:

RAG 在这里不仅仅是“上传文档，然后问答”。它被深度整合进了阅读流程。例如，MarginaliaNode 可以实时调用 RAG，在已读内容中检索，以发现跨章节的联系，这是普通 RAG 应用做不到的“主动联想”。





长期记忆的实现:

LangGraph 的 Checkpointer 机制（如 SqliteSaver）就是实现长期记忆的关键。
单本书记忆: 每本书的阅读过程都是一个独立的 thread。这个 thread 的最终状态（包含了所有章节报告、知识图谱三元组等）被持久化保存下来，这就是 Agent 对这本书的"完整记忆"。
（脑洞）跨书本记忆与"元认知": 我们可以设计一个更高阶的 MetaReader Agent。当用户提问"请比较一下《未来简史》和《人类简史》中关于'自由意志'的看法"时，这个 MetaReader 会被唤醒，它的任务是：
从数据库中加载这两本书已经处理好的最终状态。
访问这两本书的知识图谱和主题分析报告。
进行对比分析，生成一个全新的、跨文档的洞察。 这才是真正的"学富五车"。


前端设想 (React)
先把所有后端数据都建立好，包括思维导图、myriad等数据结构后，再做前端。
前端应该是一个交互式仪表盘（Dashboard），而不是一个简单的聊天框。

左侧: 显示可交互的书本目录。点击章节，右侧主区域会更新。
右侧主区域:
默认视图: 显示该章节的 ChapterReport（摘要、关键词等）。
切换视图:
"知识图谱"视图: 展示整本书的知识图谱，节点可点击，高亮显示关系。
"主题脉络"视图: 可视化 思维导图 结果，展示核心主题如何在章节间演进。
"原文对照"视图: 显示摘要的同时，旁边展示原文，方便溯源。
底部/侧边: 一个对话窗口。在用户看完了 Agent 生成的报告后，可以针对这本书进行追问。这个对话窗口会触发一个标准的 RAG 流程，在本书的文本块上进行检索和回答。
这个 DeepReader 的构想，已经远超一个简单的工具，它是一个可成长、可交互、有记忆的知识工作台。我们可以先从核心的后端 LangGraph 流程开始搭建，逐步实现这个激动人心的蓝图。




<!-- 


好的，我们完全遵从您的新指示。忽略之前的 `intelligent_chunker` 复杂逻辑，现在我们聚焦于构建一个**纯粹、高效的 RAG 持久化模块**。

这个模块的核心任务是：在文档转换成 Markdown 字符串后，立即将其分块并存入本地的向量数据库，为后续所有 Agent 的检索需求提供一个稳定、快速的知识基础。

我将为您制定一个清晰、可执行的开发计划，该计划完全基于您选择的技术栈：**LangChain** 的组件、**FAISS + SQLite** 的本地存储方案，以及 **OpenAI `text-embedding-3-large`** 模型。

---

### **开发计划：`deepreader` RAG 持久化模块**

**最终目标**: 创建一个独立的、可被 LangGraph 调度的 RAG 持久化流程。该流程接收长篇 Markdown 文本，使用 `RecursiveCharacterTextSplitter` 进行分块，通过 OpenAI `text-embedding-3-large` 模型生成向量，并将文本块和向量分别存入本地的 SQLite 和 FAISS 数据库中。

#### **核心设计原则**

1.  **存储优先**: 本模块的**唯一职责**是“存储”。它将所有文本块无差别地存入数据库，不进行任何基于查询的相关性过滤。后续的检索任务将完全依赖于这个全面的知识库。
2.  **分块为存储服务**: 这里的“分块”(`chunking`)是为了让向量化和检索更高效，是**数据工程**的一部分。它与 Agent 为了“理解”而进行的阅读分段是两个完全独立的机制。
3.  **封装与解耦**: 数据库的全部读写逻辑将被封装在一个独立的 `vector_store` 组件中，使得上层业务逻辑（actions 和 nodes）无需关心数据库的具体实现细节。

---

#### **第一步：环境与依赖准备**

我将首先为您准备好必要的库。`faiss-cpu` 适用于大多数开发环境，`openai` 是调用 Embedding 模型所必需的。

我将为您执行以下安装命令：

```shell
poetry add faiss-cpu openai tiktoken
```
*   `faiss-cpu`: Facebook 开源的高效向量检索库（CPU版本）。
*   `openai`: 用于调用 `text-embedding-3-large` 模型。
*   `tiktoken`: OpenAI 官方的分词器，`RecursiveCharacterTextSplitter` 在计算块大小时会用到。

现在，我来执行安装。
```bash
poetry add faiss-cpu openai tiktoken
```
非常好，依赖库已准备就绪。现在我们可以开始具体的开发步骤。

---

#### **第二步：构建 RAG 存储接口 (`components/vector_store.py`)**

这是整个 RAG 模块的基石。我们将创建一个 `DeepReaderVectorStore` 类来封装所有数据库操作。

**文件路径**: `dynamic-gptr/gpt_researcher/deepreader/backend/components/vector_store.py`

```python
import faiss
import sqlite3
import numpy as np
import json
import os
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Any

class DeepReaderVectorStore:
    def __init__(self, db_name: str, embedding_model_name: str = "text-embedding-3-large"):
        # 1. 定义文件路径
        base_path = "dynamic-gptr/gpt_researcher/deepreader/backend/memory"
        os.makedirs(base_path, exist_ok=True)
        self.db_path = os.path.join(base_path, f"{db_name}.sqlite")
        self.faiss_path = os.path.join(base_path, f"{db_name}.faiss")

        # 2. 初始化 Embedding 模型
        self.embedding_model = OpenAIEmbeddings(model=embedding_model_name, api_key=os.environ["OPENAI_API_KEY"])
        self.dimension = 3072  # text-embedding-3-large 的维度

        # 3. 加载或创建数据库和 FAISS 索引
        self._load_or_create_db()

    def _load_or_create_db(self):
        # 初始化 SQLite
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                metadata TEXT
            )
        """)
        self.conn.commit()

        # 初始化 FAISS
        if os.path.exists(self.faiss_path):
            self.index = faiss.read_index(self.faiss_path)
        else:
            # 创建一个支持动态添加的索引
            self.index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(self.index)

    def add_chunks(self, chunks: List[str], metadatas: List[Dict[str, Any]]):
        if not chunks:
            return

        # 1. 向量化
        embeddings = self.embedding_model.embed_documents(chunks)
        embeddings_np = np.array(embeddings, dtype='float32')

        # 2. 将文本和元数据存入 SQLite，并获取 ID
        ids = []
        for content, meta in zip(chunks, metadatas):
            self.cursor.execute("INSERT INTO chunks (content, metadata) VALUES (?, ?)", 
                                (content, json.dumps(meta)))
            ids.append(self.cursor.lastrowid)
        self.conn.commit()

        # 3. 将向量和 SQLite 的 ID 关联并存入 FAISS
        ids_np = np.array(ids, dtype='int64')
        self.index.add_with_ids(embeddings_np, ids_np)

        # 4. 保存 FAISS 索引
        faiss.write_index(self.index, self.faiss_path)
        print(f"成功添加 {len(chunks)} 个块到 RAG 存储。")

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_model.embed_query(query)
        query_embedding_np = np.array([query_embedding], dtype='float32')

        # 在 FAISS 中搜索
        distances, ids = self.index.search(query_embedding_np, k)

        # 从 SQLite 中根据 ID 获取内容
        results = []
        for i in ids[0]:
            if i == -1: continue # FAISS 在结果不足k个时会返回-1
            self.cursor.execute("SELECT content, metadata FROM chunks WHERE id = ?", (int(i),))
            res = self.cursor.fetchone()
            if res:
                results.append({"content": res[0], "metadata": json.loads(res[1])})
        return results

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
```

---

#### **第三步：实现核心动作 (`rag_actions.py`)**

这个文件负责编排，调用 LangChain 的分块器并与我们上面创建的 `vector_store` 交互。

**文件路径**: `dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/rag_actions.py`

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from ..components.vector_store import DeepReaderVectorStore # 路径可能需要调整
from typing import List, Dict, Any

def chunk_document(markdown_content: str, source_id: str) -> List[Dict[str, Any]]:
    """
    使用 RecursiveCharacterTextSplitter 将 Markdown 文档分块。
    """
    # 设定一个合理的块大小和重叠
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False,
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

def persist_chunks(chunk_objects: List[Dict[str, Any]], db_name: str):
    """
    将分块后的文档持久化到 RAG 数据库。
    """
    if not chunk_objects:
        print("没有可持久化的块。")
        return

    vector_store = DeepReaderVectorStore(db_name=db_name)
    
    contents = [obj['content'] for obj in chunk_objects]
    metadatas = [obj['metadata'] for obj in chunk_objects]
    
    vector_store.add_chunks(contents, metadatas)
```

---

#### **第四步：实现 LangGraph 节点 (`RAGPersistenceNode.py`)**

这个节点是整个流程在 LangGraph 中的执行入口。

**文件路径**: `dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/RAGPersistenceNode.py`

```python
from ..actions import rag_actions
# from ..state import ResearchState # 假设的状态对象

def rag_persistence_node(state: dict) -> dict:
    """
    LangGraph 节点：接收 Markdown 内容，分块并持久化到 RAG 数据库。
    """
    print("--- 进入 RAG 持久化节点 ---")
    
    # 1. 从 state 获取数据
    markdown_content = state.get("markdown_content")
    source_id = state.get("source_id", "default_source") # 文档的唯一标识
    
    if not markdown_content:
        print("错误：在 state 中未找到 'markdown_content'。")
        return {"rag_status": "Failed: No content"}

    # 2. 调用 action 进行分块
    chunk_objects = rag_actions.chunk_document(markdown_content, source_id)
    
    # 3. 调用 action 进行持久化
    # 数据库名称可以从 state 或配置中获取，这里硬编码为例
    db_name = "deepreader_rag" 
    rag_actions.persist_chunks(chunk_objects, db_name)
    
    # 4. 更新 state，返回成功信息
    print(f"--- RAG 持久化完成，共处理 {len(chunk_objects)} 个块 ---")
    return {
        "rag_status": "Completed",
        "chunk_count": len(chunk_objects)
    }

```

---

#### **总结与后续**

这个计划为您提供了一个完整、独立的 RAG 持久化模块。您现在可以开始按步骤创建这些文件。

**请注意**:
*   您需要在环境变量中设置 `OPENAI_API_KEY`。
*   我已经将所有路径都指定好，您可以直接创建这些文件并填入代码。

当您完成这部分后，我们就可以继续开发下一步——您提到的“为 agent 阅读服务的弹性分段机制”。



 -->


<!-- 


好的，非常清晰的规划。我们来将您对 `intelligent_chunker` 模块的构思，细化成一个完整、可执行的开发计划。

这个计划将围绕您提到的核心文件和逻辑，构建一个强大的文档解析与 RAG 持久化流程。

---

### **开发计划：智能分块与 RAG 持久化模块 (`deepreader.chunker`)**

**最终目标**: 创建一个健壮的文档处理节点，能够接收长篇 Markdown 文本，通过分层解析逻辑将其智能地拆分为有意义的片段 (Snippets)，并将这些片段向量化后持久存储到本地的 RAG 数据库中，为后续的深度问答和分析做准备。

#### **一、 核心组件与文件结构**

1.  **动作层 (`dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/doc_parser_actions.py`)**:
    *   **职责**: 实现所有核心的、独立的业务逻辑函数。这是我们开发的主要工作区，包含分块、分片和 RAG 持久化的具体实现。

2.  **节点层 (`dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/DocumentParsingNode.py`)**:
    *   **职责**: 作为 LangGraph 中的一个节点，它负责编排和调用动作层中的函数。它从图的状态 (State) 中获取输入，调用 actions，然后将结果更新回状态。

3.  **RAG 存储接口 (`dynamic-gptr/gpt_researcher/deepreader/backend/components/vector_sotre.py`)**:
    *   **职责**: (建议新建此文件) 封装与 FAISS 和 SQLite 数据库的所有交互。这使得存储逻辑与解析逻辑解耦，更易于维护和扩展。

4.  **数据存储目录 (`dynamic-gptr/gpt_researcher/deepreader/backend/memory`)**:
    *   **职责**: 存放由 `vector_store.py` 生成的 SQLite 数据库文件和 FAISS 索引文件。

---

#### **二、 详细开发步骤**

##### **第 1 步：实现核心动作 (`doc_parser_actions.py`)**

我们将在这个文件中创建两个核心函数：`intelligent_chunker` 和 `persist_chunks_to_rag`。

**A. `intelligent_chunker(markdown_content: str, config: dict) -> List[dict]`**

这个函数是智能分块和弹性分片的总入口，它将按顺序执行以下逻辑：

1.  **结构解析 (分层逻辑)**:
    *   **TOC 优先 (P1)**:
        *   **实现**: 编写一个内部函数 `_parse_by_toc`。使用正则表达式优先识别并解析文档开头的目录结构。匹配模式如 `1. ...`，`1.1. ...`，`Chapter 1...` 等。
        *   **输出**: 如果成功，返回一个代表文档结构的章节列表 `[{'title': '1.1 Intro', 'content': '...', 'level': 2}, ...]`。
    *   **Markdown 标题 (P2)**:
        *   **实现**: 如果 `_parse_by_toc` 失败，则调用 `_parse_by_markdown_headers`。此函数会遍历整个 Markdown 文本，根据 `#`, `##`, `###` 等标题构建章节树。
        *   **输出**: 返回与 TOC 解析格式相同的章节列表。
    *   **LLM 语义分块 (P3)**:
        *   **实现**: 如果以上两种方法都无法有效分块（例如，标题数量少于某个阈值），则调用 `_parse_by_llm`。
        *   **Prompt 设计**: 设计一个 Prompt，要求 LLM 读取文本，并在它认为合适的逻辑断点处插入一个特殊的分隔符，例如 `[---SEMANTIC-BREAK---]`。
        *   **处理**: 函数获取 LLM 的返回后，按 `[---SEMANTIC-BREAK---]` 分割文本，生成章节列表。

2.  **弹性分片 (Flexible Snippet Mechanism)**:
    *   **配置**: `config` 字典将包含 `snippet_threshold` (例如: 3000)。
    *   **实现**: 遍历上一步生成的最小粒度章节列表。
        *   如果 `len(chapter['content']) < snippet_threshold`，该章节本身就是一个"片段 (Snippet)"。
        *   如果 `len(chapter['content']) > snippet_threshold`，则使用 LangChain 的 `RecursiveCharacterTextSplitter` 对这个过长的章节内容进行二次切分，确保在句子末尾断开。每个切分出的小块都是一个"片段"。
    *   **输出**: 函数最终返回一个扁平化的**片段列表** `List[dict]`。每个字典包含:
        ```json
        {
          "snippet_id": "unique_id_for_snippet",
          "content": "A reasonably sized text snippet...",
          "source_document_id": "id_of_the_source_doc",
          "parent_chapter_title": "Title of the original chapter (e.g., '1.1 Intro')",
          "metadata": { ... } // 其他元数据
        }
        ```

**B. `persist_chunks_to_rag(snippets: List[dict], db_path: str)`**

这个函数负责将处理好的片段存入 RAG 数据库。

1.  **调用存储接口**: 它将实例化 `DeepReaderVectorStore` (我们将在下一步定义) 并调用其 `add_snippets` 方法。

##### **第 2 步：构建 RAG 存储接口 (`components/vector_store.py`)**

新建此文件，用于封装数据库操作。

```python
# components/vector_store.py
import faiss
import sqlite3
from sentence_transformers import SentenceTransformer

class DeepReaderVectorStore:
    def __init__(self, db_path: str):
        # 初始化 SQLite 连接、FAISS 索引和 embedding 模型
        self.db_path = db_path
        # ... 连接数据库，加载或创建 faiss 索引 ...
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2') # 示例模型

    def add_snippets(self, snippets: List[dict]):
        # 1. 遍历 snippets
        # 2. 为每个 snippet['content'] 生成 embedding
        embeddings = self.embedding_model.encode([s['content'] for s in snippets])
        
        # 3. 将 embeddings 添加到 FAISS 索引
        # self.faiss_index.add(embeddings)
        
        # 4. 将 snippet 的文本内容和元数据存入 SQLite 表格
        #    (表格结构: id, faiss_index_id, content, metadata_json)
        # ...

    def search(self, query: str, k: int = 5) -> List[dict]:
        # 实现 RAG 查询逻辑
        # ...
```

##### **第 3 步：实现 LangGraph 节点 (`nodes/DocumentParsingNode.py`)**

这个节点将串联起整个流程。

```python
# nodes/DocumentParsingNode.py
from ..actions import doc_parser_actions
# from ..state import ResearchState # 假设的状态对象

def document_parsing_node(state: ResearchState) -> dict:
    """
    解析从 state 获取的文档内容，并将其持久化到 RAG 数据库。
    """
    # 1. 从 state 获取原始 Markdown 内容
    markdown_content = state['raw_document_content']
    
    # 2. 调用 action 进行智能分块和分片
    chunking_config = {"snippet_threshold": 3000}
    snippets = doc_parser_actions.intelligent_chunker(
        markdown_content, 
        config=chunking_config
    )
    
    # 3. 调用 action 进行持久化
    db_path = "memory/deepreader_rag.db" # 可配置
    doc_parser_actions.persist_chunks_to_rag(snippets, db_path)
    
    # 4. 更新 state，返回成功信息
    return {
        "parsing_status": "Completed",
        "snippet_count": len(snippets)
    }
```

---

#### **三、 工作流程总结**

1.  外部调用方将原始文档（PDF/EPUB/URL）传入 `deepreader` 图。
2.  `converter` 节点（我们之前已完成）将文档转换为统一的 Markdown 文本，并存入 `ResearchState`。
3.  图流转到 `DocumentParsingNode`。
4.  该节点执行 `document_parsing_node` 函数：
    *   调用 `intelligent_chunker`，后者按 **TOC -> Markdown -> LLM** 的优先级，结合**弹性分片**机制，将长文本分解为一系列大小适中的**片段**。
    *   调用 `persist_chunks_to_rag`，后者通过 `DeepReaderVectorStore` 将这些片段**向量化**并存入 `FAISS + SQLite` 数据库。
5.  节点执行完毕，更新 `ResearchState`，图继续流转到下一个节点（例如，摘要、分析等）。

这个计划为您提供了一个清晰、模块化且可扩展的开发路线图。


 -->