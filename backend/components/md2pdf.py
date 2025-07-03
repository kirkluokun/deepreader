#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown转PDF转换器

将markdown文件转换为PDF格式输出
支持中文字符和多种样式
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any
import subprocess
import tempfile

try:
    import markdown
    from markdown.extensions import codehilite, tables, toc
except ImportError:
    print("请安装markdown库: pip install markdown")
    sys.exit(1)

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarkdownToPDFConverter:
    """Markdown转PDF转换器类"""
    
    def __init__(self, css_style: Optional[str] = None):
        """
        初始化转换器
        
        Args:
            css_style: 自定义CSS样式字符串
        """
        self.css_style = css_style or self._get_default_css()
        self._check_dependencies()
    
    def _check_dependencies(self) -> bool:
        """检查所需依赖是否安装"""
        try:
            # 检查weasyprint
            import weasyprint
            return True
        except ImportError:
            logger.warning("weasyprint未安装，将尝试使用wkhtmltopdf")
            # 检查wkhtmltopdf
            try:
                result = subprocess.run(['wkhtmltopdf', '--version'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return True
            except FileNotFoundError:
                pass
            
            logger.error("请安装以下任一依赖:")
            logger.error("1. pip install weasyprint")  
            logger.error("2. 安装wkhtmltopdf: brew install wkhtmltopdf (MacOS)")
            return False
    
    def _get_default_css(self) -> str:
        """获取默认CSS样式"""
        return """
        @page {
            size: A4;
            margin: 2cm;
        }
        
        body {
            font-family: "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: bold;
        }
        
        h1 { font-size: 24pt; border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }
        h2 { font-size: 20pt; border-bottom: 1px solid #bdc3c7; padding-bottom: 0.2em; }
        h3 { font-size: 16pt; }
        h4 { font-size: 14pt; }
        h5 { font-size: 12pt; }
        h6 { font-size: 11pt; }
        
        p {
            margin: 0.8em 0;
            text-align: justify;
        }
        
        code {
            background-color: #f8f9fa;
            color: #e83e8c;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: "Monaco", "Menlo", "Consolas", monospace;
            font-size: 0.9em;
        }
        
        pre {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 1em;
            margin: 1em 0;
            overflow-x: auto;
        }
        
        pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
        }
        
        blockquote {
            border-left: 4px solid #3498db;
            margin: 1em 0;
            padding-left: 1em;
            color: #666;
            font-style: italic;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }
        
        th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        
        ul, ol {
            margin: 1em 0;
            padding-left: 2em;
        }
        
        li {
            margin: 0.3em 0;
        }
        
        a {
            color: #3498db;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
        }
        
        hr {
            border: none;
            border-top: 1px solid #ccc;
            margin: 2em 0;
        }
        
        .toc {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 1em;
            margin: 1em 0;
        }
        
        .toc ul {
            list-style-type: none;
            padding-left: 1em;
        }
        """
    
    def markdown_to_html(self, markdown_content: str) -> str:
        """
        将markdown内容转换为HTML
        
        Args:
            markdown_content: markdown内容字符串
            
        Returns:
            转换后的HTML字符串
        """
        # 配置markdown扩展
        extensions = [
            'markdown.extensions.tables',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.fenced_code',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists'
        ]
        
        # 创建markdown实例
        md = markdown.Markdown(extensions=extensions)
        
        # 转换为HTML
        html_content = md.convert(markdown_content)
        
        # 创建完整的HTML文档
        full_html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Markdown转PDF</title>
            <style>
                {self.css_style}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        return full_html
    
    def html_to_pdf_weasyprint(self, html_content: str, output_path: str) -> bool:
        """
        使用weasyprint将HTML转换为PDF
        
        Args:
            html_content: HTML内容
            output_path: 输出PDF文件路径
            
        Returns:
            是否转换成功
        """
        try:
            import weasyprint
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            # 创建字体配置
            font_config = FontConfiguration()
            
            # 将HTML转换为PDF
            html_doc = HTML(string=html_content)
            css_doc = CSS(string=self.css_style, font_config=font_config)
            
            html_doc.write_pdf(output_path, stylesheets=[css_doc], font_config=font_config)
            
            logger.info(f"PDF已成功生成: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"weasyprint转换失败: {e}")
            return False
    
    def html_to_pdf_wkhtmltopdf(self, html_content: str, output_path: str) -> bool:
        """
        使用wkhtmltopdf将HTML转换为PDF
        
        Args:
            html_content: HTML内容
            output_path: 输出PDF文件路径
            
        Returns:
            是否转换成功
        """
        try:
            # 创建临时HTML文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', 
                                           encoding='utf-8', delete=False) as temp_file:
                temp_file.write(html_content)
                temp_html_path = temp_file.name
            
            try:
                # 执行wkhtmltopdf命令
                cmd = [
                    'wkhtmltopdf',
                    '--page-size', 'A4',
                    '--margin-top', '20mm',
                    '--margin-right', '20mm', 
                    '--margin-bottom', '20mm',
                    '--margin-left', '20mm',
                    '--encoding', 'UTF-8',
                    '--no-outline',
                    temp_html_path,
                    output_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"PDF已成功生成: {output_path}")
                    return True
                else:
                    logger.error(f"wkhtmltopdf转换失败: {result.stderr}")
                    return False
                    
            finally:
                # 清理临时文件
                os.unlink(temp_html_path)
                
        except Exception as e:
            logger.error(f"wkhtmltopdf转换失败: {e}")
            return False
    
    def convert_file(self, input_path: Union[str, Path], 
                    output_path: Optional[Union[str, Path]] = None) -> bool:
        """
        转换markdown文件为PDF
        
        Args:
            input_path: 输入的markdown文件路径
            output_path: 输出的PDF文件路径(可选，默认为同名PDF文件)
            
        Returns:
            是否转换成功
        """
        # 处理路径
        input_path = Path(input_path)
        if not input_path.exists():
            logger.error(f"输入文件不存在: {input_path}")
            return False
        
        if output_path is None:
            output_path = input_path.with_suffix('.pdf')
        else:
            output_path = Path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 读取markdown文件
            with open(input_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            logger.info(f"开始转换: {input_path} -> {output_path}")
            
            # 转换为HTML
            html_content = self.markdown_to_html(markdown_content)
            
            # 尝试使用weasyprint转换
            try:
                import weasyprint
                success = self.html_to_pdf_weasyprint(html_content, str(output_path))
            except ImportError:
                # 回退到wkhtmltopdf
                success = self.html_to_pdf_wkhtmltopdf(html_content, str(output_path))
            
            if success:
                logger.info(f"转换完成: {output_path}")
                return True
            else:
                logger.error("转换失败")
                return False
                
        except Exception as e:
            logger.error(f"转换过程中出错: {e}")
            return False
    
    def convert_content(self, markdown_content: str, output_path: Union[str, Path]) -> bool:
        """
        转换markdown内容为PDF
        
        Args:
            markdown_content: markdown内容字符串
            output_path: 输出的PDF文件路径
            
        Returns:
            是否转换成功
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"开始转换内容到: {output_path}")
            
            # 转换为HTML
            html_content = self.markdown_to_html(markdown_content)
            
            # 尝试使用weasyprint转换
            try:
                import weasyprint
                success = self.html_to_pdf_weasyprint(html_content, str(output_path))
            except ImportError:
                # 回退到wkhtmltopdf
                success = self.html_to_pdf_wkhtmltopdf(html_content, str(output_path))
            
            if success:
                logger.info(f"转换完成: {output_path}")
                return True
            else:
                logger.error("转换失败")
                return False
                
        except Exception as e:
            logger.error(f"转换过程中出错: {e}")
            return False


def main():
    """命令行入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='将Markdown文件转换为PDF')
    parser.add_argument('input', help='输入的markdown文件路径')
    parser.add_argument('-o', '--output', help='输出的PDF文件路径(可选)')
    parser.add_argument('--css', help='自定义CSS样式文件路径(可选)')
    
    args = parser.parse_args()
    
    # 读取自定义CSS(如果提供)
    css_style = None
    if args.css and os.path.exists(args.css):
        with open(args.css, 'r', encoding='utf-8') as f:
            css_style = f.read()
    
    # 创建转换器
    converter = MarkdownToPDFConverter(css_style=css_style)
    
    # 执行转换
    success = converter.convert_file(args.input, args.output)
    
    if success:
        print("转换成功!")
        sys.exit(0)
    else:
        print("转换失败!")
        sys.exit(1)


if __name__ == '__main__':
    main()
