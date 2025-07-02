### **DeepReader Agent - 开发计划 (Development Plan)**

本计划基于 `PRD.md` 2.0 版本制定，旨在将 `DeepReader` Agent 从概念转化为可执行的、分阶段的开发任务。

#### **第一阶段：项目搭建与基础架构 (Milestone 1: Project Scaffolding & Core Architecture)**

**目标**: 建立稳固的项目骨架，为后续功能开发铺平道路。

1.  **环境与依赖 (1.1)**:
    *   使用 `Poetry` 初始化项目，管理 `pyproject.toml` 中的依赖。
    *   安装核心依赖: `langgraph`, `langchain`, `pydantic`, `typer` (用于 CLI), `marker-pdf`, `ebooklib`, `markdownify`。

3.  **核心状态定义 (1.3)**:
    *   在 `graph/state.py` 中，使用 `TypedDict` 严格定义 `DeepReaderState`，包含 `PRD` 中所有字段。这是整个应用的数据契约。
4.  **图骨架搭建 (1.4)**:
    *   在 `graph/graph.py` 中，创建 `StateGraph` 的实例，并设置 `DeepReaderState` 为其状态。路径为：dynamic-gptr/gpt_researcher/deepreader/backend/graph/read_state.py
    *   定义一个空的图，包含入口和出口，确保可以编译 (`.compile()`) 和调用。

---
#### **第二阶段：文档解析与结构化 (Milestone 2: Document Ingestion & Structuring)**

**目标**: 实现稳定、高效的文档摄入流程，将任意格式的文档转化为结构化的、可供 Agent 处理的数据。

1.  **文档格式转换 (2.1)**:
    *   **模块**: `dynamic-gptr/gpt_researcher/deepreader/backend/scraper`
    *   **任务**:
        *   实现 PDF to Markdown 转换，使用 `marker` 库以保留结构。
        *   实现 EPUB to Markdown 转换，使用 `EbookLib` 和 `markdownify`。
        *   (待定) 实现 URL to Markdown 的 web scraper。



#### 3.  **文档解析节点 (2.3)**:RAGPersistenceNode
    *   **模块**: `dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/RAGPersistenceNode.py`
    dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/docparsing_actions.py是执行动作的脚本
    *   **任务**: 
    实现 `DocumentParsingNode`，该节点负责根据输入来源不同的文件类型调用tool进行解析存档
    执行脚本
        - epub：使用dynamic-gptr/gpt_researcher/deepreader/backend/scraper/epub_converter.py
        - pdf：dynamic-gptr/gpt_researcher/deepreader/backend/scraper/pdf_converter.py
        - urls：dynamic-gptr/gpt_researcher/deepreader/backend/scraper/web_scraper.py
    有一些例外：例如arxiv的网站pdf文件结尾没有【.pdf】，但是他又不能被webscraper解析，那就要使用pdf解析。这种情况要识别，可以用elif逻辑。正常情况下输入文件一般是以pdf, epub结尾或者http开头的比较好识别

    转换成功后输出的都是str，这些str接下来要经过几个步骤的处理
    都在执行脚本中实现：dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/rag_actions.py
    1、调用openai的gpt-4.1-mini，识别输入文档的前500个文字，智能的提取出来meta信息，例如标题、作者、创作时间。（若果没有就[]），这个要返回作为state信息
    2、对转换后输出的str进行indexing转换成rag存储。ragaction只有chunk功能

dynamic-gptr/gpt_researcher/deepreader/backend/read_graph.py是图执行的脚本
dynamic-gptr/gpt_researcher/deepreader/backend/read_state.py

        











好的，这是一个非常核心和复杂的节点开发任务。我完全理解您的需求，我们不仅要处理不同的文件类型，还要在解析后立即进行初步的 AI 分析（元数据提取）和内容分块，为后续的深度分析做好准备。

这是一个非常好的设计，将“获取原始文本”、“提取元数据”和“内容分块”这三个紧密相关的步骤整合到一个逻辑节点中。

首先，关于节点命名，根据您的描述，这个节点的核心任务是“文档解析与预处理”。因此，我建议创建一个新的节点文件 `DocumentParsingNode.py`，而不是复用 `RAGPersistenceNode.py`。这能让图的结构更清晰：一个节点负责解析，另一个节点负责持久化。

接下来，我为您制定一个详细的开发计划，涵盖您提到的所有要点，并完善 `DeepReaderState`。

---

### **文档解析节点 (DocumentParsingNode) 开发计划**

#### **目标**
创建一个健壮的 LangGraph 节点，该节点能自动识别输入源的类型（PDF, EPUB, URL, ArXiv），调用相应的工具将其转换为纯净的 Markdown 文本，然后使用 LLM 提取文档元数据，并最终将内容分块，更新到核心状态 `DeepReaderState` 中。

---

#### **第一阶段：完善核心状态 (`read_state.py`)**

这是我们所有工作的基础。根据您的新需求，我将对 `DeepReaderState` 进行扩展，以容纳此节点产生的输出。

**修改方案 for `read_state.py`:**
1.  **输入字段**:
    *   `document_path: str`: 这个字段已经存在，将作为本节点的输入。
2.  **输出字段**:
    *   `raw_markdown_content: str`: **（新增）** 用于存储从 PDF, EPUB 或网页转换而来的、未经处理的完整 Markdown 字符串。这对于调试和可能的后续处理非常有用。
    *   `document_metadata: Dict[str, Any]`: 这个字段已经存在，我们将用 LLM 提取的 `title`, `author`, `creation_date` 等信息来填充它。
    *   `chunks: List[Dict[str, Any]]`: 这个字段也已存在，我们将用处理后的分块内容来填充它。

**小结**: 此阶段我们只需在 `DeepReaderState` 中增加 `raw_markdown_content: str` 字段。

---

#### **第二阶段：创建核心动作脚本 (`docparsing_actions.py`)**

这个新文件将包含节点执行的所有复杂逻辑，使其与 LangGraph 的节点定义解耦，便于独立测试。

**文件**: `dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/docparsing_actions.py`

**实现内容**:

1.  **函数 1: `_route_and_parse(document_path: str) -> str` (内部函数)**
    *   **目的**: 实现智能路由，根据 `document_path` 调用正确的解析工具。
    *   **逻辑**:
        *   `if "arxiv.org/pdf/" in document_path or document_path.lower().endswith('.pdf'):`
            *   调用 `pdf_to_markdown_tool`。
        *   `elif document_path.lower().endswith('.epub'):`
            *   调用 `epub_to_markdown_tool`。
        *   `elif document_path.lower().startswith('http'):`
            *   调用 `web_urls_to_markdown_tool`。
        *   `else:`
            *   抛出 `ValueError`，报告不支持的文件类型。
    *   **返回**: 纯净的 Markdown 字符串。

