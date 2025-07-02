# DeepReader - 智能文档深度阅读与分析系统

## 🎯 项目简介

**DeepReader** 是一个基于 LangGraph 的高级智能文档阅读和分析系统，旨在模拟人类专家的沉浸式、反思式阅读过程。该系统能够在短时间内深度理解、分析和重构任何长篇或复杂的文档（如书籍、财报、研究论文等），并根据用户的特定需求生成高度定制化的知识产物。

### 核心特色

- 🤖 **多智能体协作**：通过 ReadingAgent、ReviewerAgent、SummaryAgent 等多个专业化AI代理的协同工作，实现对文档的多维度、深层次分析。
- 🧠 **主动式迭代阅读**：模仿人类精读过程，包含提出问题、基于问题进行检索（RAG）、生成边栏笔记、整合记忆等步骤，循环往复直至读完整篇文档。
- 🔍 **RAG 增强分析**：内置基于 FAISS 和 SQLite 的本地知识库，在阅读过程中随时进行全文检索和深度问答，发现跨章节的隐藏关联。
- 💾 **状态持久化与断点续传**：所有处理过程和状态都通过 LangGraph 的 Checkpointer 机制进行持久化，支持从任意中断点无缝恢复任务，无惧长文档处理过程中的意外中断。
- 📊 **结构化与定制化输出**：能够生成章节摘要、主题思想分析、批判性辩论记录、完整分析报告等多种结构化的知识产物。

---

## ⚙️ 工作机制

DeepReader 的核心是一个由 LangGraph 精心编排的、有状态的图（Graph）。这个图定义了一系列节点（工作单元）和边（流转条件），模拟了专家的阅读思考流程。

### 系统工作流程

```mermaid
graph TD
    %% 输入阶段
    START([用户输入]) --> INPUT{文档类型判断}
    INPUT -->|PDF文件| PDF[PDF解析器]
    INPUT -->|EPUB文件| EPUB[EPUB解析器]
    INPUT -->|网页URL| WEB[网页抓取器]
    
    %% RAG持久化节点 - 第一个核心节点
    PDF --> RAG_NODE[RAG持久化节点<br/>RAGPersistenceNode]
    EPUB --> RAG_NODE
    WEB --> RAG_NODE
    
    subgraph RAG_PROCESS [RAG持久化处理]
        RAG_CACHE{检查缓存}
        RAG_PARSE[文档解析转换]
        RAG_META[提取元数据]
        RAG_CHUNK[内容分块]
        RAG_STORE[向量存储<br/>FAISS+SQLite]
        
        RAG_CACHE -->|缓存存在| RAG_SKIP[跳过处理]
        RAG_CACHE -->|缓存不存在| RAG_PARSE
        RAG_PARSE --> RAG_META
        RAG_META --> RAG_CHUNK
        RAG_CHUNK --> RAG_STORE
    end
    
    RAG_NODE --> RAG_PROCESS
    RAG_PROCESS --> RAG_CHECK{RAG处理结果}
    RAG_CHECK -->|失败| ERROR_END[错误终止]
    RAG_CHECK -->|成功| READING_NODE
    
    %% 迭代阅读循环节点 - 第二个核心节点
    READING_NODE[迭代阅读循环节点<br/>IterativeReadingLoop]
    
    subgraph READING_PROCESS [迭代阅读处理]
        INIT_CHECK{首次运行?}
        STRUCT_DOC[文档结构化<br/>生成阅读片段]
        FIND_SNIPPET[查找下一个<br/>未读片段]
        SNIPPET_CHECK{还有未读片段?}
        
        %% 三个Agent并行处理
        subgraph AGENTS [智能体协作分析]
            READING_AGENT[ReadingAgent<br/>阅读分析]
            KEYINFO_AGENT[KeyInfoAgent<br/>关键信息提取]
            REVIEWER_AGENT[ReviewerAgent<br/>RAG问答检索]
            SUMMARY_AGENT[SummaryAgent<br/>记忆整合]
        end
        
        UPDATE_STATE[更新状态<br/>标记片段已读]
        
        INIT_CHECK -->|是| STRUCT_DOC
        INIT_CHECK -->|否| FIND_SNIPPET
        STRUCT_DOC --> FIND_SNIPPET
        FIND_SNIPPET --> SNIPPET_CHECK
        SNIPPET_CHECK -->|有| AGENTS
        SNIPPET_CHECK -->|无| READING_COMPLETE
        AGENTS --> UPDATE_STATE
        UPDATE_STATE --> FIND_SNIPPET
    end
    
    READING_NODE --> READING_PROCESS
    READING_PROCESS --> READING_CHECK{阅读完成?}
    READING_CHECK -->|否| READING_NODE
    READING_CHECK -->|是| REPORT_NODE
    
    %% 报告生成节点 - 第三个核心节点
    REPORT_NODE[报告生成节点<br/>ReportGenerationNode]
    
    subgraph REPORT_PROCESS [写作研讨会]
        NARRATIVE[脉络分析师<br/>梳理书籍脉络]
        THEMES[主题思想家<br/>提炼核心思想]
        
        subgraph DEBATE [思想辩论环节]
            CRITIC[批判者<br/>质疑与反驳]
            REFINE[思想家<br/>优化完善]
            DEBATE_CHECK{达成共识?}
        end
        
        EDITOR[总编辑<br/>生成报告大纲]
        
        subgraph WRITING [迭代写作]
            WRITER[Writer<br/>章节撰写]
            MATERIAL[素材准备<br/>RAG+摘要+关键信息]
        end
        
        NARRATIVE --> THEMES
        THEMES --> DEBATE
        DEBATE --> CRITIC
        CRITIC --> REFINE
        REFINE --> DEBATE_CHECK
        DEBATE_CHECK -->|否| CRITIC
        DEBATE_CHECK -->|是| EDITOR
        EDITOR --> WRITING
        WRITING --> FINAL_REPORT
    end
    
    REPORT_NODE --> REPORT_PROCESS
    REPORT_PROCESS --> FINAL_REPORT[最终结构化报告]
    
    %% 输出
    FINAL_REPORT --> OUTPUT[输出文件<br/>JSON/Markdown]
    READING_COMPLETE[阅读完成标志] --> REPORT_NODE
    
    %% 样式定义
    classDef nodeStyle fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef processStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef agentStyle fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef errorStyle fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    class RAG_NODE,READING_NODE,REPORT_NODE nodeStyle
    class RAG_PROCESS,READING_PROCESS,REPORT_PROCESS processStyle
    class READING_AGENT,KEYINFO_AGENT,REVIEWER_AGENT,SUMMARY_AGENT,NARRATIVE,THEMES,CRITIC,EDITOR,WRITER agentStyle
    class ERROR_END errorStyle
```

