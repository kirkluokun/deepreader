# Markdown转PDF工具

这个模块提供了将Markdown文件转换为PDF格式的功能，支持中文字符和多种样式。

## 功能特点

- ✅ **完全支持中文**：使用中文友好的字体配置
- ✅ **表格转换**：完美支持markdown表格格式
- ✅ **代码高亮**：支持代码块语法高亮
- ✅ **自定义样式**：可以使用自定义CSS样式
- ✅ **多种输入方式**：支持文件转换和内容转换
- ✅ **多种PDF引擎**：支持weasyprint和wkhtmltopdf

## 安装依赖

### 方法1：使用weasyprint（推荐）

```bash
# 使用Poetry安装（推荐）
poetry add weasyprint

# 或者使用pip安装
pip install weasyprint
```

### 方法2：使用wkhtmltopdf（备选）

如果weasyprint安装失败，可以使用wkhtmltopdf：

```bash
# MacOS
brew install wkhtmltopdf

# Ubuntu/Debian
sudo apt-get install wkhtmltopdf

# Windows
# 下载并安装：https://wkhtmltopdf.org/downloads.html
```

## 使用方法

### 1. 基本使用

```python
from md2pdf import MarkdownToPDFConverter

# 创建转换器
converter = MarkdownToPDFConverter()

# 转换文件
success = converter.convert_file("input.md", "output.pdf")

if success:
    print("转换成功!")
else:
    print("转换失败!")
```

### 2. 转换markdown内容

```python
from md2pdf import MarkdownToPDFConverter

# markdown内容
markdown_content = """
# 标题

这是一个**测试文档**。

## 子标题

- 列表项1
- 列表项2

```python
print("Hello World")
```
"""

# 创建转换器并转换
converter = MarkdownToPDFConverter()
success = converter.convert_content(markdown_content, "output.pdf")
```

### 3. 使用自定义CSS样式

```python
from md2pdf import MarkdownToPDFConverter

# 自定义CSS样式
custom_css = """
body {
    font-family: "PingFang SC", Arial, sans-serif;
    font-size: 14pt;
    color: #2c3e50;
}

h1 {
    color: #e74c3c;
    border-bottom: 2px solid #e74c3c;
}
"""

# 创建使用自定义样式的转换器
converter = MarkdownToPDFConverter(css_style=custom_css)
converter.convert_file("input.md", "styled_output.pdf")
```

### 4. 命令行使用

```bash
# 基本转换
python md2pdf.py input.md

# 指定输出文件
python md2pdf.py input.md -o output.pdf

# 使用自定义CSS样式
python md2pdf.py input.md -o output.pdf --css custom.css
```

## API参考

### MarkdownToPDFConverter类

#### 构造函数

```python
MarkdownToPDFConverter(css_style: Optional[str] = None)
```

- `css_style`: 可选的自定义CSS样式字符串

#### 主要方法

##### convert_file()

```python
convert_file(input_path: Union[str, Path], 
            output_path: Optional[Union[str, Path]] = None) -> bool
```

转换markdown文件为PDF。

- `input_path`: 输入的markdown文件路径
- `output_path`: 输出的PDF文件路径（可选，默认为同名PDF文件）
- 返回值: 转换是否成功

##### convert_content()

```python
convert_content(markdown_content: str, output_path: Union[str, Path]) -> bool
```

转换markdown内容为PDF。

- `markdown_content`: markdown内容字符串
- `output_path`: 输出的PDF文件路径
- 返回值: 转换是否成功

## 支持的Markdown语法

- [x] 标题 (H1-H6)
- [x] 粗体和斜体文本
- [x] 列表（有序和无序）
- [x] 代码块和行内代码
- [x] 表格
- [x] 引用块
- [x] 链接
- [x] 分割线
- [x] 目录生成

## 默认样式特点

- **字体**：使用中文友好字体（PingFang SC, Microsoft YaHei）
- **页面**：A4大小，2cm边距
- **颜色**：使用现代化的配色方案
- **表格**：带边框和斑马条纹
- **代码**：灰色背景，等宽字体

## 故障排除

### 常见问题

1. **weasyprint安装失败**
   - 解决方案：使用系统包管理器安装系统依赖，或使用wkhtmltopdf作为替代

2. **中文字符显示异常**
   - 解决方案：确保系统安装了中文字体，或在CSS中指定字体路径

3. **PDF生成失败**
   - 检查输出目录是否存在写入权限
   - 确认markdown语法是否正确

### 获取帮助

如果遇到问题，请检查：

1. 依赖是否正确安装
2. 输入文件是否存在
3. 输出目录是否有写入权限
4. 查看日志输出了解具体错误信息

## 示例

运行示例程序：

```bash
python md2pdf_example.py
```

这将创建示例文件并演示各种转换功能。

## 许可证

MIT License 