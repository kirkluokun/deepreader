# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: multipdf.py
@time: 2024-07-21
@desc: 此脚本处理指定目录中的所有 PDF 文件，
       使用 marker API 将它们转换为 Markdown，
       并将输出保存到指定目录。
"""

import logging
from pathlib import Path

# 使用绝对导入，假设脚本从项目根目录（FinAIcrew）运行，
# 并且 poetry 环境已正确设置路径。
try:
    from gpt_researcher.deepreader.backend.scraper.pdf_converter import convert_pdf_to_markdown
except ImportError:
    import sys
    # 如果直接运行此脚本，可能需要将项目根目录添加到 python 路径中
    # 从当前文件位置 (scraper/backend/deepreader/gpt_researcher/dynamic-gptr) 向上追溯
    project_root = Path(__file__).resolve().parents[5]
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    from gpt_researcher.deepreader.backend.scraper.pdf_converter import convert_pdf_to_markdown


# 定义相对于项目根目录的输入和输出目录
# workspace root is /Users/kirk/PROJECT/FinAIcrew
INPUT_DIR = Path("dynamic-gptr/gpt_researcher/deepreader/input/稳定币")
OUTPUT_DIR = Path("dynamic-gptr/gpt_researcher/deepreader/input/稳定币/output")


def process_pdfs_in_directory(input_dir: Path, output_dir: Path):
    """
    处理输入目录中的所有 PDF 文件，将它们转换为 Markdown，
    并保存到输出目录。

    Args:
        input_dir: 包含 PDF 文件的目录。
        output_dir: 将保存 Markdown 文件的目录。
    """
    logging.info(f"开始处理目录中的 PDF 文件: {input_dir.resolve()}")

    if not input_dir.is_dir():
        logging.error(f"输入目录不存在: {input_dir.resolve()}")
        return

    # 如果输出目录不存在，则创建它
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"输出目录已创建或已存在: {output_dir.resolve()}")

    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        logging.warning(f"在目录 {input_dir.resolve()} 中未找到 PDF 文件。")
        return

    logging.info(f"找到 {len(pdf_files)} 个 PDF 文件进行处理。")

    for pdf_path in pdf_files:
        logging.info(f"正在处理文件: {pdf_path.name}")
        try:
            # 调用转换函数
            markdown_content = convert_pdf_to_markdown(str(pdf_path))

            # 创建输出文件路径
            output_filename = pdf_path.stem + ".md"
            output_filepath = output_dir / output_filename

            # 将转换后的 markdown 保存到输出文件
            output_filepath.write_text(markdown_content, encoding='utf-8')
            logging.info(f"成功将 {pdf_path.name} 转换为 Markdown 并保存至 {output_filepath.resolve()}")

        except FileNotFoundError:
            logging.error(f"文件未找到，跳过: {pdf_path.name}")
        except Exception as e:
            logging.error(f"处理文件 {pdf_path.name} 时发生错误: {e}", exc_info=True)

    logging.info("所有 PDF 文件处理完成。")


if __name__ == "__main__":
    # 配置日志记录
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('multipdf_conversion.log', mode='w', encoding='utf-8')
        ]
    )

    logging.info("开始执行多 PDF 处理脚本...")
    process_pdfs_in_directory(INPUT_DIR, OUTPUT_DIR)
    logging.info("脚本执行完毕。")