**系统核心架构说明：**

### 🔄 三大核心节点

**1. RAG持久化节点 (RAGPersistenceNode)**
- **功能**：文档预处理和向量化存储
- **缓存机制**：基于文档路径哈希检查，避免重复处理
- **输出**：Markdown内容、元数据、分块数据、FAISS向量库

**2. 迭代阅读循环节点 (IterativeReadingLoop)**  
- **功能**：模拟人类专家的主动式阅读过程
- **智能体协作**：ReadingAgent、KeyInfoAgent、ReviewerAgent、SummaryAgent 并行工作
- **状态管理**：维护阅读进度、跨片段上下文、累积记忆

**3. 报告生成节点 (ReportGenerationNode)**
- **功能**：多轮辩论式写作研讨会
- **写作流程**：脉络分析 → 主题提炼 → 批判辩论 → 大纲制定 → 迭代写作
- **并行优化**：素材准备（RAG检索、摘要选择、关键信息筛选）同步进行

### 🎯 关键特性

- **状态持久化**：所有处理状态通过 LangGraph Checkpointer 保存，支持断点续传
- **并行处理**：多个 Agent 同时工作，提高处理效率
- **智能缓存**：避免重复处理相同文档
- **条件流转**：基于处理结果动态决定下一步流程

---

## 🚀 快速开始

请遵循以下步骤来安装和运行 DeepReader。

### 1. 环境与版本管理 (强烈推荐)

为了保证项目在不同环境下的一致性，我们强烈建议使用 `pyenv` 来管理 Python 版本，并结合 `poetry` 管理项目依赖。

**a. 安装 pyenv** (如果尚未安装)

**macOS (使用 Homebrew):**
```bash
brew install pyenv
```

**Windows (使用 pyenv-win):**
```powershell
# 使用 Git 安装 pyenv-win
git clone https://github.com/pyenv-win/pyenv-win.git %USERPROFILE%\.pyenv

# 或者使用 pip 安装
pip install pyenv-win --target %USERPROFILE%\.pyenv
```

**Windows 环境变量配置:**
在 Windows 系统中，需要手动添加环境变量：
1. 按 `Win + R`，输入 `sysdm.cpl`，打开系统属性
2. 点击"环境变量"按钮
3. 在"用户变量"中添加以下变量：
   - `PYENV` = `%USERPROFILE%\.pyenv\pyenv-win`
   - `PYENV_ROOT` = `%USERPROFILE%\.pyenv\pyenv-win`
   - `PYENV_HOME` = `%USERPROFILE%\.pyenv\pyenv-win`
