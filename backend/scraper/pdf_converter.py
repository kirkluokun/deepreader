# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: pdf_converter.py
@time: 2025-06-16 12:00
@desc: 使用本地 marker 实现 PDF 到纯净 Markdown 的转换
"""
import logging
import subprocess
from pathlib import Path
from typing import Optional

from .clean_rule import clean_markdown_text


def convert_pdf_to_markdown(pdf_path: str, output_path: Optional[str] = None) -> str:
    """
    使用本地安装的 marker 将 PDF 文件转换为纯净、结构化的 Markdown 文本。

    Args:
        pdf_path: 需要转换的 PDF 文件的路径。
        output_path: 可选的输出路径。如果未提供，将输出到与PDF同目录。

    Returns:
        一个字符串，其中包含从 PDF 转换而来并经过清洗的 Markdown 文本。

    Raises:
        FileNotFoundError: 如果指定的 `pdf_path` 不存在。
        subprocess.CalledProcessError: 如果 marker 命令执行失败。
        Exception: 在转换过程中发生任何其他未预期的错误。
    """
    logging.info(f"开始使用本地 marker 将 PDF 转换为 Markdown: {pdf_path}")
    pdf_file = Path(pdf_path)
    if not pdf_file.is_file():
        raise FileNotFoundError(f"错误：未在指定路径找到 PDF 文件: {pdf_path}")

    try:
        # 确定输出目录 - marker 会在PDF文件的父目录下创建同名子文件夹
        if output_path:
            output_dir = Path(output_path).parent
        else:
            output_dir = pdf_file.parent
        
        output_dir.mkdir(parents=True, exist_ok=True)

        # 构建 marker_single 命令
        cmd = [
            "marker_single",
            str(pdf_file.resolve()),
            "--output_format", "markdown",
            "--output_dir", str(output_dir),
            "--disable_image_extraction",  # 禁用图片提取
        ]

        logging.info(f"执行命令: {' '.join(cmd)}")
        
        # 执行 marker 命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        logging.info("marker 命令执行成功")
        if result.stdout:
            logging.info(f"marker 输出: {result.stdout}")
        if result.stderr:
            logging.warning(f"marker 警告: {result.stderr}")

        # marker 会创建一个以文件名命名的子目录，然后在里面生成 markdown 文件
        expected_md_dir = output_dir / pdf_file.stem
        expected_md_file = expected_md_dir / f"{pdf_file.stem}.md"
        
        # 查找生成的 markdown 文件
        actual_md_file = None
        if expected_md_file.exists():
            actual_md_file = expected_md_file
            logging.info(f"找到预期路径的 Markdown 文件: {actual_md_file}")
        else:
            # 搜索可能的位置
            search_locations = [
                output_dir / f"{pdf_file.stem}.md",  # 直接在输出目录
                expected_md_dir,  # 子目录中
                output_dir,  # 父目录中
            ]
            
            for search_dir in search_locations:
                if search_dir.is_file() and search_dir.suffix == '.md':
                    actual_md_file = search_dir
                    break
                elif search_dir.is_dir():
                    # 在目录中查找 .md 文件
                    md_files = list(search_dir.glob("*.md"))
                    if md_files:
                        # 优先选择与PDF文件名匹配的
                        for md_file in md_files:
                            if md_file.stem == pdf_file.stem:
                                actual_md_file = md_file
                                break
                        # 如果没有匹配的，使用第一个
                        if not actual_md_file:
                            actual_md_file = md_files[0]
                        break
            
            if actual_md_file:
                logging.info(f"在搜索路径中找到 Markdown 文件: {actual_md_file}")
            else:
                raise FileNotFoundError(f"未找到生成的 markdown 文件。预期位置: {expected_md_file}")
        
        # 读取生成的 markdown 文件
        markdown_text = actual_md_file.read_text(encoding='utf-8')
        logging.info(f"成功读取生成的 Markdown 文件: {actual_md_file}，内容长度: {len(markdown_text)}")

        # 清洗转换后的文本
        cleaned_text = clean_markdown_text(markdown_text)
        logging.info(
            f"Markdown 文本已清洗。原始长度: {len(markdown_text)}, "
            f"清洗后长度: {len(cleaned_text)}"
        )

        # 如果指定了输出路径，将清洗后的内容写入该路径
        if output_path:
            output_file = Path(output_path)
            output_file.write_text(cleaned_text, encoding='utf-8')
            logging.info(f"清洗后的 Markdown 已保存到: {output_file}")
        else:
            # 更新原始生成的文件
            actual_md_file.write_text(cleaned_text, encoding='utf-8')
            logging.info(f"清洗后的 Markdown 已更新到: {actual_md_file}")

        return cleaned_text

    except FileNotFoundError:
        logging.error(f"错误：未在指定路径找到 PDF 文件: {pdf_path}")
        raise
    except subprocess.CalledProcessError as e:
        logging.error(f"marker 命令执行失败 ({pdf_path}): {e}")
        logging.error(f"标准输出: {e.stdout}")
        logging.error(f"标准错误: {e.stderr}")
        raise
    except Exception as e:
        logging.error(f"PDF 转换过程中发生未知错误 ({pdf_path}): {e}")
        raise


if __name__ == "__main__":
    # 配置日志记录以进行测试
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 定义一个测试用的PDF文件路径
    # 请将其替换为您本地的PDF文件路径
    test_pdf_path = "input/test.pdf"
    
    if not Path(test_pdf_path).exists():
        logging.error(f"测试文件未找到: {test_pdf_path}")
        logging.error("请提供一个有效的PDF文件路径进行测试。")
    else:
        logging.info(f"开始测试 PDF 转换: {test_pdf_path}")
        try:
            markdown_output = convert_pdf_to_markdown(test_pdf_path)
            logging.info("PDF 转换和清洗成功完成。")
            
            logging.info("转换后的 Markdown (前500字符):")
            print("---")
            print(markdown_output[:500])
            print("---")
            
        except Exception as e:
            logging.error(f"在测试转换过程中发生错误: {e}", exc_info=True)