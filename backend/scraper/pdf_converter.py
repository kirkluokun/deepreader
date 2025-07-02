# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: pdf_converter.py
@time: 2024-07-16 12:00
@desc: 使用 marker API 实现 PDF 到纯净 Markdown 的转换
"""
import json
import logging
import re
from pathlib import Path

import requests
from gpt_researcher.deepreader.backend.scraper.clean_rule import clean_markdown_text

# 定义 marker API 的地址
MARKER_API_URL = "http://127.0.0.1:8001/marker"


def convert_pdf_to_markdown(pdf_path: str) -> str:
    """
    使用 marker API 服务将单个 PDF 文件高效转换为纯净、结构化的 Markdown 文本。

    该函数通过调用一个在后台运行的 marker FastAPI 服务来执行转换。
    这避免了在当前进程中加载重量级模型。
    转换后，会调用内部清洗函数，确保最终输出不含任何图片。

    Args:
        pdf_path: 需要转换的 PDF 文件的路径。

    Returns:
        一个字符串，其中包含从 PDF 转换而来并经过清洗的 Markdown 文本。

    Raises:
        FileNotFoundError: 如果指定的 `pdf_path` 不存在。
        requests.exceptions.RequestException: 如果 API 调用失败。
        Exception: 在转换过程中发生任何其他未预期的错误。
    """
    logging.info(f"开始通过 API 将 PDF 转换为 Markdown: {pdf_path}")
    pdf_file = Path(pdf_path)
    if not pdf_file.is_file():
        raise FileNotFoundError(f"错误：未在指定路径找到 PDF 文件: {pdf_path}")

    try:
        # 确保传递给 API 的是绝对路径
        abs_pdf_path = str(pdf_file.resolve())
        payload = {
            "filepath": abs_pdf_path,
            "disable_image_extraction": True  # 根据用户要求，禁用图片提取
        }

        logging.info(f"向 marker API ({MARKER_API_URL}) 发送请求...")
        response = requests.post(MARKER_API_URL, json=payload)
        response.raise_for_status()  # 如果状态码不是 2xx，则引发 HTTPError

        # 解析JSON响应并提取 "output" 字段的内容
        try:
            response_json = response.json()
            markdown_text = response_json["output"]
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"解析 API 响应失败或响应中缺少 'output' 键: {e}")
            logging.error(f"收到的原始响应文本 (前500字符): {response.text[:500]}")
            raise ValueError("无法从API响应中解析Markdown内容。") from e

        logging.info(f"成功从 API 获取响应。Markdown 内容长度: {len(markdown_text)}")

        # 清洗转换后的文本
        # cleaned_text = clean_markdown_text(markdown_text)
        # logging.info(
        #     f"Markdown 文本已清洗。原始长度: {len(markdown_text)}, 清洗后长度: {len(cleaned_text)}"
        # )
        cleaned_text = markdown_text

        return cleaned_text
    except FileNotFoundError:
        logging.error(f"错误：未在指定路径找到 PDF 文件: {pdf_path}")
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"调用 marker API 时发生网络错误 ({pdf_path}): {e}")
        raise
    except Exception as e:
        logging.error(f"PDF 转换过程中发生未知错误 ({pdf_path}): {e}")
        raise


if __name__ == "__main__":
    # 配置日志记录以进行测试
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 定义一个测试用的PDF文件路径
    # 请将其替换为您本地的PDF文件路径
    test_pdf_path = "dynamic-gptr/gpt_researcher/deepreader/input/稳定币/crypto.pdf"
    
    if not Path(test_pdf_path).exists():
        logging.error(f"测试文件未找到: {test_pdf_path}")
        logging.error("请在 __main__ 代码块中提供一个有效的PDF文件路径进行测试。")
    else:
        logging.info(f"开始测试 PDF 转换: {test_pdf_path}")
        try:
            markdown_output = convert_pdf_to_markdown(test_pdf_path)
            logging.info("PDF 转换和清洗成功完成。")
            
            # 将结果写入文件以便查看
            output_file = Path("test_pdf_output.md")
            output_file.write_text(markdown_output, encoding='utf-8')
            
            logging.info(f"转换后的 Markdown (前500字符):\n---")
            print(markdown_output[:500])
            logging.info(f"---\n完整输出已保存到: {output_file.resolve()}")
            
        except Exception as e:
            logging.error(f"在测试转换过程中发生错误: {e}", exc_info=True)