4. 在 `PATH` 变量中添加：
   - `%USERPROFILE%\.pyenv\pyenv-win\bin`
   - `%USERPROFILE%\.pyenv\pyenv-win\shims`

**Linux/Ubuntu:**
```bash
curl https://pyenv.run | bash
```

安装后，请根据 `pyenv` 的提示完成 shell 的初始化配置。

**b. 安装指定的 Python 版本**
本项目在 `pyproject.toml` 中指定的 Python 版本为 `3.12+`。

**macOS/Linux:**
```bash
# 安装 python 3.12.3 或更高版本
pyenv install 3.12.3

# 进入项目目录
# git clone <your-repo-url>
# cd deepreader

# 为当前目录设置 python 版本
pyenv local 3.12.3
```

**Windows:**
```powershell
# 安装 python 3.12.3 或更高版本
pyenv install 3.12.3

# 进入项目目录 (使用 PowerShell 或 CMD)
# git clone <your-repo-url>
# cd deepreader

# 为当前目录设置 python 版本
pyenv local 3.12.3
```

设置成功后，在此目录中执行 `python --version` 应该会显示 `3.12.3` 或更高版本。

### 2. 安装依赖

您可以选择使用 `poetry` 或 `pip` 来安装项目依赖。

#### 方式一：使用 Poetry (推荐)

**a. 克隆项目并进入目录**
```bash
git clone https://github.com/kirkluokun/deepreader.git
cd deepreader
```

**b. 使用 Poetry 安装依赖**
```bash
# 这将创建一个虚拟环境并安装所有在 pyproject.toml 中定义的依赖
poetry install
```

**c. 激活 Poetry 的虚拟环境**
```bash
poetry shell
```
之后的所有命令都将在这个虚拟环境中执行。

#### 方式二：使用 pip 和 requirements.txt

如果您不使用 Poetry，也可以使用传统的 `requirements.txt` 文件。

**a. 克隆项目并进入目录**
```bash
git clone https://github.com/kirkluokun/deepreader.git
cd deepreader
```

**b. 创建并激活虚拟环境**

**macOS/Linux:**
```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate
```

**Windows:**
```powershell
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (PowerShell)
.venv\Scripts\Activate.ps1

# 或者在 CMD 中激活
# .venv\Scripts\activate.bat
```

**c. 安装依赖**
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

DeepReader 需要访问 LLM 服务。请根据您的操作系统设置 API 密钥。

**macOS/Linux:**
```bash
# 以 OpenAI 为例
export OPENAI_API_KEY="your-openai-api-key"

# 如果您使用其他模型，也请设置相应的环境变量
export GOOGLE_API_KEY="your-google-api-key"
```

**Windows (PowerShell):**
```powershell
# 以 OpenAI 为例
$env:OPENAI_API_KEY="your-openai-api-key"

# 如果您使用其他模型，也请设置相应的环境变量
$env:GOOGLE_API_KEY="your-google-api-key"
```

**Windows (CMD):**
```cmd
# 以 OpenAI 为例
set OPENAI_API_KEY=your-openai-api-key

# 如果您使用其他模型，也请设置相应的环境变量
set GOOGLE_API_KEY=your-google-api-key
```

**推荐方式：使用 .env 文件**
在项目根目录创建 `.env` 文件，添加以下内容：
```
OPENAI_API_KEY=your-openai-api-key
GOOGLE_API_KEY=your-google-api-key
```
这种方式在所有操作系统上都通用，且更加安全。

### 4. 安装 marker（PDF 处理依赖）

DeepReader 使用 marker 进行高质量的 PDF 转换。请安装：

```bash
pip install marker-pdf
```

### 5. 运行系统

确保您已进入 `deepreader` 目录并已激活虚拟环境。

```bash
python main.py
```

## 📄 支持的文件格式

DeepReader 支持多种文档格式，系统会自动检测并处理：

### 📋 Markdown 文件 (.md)
- **处理方式**：直接读取，无需转换
- **适用场景**：已经是 Markdown 格式的文档
- **示例**：`/path/to/document.md`

### 📕 PDF 文件 (.pdf)
- **处理方式**：使用本地 marker 进行高质量转换
- **转换特性**：
  - 保留文档结构和格式
  - 智能识别表格和公式
  - 禁用图片提取以专注文本内容
