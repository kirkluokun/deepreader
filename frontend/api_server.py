# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: api_server.py
@time: 2025-01-01 10:00
@desc: DeepReader 前端API服务器
"""

import asyncio
import json
import logging
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import aiofiles

from fastapi import (
    FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, 
    Form, HTTPException
)
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 设置环境
from dotenv import load_dotenv
load_dotenv()

# 获取当前脚本所在的目录并设置工作目录
script_dir = Path(__file__).parent.resolve()
deepreader_root = script_dir.parent  # backend/../ -> deepreader/
# deepreader/../../../ -> dynamic-gptr/
workspace_root = deepreader_root.parent.parent.parent

# 切换到dynamic-gptr根目录
os.chdir(workspace_root)
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

# 导入DeepReader模块
from backend.read_graph import create_deepreader_graph
from backend.read_state import DeepReaderState
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# 配置
UPLOAD_DIR = deepreader_root / "frontend" / "uploads"
CACHE_DIR = deepreader_root / "backend" / "cache"
OUTPUT_DIR = deepreader_root / "output"
CHECKPOINTER_DB_PATH = CACHE_DIR / "checkpoints.sqlite"

# 确保目录存在
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="DeepReader API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储活动的WebSocket连接
active_connections: Dict[str, WebSocket] = {}

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections[task_id] = websocket
        logger.info(f"WebSocket连接已建立，任务ID: {task_id}")

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]
            logger.info(f"WebSocket连接已断开，任务ID: {task_id}")

    async def send_message(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            try:
                await self.active_connections[task_id].send_text(
                    json.dumps(message, ensure_ascii=False)
                )
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {e}")
                self.disconnect(task_id)

manager = WebSocketManager()

# 文档转换函数
def convert_document_to_markdown(file_path: str) -> str:
    """根据文件类型将文档转换为 Markdown 格式"""
    from backend.scraper.pdf_converter import convert_pdf_to_markdown
    from backend.scraper.epub_converter import convert_epub_to_markdown
    
    file_path_obj = Path(file_path)
    file_ext = file_path_obj.suffix.lower()
    
    if file_ext == '.md':
        logger.info(f"检测到 Markdown 文件，直接读取: {file_path}")
        return file_path_obj.read_text(encoding='utf-8')
    
    elif file_ext == '.pdf':
        logger.info(f"检测到 PDF 文件，开始转换: {file_path}")
        expected_md_dir = file_path_obj.parent / file_path_obj.stem
        expected_md_path = expected_md_dir / f"{file_path_obj.stem}.md"
        
        if expected_md_path.exists():
            return expected_md_path.read_text(encoding='utf-8')
        
        # 执行转换
        markdown_content = convert_pdf_to_markdown(file_path)
        
        # 查找生成的markdown文件
        if expected_md_path.exists():
            return expected_md_path.read_text(encoding='utf-8')
        else:
            # 搜索其他可能的位置
            search_locations = [
                file_path_obj.with_suffix('.md'),
                file_path_obj.parent,
                expected_md_dir,
            ]
            
            for search_location in search_locations:
                if search_location.is_file() and search_location.suffix == '.md':
                    if search_location.stem == file_path_obj.stem:
                        return search_location.read_text(encoding='utf-8')
                elif search_location.is_dir():
                    md_files = list(search_location.glob("*.md"))
                    for md_file in md_files:
                        if md_file.stem == file_path_obj.stem:
                            return md_file.read_text(encoding='utf-8')
                    if md_files:
                        return md_files[0].read_text(encoding='utf-8')
        
        raise FileNotFoundError(f"未找到转换后的 Markdown 文件")
        
    elif file_ext == '.epub':
        logger.info(f"检测到 EPUB 文件，开始转换: {file_path}")
        # 类似PDF的处理逻辑
        expected_md_dir = file_path_obj.parent / file_path_obj.stem
        expected_md_path = expected_md_dir / f"{file_path_obj.stem}.md"
        
        if expected_md_path.exists():
            return expected_md_path.read_text(encoding='utf-8')
        
        markdown_content = convert_epub_to_markdown(file_path)
        
        if expected_md_path.exists():
            return expected_md_path.read_text(encoding='utf-8')
        else:
            # 搜索其他可能的位置（同PDF处理）
            search_locations = [
                file_path_obj.with_suffix('.md'),
                file_path_obj.parent,
                expected_md_dir,
            ]
            
            for search_location in search_locations:
                if search_location.is_file() and search_location.suffix == '.md':
                    if search_location.stem == file_path_obj.stem:
                        return search_location.read_text(encoding='utf-8')
                elif search_location.is_dir():
                    md_files = list(search_location.glob("*.md"))
                    for md_file in md_files:
                        if md_file.stem == file_path_obj.stem:
                            return md_file.read_text(encoding='utf-8')
                    if md_files:
                        return md_files[0].read_text(encoding='utf-8')
        
        raise FileNotFoundError(f"未找到转换后的 Markdown 文件")
        
    else:
        raise ValueError(f"不支持的文件类型: {file_ext}。支持的格式: .md, .pdf, .epub")

# API路由
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文档文件"""
    try:
        # 检查文件类型
        allowed_extensions = {'.pdf', '.epub', '.md'}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            error_msg = f"不支持的文件类型。支持的格式: {', '.join(allowed_extensions)}"
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 保存文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"文件上传成功: {filename}")
        return {
            "status": "success", 
            "filename": filename, 
            "path": str(file_path)
        }
    
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start_research")
async def start_research(
    filename: str = Form(...),
    user_core_question: str = Form(...),
    research_role: str = Form(default="资深行业分析师")
):
    """开始研究任务"""
    try:
        # 验证文件存在
        file_path = UPLOAD_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="上传的文件不存在")
        
        # 生成任务ID
        task_data = f"{filename}_{user_core_question}_{datetime.now()}"
        task_id = hashlib.md5(task_data.encode()).hexdigest()
        
        # 启动异步任务
        asyncio.create_task(process_document_task(
            task_id=task_id,
            file_path=str(file_path),
            user_core_question=user_core_question,
            research_role=research_role
        ))
        
        return {"status": "success", "task_id": task_id}
    
    except Exception as e:
        logger.error(f"启动研究任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_document_task(
    task_id: str, file_path: str, user_core_question: str, research_role: str
):
    """异步处理文档的任务"""
    try:
        # 发送开始消息
        await manager.send_message(task_id, {
            "type": "progress",
            "stage": "start",
            "message": "任务开始...",
            "progress": 0
        })
        
        # 文档转换
        await manager.send_message(task_id, {
            "type": "progress",
            "stage": "document_conversion", 
            "message": "正在转换文档...",
            "progress": 10
        })
        
        raw_markdown_content = convert_document_to_markdown(file_path)
        
        # 生成线程ID
        thread_data = str(Path(file_path).resolve())
        thread_id = hashlib.md5(thread_data.encode()).hexdigest()
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50000
        }
        
        await manager.send_message(task_id, {
            "type": "progress",
            "stage": "rag_preparation",
            "message": "正在准备RAG数据库...",
            "progress": 20
        })
        
        # 创建初始状态
        initial_state = DeepReaderState(
            user_core_question=user_core_question,
            research_role=research_role,
            document_path=file_path,
            db_name=str(CACHE_DIR / f"{Path(file_path).stem}_{thread_id}.db"),
            raw_markdown_content=raw_markdown_content,
            document_metadata={},
            table_of_contents=None,
            reading_snippets=None,
            snippet_analysis_history=[],
            active_memory={},
            chunks=[],
            chapter_summaries={},
            marginalia={},
            entities=[],
            entity_relationships=[],
            synthesis_report="",
            rag_status=None,
            raw_reviewer_outputs=[],
            report_narrative_outline=None,
            thematic_analysis=None,
            critic_consensus_log=[],
            final_keys=None,
            final_report_outline=None,
            draft_report=None,
            reading_completed=None,
            error=None
        )
        
        # 执行图流程
        db_path = str(CHECKPOINTER_DB_PATH)
        async with AsyncSqliteSaver.from_conn_string(db_path) as memory:
            app_graph = create_deepreader_graph().compile(checkpointer=memory)
            
            current_progress = 20
            async for event in app_graph.astream(initial_state, config=config):
                # 根据节点更新进度
                for node_name, node_data in event.items():
                    if node_name == "rag_parser":
                        current_progress = 40
                        await manager.send_message(task_id, {
                            "type": "progress",
                            "stage": "rag_parsing",
                            "message": "RAG解析完成，开始阅读文档...",
                            "progress": current_progress
                        })
                    elif node_name == "reading_loop":
                        current_progress = min(80, current_progress + 5)
                        await manager.send_message(task_id, {
                            "type": "progress", 
                            "stage": "reading",
                            "message": "正在进行迭代式阅读...",
                            "progress": current_progress
                        })
                    elif node_name == "report_generation":
                        current_progress = 90
                        await manager.send_message(task_id, {
                            "type": "progress",
                            "stage": "report_generation",
                            "message": "正在生成最终报告...",
                            "progress": current_progress
                        })
                
                # 发送详细的节点信息
                await manager.send_message(task_id, {
                    "type": "node_update",
                    "event": event
                })
            
            # 获取最终状态
            final_snapshot = await app_graph.aget_state(config)
            final_state = final_snapshot.values if final_snapshot else None
            
            if final_state:
                # 保存结果
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = OUTPUT_DIR / f"{timestamp}_{Path(file_path).stem}"
                await save_results_async(output_dir, final_state)
                
                # 发送完成消息
                await manager.send_message(task_id, {
                    "type": "completion",
                    "message": "研究完成！",
                    "progress": 100,
                    "output_dir": str(output_dir),
                    "final_state": dict(final_state)
                })
            else:
                await manager.send_message(task_id, {
                    "type": "error",
                    "message": "未能获取最终状态"
                })
    
    except Exception as e:
        logger.error(f"处理任务失败: {e}")
        await manager.send_message(task_id, {
            "type": "error",
            "message": f"任务失败: {str(e)}"
        })