2.  **函数 2: `_extract_metadata_with_llm(content_preview: str) -> Dict[str, Any]` (内部函数)**
    *   **目的**: 使用 LLM 从文本预览中提取元数据。
    *   **逻辑**:
        *   接收文本的前 500 个字符作为 `content_preview`。
        *   构建一个英文 Prompt，指示 `gpt-4o-mini` (或者您指定的`gpt-4.1-mini`) 扮演一个图书管理员，从文本中识别并以 JSON 格式返回 `title`, `author`, `creation_date`。如果找不到，则对应的值为 `None`。
        *   调用 LLM 并解析其返回的 JSON 字符串。
    *   **返回**: 一个包含元数据的字典，例如 `{'title': '...', 'author': '...'}`。

3.  **函数 3: `parse_and_prepare_document(document_path: str) -> dict` (主函数)**
    *   **目的**: 编排整个流程，供节点直接调用。
    *   **逻辑**:
        1.  调用 `_route_and_parse(document_path)` 获取 `raw_markdown_content`。
        2.  如果内容为空，则提前返回错误。
        3.  调用 `_extract_metadata_with_llm(raw_markdown_content[:500])` 获取 `document_metadata`。
        4.  调用 `rag_actions.chunk_document(raw_markdown_content, source_id=document_path)` 来获取 `chunks`。
    *   **返回**: 一个包含所有结果的字典，键名与 `DeepReaderState` 中的字段完全对应：`{'raw_markdown_content': ..., 'document_metadata': ..., 'chunks': ...}`。

#### **第三阶段：增强 `RAGPersistenceNode`**

这是计划的核心，我们将重构 `RAGPersistenceNode`，使其成为一个强大的编排器。

**修改方案 for `RAGPersistenceNode.py`:**
*   **重构 `rag_persistence_node` 函数**:
    1.  从 `state` 中获取 `document_path` 和 `db_name`。
    2.  调用 `docparsing_actions.route_and_parse()` 获取 `raw_markdown_content`。
    3.  调用 `docparsing_actions.extract_metadata()` 获取 `document_metadata`。
    4.  调用现有的 `rag_actions.chunk_document()` 对 `raw_markdown_content` 进行分块，得到 `chunks`。
    5.  调用现有的 `rag_actions.persist_chunks()`，将 `chunks` 持久化到由 `db_name` 指定的向量数据库中。
    6.  返回一个包含所有更新的字典：`{'raw_markdown_content': ..., 'document_metadata': ..., 'chunks': ..., 'rag_status': 'Completed'}`。

---

### **执行计划总结**

我将按以下顺序为您执行开发：

1.  **修改** `dynamic-gptr/gpt_researcher/deepreader/backend/read_state.py`，添加 `raw_markdown_content` 和 `db_name` 字段。
2.  **创建** 新文件 `dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/docparsing_actions.py`，并实现路由解析和元数据提取功能。
3.  **重构** `dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/RAGPersistenceNode.py`，使其执行完整的解析、分块和持久化流程。

这个计划将您的所有需求整合到了一个统一的节点中，同时保持了代码的良好结构。

如果这个计划符合您的设想，我将首先开始**修改 `read_state.py` 文件**。



#### 对阅读内容的动态分段








#### **第三阶段：主动式阅读循环 (Milestone 3: Active Reading Loop)**

**目标**: 模拟人类专家精读过程，实现对文本片段的深度分析与联想。

1.  **"边栏笔记"节点 (3.1)**:
    *   **模块**: `dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/IterativeReadingLoop.py`, `dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/reading_knowledge_actions.py`
    *   **llm设置**： 
    备选两种llm，一种是搜索llm，对应googlellm,一种是fastllm，_call_normal_llm使用这个
    调用gptresearch模块的googlellm，他自带搜索功能，非常适合reader想到问题适合提问

dynamic-gptr/gpt_researcher/utils/google_llm.py，这个是搜索llm

dynamic-gptr/gpt_researcher/components/outline_planner.py
```python
# -*- coding: utf-8 -*-
import asyncio
from typing import Dict, Any

from gpt_researcher.prompts.graph_node_prompts.planning.initial_planning_prompts import (
    FINALIZE_OUTLINE_PROMPT,
    GENERATE_INITIAL_OUTLINE_PROMPT,
    GENERATE_RESEARCH_ROLE_PROMPT,
)
from gpt_researcher.utils.google_llm import call_google_llm
from gpt_researcher.utils.json_cleaner import clean_json_string
from gpt_researcher.utils.llm import create_chat_completion


class OutlinePlanner:
    """
    负责生成初步研究大纲和研究角色。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化大纲规划器。

        Args:
            config (Dict[str, Any]): 包含模型、温度等设置的配置字典。
        """
        self.config = config
        self.use_mock = self.config.get("use_mock", False)

    async def _call_normal_llm(self, prompt: str, llm_type: str) -> str:
        """
        封装标准的LLM调用（非搜索专用）。

        Args:
            prompt (str): 发送给模型的提示。
            llm_type (str): 要使用的LLM类型 (e.g., "smart_llm", "fast_llm", "strategic_llm").

        Returns:
            str: 模型返回的文本响应。
        """
        llm_provider = self.config.get(f"{llm_type}_provider")
        llm_model = self.config.get(f"{llm_type}_model")

        print(f"--- 正在使用 LangChain ({llm_provider}) 调用模型: {llm_model} ---")
        messages = [{"role": "user", "content": prompt}]
        temperature = self.config.get("temperature", 0.7)
        llm_kwargs = self.config.get("llm_kwargs", {}).copy()

        return await create_chat_completion(
            messages=messages,
            model=llm_model,
            llm_provider=llm_provider,
            temperature=temperature,
            llm_kwargs=llm_kwargs,
        )

    async def _call_search_llm(self, prompt: str) -> str:
        """
        封装需要联网搜索的LLM调用，优先使用Google原生SDK。
        """
        llm_provider = self.config.get("search_llm_provider")
        llm_model = self.config.get("search_llm_model")

        if llm_provider == "google_genai":
            return await call_google_llm(prompt, llm_model)
```
    *   记忆机制：https://langchain-ai.github.io/langgraph/how-tos/memory/
    https://langchain-ai.github.io/langgraph/how-tos/memory/#add-short-term-memory
    一本书形成一个短期记忆
    一本书看完后https://langchain-ai.github.io/langgraph/how-tos/memory/#add-long-term-memory形成长期记忆