- **输出位置**：在同目录下创建 `文件名/文件名.md`
- **示例**：`/path/to/annual_report.pdf` → `/path/to/annual_report/annual_report.md`

### 📚 EPUB 电子书 (.epub)
- **处理方式**：使用 ebooklib 提取文本内容
- **转换特性**：
  - 提取所有章节内容
  - 保留段落结构
  - 自动清理 HTML 标签
- **输出位置**：在同目录下创建 `文件名/文件名.md`
- **示例**：`/path/to/book.epub` → `/path/to/book/book.md`

## 🔄 智能文档处理流程

### 程序启动后的交互流程：

1. **文件路径输入**：输入支持的文件格式路径
   ```
   请输入待处理文件的绝对路径: /Users/username/Documents/report.pdf
   ```

2. **自动格式检测**：系统识别文件类型并选择相应处理器

3. **转换处理**（如需要）：
   - PDF：调用 marker 进行转换
   - EPUB：调用 ebooklib 进行提取
   - Markdown：直接读取

4. **文档清理提示**：
   ```
   ⚠️  请检查生成的 Markdown 文件并进行必要的清理：
      - 删除不相关的内容（如附录、声明等）
      - 检查格式是否正确
      - 确保章节结构清晰
   
   请完成文件清理后按回车键继续...
   ```

5. **继续分析**：确认清理完成后，进入 DeepReader 智能分析流程

## 💡 文档质量优化建议

### 🎯 为什么需要人工清理？

**提升 LLM 处理效率**：
- 🚀 **减少噪音**：移除无关内容可以让 AI 专注于核心信息
- 📊 **提高准确性**：清晰的结构有助于 AI 更好地理解文档层次
- ⚡ **节省 Token**：减少不必要的内容可以降低 API 成本
- 🎯 **增强相关性**：保留与研究问题相关的内容

### 📝 推荐的清理步骤：

**1. 删除冗余部分**
- 版权声明和法律条款
- 重复的目录和索引
- 大量的附录和参考文献
- 广告和推广内容

**2. 优化格式结构**
- 确保标题层次清晰（使用 #、##、### 等）
- 保留重要的表格和数据
- 修正转换错误的格式

**3. 保留核心内容**
- 主要章节和论述
- 关键数据和图表说明
- 重要的结论和观点
- 与研究问题相关的案例

**4. 验证文档质量**
- 检查是否有乱码或格式错误
- 确认章节完整性
- 验证重要信息是否保留

### 📋 用户输入信息：

完成文档处理后，系统会提示输入：

1. **核心探索问题**：您希望通过阅读解决的核心问题
   - 示例：`"这家公司去年的核心增长动力是什么？"`
   - 示例：`"这本书的主要观点和实践建议是什么？"`

2. **期望的研究角色**：指定 AI Agent 的分析视角
   - 示例：`"资深财务分析师"`
   - 示例：`"技术架构师"`
   - 示例：`"产品经理"`

## 🎬 完整使用示例

以下是一个典型的使用流程示例：

```bash
# 1. 启动程序
python main.py

# 2. 输入文件路径
请输入待处理文件的绝对路径: /Users/username/Documents/annual_report.pdf

# 3. 系统自动检测并转换
检测到 PDF 文件，开始转换: /Users/username/Documents/annual_report.pdf
执行命令: marker_single /Users/username/Documents/annual_report.pdf --output_format markdown --output_dir /Users/username/Documents --disable_image_extraction

✅ PDF 转换完成，已保存到: /Users/username/Documents/annual_report/annual_report.md

# 4. 文档清理提示
⚠️  请检查生成的 Markdown 文件并进行必要的清理：
   - 删除不相关的内容（如附录、声明等）
   - 检查格式是否正确
   - 确保章节结构清晰

请完成文件清理后按回车键继续...

# 5. 输入分析参数
请输入您的核心探索问题: 这家公司2023年的主要增长驱动因素是什么？
请输入您期望的研究角色: 资深财务分析师

# 6. 开始智能分析
--- 任务信息 ---
文档: annual_report.pdf
任务ID: a1b2c3d4e5f6...

--- 进入增强型 RAG 持久化节点 ---
--- 迭代式阅读节点开始 ---
--- 报告生成节点启动：写作研讨会开始 ---

# 7. 输出结果
✅ 完整状态已保存: output/20250702_210000_annual_report/final_state.json
✅ 已生成报告: chapter_summary.md
✅ 已生成报告: draft_report.md
✅ 已生成报告: thematic_analysis.md
✅ 已生成报告: debate_questions.md
```

---

## ⚠️ 潜在版本冲突与解决方案

