# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: main.py
@time: 2025-06-30 11:00
@desc: DeepReader Agent 的主程序入口
"""


import asyncio
import os
import sys
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from pprint import pprint
from typing import Dict, Any, List, Optional

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# --- 1. 初始化环境 ---
def setup_environment():
    """设置工作目录和 sys.path，确保脚本从 dynamic-gptr 根目录运行"""
    # 获取当前脚本所在的目录
    script_dir = Path(__file__).parent.resolve()
    # 寻找 dynamic-gptr 根目录
    workspace_root = script_dir
    while workspace_root.name != 'dynamic-gptr' and workspace_root.parent != workspace_root:
        workspace_root = workspace_root.parent
    
    if workspace_root.name == 'dynamic-gptr':
        os.chdir(workspace_root)
        print(f"工作目录已切换到: {os.getcwd()}")
    else:
        print("错误: 未能在父目录中找到 'dynamic-gptr'。请确保项目结构正确。")
        sys.exit(1)

    # 将工作目录添加到 sys.path
    if str(workspace_root) not in sys.path:
        sys.path.insert(0, str(workspace_root))

# setup_environment()

# --- 2. 导入必要的模块 ---
from backend.read_graph import create_deepreader_graph
from backend.read_state import DeepReaderState
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# --- 3. 定义常量 ---
# 基于 main.py 文件所在目录定义路径，确保输出目录正确
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_OUTPUT_DIR = SCRIPT_DIR / "output"
CACHE_DIR = SCRIPT_DIR / "backend/cache" 
SESSION_CACHE_FILE = CACHE_DIR / "session_cache.json"
CHECKPOINTER_DB_PATH = CACHE_DIR / "checkpoints.sqlite"

# --- 4. 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# 过滤掉一些过于冗长的第三方库日志
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- 5. 会话管理 ---
def load_session_cache() -> Dict[str, str]:
    """加载上一次的用户输入"""
    if SESSION_CACHE_FILE.exists():
        try:
            with open(SESSION_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_session_cache(data: Dict[str, str]):
    """保存当前用户输入"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(SESSION_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_inputs(defaults: Dict[str, str]) -> Dict[str, str]:
    """提示用户输入并获取必要的参数"""
    print("\\n--- 请输入研究任务所需信息 ---")
    
    document_path = input(f"请输入待处理文件的绝对路径 [{defaults.get('document_path', '')}]: ") or defaults.get('document_path', '')
    while not Path(document_path).exists() or not Path(document_path).is_file():
        print("❌ 文件路径无效或文件不存在，请重新输入。")
        document_path = input("请输入待处理文件的绝对路径: ")

    user_core_question = input(f"请输入您的核心探索问题 [{defaults.get('user_core_question', '')}]: ") or defaults.get('user_core_question', '')
    research_role = input(f"请输入您期望的研究角色 [{defaults.get('research_role', '资深行业分析师')}]: ") or defaults.get('research_role', '资深行业分析师')

    return {
        "document_path": document_path,
        "user_core_question": user_core_question,
        "research_role": research_role
    }