`
    *   **任务**: 
            *分段功能*：这个功能放在阅读循环流程中：chapter
                2.  **分层解析逻辑**:dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/IterativeReadingLoop.py，动作dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/docparsing_actions.py实现功能，
                * **Markdown 标题->json**。如果没有TOC，则根据 Markdown 的 `#`, `##`, `###` 等标题层级进行递归切分，形成一个嵌套的章节树。优先切分到最细粒度的章节单元（ `###` 或 `####`）。把所有的#都统计完后，自动转换成json格式，章节名称为字段的名称，这样子书本的结构就非常完整了。而且这样子非常适合存储到state中作为一个结构清晰的文本。
                3.  **弹性分片机制 (Flexible Snippet Mechanism)**:
                如果没有#符号，无法通过markdown格式来划分段落。
                    * 设定一个"最佳阅读片段"字数阈值（设置默认，3000字）。
                把分段整理成阅读片段后，把内容保存到一个state中的raw_book字段。作为每个片段的内容记录state，`summary`, `questions_raised`、'status'、conclusion等，相当于是读书笔记的记录本子了。
        ---
        dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/reading_knowledge_actions.py是action脚本，
        node脚本在dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/IterativeReadingLoop.py
        阅读开始前，获取state中关于材料的metadata:author, title, creation_date
        实现 `ReadingNode`，它接收单个 `chapter` 并开始阅读规划。
        分段阅读逻辑：统计每个等级、每个单元的字数。优先从1级提纲开始阅读，一次阅读不超过5000字；如果1级提纲超过5000字，则分为多个5000字片段来阅读。如果1级提纲少于5000字，就正常阅读即可。
        读取state中的(`user_core_question`)：最开始的时候前端提供一个输入框，让用户在上传文档时，可以选择输入一个"核心探索问题" (`user_core_question`)。
        *   驱动调用不同的 LLM 生成多维笔记 
        fastllm-readingagent：要保持短期记忆
        阅读state中的rawbook，按照章节开始按顺序循环阅读
        输入：rawbook+(`user_core_question`)+背景记忆（如果有）
        输出：
        `chapter_summary`:带着用户的问题(`user_core_question`)阅读，总结本章节chapter的叙事脉络逻辑、精髓观点、重要数据。为后续的思维导图做好准备。读完一个章节后会生成一个summary，保存到章节的state字段中。
        `questions`：围绕本章节后续主旨发展的核心问题。不超过3个。

        revieweragent：
        输出的question，给revieweragent，使用fastllm，调用dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/rag_actions.py中（新增一个chat函数）的chat with 已经rag好的书本内容。
         *   **集成文档内 RAG**: 根据生成的 `questions` 或自身判断，调用 `vector_store.py` 在**全书范围**内进行检索，寻找关联信息，实现"跳跃式阅读"和"主动联想"。针对问题输出的内容组成了‘背景记忆’，再次保存到state中去。
         输出：对问题的回答，没有找到相关信息，就回复空白[]

        summaryagent:等待readingagent和revieweragent协作完毕后，针对对读完的章节做一个高度的浓缩总结，这个总结要有利于作为【背景记忆】，让readingagent接下来继续阅读。

        再进行下章节的阅读，一直到第一轮阅读完毕。

        
###

好的，非常清晰的第三阶段开发需求！这是一个非常激动人心的功能，它将使研究代理从简单的“信息提取”升级为“主动学习和思考”。

遵照您的指示，我将为您制定一个详细、分阶段的开发计划。此计划严格依据您提供的 PRD，旨在将复杂的任务分解为可执行、可验证的步骤。

---

### **第三阶段：主动式阅读循环 (Active Reading Loop) - 开发计划**

**核心目标**: 构建一个模拟人类专家精读的、可循环的 LangGraph 节点。该节点能够分层解析文档，并在“用户核心问题”的指引下，通过多智能体协作（阅读、反思、总结）对内容进行深度分析，同时利用短期记忆和 RAG 技术实现知识的联想与巩固。

---

#### **Phase 0: 环境搭建与状态扩展 (Setup & State Expansion)**

在编写核心逻辑之前，首先需要搭建好基础框架和数据结构。

*   **任务 0.1: 已经创建文件**
    *   dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/IterativeReadingLoop.py
    *   dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/reading_knowledge_actions.py

*   **任务 0.2: 扩展核心状态 `DeepReaderState`**
    *   打开 `dynamic-gptr/gpt_researcher/deepreader/backend/graph/read_state.py`。
    *   在 `DeepReaderState` 中添加以下字段，以支持阅读循环所需的数据：
        *   `user_core_question: Optional[str]`: 用于存储用户在前端输入的核心探索问题，可以为空。
        *   `table_of_contents: Optional[Dict[str, Any]]`: 用于存储从 Markdown 标题解析出的 JSON 格式章节树。
        *   `reading_snippets: Optional[List[Dict[str, Any]]]`: 当无法生成 `table_of_contents` 时，用于存储按字数切分的阅读片段。
        *   `active_memory: Dict[str, Any]`: 用于在循环中传递上下文，如 `background_summary`。

*   **任务 0.3: LLM 调用工具函数准备**
    参考：dynamic-gptr/gpt_researcher/components/outline_planner.py
    *   在 `reading_knowledge_actions.py` 中，参考 `outline_planner.py` 的实现，创建两个 LLM 调用辅助函数：
        *   `_call_fast_llm(prompt: str)`: 用于执行总结、提问等常规任务。
        *   `_call_search_llm(prompt: str)`: 用于需要联网搜索的场景，直接调用 `gpt_researcher.utils.google_llm.call_google_llm`。

        参考  ```python 
        import asyncio
from typing import Dict, Any

from gpt_researcher.prompts.graph_node_prompts.planning.initial_planning_prompts import (
    FINALIZE_OUTLINE_PROMPT,
    GENERATE_INITIAL_OUTLINE_PROMPT,
    GENERATE_RESEARCH_ROLE_PROMPT,
)
from gpt_researcher.utils.google_llm import call_google_llm
from gpt_researcher.utils.json_cleaner import clean_json_string
from gpt_researcher.utils.llm import create_chat_completion


class OutlinePlanner:
    """
    负责生成初步研究大纲和研究角色。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化大纲规划器。

        Args:
            config (Dict[str, Any]): 包含模型、温度等设置的配置字典。
        """
        self.config = config
        self.use_mock = self.config.get("use_mock", False)

    async def _call_normal_llm(self, prompt: str, llm_type: str) -> str:
        """
        封装标准的LLM调用（非搜索专用）。

        Args:
            prompt (str): 发送给模型的提示。
            llm_type (str): 要使用的LLM类型 (e.g., "smart_llm", "fast_llm", "strategic_llm").

        Returns:
            str: 模型返回的文本响应。
        """
        llm_provider = self.config.get(f"{llm_type}_provider")
        llm_model = self.config.get(f"{llm_type}_model")

        print(f"--- 正在使用 LangChain ({llm_provider}) 调用模型: {llm_model} ---")
        messages = [{"role": "user", "content": prompt}]
        temperature = self.config.get("temperature", 0.7)
        llm_kwargs = self.config.get("llm_kwargs", {}).copy()

        return await create_chat_completion(
            messages=messages,
            model=llm_model,
            llm_provider=llm_provider,
            temperature=temperature,
            llm_kwargs=llm_kwargs,
        )

    async def _call_search_llm(self, prompt: str) -> str:
        """
        封装需要联网搜索的LLM调用，优先使用Google原生SDK。
        """
        llm_provider = self.config.get("search_llm_provider")
        llm_model = self.config.get("search_llm_model")

        if llm_provider == "google_genai":
            return await call_google_llm(prompt, llm_model)
            ```