async def save_results_async(output_dir: Path, final_state: Dict[str, Any]):
    """异步保存结果"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存完整状态
    final_state_path = output_dir / "final_state.json"
    serializable_state = dict(final_state)
    async with aiofiles.open(final_state_path, 'w', encoding='utf-8') as f:
        content = json.dumps(serializable_state, ensure_ascii=False, indent=4)
        await f.write(content)
    
    # 保存各种报告
    reports = {
        "chapter_summary.md": _format_summaries_to_md(
            final_state.get("chapter_summaries")
        ),
        "draft_report.md": _format_draft_report_to_md(
            final_state.get("draft_report")
        ),
        "thematic_analysis.md": _format_thematic_analysis_to_md(
            final_state.get("thematic_analysis")
        ),
        "debate_questions.md": _format_debate_to_md(
            final_state.get("raw_reviewer_outputs")
        )
    }
    
    for filename, content in reports.items():
        if content:
            file_path = output_dir / filename
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)

# 格式化函数（从main.py复制）
def _format_summaries_to_md(summaries: Dict[str, str]) -> str:
    """格式化章节摘要为 Markdown"""
    if not summaries:
        return "没有可用的章节摘要。"
    content = ["# 章节摘要"]
    for title, summary in sorted(summaries.items()):
        content.append(f"## {title}\n\n{summary}")
    return "\n\n".join(content)

def _format_thematic_analysis_to_md(analysis: Dict[str, str]) -> str:
    """格式化主题分析为 Markdown"""
    if not analysis:
        return "没有可用的主题分析。"
    content = ["# 主题思想分析"]
    for key, value in analysis.items():
        formatted_key = key.replace('_', ' ').title()
        content.append(f"## {formatted_key}\n\n{value}")
    return "\n\n".join(content)

def _format_debate_to_md(rounds) -> str:
    """格式化批判性辩论为 Markdown"""
    if not rounds:
        return "没有可用的辩论记录。"
    content = ["# 批判性辩论问答"]
    for i, round_data in enumerate(rounds):
        content.append(f"## 辩论轮次 {i+1}")
        if isinstance(round_data, list):
            for item in round_data:
                question = item.get('question', 'N/A')
                answer = item.get('content_retrieve_answer', '无回答')
                content.append(f"### 问题: {question}\n\n**回答:** {answer}")
    return "\n\n".join(content)

def _format_draft_report_to_md(report_data) -> str:
    """格式化最终报告为 Markdown"""
    if not report_data:
        return "未能生成最终报告。"
    
    md_parts = []

    def _parse_recursive(section_list, level: int):
        for section in section_list:
            title = section.get("title", "无标题")
            md_parts.append(f"{'#' * level} {title}")

            content_brief = section.get("content_brief")
            if content_brief:
                md_parts.append(f"_{content_brief}_")
            
            written_content = section.get("written_content")
            if written_content and isinstance(written_content, list):
                md_parts.append("\n\n".join(written_content))
            
            children = section.get("children")
            if children:
                _parse_recursive(children, level + 1)

    _parse_recursive(report_data, 1)
    return "\n\n".join(md_parts)

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket端点用于实时通信"""
    await manager.connect(websocket, task_id)
    try:
        while True:
            await websocket.receive_text()
            # 这里可以处理来自客户端的消息
    except WebSocketDisconnect:
        manager.disconnect(task_id)

@app.get("/api/results/{task_id}")
async def get_results(task_id: str):
    """获取任务结果"""
    # 这里可以实现结果查询逻辑
    return {"message": "结果查询接口"}

# 静态文件服务
frontend_dir = Path(__file__).parent / "static"
if frontend_dir.exists():
    app.mount(
        "/", 
        StaticFiles(directory=str(frontend_dir), html=True), 
        name="static"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)