def convert_document_to_markdown(file_path: str) -> str:
    """
    根据文件类型将文档转换为 Markdown 格式
    
    Args:
        file_path: 文档文件路径
        
    Returns:
        转换后的 Markdown 内容
    """
    from backend.scraper.pdf_converter import convert_pdf_to_markdown
    from backend.scraper.epub_converter import convert_epub_to_markdown
    
    file_path_obj = Path(file_path)
    file_ext = file_path_obj.suffix.lower()
    
    if file_ext == '.md':
        # 如果已经是 Markdown 文件，直接读取
        logging.info(f"检测到 Markdown 文件，直接读取: {file_path}")
        return file_path_obj.read_text(encoding='utf-8')
    
    elif file_ext == '.pdf':
        # 转换 PDF 文件
        logging.info(f"检测到 PDF 文件，开始转换: {file_path}")
        
        # marker 会创建一个以文件名命名的目录，然后在里面生成 markdown 文件
        expected_md_dir = file_path_obj.parent / file_path_obj.stem
        expected_md_path = expected_md_dir / f"{file_path_obj.stem}.md"
        
        # 检查是否已存在转换后的文件
        if expected_md_path.exists():
            choice = input(f"\\n发现已存在的 Markdown 文件: {expected_md_path}\\n是否使用现有文件? (Y/n): ").lower()
            if choice == 'y' or choice == '':
                return expected_md_path.read_text(encoding='utf-8')
        
        # 执行转换
        markdown_content = convert_pdf_to_markdown(file_path)
        
        # 查找实际生成的 markdown 文件
        actual_md_path = None
        if expected_md_path.exists():
            actual_md_path = expected_md_path
            logging.info(f"找到预期路径的 Markdown 文件: {actual_md_path}")
        else:
            # 如果预期路径不存在，搜索可能的位置
            search_locations = [
                file_path_obj.with_suffix('.md'),  # 同目录下的直接替换
                expected_md_path,  # 子目录中的预期位置
                file_path_obj.parent,  # 父目录中搜索
                expected_md_dir,  # 子目录中搜索
            ]
            
            logging.info(f"在预期路径未找到文件，开始搜索其他位置...")
            
            for search_location in search_locations:
                if search_location.is_file() and search_location.suffix == '.md':
                    # 直接是一个 .md 文件
                    if search_location.stem == file_path_obj.stem:
                        actual_md_path = search_location
                        logging.info(f"找到匹配的 Markdown 文件: {actual_md_path}")
                        break
                elif search_location.is_dir():
                    # 在目录中搜索 .md 文件
                    md_files = list(search_location.glob("*.md"))
                    if md_files:
                        # 优先选择与原文件名匹配的
                        for md_file in md_files:
                            if md_file.stem == file_path_obj.stem:
                                actual_md_path = md_file
                                logging.info(f"在目录 {search_location} 中找到匹配的 Markdown 文件: {actual_md_path}")
                                break
                        # 如果没有完全匹配的，使用第一个 .md 文件
                        if not actual_md_path and md_files:
                            actual_md_path = md_files[0]
                            logging.info(f"在目录 {search_location} 中找到 Markdown 文件（非完全匹配）: {actual_md_path}")
                        break
        
        if not actual_md_path or not actual_md_path.exists():
            raise FileNotFoundError(f"未找到转换后的 Markdown 文件。预期位置: {expected_md_path}")
        
        print(f"\\n✅ PDF 转换完成，已保存到: {actual_md_path}")
        
        # 提示用户检查和清理
        print("\\n⚠️  请检查生成的 Markdown 文件并进行必要的清理：")
        print("   - 删除不相关的内容（如附录、声明等）")
        print("   - 检查格式是否正确")
        print("   - 确保章节结构清晰")
        
        input("\\n请完成文件清理后按回车键继续...")
        
        # 重新读取可能被用户修改的文件
        return actual_md_path.read_text(encoding='utf-8')
        
    elif file_ext == '.epub':
        # 转换 EPUB 文件
        logging.info(f"检测到 EPUB 文件，开始转换: {file_path}")
        
        # EPUB 也输出到子文件夹，与 PDF 保持一致
        expected_md_dir = file_path_obj.parent / file_path_obj.stem
        expected_md_path = expected_md_dir / f"{file_path_obj.stem}.md"
        
        # 检查是否已存在转换后的文件
        if expected_md_path.exists():
            choice = input(f"\\n发现已存在的 Markdown 文件: {expected_md_path}\\n是否使用现有文件? (Y/n): ").lower()
            if choice == 'y' or choice == '':
                return expected_md_path.read_text(encoding='utf-8')
        
        # 执行转换
        markdown_content = convert_epub_to_markdown(file_path)
        
        # 查找实际生成的 markdown 文件  
        actual_md_path = None
        if expected_md_path.exists():
            actual_md_path = expected_md_path
            logging.info(f"找到预期路径的 Markdown 文件: {actual_md_path}")
        else:
            # 如果预期路径不存在，搜索可能的位置
            search_locations = [
                file_path_obj.with_suffix('.md'),  # 同目录下的直接替换
                expected_md_path,  # 子目录中的预期位置
                file_path_obj.parent,  # 父目录中搜索
                expected_md_dir,  # 子目录中搜索
            ]
            
            logging.info(f"在预期路径未找到文件，开始搜索其他位置...")
            
            for search_location in search_locations:
                if search_location.is_file() and search_location.suffix == '.md':
                    # 直接是一个 .md 文件
                    if search_location.stem == file_path_obj.stem:
                        actual_md_path = search_location
                        logging.info(f"找到匹配的 Markdown 文件: {actual_md_path}")
                        break
                elif search_location.is_dir():
                    # 在目录中搜索 .md 文件
                    md_files = list(search_location.glob("*.md"))
                    if md_files:
                        # 优先选择与原文件名匹配的
                        for md_file in md_files:
                            if md_file.stem == file_path_obj.stem:
                                actual_md_path = md_file
                                logging.info(f"在目录 {search_location} 中找到匹配的 Markdown 文件: {actual_md_path}")
                                break
                        # 如果没有完全匹配的，使用第一个 .md 文件
                        if not actual_md_path and md_files:
                            actual_md_path = md_files[0]
                            logging.info(f"在目录 {search_location} 中找到 Markdown 文件（非完全匹配）: {actual_md_path}")
                        break
        
        if not actual_md_path or not actual_md_path.exists():
            raise FileNotFoundError(f"未找到转换后的 Markdown 文件。预期位置: {expected_md_path}")
        
        print(f"\\n✅ EPUB 转换完成，已保存到: {actual_md_path}")
        
        # 提示用户检查和清理
        print("\\n⚠️  请检查生成的 Markdown 文件并进行必要的清理：")
        print("   - 删除不相关的内容（如目录、版权信息等）")
        print("   - 检查格式是否正确")
        print("   - 确保章节结构清晰")
        
        input("\\n请完成文件清理后按回车键继续...")
        
        # 重新读取可能被用户修改的文件
        return actual_md_path.read_text(encoding='utf-8')
        
    else:
        raise ValueError(f"不支持的文件类型: {file_ext}。支持的格式: .md, .pdf, .epub")