---

#### **Phase 1: 文档结构化解析 (Document Structuring)**

此阶段的核心是将原始的 Markdown 文本转换为结构化的、可供循环处理的格式。
上一个节点生成的pdf转换成md文件是str，此时作为输入

*   **任务 1.1: 实现 Markdown 标题解析功能**
    *   **位置**: `dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/docparsing_actions.py`。
    *   **函数**: 创建一个新函数 `parse_markdown_to_json_toc(markdown_text: str) -> Dict[str, Any]`。
    *   **逻辑**:
        1.  使用正则表达式或一个简单的解析器遍历 Markdown 文本，识别所有 `#`, `##`, `###` 等标题行。
        2.  根据标题级别构建一个嵌套的 Python 字典（JSON 结构），其中每个键是章节名，值可以是一个包含`content`和`children`（子章节字典）的字典。
        3.  函数应能处理不规范的标题顺序，并返回一个完整的、代表全书结构的章节树。

*   **任务 1.2: 实现弹性分片备用机制**
    *   **位置**: 同样在 `docparsing_actions.py`。
    *   **函数**: 创建 `chunk_text_by_size(markdown_text: str, chunk_size: int = 3000) -> List[str]`。
    *   **逻辑**: 简单地将文本按指定的字数阈值（默认为 3000）切分为字符串列表。

*   **任务 1.3: 创建文档结构化 Action**
    *   **位置**: `reading_knowledge_actions.py`。
    *   **函数**: 创建 `structure_document_action(state: DeepReaderState) -> Dict[str, Any]`。
    *   **逻辑**:
        1.  从 `state` 中获取 `raw_markdown_content`。
        2.  调用 `docparsing_actions.py` 中的 `parse_markdown_to_json_toc`。
        3.  如果返回的 TOC 非空，则将其格式化（例如，展平为一个包含路径和内容的章节列表）并存入 `table_of_contents` 状态字段。
        4.  如果 TOC 为空（说明没有#标题），则调用 `chunk_text_by_size`，将结果存入 `reading_snippets` 状态字段。
        5.  此 Action 为阅读循环准备好要迭代处理的数据。

---

#### **Phase 2: "边栏笔记" 节点与多智能体协作 (Reading Loop & Agent Collaboration)**

这是本阶段最核心的部分，将实现具体的阅读、反思、总结循环。

所有prompts在：dynamic-gptr/gpt_researcher/deepreader/backend/prompts.py
*   **任务 2.1: 实现 ReadingAgent 核心逻辑**
    *   **位置**: `reading_knowledge_actions.py`。
    *   **函数**: `reading_agent_action(chapter_content: str, user_question: str, background_memory: str) -> Dict[str, Any]`。
    *   **逻辑**:
        1.  接收当前章节内容、用户核心问题和上一轮的背景记忆。
        2.  使用 `_call_fast_llm`，构建 Prompt，要求 LLM 完成两件事：
            *   生成 `chapter_summary`: 总结章节核心观点和脉络。
            *   生成 `questions`: 提出不超过3个关于后续内容或当前内容深度探索的问题。
        3.  返回包含 `summary` 和 `questions` 的字典。

*   **任务 2.2: 实现 ReviewerAgent (RAG) 逻辑**
    *   **位置**: `dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/rag_actions.py`。
    *   **函数**: 新增一个 `chat_with_retriever(questions: List[str], db_name: str) -> List[str]`。
    *   **逻辑**:
        1.  接收 ReadingAgent 生成的问题列表和当前文档的数据库名 (`db_name`)。
        2.  加载对应的 FAISS 和 SQLite 数据库。
        3.  对每个问题，在**全书范围**内执行 RAG 检索。
        4.  将检索到的上下文和问题喂给 `_call_fast_llm` 生成答案。
        5.  返回一个答案列表。如果找不到信息，对应答案为空字符串。

*   **任务 2.3: 实现 SummaryAgent 逻辑**
    *   **位置**: `reading_knowledge_actions.py`。
    *   **函数**: `summary_agent_action(chapter_summary: str, reviewed_answers: List[str]) -> str`。
    *   **逻辑**:
        1.  接收本章小结和 ReviewerAgent 的回答。
        2.  使用 `_call_fast_llm`，要求 LLM 将这些信息浓缩成一个高度精炼的、适合作为下一轮阅读背景记忆的段落 (`background_memory`)。
        3.  返回这个精炼总结。

---




























#### **Phase 3: 循环控制器与状态/记忆管理 (Loop Controller & Memory)**

此阶段负责将上述 Agent 串联起来，并管理整个循环流程和记忆。

*   **任务 3.1: 构建 `IterativeReadingLoop` 节点**
    *   **位置**: `IterativeReadingLoop.py`。
    *   **逻辑**:
        1.  这是一个 `async def` 函数，接收 `state: DeepReaderState`。
        2.  **首次运行**: 调用 `structure_document_action` 准备阅读材料。
        3.  **循环迭代**:
            *   从 `table_of_contents` 或 `reading_snippets` 中获取当前要阅读的章节/片段。
            *   获取 `user_core_question` 和 `active_memory` 中的 `background_memory`。
            *   **调用 ReadingAgent**: 执行 `reading_agent_action`。
            *   **调用 ReviewerAgent**: 将上一步生成的 `questions` 传递给 `rag_actions.chat_with_retriever`。
            *   **调用 SummaryAgent**: 执行 `summary_agent_action`，生成新的 `background_memory`。
            *   **更新状态**: 将本轮生成的 `chapter_summary`, `questions`, `reviewed_answers` 更新回 `state` 中对应的章节/片段记录里。将新的 `background_memory` 更新到 `active_memory` 中。
        4.  返回更新后的状态字典。

