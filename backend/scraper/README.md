# 文档解析器模块 (Scraper)

该模块负责处理不同格式的文档，将其转换为统一的 Markdown 格式供 DeepReader 系统分析。

## 📄 支持的文档格式

### PDF 文件 (`pdf_converter.py`)
- **工具**：本地 marker
- **特性**：高质量转换，保留格式和结构
- **输出**：`文件名/文件名.md`

### EPUB 电子书 (`epub_converter.py`)
- **工具**：ebooklib
- **特性**：提取文本内容，保留章节结构
- **输出**：`文件名/文件名.md`

### 网页内容 (`web_scraper.py`)
- **工具**：自定义抓取器
- **特性**：清理HTML，提取主要内容
- **输出**：纯净的 Markdown 文本

## 🧹 文本清洗

### 清洗规则 (`clean_rule.py`)
- 移除多余的空行和空格
- 标准化标题格式
- 清理特殊字符和符号
- 优化表格和列表格式

## 🔧 工具函数

### 通用工具 (`scraper_tools.py`)
- 文件类型检测
- 路径处理
- 编码转换
- 错误处理

### 批量处理 (`multipdf.py`)
- 批量处理多个 PDF 文件
- 并行转换提高效率
- 统一输出管理

## 🚀 使用方式

这些模块主要通过 `main.py` 中的 `convert_document_to_markdown()` 函数调用，用户无需直接使用。

### 直接调用示例

```python
from backend.scraper.pdf_converter import convert_pdf_to_markdown
from backend.scraper.epub_converter import convert_epub_to_markdown

# 转换 PDF
markdown_content = convert_pdf_to_markdown("document.pdf")

# 转换 EPUB  
markdown_content = convert_epub_to_markdown("book.epub")
```

## 📝 扩展支持

要添加新的文档格式支持：

1. 在 `scraper/` 目录创建新的转换器文件
2. 实现统一的转换接口
3. 在 `main.py` 的 `convert_document_to_markdown()` 中添加格式检测
4. 更新文档说明