# --- 6. 结果格式化与保存 ---
def _format_summaries_to_md(summaries: Dict[str, str]) -> str:
    """格式化章节摘要为 Markdown"""
    if not summaries:
        return "没有可用的章节摘要。"
    content = ["# 章节摘要"]
    # 按章节标题（键）排序
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

def _format_debate_to_md(rounds: List[List[Dict[str, Any]]]) -> str:
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

def _format_draft_report_to_md(report_data: List[Dict[str, Any]]) -> str:
    """格式化最终报告为 Markdown"""
    if not report_data:
        return "未能生成最终报告。"
    
    md_parts = []

    def _parse_recursive(section_list: List[Dict[str, Any]], level: int):
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


def save_results(output_dir: Path, final_state: Dict[str, Any]):
    """将最终状态和格式化后的报告保存到文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n--- 正在保存结果至: {output_dir} ---")

    # 1. 保存完整的最终状态
    final_state_path = output_dir / "final_state.json"
    try:
        # TypedDict 转 dict
        serializable_state = dict(final_state)
        with open(final_state_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_state, f, ensure_ascii=False, indent=4)
        print(f"✅ 完整状态已保存: {final_state_path}")
    except Exception as e:
        print(f"❌ 保存完整状态失败: {e}")
        print("--- 最终状态内容 (pprint): ---")
        pprint(dict(final_state))

    # 2. 格式化并保存 Markdown 文件
    report_map = {
        "chapter_summary.md": (_format_summaries_to_md, final_state.get("chapter_summaries")),
        "draft_report.md": (_format_draft_report_to_md, final_state.get("draft_report")),
        "thematic_analysis.md": (_format_thematic_analysis_to_md, final_state.get("thematic_analysis")),
        "debate_questions.md": (_format_debate_to_md, final_state.get("raw_reviewer_outputs"))
    }

    for filename, (formatter, data) in report_map.items():
        output_path = output_dir / filename
        try:
            if data is not None:
                md_content = formatter(data)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                print(f"✅ 已生成报告: {output_path.name}")
            else:
                print(f"ℹ️ 无数据可用于生成: {output_path.name}")
        except Exception as e:
            print(f"❌ 生成报告 {filename} 失败: {e}")


# --- 7. 主程序 ---
async def main():
    """主测试函数"""
    
    # 获取用户输入并维护会话
    session_defaults = load_session_cache()
    user_inputs = get_user_inputs(session_defaults)
    save_session_cache(user_inputs)
    
    document_path = Path(user_inputs["document_path"])
    
    # 根据文件类型进行转换处理
    try:
        raw_markdown_content = convert_document_to_markdown(str(document_path))
        logging.info(f"✅ 文档处理完成，内容长度: {len(raw_markdown_content)}")
    except Exception as e:
        logging.error(f"❌ 文档转换失败 '{document_path}': {e}")
        return

    # 为每个文档创建一个唯一的线程ID
    thread_id = hashlib.md5(str(document_path.resolve()).encode()).hexdigest()
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50000  # 提高递归限制以处理长文档
    }

    print(f"\n--- 任务信息 ---")
    print(f"文档: {document_path.name}")
    print(f"任务ID: {thread_id}")
    
    final_state = None
    # 使用 async with 来正确管理异步 checkpointer 的生命周期
    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINTER_DB_PATH)) as memory:
        # 检查是否有未完成的任务
        continue_task = False
        try:
            existing_state = await memory.aget_state(config)
            if existing_state and existing_state.next:
                print("\n⚠️ 检测到该文档有未完成的任务。")
                choice = input("是否从上次断点处继续? (Y/n): ").lower()
                if choice == 'y' or choice == '':
                    continue_task = True
                    print("▶️ 正在恢复任务...")
                else:
                    print("🗑️ 已选择开始新任务，旧进度将被覆盖。")
            elif existing_state and not existing_state.next:
                 print("\nℹ️ 检测到该文档已有一个完成的任务。将开始一个新任务。")
        except Exception:
            # 可能是第一次运行，表不存在等
            print("\nℹ️ 未检测到历史任务，将开始一个新任务。")

        # 编译图，并直接关联 checkpointer
        app = create_deepreader_graph().compile(checkpointer=memory)
        
        if continue_task:
            # 在恢复前，强制更新检查点中的文档内容，确保任务的健壮性
            try:
                print("ℹ️ 为确保任务能正确恢复，正在更新检查点中的文档内容...")
                await memory.aupdate_state(
                    config,
                    {"raw_markdown_content": raw_markdown_content}
                )
                print("✅ 检查点更新成功。")
            except Exception as e:
                print(f"⚠️ 更新检查点失败: {e}。将尝试直接恢复，但可能出错。")
            
            # 从断点恢复
            async for event in app.astream(None, config=config):
                pprint(event)
                print("-" * 40)
        else:
            # 开始一个新任务
            initial_state = DeepReaderState(
                user_core_question=user_inputs["user_core_question"],
                research_role=user_inputs["research_role"],
                document_path=str(document_path),
                db_name=str(CACHE_DIR / f"{document_path.stem}_{thread_id}.db"),
                # 其他字段由图填充
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
            async for event in app.astream(initial_state, config=config):
                pprint(event)
                print("-" * 40)

        print("\n--- ✅ 图流程执行完毕 ---")

        # 获取最终状态
        try:
            final_snapshot = await app.aget_state(config)
            if final_snapshot:
                final_state = final_snapshot.values
                print("✅ 成功从检查点恢复最终状态。")
            else:
                print("❌ 未能获取最终状态。")
                # 在 with 块内部，所以不能直接 return
        except Exception as e:
            print(f"❌ 获取最终状态时出错: {e}")

    # 创建输出目录并保存结果 (在 with 块之外)
    if final_state:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = BASE_OUTPUT_DIR / f"{timestamp}_{document_path.stem}"
        
        save_results(output_dir, final_state)
    else:
        print("未获取到最终状态，无法保存结果。")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n🛑 用户中断了程序。")
        sys.exit(0)