*   **任务 3.2: 实现短期记忆 (Short-Term Memory)**
    *   **方法**: 利用 LangGraph 的检查点 (Checkpointer) 机制。
    *   **实现**:
        1.  在主图 (`read_graph.py`) 的编译阶段，配置一个 `langgraph.checkpoint.sqlite.SqliteSaver`。
        2.  在调用图 (`app.ainvoke`) 时，传入一个唯一的 `thread_id`（例如基于书本的 ID 或 session ID）。
    *   **效果**: LangGraph 会自动将每一步执行后的 `DeepReaderState` 完整地保存到 SQLite 数据库中。这天然地实现了“一本书形成一个短期记忆”，并且支持任务的中断和恢复。

*   **任务 3.3: 规划长期记忆 (Long-Term Memory)**
    *   **方法**: 在阅读循环结束后，增加一个最终总结节点。
    *   **实现**: 创建一个 `FinalSummaryNode`，它在循环结束后被调用。
    *   **逻辑**: 此节点遍历 `state` 中记录的所有章节的 `chapter_summary` 和 `reviewed_answers`，生成一份关于整本书的、高度浓缩的最终报告或知识图谱。这份报告可以被存储到专门的长期记忆数据库中，供未来的跨文档查询使用。

---














#### **Phase 4: 图的集成与路由 (Graph Integration & Routing)**

最后，将所有新组件集成到主 LangGraph 中。

*   **任务 4.1: 更新主图 (`read_graph.py`)**
    *   注册新节点: `graph.add_node("structuring", structure_document_action)` 和 `graph.add_node("reading_loop", IterativeReadingLoop)`。
    *   **修改边**: 将 `RAGPersistenceNode` 的下一条边指向 `structuring` 节点。
    *   **定义条件边**: 在 `reading_loop` 节点后添加一个条件边。
        *   **条件函数**: `should_continue_reading(state: DeepReaderState) -> str`。
        *   **逻辑**: 检查是否所有章节/片段都已处理完毕。如果处理完，返回 `"end_reading"`；否则返回 `"continue_reading"`。
        *   **路由**: `"continue_reading"` 指向 `reading_loop` 自身，形成循环。`"end_reading"` 指向 `END` 或未来的 `FinalSummaryNode`。

这个计划将开发过程分解成了四个逻辑清晰、循序渐进的阶段。建议按顺序完成每个阶段的任务，这样可以确保每个组件在集成前都已稳定，便于调试。














好的，我理解您的需求。这是一个相当核心的调整，从“按章节”阅读的确定性模型转向“按固定字数分块”的非确定性模型，确实需要对状态管理、Agent 协作逻辑和 Prompt 进行一次全面的、谨慎的升级。

您考虑得非常周到，这个改动确实会影响 `read_state.py`, `IterativeReadingLoop.py`, `reading_knowledge_actions.py` 和 `prompts.py`。

在动手修改代码之前，我先为您制定一个详细的、分阶段的改造方案。请您审阅，确认无误后我再开始实施。

---

### **改造方案：支持“跨片段上下文感知”的固定块阅读模式**

**核心目标：** 让 `ReadingAgent` 能够处理任意文本片段，并利用前一片段的分析结果，智能地拼接和理解跨越片段边界的章节内容。

---

#### **第一阶段：数据结构升级 (`read_state.py`)**

为了支持新的阅读模式，我们需要调整核心状态 `DeepReaderState` 来跟踪和传递更丰富的上下文。

1.  **新增 `snippet_analysis_history` 字段**:
    *   我将在 `DeepReaderState` 中添加一个新字段：
        ```python
        snippet_analysis_history: List[List[Dict[str, Any]]]
        ```
    *   **用途**：这将是一个列表的列表，专门用于存储每个片段（snippet）的阅读产出。
        *   外层列表的每个元素代表一个已阅读的片段。
        *   内层列表是 `ReadingAgent` 对该片段分析后返回的 `[{ "title": "...", "chapter_summary": "...", "questions": [] }, ...]` 数组。
    *   **作用**：这个历史记录将成为实现“跨片段上下文感知”的核心数据源。下一个 `ReadingAgent` 在处理新片段前，会从这里读取上一个片段的分析结果。

2.  **调整 `active_memory` 的角色**:
    *   `active_memory` 中的 `background_summary` 将继续扮演“全局背景记忆”的角色。它由 `SummaryAgent` 在每个片段阅读循环结束时更新，包含截至目前所有已读内容的浓缩精华，为 `ReadingAgent` 提供宏观指引。

---

#### **第二阶段：Prompt 重新设计 (`prompts.py`)**

我将根据您的要求，优化三个核心 Agent 的 Prompt。

1.  **`READING_AGENT_PROMPT` (核心改造)**:
    *   **输入变量**：增加一个新的输入变量 `previous_chapters_context`。
    *   **模板逻辑**：
        *   明确告知 LLM，它正在处理的 `current_snippet` 可能包含从上一个片段延续而来的、不完整的章节。
        *   `previous_chapters_context` 将被填充为上一个片段产出的**最后1-2个章节的分析对象 (title, summary)**。
        *   Prompt 会指示 LLM：在分析当前片段时，首先检查内容的开头是否能与 `previous_chapters_context` 无缝衔接。如果能，就将它们**合并理解**，并生成一个更完整、连贯的 `chapter_summary`。
        *   **输出格式**：严格要求 LLM 输出您指定的 **JSON数组** 格式：`[{ "title": "...", "chapter_summary": "...", "questions": [...] }]`。

2.  **`REVIEWER_AGENT_PROMPT` (聚焦优化)**:
    *   **输入变量**：增加 `user_question`。
    *   **模板逻辑**：指示 `ReviewerAgent` 在回答具体问题时，要始终围绕用户最初的核心研究问题 (`user_question`) 来组织答案，使其回答更有针对性。

3.  **`SUMMARY_AGENT_PROMPT` (动态综合)**:
    *   **输入变量**：将 `chapter_summary` 调整为 `newly_generated_summaries` (一个包含当前片段所有章节摘要的字符串)。
    *   **模板逻辑**：指示 `SummaryAgent` 将当前片段产生的所有新章节摘要 (`newly_generated_summaries`) 和 `ReviewerAgent` 的回答进行综合，提炼成一段**新的、补充性的背景记忆**，用于更新全局的 `active_memory`。

---

#### **第三阶段：核心业务逻辑重构 (`reading_knowledge_actions.py` 和 `IterativeReadingLoop.py`)**

这是将新策略落地的关键步骤。

