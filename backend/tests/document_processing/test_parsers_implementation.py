"""
测试 WordParser, TextParser, MarkdownParser 的实现
"""
import sys
from pathlib import Path
import tempfile
import os

# 添加 backend 目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# 直接导入类型和异常
import importlib.util

# 加载 types 模块
types_path = backend_dir / "app" / "services" / "document_processing" / "types.py"
spec = importlib.util.spec_from_file_location("types_module", types_path)
types_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(types_module)

# 加载 exceptions 模块
exceptions_path = backend_dir / "app" / "services" / "document_processing" / "exceptions.py"
spec = importlib.util.spec_from_file_location("exceptions_module", exceptions_path)
exceptions_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exceptions_module)

# 加载 parsers 模块
parsers_path = backend_dir / "app" / "services" / "document_processing" / "parsers.py"
spec = importlib.util.spec_from_file_location("parsers_module", parsers_path)
parsers_module = importlib.util.module_from_spec(spec)

# 注入依赖
sys.modules['types_module'] = types_module
sys.modules['exceptions_module'] = exceptions_module

# 修改 parsers 模块的导入
parsers_code = parsers_path.read_text(encoding='utf-8')
parsers_code = parsers_code.replace(
    "from .types import ParsedDocument",
    "from types_module import ParsedDocument"
).replace(
    "from .exceptions import UnsupportedFileTypeError, FileParseError",
    "from exceptions_module import UnsupportedFileTypeError, FileParseError"
)

# 执行修改后的代码
exec(parsers_code, parsers_module.__dict__)

# 提取需要的类
TextParser = parsers_module.TextParser
MarkdownParser = parsers_module.MarkdownParser
WordParser = parsers_module.WordParser
FileParseError = exceptions_module.FileParseError
ParsedDocument = types_module.ParsedDocument


def test_text_parser_basic():
    """测试 TextParser 基本功能"""
    print("测试 1: TextParser 基本功能")
    
    # 创建临时文本文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("Hello, World!\nThis is a test.\nLine 3.")
        temp_path = f.name
    
    try:
        parser = TextParser()
        result = parser.parse(temp_path)
        
        # 验证返回类型
        assert isinstance(result, ParsedDocument), "返回值应该是 ParsedDocument"
        
        # 验证内容
        assert "Hello, World!" in result.content, "内容应包含 'Hello, World!'"
        assert "This is a test." in result.content, "内容应包含 'This is a test.'"
        assert "Line 3." in result.content, "内容应包含 'Line 3.'"
        
        # 验证元数据
        assert result.metadata is not None, "元数据不应为空"
        assert "encoding" in result.metadata, "元数据应包含 encoding"
        assert "line_count" in result.metadata, "元数据应包含 line_count"
        assert "total_chars" in result.metadata, "元数据应包含 total_chars"
        assert result.metadata["line_count"] == 3, "行数应为 3"
        
        # 验证 page_count 为 None
        assert result.page_count is None, "纯文本文件的 page_count 应为 None"
        
        print("  ✓ TextParser 基本功能正常")
        print(f"  ✓ 编码: {result.metadata['encoding']}")
        print(f"  ✓ 行数: {result.metadata['line_count']}")
        print(f"  ✓ 字符数: {result.metadata['total_chars']}")
    finally:
        os.unlink(temp_path)
    
    print("测试 1 通过！\n")


def test_text_parser_empty_file():
    """测试 TextParser 处理空文件"""
    print("测试 2: TextParser 处理空文件")
    
    # 创建空文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("")
        temp_path = f.name
    
    try:
        parser = TextParser()
        try:
            result = parser.parse(temp_path)
            assert False, "空文件应该抛出 FileParseError"
        except FileParseError as e:
            assert "空" in str(e), "错误消息应提到文件为空"
            print("  ✓ 空文件正确抛出 FileParseError")
    finally:
        os.unlink(temp_path)
    
    print("测试 2 通过！\n")


def test_text_parser_nonexistent_file():
    """测试 TextParser 处理不存在的文件"""
    print("测试 3: TextParser 处理不存在的文件")
    
    parser = TextParser()
    try:
        result = parser.parse("/nonexistent/file.txt")
        assert False, "不存在的文件应该抛出 FileParseError"
    except FileParseError as e:
        assert "不存在" in str(e), "错误消息应提到文件不存在"
        print("  ✓ 不存在的文件正确抛出 FileParseError")
    
    print("测试 3 通过！\n")


