# -*- coding: utf-8 -*-
"""
@author: FinAI-Chat
@file: mobi_converter.py
@time: 2025-11-06 20:30
@desc: 使用 mobi 和 BeautifulSoup 实现 MOBI 到纯净 Markdown 的转换
"""
import logging
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup
from .clean_rule import clean_markdown_text
import sys


def convert_mobi_to_markdown(file_path: str, output_path: Optional[str] = None) -> str:
    """
    将 MOBI 文件转换为干净的 Markdown 文本。
    
    Args:
        file_path (str): MOBI 文件的路径。
        output_path (Optional[str]): 可选的输出路径。如果未提供，将输出到与 MOBI 同目录。
        
    Returns:
        str: 转换后的 Markdown 文本。
    """
    try:
        # 尝试导入 mobi 库
        try:
            import mobi
        except ImportError:
            logging.error("未安装 mobi 库。请运行: pip install mobi")
            raise ImportError(
                "需要安装 mobi 库来处理 MOBI 文件。\\n"
                "请运行: pip install mobi"
            )
        
        logging.info(f"开始解析 MOBI 文件: {file_path}")
        
        # 1. 解压 MOBI 文件
        temp_dir, _ = mobi.extract(file_path)
        
        # 2. 查找 HTML 文件
        temp_path = Path(temp_dir)
        html_files = list(temp_path.glob("*.html"))
        
        if not html_files:
            # 如果没有找到 .html 文件，尝试查找 .htm 文件
            html_files = list(temp_path.glob("*.htm"))
        
        if not html_files:
            raise FileNotFoundError(f"在解压的 MOBI 文件中未找到 HTML 文件: {temp_dir}")
        
        # 3. 合并所有 HTML 文件的内容
        full_text = []
        
        logging.info(f"找到 {len(html_files)} 个 HTML 文件，开始提取内容...")
        
        for html_file in sorted(html_files):
            try:
                with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                    html_content = f.read()
                    
                # 使用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 移除不需要的元素
                for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                    tag.decompose()
                
                # 提取文本，保留段落结构
                text = soup.get_text(separator='\\n\\n', strip=True)
                if text:
                    full_text.append(text)
                    
            except Exception as e:
                logging.warning(f"处理 HTML 文件 {html_file.name} 时出错: {e}")
                continue
        
        # 4. 合并所有部分
        raw_markdown = "\\n\\n".join(full_text)
        
        # 5. 使用统一的清洗函数进行深度清洗
        cleaned_markdown = clean_markdown_text(raw_markdown)
        
        # 6. 保存到指定路径或默认路径
        file_path_obj = Path(file_path)
        if output_path:
            output_file = Path(output_path)
        else:
            # 创建与文件名同名的子文件夹，然后在里面生成 markdown 文件
            output_dir = file_path_obj.parent / file_path_obj.stem
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{file_path_obj.stem}.md"
        
        output_file.write_text(cleaned_markdown, encoding='utf-8')
        logging.info(f"MOBI 文件 '{file_path}' 已成功转换为 Markdown 并保存到: {output_file}")
        
        # 7. 清理临时文件
        try:
            import shutil
            shutil.rmtree(temp_dir)
            logging.debug(f"已清理临时目录: {temp_dir}")
        except Exception as e:
            logging.warning(f"清理临时目录失败: {e}")
        
        return cleaned_markdown

    except Exception as e:
        logging.error(f"处理 MOBI 文件 '{file_path}' 时发生错误: {e}", exc_info=True)
        return ""


if __name__ == "__main__":
    # 配置日志记录以进行测试
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 从命令行参数获取 MOBI 文件路径
    if len(sys.argv) < 2:
        print("用法: python mobi_converter.py <mobi文件路径>")
        sys.exit(1)
    
    test_mobi_path = sys.argv[1]
    
    if not Path(test_mobi_path).exists():
        logging.error(f"测试文件未找到: {test_mobi_path}")
        logging.error("请提供一个有效的 MOBI 文件路径作为命令行参数。")
    else:
        logging.info(f"开始测试 MOBI 转换: {test_mobi_path}")
        try:
            markdown_output = convert_mobi_to_markdown(test_mobi_path)
            logging.info("MOBI 转换和清洗成功完成。")
            
            logging.info("转换后的 Markdown (前500字符):")
            print("---")
            print(markdown_output[:500])
            print("---")
            
        except Exception as e:
            logging.error(f"在测试转换过程中发生错误: {e}", exc_info=True)

