# 🔍 DeepReader 前端界面

DeepReader 的现代化Web界面，提供直观的文档分析体验。

## ✨ 功能特性

- 📄 **多格式文档支持**: 支持 PDF、EPUB、Markdown 文件上传
- 🎯 **智能分析**: 基于用户核心问题进行深度分析
- 📊 **实时进度**: WebSocket 实时显示分析进度和节点状态
- 📋 **多维度结果**: 提供最终报告、章节摘要、主题分析、批判性问答等多种视角
- 💻 **响应式设计**: 适配桌面和移动设备
- 🎨 **Markdown 渲染**: 支持代码高亮和丰富格式

## 🚀 快速开始

### 1. 安装依赖

```bash
cd FinAIcrew/dynamic-gptr/AgentCrew/DeepReader/frontend
pip install -r requirements.txt
```

### 2. 启动服务器

#### 方式一：使用启动脚本（推荐）
```bash
python start_server.py
```

#### 方式二：直接运行
```bash
python api_server.py
```

#### 方式三：使用 uvicorn
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 访问界面

- 🌐 **前端界面**: http://localhost:8000
- 📋 **API 文档**: http://localhost:8000/docs
- 🔧 **交互式 API**: http://localhost:8000/redoc

## 📖 使用指南

### 基本流程

1. **上传文档**
   - 点击上传区域或拖拽文件
   - 支持 PDF、EPUB、Markdown 格式
   - 文件大小建议不超过 100MB

2. **设置分析参数**
   - **核心探索问题**: 输入您希望通过文档回答的关键问题
   - **研究身份**: 选择分析视角（如学术研究者、行业分析师等）

3. **开始分析**
   - 点击"🚀 开始深度分析"按钮
   - 系统将自动处理文档并显示实时进度

4. **查看结果**
   - 分析完成后，可在多个标签页中查看不同维度的结果
   - 支持 Markdown 格式渲染，包括代码高亮

### 进度监控

分析过程分为三个主要阶段：

- 🗃️ **RAG 数据准备**: 文档解析、分块和向量化
- 📚 **迭代式阅读**: 深度理解和知识提取
- 📝 **报告生成**: 多维度分析和报告撰写

每个阶段都有对应的视觉指示器和详细日志。

### 结果说明

- **📖 最终报告**: 基于核心问题的综合分析报告
- **📝 章节摘要**: 文档各章节的要点总结
- **🎯 主题分析**: 提取的核心思想和主题
- **💬 批判性问答**: AI生成的深度问题与回答

## 🛠️ 技术架构

### 后端 (FastAPI)
- **异步处理**: 基于 asyncio 的高性能异步架构
- **WebSocket**: 实时双向通信
- **文件管理**: 安全的文件上传和存储
- **错误处理**: 完善的异常处理和日志记录

### 前端 (HTML/JavaScript)
- **现代UI**: 基于 Tailwind CSS 的响应式设计
- **实时通信**: WebSocket 客户端
- **Markdown渲染**: marked.js + Prism.js 代码高亮
- **文件上传**: 支持拖拽和点击上传

### 核心组件
- **LangGraph**: 图形化工作流引擎
- **RAG系统**: 检索增强生成
- **多Agent协作**: 专业化的分析代理

## 📁 目录结构

```
frontend/
├── api_server.py          # FastAPI 服务器
├── start_server.py        # 启动脚本
├── requirements.txt       # Python 依赖
├── README.md             # 说明文档
├── static/               # 前端静态文件
│   ├── index.html        # 主页面
│   └── app.js           # JavaScript 逻辑
└── uploads/             # 上传文件存储（自动创建）
```

## ⚙️ 配置选项

### 环境变量

可以在 `.env` 文件中配置以下环境变量：

```env
# API 配置
API_HOST=0.0.0.0
API_PORT=8000

# 文件上传配置
MAX_FILE_SIZE=104857600  # 100MB
ALLOWED_EXTENSIONS=.pdf,.epub,.md

# 日志配置
LOG_LEVEL=INFO
```

### 系统要求

- **Python**: 3.8+
- **内存**: 建议 4GB+
- **磁盘**: 预留足够空间存储文档和缓存
- **网络**: 需要访问 LLM API（如 OpenAI）

## 🔧 开发指南

### 本地开发

1. 克隆代码并安装依赖
2. 设置环境变量（LLM API 密钥等）
3. 运行 `python start_server.py --reload`
4. 访问 http://localhost:8000 进行开发

### API 扩展

FastAPI 提供了自动化的 API 文档，可在 `/docs` 查看所有接口。

主要 API 端点：
- `POST /api/upload` - 文件上传
- `POST /api/start_research` - 开始分析任务
- `WebSocket /ws/{task_id}` - 实时通信
- `GET /api/results/{task_id}` - 获取结果

### 前端定制

前端使用纯 HTML/CSS/JavaScript，易于定制：
- 修改 `static/index.html` 调整界面布局
- 修改 `static/app.js` 添加新功能
- 使用 Tailwind CSS 类进行样式调整

## 🐛 故障排除

### 常见问题

1. **端口占用**: 
   ```bash
   lsof -i :8000  # 查看端口占用
   kill -9 <PID>  # 终止进程
   ```

2. **依赖缺失**:
   ```bash
   pip install -r requirements.txt
   ```

3. **文件上传失败**:
   - 检查文件格式是否支持
   - 确认文件大小不超过限制
   - 检查磁盘空间是否充足

4. **WebSocket 连接失败**:
   - 检查防火墙设置
   - 确认服务器正常运行
   - 查看浏览器控制台错误信息

### 日志查看

服务器日志包含详细的运行信息，可用于诊断问题：
- 控制台输出：实时日志
- 文件日志：可配置日志文件路径

## 📞 技术支持

如果遇到问题或需要帮助：

1. 查看本 README 文档
2. 检查 API 文档 (`/docs`)
3. 查看服务器日志
4. 联系开发团队

---

**DeepReader** - 让文档分析更加智能和高效！ 🚀