1.  **`reading_knowledge_actions.py` 的改动**:
    *   **`reading_agent_action` 函数**:
        *   **函数签名**：增加 `previous_chapters_context: str` 参数。
        *   **返回值**：返回值类型从 `Dict[str, Any]` 变为 `List[Dict[str, Any]]`，以匹配新的 Prompt 输出。
        *   **内部逻辑**：更新 JSON 解析和验证逻辑，以处理和校验返回的 JSON 数组。
    *   **`summary_agent_action` 函数**:
        *   **函数签名**：参数 `chapter_summary: str` 将变为 `newly_generated_summaries: str`，以便接收一个包含多段总结的组合字符串。

2.  **`IterativeReadingLoop.py` (`iterative_reading_node`) 的改动**:
    *   **读取上下文**: 在调用 `reading_agent_action` 之前，从 `state.snippet_analysis_history` 中提取最后一个元素（即上一个片段的分析结果），并从中获取最后两个章节的摘要，格式化为字符串后作为 `previous_chapters_context`。
    *   **调用 Agents**:
        *   将 `previous_chapters_context` 传入 `reading_agent_action`。
        *   `reading_agent_action` 返回的是一个列表，节点需要遍历此列表：
            *   **收集问题**：将所有 `questions` 收集起来，统一交给 `ReviewerAgent`。
            *   **拼接摘要**：将所有 `chapter_summary` 拼接成一个长字符串，交给 `SummaryAgent`。
    *   **更新状态**:
        *   将 `reading_agent_action` 返回的完整列表追加到 `state.snippet_analysis_history` 中。
        *   将 `SummaryAgent` 返回的新背景记忆更新到 `state.active_memory.background_summary`。
        *   遍历 `ReadingAgent` 的输出，用 `title` 和 `chapter_summary` 更新 `state.chapter_summaries` 字典，以供最终报告生成时使用。

---

这个方案旨在以最小的侵入性实现最大的功能升级，确保数据流清晰、逻辑严谨。如果您对这个方案满意，我将立刻开始着手实施。
















---
#### **第四阶段：全局综合与关系构建 (Milestone 4: Global Synthesis & Relationship Mapping)**

**目标**: 从章节理解跃升至全书洞察，提炼核心实体与关系。


<!-- 2.  **实体关系链接节点 (4.2)**:
    *   **模块**: `graph/nodes/synthesis.py`
    *   **任务**: 实现 `KeyEntityLinkageNode`：
        *   统计所有 `entities`，找出高频核心实体。
        *   针对核心实体对，使用 RAG 在全书中检索相关上下文。
        *   调用 LLM 提炼它们之间的关系，并更新到 `DeepReaderState`。 -->

---
#### **第五阶段：输出与集成 (Milestone 5: Output & Integration)**


接下来完成读书报告的输出工作
我先阐述我需要的是一份什么样的报告
1、完全基于内容的内容整合
2、能够找到这本书的精髓和重点、梳理清楚脉络
3、用户提出的核心问题能够得到充分的解释
4、输出一个清晰的思维导图
这个工作可以由几个agent组成一个小组来做





