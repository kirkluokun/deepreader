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
import sys

# 条件导入：支持直接运行和模块导入两种方式
try:
    from .clean_rule import clean_markdown_text
except ImportError:
    # 如果相对导入失败（直接运行脚本时），尝试绝对导入
    try:
        from clean_rule import clean_markdown_text
    except ImportError:
        # 如果都失败，定义一个简单的清洗函数
        def clean_markdown_text(text):
            """简单的文本清洗函数（fallback）"""
            import re
            # 基本清洗
            text = re.sub(r'<[^>]+>', '', text)  # 移除 HTML 标签
            text = re.sub(r'&nbsp;', ' ', text)  # 替换 &nbsp;
            text = re.sub(r' +', ' ', text)  # 合并多个空格
            lines = text.split('\n')
            non_empty_lines = [line.strip() for line in lines if line.strip()]
            return '\n'.join(non_empty_lines)


def convert_mobi_to_markdown(file_path: str, output_path: Optional[str] = None) -> str:
    """
    将 MOBI 文件转换为干净的 Markdown 文本。
    
    Args:
        file_path (str): MOBI 文件的路径。
        output_path (Optional[str]): 可选的输出路径。如果未提供，将输出到与 MOBI 同目录。
        
    Returns:
        str: 转换后的 Markdown 文本。
    """
    # 尝试导入 mobi 库
    try:
        import mobi
    except ImportError:
        logging.error("未安装 mobi 库。请运行: pip install mobi")
        raise ImportError(
            "需要安装 mobi 库来处理 MOBI 文件。\\n"
            "请运行: pip install mobi"
        )
    
    temp_dir = None
    
    try:
        logging.info(f"开始解析 MOBI 文件: {file_path}")
        
        # 方案1: 尝试直接读取 MOBI 内容
        try:
            logging.info("尝试方案1: 直接读取 MOBI 文本内容...")
            book_content, _ = mobi.extract(file_path)
            
            # mobi.extract 返回的第一个值可能是内容字符串
            if isinstance(book_content, str) and len(book_content) > 100:
                logging.info("✅ 成功直接提取 MOBI 内容")
                
                # 使用 BeautifulSoup 清理 HTML 标签
                soup = BeautifulSoup(book_content, 'html.parser')
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'img']):
                    tag.decompose()
                
                raw_markdown = soup.get_text(separator='\\n\\n', strip=True)
                
                # 清洗并保存
                cleaned_markdown = clean_markdown_text(raw_markdown)
                _save_markdown(file_path, output_path, cleaned_markdown)
                return cleaned_markdown
        except Exception as e:
            logging.info(f"方案1 失败: {e}，尝试方案2...")
        
        # 方案2: 解压到临时目录并提取文件
        
        # 1. 解压 MOBI 文件
        temp_dir, _ = mobi.extract(file_path)
        temp_path = Path(temp_dir)
        
        logging.info(f"MOBI 文件已解压到临时目录: {temp_dir}")
        
        # 2. 查找 HTML 文件（递归搜索，因为可能在子目录中）
        html_files = list(temp_path.rglob("*.html")) + list(temp_path.rglob("*.htm"))
        
        # 3. 如果还是找不到 HTML 文件，列出目录内容以调试
        if not html_files:
            logging.warning(f"在 {temp_dir} 中未找到 HTML 文件，列出目录内容：")
            all_files = list(temp_path.rglob("*"))
            for f in all_files[:20]:  # 只列出前 20 个文件
                logging.warning(f"  - {f.name} ({f.suffix})")
            
            # 尝试查找其他可能的文本文件
            text_files = (
                list(temp_path.rglob("*.txt")) + 
                list(temp_path.rglob("*.xhtml")) + 
                list(temp_path.rglob("*.xml"))
            )
            
            if text_files:
                logging.info(f"找到 {len(text_files)} 个备选文本文件，尝试使用...")
                html_files = text_files
            else:
                raise FileNotFoundError(
                    f"在解压的 MOBI 文件中未找到可用的文本文件: {temp_dir}\\n"
                    f"请确保 MOBI 文件格式正确，或尝试使用 Calibre 手动转换。"
                )
        
        # 4. 合并所有文件的内容
        full_text = []
        
        logging.info(f"找到 {len(html_files)} 个文件，开始提取内容...")
        
        for idx, content_file in enumerate(sorted(html_files), 1):
            try:
                logging.debug(f"处理第 {idx}/{len(html_files)} 个文件: {content_file.name}")
                
                with open(content_file, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
                
                # 根据文件类型决定处理方式
                if content_file.suffix.lower() in ['.html', '.htm', '.xhtml']:
                    # 使用 BeautifulSoup 解析 HTML/XHTML
                    soup = BeautifulSoup(file_content, 'html.parser')
                    
                    # 移除不需要的元素
                    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'img']):
                        tag.decompose()
                    
                    # 提取文本，保留段落结构
                    text = soup.get_text(separator='\\n\\n', strip=True)
                elif content_file.suffix.lower() == '.txt':
                    # 纯文本文件直接使用
                    text = file_content
                elif content_file.suffix.lower() == '.xml':
                    # XML 文件也尝试用 BeautifulSoup 解析
                    soup = BeautifulSoup(file_content, 'xml')
                    text = soup.get_text(separator='\\n\\n', strip=True)
                else:
                    logging.warning(f"未知文件类型: {content_file.suffix}，跳过")
                    continue
                
                if text and len(text.strip()) > 100:  # 只保留有实质内容的文件
                    full_text.append(text)
                    logging.debug(f"  ✅ 提取了 {len(text)} 字符")
                    
            except Exception as e:
                logging.warning(f"处理文件 {content_file.name} 时出错: {e}")
                continue
        
        if not full_text:
            raise ValueError(f"未能从 MOBI 文件中提取任何有效内容: {file_path}")
        
        # 5. 合并所有部分
        raw_markdown = "\\n\\n".join(full_text)
        logging.info(f"✅ 成功提取内容，总长度: {len(raw_markdown)} 字符")
        
        # 6. 使用统一的清洗函数进行深度清洗
        cleaned_markdown = clean_markdown_text(raw_markdown)
        
        # 7. 保存文件
        _save_markdown(file_path, output_path, cleaned_markdown)
        
        return cleaned_markdown

    except Exception as e:
        logging.error(f"处理 MOBI 文件 '{file_path}' 时发生错误: {e}", exc_info=True)
        return ""
    finally:
        # 8. 清理临时文件
        if temp_dir:
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logging.debug(f"已清理临时目录: {temp_dir}")
            except Exception as e:
                logging.warning(f"清理临时目录失败: {e}")


def _save_markdown(file_path: str, output_path: Optional[str], content: str) -> Path:
    """保存 Markdown 内容到文件"""
    file_path_obj = Path(file_path)
    
    if output_path:
        output_file = Path(output_path)
    else:
        # 创建与文件名同名的子文件夹，然后在里面生成 markdown 文件
        output_dir = file_path_obj.parent / file_path_obj.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{file_path_obj.stem}.md"
    
    output_file.write_text(content, encoding='utf-8')
    logging.info(f"MOBI 文件 '{file_path}' 已成功转换为 Markdown 并保存到: {output_file}")
    
    return output_file


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
            
            # 显示文件信息
            file_path_obj = Path(test_mobi_path)
            expected_output = file_path_obj.parent / file_path_obj.stem / f"{file_path_obj.stem}.md"
            logging.info(f"完整输出保存在: {expected_output}")
            
        except Exception as e:
            logging.error(f"在测试转换过程中发生错误: {e}", exc_info=True)