def test_markdown_parser_basic():
    """测试 MarkdownParser 基本功能"""
    print("测试 4: MarkdownParser 基本功能")
    
    # 创建临时 Markdown 文件
    markdown_content = """# Title

## Section 1

This is **bold** text.

### Subsection

- Item 1
- Item 2

```python
def hello():
    print("Hello")
```

## Section 2

More content here.
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(markdown_content)
        temp_path = f.name
    
    try:
        parser = MarkdownParser()
        result = parser.parse(temp_path)
        
        # 验证返回类型
        assert isinstance(result, ParsedDocument), "返回值应该是 ParsedDocument"
        
        # 验证内容保留了格式标记
        assert "# Title" in result.content, "应保留一级标题标记"
        assert "## Section 1" in result.content, "应保留二级标题标记"
        assert "**bold**" in result.content, "应保留粗体标记"
        assert "```python" in result.content, "应保留代码块标记"
        assert "- Item 1" in result.content, "应保留列表标记"
        
        # 验证元数据
        assert result.metadata is not None, "元数据不应为空"
        assert "encoding" in result.metadata, "元数据应包含 encoding"
        assert "line_count" in result.metadata, "元数据应包含 line_count"
        assert "heading_count" in result.metadata, "元数据应包含 heading_count"
        assert "code_block_count" in result.metadata, "元数据应包含 code_block_count"
        assert "format" in result.metadata, "元数据应包含 format"
        assert result.metadata["format"] == "markdown", "format 应为 markdown"
        assert result.metadata["heading_count"] >= 4, "标题数应至少为 4"
        assert result.metadata["code_block_count"] >= 1, "代码块数应至少为 1"
        
        # 验证 page_count 为 None
        assert result.page_count is None, "Markdown 文件的 page_count 应为 None"
        
        print("  ✓ MarkdownParser 基本功能正常")
        print(f"  ✓ 编码: {result.metadata['encoding']}")
        print(f"  ✓ 行数: {result.metadata['line_count']}")
        print(f"  ✓ 标题数: {result.metadata['heading_count']}")
        print(f"  ✓ 代码块数: {result.metadata['code_block_count']}")
    finally:
        os.unlink(temp_path)
    
    print("测试 4 通过！\n")


def test_markdown_parser_empty_file():
    """测试 MarkdownParser 处理空文件"""
    print("测试 5: MarkdownParser 处理空文件")
    
    # 创建空文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write("")
        temp_path = f.name
    
    try:
        parser = MarkdownParser()
        try:
            result = parser.parse(temp_path)
            assert False, "空文件应该抛出 FileParseError"
        except FileParseError as e:
            assert "空" in str(e), "错误消息应提到文件为空"
            print("  ✓ 空文件正确抛出 FileParseError")
    finally:
        os.unlink(temp_path)
    
    print("测试 5 通过！\n")


def test_word_parser_nonexistent_file():
    """测试 WordParser 处理不存在的文件"""
    print("测试 6: WordParser 处理不存在的文件")
    
    parser = WordParser()
    try:
        result = parser.parse("/nonexistent/file.docx")
        assert False, "不存在的文件应该抛出 FileParseError"
    except FileParseError as e:
        assert "不存在" in str(e), "错误消息应提到文件不存在"
        print("  ✓ 不存在的文件正确抛出 FileParseError")
    
    print("测试 6 通过！\n")


def test_text_parser_chinese_content():
    """测试 TextParser 处理中文内容"""
    print("测试 7: TextParser 处理中文内容")
    
    # 创建包含中文的文本文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("这是一个测试文件。\n包含中文内容。\n第三行。")
        temp_path = f.name
    
    try:
        parser = TextParser()
        result = parser.parse(temp_path)
        
        # 验证中文内容
        assert "这是一个测试文件" in result.content, "应包含中文内容"
        assert "包含中文内容" in result.content, "应包含中文内容"
        
        print("  ✓ TextParser 正确处理中文内容")
    finally:
        os.unlink(temp_path)
    
    print("测试 7 通过！\n")


def test_markdown_parser_chinese_content():
    """测试 MarkdownParser 处理中文内容"""
    print("测试 8: MarkdownParser 处理中文内容")
    
    # 创建包含中文的 Markdown 文件
    markdown_content = """# 中文标题

## 第一节

这是**粗体**文字。

### 子节

- 项目 1
- 项目 2

```python
# 中文注释
def 你好():
    print("你好，世界！")
```
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(markdown_content)
        temp_path = f.name
    
    try:
        parser = MarkdownParser()
        result = parser.parse(temp_path)
        
        # 验证中文内容和格式标记
        assert "# 中文标题" in result.content, "应保留中文标题"
        assert "**粗体**" in result.content, "应保留格式标记"
        assert "你好，世界！" in result.content, "应包含中文内容"
        
        print("  ✓ MarkdownParser 正确处理中文内容")
    finally:
        os.unlink(temp_path)
    
    print("测试 8 通过！\n")


if __name__ == "__main__":
    print("=" * 60)
    print("WordParser, TextParser, MarkdownParser 实现测试")
    print("=" * 60 + "\n")
    
    test_text_parser_basic()
    test_text_parser_empty_file()
    test_text_parser_nonexistent_file()
    test_markdown_parser_basic()
    test_markdown_parser_empty_file()
    test_word_parser_nonexistent_file()
    test_text_parser_chinese_content()
    test_markdown_parser_chinese_content()
    
    print("=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