2. 解决方案：从“单兵作战”到“动态读书会小组”
为了解决上述问题，并满足您“讨论组写作”、“结合现实世界”、“捕捉精髓”的需求，我建议我们将gpt-researcher的框架从一个线性的研究员模型升级为一个协作式的多智能体（Multi-Agent）讨论模型。
我们可以构建一个“动态读书会小组”，每个Agent扮演不同角色，它们的协作与辩论将共同“挖掘”出书籍的深层价值。这非常契合LangGraph的图状、循环、状态驱动的特性。
建议的角色设计 (Agent Roles):
首席编辑 (Chief Editor / Orchestrator)
职责: 负责整体流程的推进。它不直接写作，而是提出议题（例如：“我们先来分析第一章的核心论点是什么？”），将其他Agent的产出进行整合、提炼和总结，并决定下一步的讨论方向。这是GPTResearcher类角色的自然演进。
内容分析师 (Content Analyst)
职责: 负责精准的文本内（In-Text）分析。它的任务是进行高质量的摘要、梳理章节的逻辑脉络、提取关键论点和论据。它是保证讨论基于原著事实的基础。
主题思想家 (Thematic Thinker)
职责: 负责跨文本（Cross-Text）的抽象思考。它接收“内容分析师”的产出，并思考：“这些论点背后反映了作者怎样的核心思想？它们与书中其他章节的哪些主题有关联？作者的世界观是什么？”
批判性思考者 (Critical Thinker / Devil's Advocate)
职责: 负责提出挑战和不同视角。它会质疑：“作者的这个论据是否充分？他的逻辑有没有漏洞？是否存在其他的解释或反例？” 这个角色对于保证报告的深度和思辨性至关重要。
现实世界连接者 (Real-World Connector)
职责: 负责将书本与现实世界连接起来，这正是您所期望的。它会主动使用检索工具（如网络搜索Agent）来寻找：“书中的理论在今天的商业世界/科技领域/社会事件中有什么应用或体现？有没有最近的新闻或研究可以印证或反驳作者的观点？”




好的，这是一个非常精彩和富有远见的构想！将阅读理解的产出（`IterativeReadingLoop`的结果）作为输入，启动一个多智能体“写作研讨会”，这完全符合从“知识内化”到“思想输出”的高级认知流程。这个设计不仅能生成报告，更能确保报告的深度、逻辑性和思辨性。

我将为您设计一个清晰、完整、可执行的开发PLAN，严格遵循您的构想和技术路径。

---

### **开发计划：构建“写作研讨会”智能体团队**

**核心目标**：创建一个新的 LangGraph 流程，该流程在`IterativeReadingLoop`之后启动，通过一个由“脉络分析师”、“主题思想家”、“批判者”、“总编辑”和“Writer”组成的协作团队，将精读分析的成果转化为一篇结构严谨、思想深刻的读书笔记。

---

#### **第二阶段：Prompt设计与Action脚本开发 (`prompts.py` & `writing_actions.py`)**

在构建图节点之前，我们先定义每个智能体执行任务时所需的“大脑”（Prompts）和“手臂”（Actions）。

*   **文件1**: `dynamic-gptr/gpt_researcher/deepreader/backend/prompts.py`
    *   **任务**: 新增以下英文Prompt模板：
        *   `ANALYZE_NARRATIVE_FLOW_PROMPT`: 指导“脉络分析师”阅读所有章节摘要，并输出一个连贯的叙事或逻辑大纲。
        *   `EXTRACT_THEMES_PROMPT`: 指导“主题思想家”提炼3个核心Key。
        *   `CRITIQUE_THEMES_PROMPT`: 指导“批判者”根据已有材料对3个Key提出质疑和改进建议。
        *   `REFINE_THEMES_PROMPT`: 指导“主题思想家”根据“批判者”的反馈，优化3个Key。
        *   `GENERATE_FINAL_OUTLINE_PROMPT`: 指导“总编辑”整合所有信息，创建最终报告大纲。
        *   `WRITE_REPORT_SECTION_PROMPT`: 指导“Writer”根据丰富、多源的上下文，撰写指定的报告段落。

*   **文件2**: `dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/writing_actions.py`
    *   **任务**: 创建以下与Agent角色一一对应的Action函数：
        *   `analyze_narrative_flow_action(...)`: 调用`smart_llm`，执行“脉络分析师”任务。
        *   `extract_themes_action(...)`: 调用`smart_llm`，执行“主题思想家”任务。
        *   `critique_and_refine_action(...)`: 实现“批判者”与“思想家”的辩论循环。内部会多次调用`smart_llm`。
        *   `generate_final_outline_action(...)`: 调用`smart_llm`，执行“总编辑”任务。
        *   `write_section_action(...)`: 调用`smart_llm`，执行“Writer”任务。
        *   `rag_chat_action(query: str, db_name: str)`: **(新增RAG接口)** 封装与FAISS/SQLite交互的逻辑，供“Writer”和“批判者”按需调用。
        *   `search_with_google_action(query: str)`: **(新增搜索接口)** 封装调用`call_google_llm`的逻辑，供需要时进行外部验证。

---

#### **第三阶段：写作团队的图节点实现 (`ReportGenerationNode.py`)**

这是整个计划的核心。我们将创建一个单独的、功能强大的节点来封装整个写作团队的协作流程。

*   **文件**: `dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/ReportGenerationNode.py`
*   **任务**: 实现`report_generation_node(state: DeepReaderState) -> Dict[str, Any]`函数。

**节点内部执行逻辑（伪代码）:**

```python
async def report_generation_node(state):
    # --- 1. 脉络分析师 ---
    all_summaries = state.chapter_summaries
    narrative_outline = await analyze_narrative_flow_action(all_summaries)
    state['report_narrative_outline'] = narrative_outline

    # --- 2. 主题思想家 (初稿) ---
    initial_keys = await extract_themes_action(all_summaries)
    state['thematic_analysis'] = initial_keys

    # --- 3. 批判者与思想家 (辩论与共识) ---
    # 此处模拟一个2轮的辩论循环以达成共识
    current_keys = initial_keys
    discussion_log = []
    for i in range(2):
        feedback = await critique_and_refine_action(
            current_keys, 
            state.raw_reviewer_outputs, 
            state.background_summary
        )
        discussion_log.append(f"Round {i+1} Critique: {feedback}")
        
        refined_keys = await extract_themes_action(
            all_summaries, 
            feedback_from_critic=feedback
        )
        current_keys = refined_keys
        discussion_log.append(f"Round {i+1} Refinement: {refined_keys}")

    state['final_keys'] = current_keys
    state['critic_consensus_log'] = discussion_log

    # --- 4. 总编辑 ---
    final_outline = await generate_final_outline_action(
        narrative_outline, 
        state.final_keys
    )
    state['final_report_outline'] = final_outline

    # --- 5. Writer (迭代写作) ---
    draft_report_parts = []
    writer_context = "这是报告的开篇。"
    for section in state.final_report_outline:
        # 为每个子标题进行写作
        for sub_section in section.get('children', []):
            rag_context = await rag_chat_action(
                query=f"关于 '{sub_section['title']}' 的详细资料",
                db_name=state.db_name
            )
            
            written_part, part_summary = await write_section_action(
                final_keys=state.final_keys,
                full_outline=state.final_report_outline,
                current_section_title=sub_section['title'],
                rag_context=rag_context,
                all_summaries=all_summaries,
                previous_part_summary=writer_context
            )
            draft_report_parts.append(written_part)
            writer_context = part_summary # 迭代上下文

    state['draft_report'] = "\\n\\n".join(draft_report_parts)
    
    # --- 最终返回更新后的完整状态 ---
    return state
```

---

#### **第四阶段：图的集成与记忆配置 (`read_graph.py`)**

最后，我们将这个新的“写作研讨会”节点无缝地集成到现有的 `DeepReader` 图流程中。

*   **文件**: `dynamic-gptr/gpt_researcher/deepreader/backend/read_graph.py`
*   **任务**:
    1.  **注册新节点**:
        ```python
        from .graph.nodes.ReportGenerationNode import report_generation_node
        # ...
        graph.add_node("report_generation", report_generation_node)
        ```
    2.  **修改图的流程**:
        *   找到`reading_loop`节点的条件边定义。
        *   将其中的`"end": END`修改为`"end": "report_generation"`。这表示阅读循环结束后，流程自动进入报告生成阶段。
    3.  **连接到终点**:
        *   在图的定义中增加一条从`report_generation`到`END`的边：
        ```python
        graph.add_edge("report_generation", END)
        ```
    4.  **配置检查点 (Checkpointing)**:
        *   正如您提到的，我们将利用LangGraph的检查点机制来保存`DeepReaderState`的每一步变化，这天然地为整个“阅读-写作”流程提供了强大的短期记忆和断点续传能力。确保在图编译时配置了`SqliteSaver`。

---

### **执行计划总结**

我将严格按照以下顺序为您执行开发：

1.  **修改** `read_state.py`，添加支持写作团队所需的所有新字段。
2.  **创建** `writing_actions.py` 和 **更新** `prompts.py`，为所有Agent角色定义其核心能力。
3.  **开发** `ReportGenerationNode.py`，实现多智能体协作、辩论和迭代写作的复杂逻辑。
4.  **最后，修改** `read_graph.py`，将新的写作节点集成到主流程中，完成整个工作流的闭环。

这个计划将您的宏大构想转化为了一个结构化、分阶段、可实施的工程蓝图。如果此方案符合您的预期，我将立即开始**第一阶段：修改 `read_state.py` 文件**。







改造环节

#### **第一阶段：状态与Prompt基础建设 (State & Prompt Foundation)**

为新的`KeyInfoAgent`准备好数据契约和“大脑”。

1.  **任务1.1: 扩展核心状态 `DeepReaderState` (`dynamic-gptr/gpt_researcher/deepreader/backend/read_state.py`)**
    *   **目的**: 为存储提取的关键信息和管理跨片段上下文提供数据结构。
    *   **修改点**: 在`DeepReaderState`中增加以下字段：
        ```python
        key_information: List[Dict[str, Any]]
        """
        存储从文档中提取的所有关键信息（数据和论断）的列表。
        列表中的每个元素都是一个由 KeyInfoAgent 输出的结构化字典。
        """

        active_memory: Optional[Dict[str, Any]]
        """
        (扩展现有字段)
        用于在循环中传递上下文。我们将在此字典内增加一个键：
        'last_data_item_context': 用于存放上一个片段结尾可能未完成的数据项，以解决跨片段问题。
        """
        ```

2.  **任务1.2: 设计 `KeyInfoAgent` 的Prompt (`dynamic-gptr/gpt_researcher/deepreader/backend/prompts.py`)**
    *   **目的**: 创建一个专门用于指导LLM进行精确信息提取的Prompt。
    *   **新增Prompt**: `KEY_INFO_AGENT_PROMPT`
        ```python
        KEY_INFO_AGENT_PROMPT = """
        As a meticulous data analyst playing the role of a {research_role}, your task is to extract valuable, citable data points and key assertions from the provided text snippet. Your extraction must be sharply focused on information relevant to the **User's Core Question**. You are not just extracting any data, but data that serves as evidence or a core component for answering this question.

        **Critical Instructions:**
        1.  **Value-Driven Extraction:** Only extract data or assertions that are directly useful for addressing the **User's Core Question**. Ignore trivial or irrelevant information.
        2.  **Handle Cross-Snippet Data:** A data block (like a table or complex description) might have started in a previous snippet. The **Last Data Item Context** contains the last data object from the previous snippet if it was potentially incomplete. If the current snippet's beginning clearly continues this data, you MUST merge them into a single, complete data entry in your output.
        3.  **Maintain Order:** The extracted data items MUST be listed in the exact order they appear in the **Content to Analyze**.
        4.  **Output Language:** Must be in Chinese.

        **Context Provided for Your Judgment:**
        1.  **User's Core Question:** {user_question}
        2.  **Overall Background Memory:** {background_memory}
        3.  **Last Data Item Context (from preceding snippet, if any):**
            {last_data_item_context}

        **Content to Analyze:**
        ---
        {chapter_content}
        ---

        **Required Output Format (Strict):**
        *   If you find one or more valuable data points, you MUST respond with a single, valid JSON array of objects. Do NOT include any text outside this array. Each object must have the following structure:
            ```json
            [
              {{
                "data_name": "该数据或论断的简明标题",
                "description": "对该数据或论断的核心意义进行精炼的描述，说明其为何与核心问题相关",
                "rawdata": {{ "key": "value", "table_rows": [...] }},
                "originfrom": "数据来源的章节标题 (如果清晰可辨，否则为空)"
              }}
            ]
            ```
        *   If, after careful evaluation, you find absolutely no valuable data in the snippet relevant to the user's question, you MUST respond with the exact plain text string: **无有价值数据**
        """
        ```

---

#### **第二阶段：核心动作实现 (Action Implementation)**

创建`KeyInfoAgent`的具体执行逻辑。

1.  **任务2.1: 创建`key_info_agent_action`函数 (`dynamic-gptr/gpt_researcher/deepreader/backend/graph/actions/reading_knowledge_actions.py`)**
    *   **目的**: 封装调用LLM、处理Prompt和解析响应的完整业务逻辑。
    *   **函数签名**:
        ```python
        async def key_info_agent_action(
            current_chunk: str,
            user_question: str,
            background_memory: str,
            research_role: str,
            last_data_item_context: str
        ) -> List[Dict[str, Any]]:
        ```
    *   **实现逻辑**:
        1.  使用传入的参数格式化`KEY_INFO_AGENT_PROMPT`。
        2.  调用`call_fast_llm`获取响应。
        3.  **解析响应**:
            *   如果响应是`"无有价值数据"`，则返回一个空列表`[]`。
            *   否则，使用`json_repair_loads`尝试将响应解析为JSON数组。gemini一般会有一个```json```包裹json内容
            *   **增加重试机制**: 如果JSON解析失败，应像`reading_agent_action`一样进行重试。
            *   **验证结构**: 验证解析后的列表中，每个对象都包含`data_name`, `description`, `rawdata`, `originfrom`这些必需的键。
        4.  返回验证通过的JSON列表。如果多次重试后依然失败，记录错误并返回空列表。

---

#### **第三阶段：集成到阅读循环 (Integration into Reading Loop)**

将新的Agent无缝地嵌入到`IterativeReadingLoop`中。

1.  **任务3.1: 修改`iterative_reading_node` (`dynamic-gptr/gpt_researcher/deepreader/backend/graph/nodes/IterativeReadingLoop.py`)**
    *   **目的**: 编排`KeyInfoAgent`的调用，并管理其状态。
    *   **修改点**:
        1.  **初始化**: 在首次运行时，确保新状态字段被初始化。
            ```python
            # ...
            structured_state.setdefault("key_information", [])
            structured_state.setdefault("active_memory", {
                "background_summary": "这是文档的开端。",
                "last_data_item_context": "" # 初始化为空字符串
            })
            return structured_state
            ```
        2.  **并行调用**: 在`iterative_reading_node`的主流程中，与`reading_agent_action`并行或紧随其后，调用新的`key_info_agent_action`。
            ```python
            # ...
            last_data_item_context = state.get("active_memory", {}).get("last_data_item_context", "")

            # 使用 asyncio.gather 实现并行调用
            results = await asyncio.gather(
                reading_agent_action(...),
                key_info_agent_action(
                    current_chunk,
                    user_question,
                    background_memory,
                    research_role,
                    last_data_item_context
                )
            )
            reading_result_list = results[0]
            key_info_result_list = results[1]
            ```
        3.  **状态更新**:
            *   **聚合结果**: 将`key_info_result_list`的内容追加到全局的`key_information`列表中。
            *   **管理跨片段上下文**:
                *   检查`key_info_result_list`是否为空。
                *   如果不为空，则将其**最后一个元素**转换为JSON字符串，存入`active_memory`的`last_data_item_context`字段，供下一次循环使用。
                *   如果为空，则将`last_data_item_context`重置为空字符串`""`。
            *   **最终返回**: 在函数末尾返回的状态更新字典中，包含对`key_information`和`active_memory`的更新。
                ```python
                # 示例
                new_last_data_context = json.dumps(key_info_result_list[-1], ensure_ascii=False) if key_info_result_list else ""

                updated_state = {
                    "key_information": state.get("key_information", []) + key_info_result_list,
                    "active_memory": {
                        "background_summary": new_background_memory,
                        "last_data_item_context": new_last_data_context
                    },
                    # ... 其他字段
                }
                ```

---

这个计划详细地描述了如何实现一个独立、精确、上下文感知的关键信息提取代理，并将其无缝集成到您现有的高级阅读框架中。如果此方案符合您的设-想，请告知，我们可以随时准备进入代码实现阶段。