由于项目依赖了多个复杂的AI和机器学习库，可能会遇到一些包版本冲突。以下是已知的潜在冲突及解决方案：

### 已知冲突

1. **langchain-google-genai vs google-ai-generativelanguage**
   ```
   langchain-google-genai 2.1.6 requires google-ai-generativelanguage>=0.6.18
   但安装的是 google-ai-generativelanguage 0.6.15
   ```

2. **marker-pdf vs Pillow**
   ```
   marker-pdf 1.8.0 requires Pillow<11.0.0,>=10.1.0
   但安装的是 pillow 11.3.0
   ```

3. **surya-ocr vs Pillow**
   ```
   surya-ocr 0.14.6 requires pillow<11.0.0,>=10.2.0
   但安装的是 pillow 11.3.0
   ```

### 解决方案

这些版本冲突是**非致命性**的，不会影响核心功能的运行。如果遇到问题，可以尝试以下解决方案：

#### 方案1：忽略冲突（推荐）
大多数情况下，这些小的版本差异不会影响程序运行。如果程序能正常工作，可以忽略这些警告。

#### 方案2：重新创建虚拟环境
如果遇到运行时错误，可以删除虚拟环境重新安装：

**macOS/Linux:**
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
Remove-Item -Recurse -Force .venv
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows (CMD):**
```cmd
rmdir /s .venv
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

#### 方案3：手动解决特定冲突
如果某个特定功能不工作，可以针对性地调整版本：
```bash
# 示例：如果 Google AI 功能有问题
pip install "google-ai-generativelanguage>=0.6.18"

# 示例：如果图像处理有问题
pip install "pillow>=10.1.0,<11.0.0"
```

### 检查冲突状态
可以使用以下命令检查当前的依赖冲突：
```bash
pip check
```

---

## 📁 项目结构

```
deepreader/
├── main.py                 # 主程序入口，集成多格式文档处理
├── README.md               # 本文档
├── pyproject.toml          # Poetry 依赖与项目配置
├── requirements.txt        # pip 依赖文件
├── backend/
│   ├── read_graph.py       # LangGraph 工作流定义
│   ├── read_state.py       # 核心状态对象 (State)
│   ├── config.py           # 系统配置 (模型、解析策略等)
│   ├── prompts.py          # 所有 Prompt 模板
│   ├── components/         # 核心组件 (LLM调用, 向量数据库等)
│   ├── graph/              # LangGraph 的节点与业务逻辑
│   ├── scraper/            # 文档解析器模块
│   │   ├── pdf_converter.py      # PDF转换器 (本地marker)
│   │   ├── epub_converter.py     # EPUB转换器 (ebooklib)
│   │   ├── web_scraper.py        # 网页抓取器
│   │   ├── clean_rule.py         # Markdown清洗规则
│   │   ├── scraper_tools.py      # 通用工具函数
│   │   └── multipdf.py           # 批量PDF处理
│   ├── cache/              # 缓存目录 (检查点, 会话信息等)
│   └── memory/             # 向量存储目录 (FAISS, SQLite)
└── output/                 # 分析结果输出目录
    └── [timestamp]_[document]/  # 按时间戳和文档名组织的结果
        ├── final_state.json     # 完整分析状态
        ├── chapter_summary.md   # 章节摘要
        ├── draft_report.md      # 最终分析报告
        ├── thematic_analysis.md # 主题思想分析
        └── debate_questions.md  # 批判性问答记录
```

### 🔧 核心模块说明

**文档解析器 (backend/scraper/)**
- `pdf_converter.py`: 使用本地 marker 进行高质量 PDF 转换
- `epub_converter.py`: 使用 ebooklib 处理 EPUB 电子书
- `web_scraper.py`: 网页内容抓取和清理
- `clean_rule.py`: 统一的 Markdown 文本清洗规则
- `multipdf.py`: 批量处理多个 PDF 文件的工具

## 📊 输出结果

分析完成后，所有结果将保存在 `output/` 目录下，以时间戳和文档名命名的子目录中。
- `final_state.json`: 包含所有中间过程和最终结果的完整 JSON 数据。
- `chapter_summary.md`: 各章节的详细摘要。
- `draft_report.md`: 格式化后的最终分析报告。
- `thematic_analysis.md`: 主题思想分析。
- `debate_questions.md`: AI 代理在阅读过程中提出的深度问题及 RAG 检索到的答案。

## 🤝 贡献指南

我们欢迎各种形式的贡献，包括 Bug 报告、功能建议和代码贡献。请通过提交 Pull Request 或创建 Issue 的方式参与项目。

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。
