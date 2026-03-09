"""
独立测试：直接测试 parsers 模块，完全避免应用初始化
"""
import sys
from pathlib import Path

# 添加 backend 目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# 直接导入类型和异常，避免通过 app.services
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
import types as types_builtin
parsers_code = parsers_path.read_text()
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
FileParser = parsers_module.FileParser
FileParserFactory = parsers_module.FileParserFactory
PDFParser = parsers_module.PDFParser
WordParser = parsers_module.WordParser
TextParser = parsers_module.TextParser
MarkdownParser = parsers_module.MarkdownParser
UnsupportedFileTypeError = exceptions_module.UnsupportedFileTypeError


def test_factory_returns_correct_parser_types():
    """测试工厂类返回正确的解析器类型"""
    print("测试 1: 工厂类返回正确的解析器类型")
    
    # 测试 PDF
    parser = FileParserFactory.get_parser("pdf")
    assert isinstance(parser, PDFParser), "PDF 解析器类型错误"
    print("  ✓ PDF 解析器类型正确")
    
    # 测试 Word
    parser = FileParserFactory.get_parser("docx")
    assert isinstance(parser, WordParser), "Word 解析器类型错误"
    print("  ✓ Word 解析器类型正确")
    
    # 测试 Text
    parser = FileParserFactory.get_parser("txt")
    assert isinstance(parser, TextParser), "Text 解析器类型错误"
    print("  ✓ Text 解析器类型正确")
    
    # 测试 Markdown
    parser = FileParserFactory.get_parser("md")
    assert isinstance(parser, MarkdownParser), "Markdown 解析器类型错误"
    print("  ✓ Markdown 解析器类型正确")
    
    print("测试 1 通过！\n")


def test_factory_case_insensitive():
    """测试工厂类不区分大小写"""
    print("测试 2: 工厂类不区分大小写")
    
    # 测试大写
    parser = FileParserFactory.get_parser("PDF")
    assert isinstance(parser, PDFParser), "大写 PDF 解析器类型错误"
    print("  ✓ 大写 PDF 正确")
    
    # 测试混合大小写
    parser = FileParserFactory.get_parser("DoCx")
    assert isinstance(parser, WordParser), "混合大小写 DOCX 解析器类型错误"
    print("  ✓ 混合大小写 DOCX 正确")
    
    print("测试 2 通过！\n")


def test_factory_unsupported_type_raises_error():
    """测试不支持的文件类型抛出异常"""
    print("测试 3: 不支持的文件类型抛出异常")
    
    unsupported_types = ["doc", "xlsx", "ppt", "jpg", "png", "unknown"]
    
    for file_type in unsupported_types:
        try:
            FileParserFactory.get_parser(file_type)
            assert False, f"应该抛出 UnsupportedFileTypeError，但没有抛出: {file_type}"
        except UnsupportedFileTypeError as e:
            # 验证异常消息包含文件类型
            assert file_type in str(e), f"异常消息应包含文件类型: {file_type}"
            # 验证异常详情包含支持的类型列表
            assert e.details["file_type"] == file_type, "异常详情中的文件类型不正确"
            assert "supported_types" in e.details, "异常详情应包含支持的类型列表"
            print(f"  ✓ {file_type} 正确抛出异常")
    
    print("测试 3 通过！\n")


def test_factory_get_supported_types():
    """测试获取支持的文件类型列表"""
    print("测试 4: 获取支持的文件类型列表")
    
    supported_types = FileParserFactory.get_supported_types()
    
    assert isinstance(supported_types, list), "返回值应该是列表"
    assert len(supported_types) == 4, "应该支持 4 种文件类型"
    assert "pdf" in supported_types, "应该支持 PDF"
    assert "docx" in supported_types, "应该支持 DOCX"
    assert "txt" in supported_types, "应该支持 TXT"
    assert "md" in supported_types, "应该支持 MD"
    
    print(f"  ✓ 支持的文件类型: {supported_types}")
    print("测试 4 通过！\n")


def test_parser_is_abstract():
    """测试 FileParser 是抽象类"""
    print("测试 5: FileParser 是抽象类")
    
    try:
        # 尝试直接实例化抽象类
        parser = FileParser()
        assert False, "不应该能够直接实例化 FileParser"
    except TypeError as e:
        assert "abstract" in str(e).lower(), "错误消息应提到抽象类"
        print("  ✓ FileParser 是抽象类，无法直接实例化")
    
    print("测试 5 通过！\n")


if __name__ == "__main__":
    print("=" * 60)
    print("FileParser 和 FileParserFactory 基本功能测试")
    print("=" * 60 + "\n")
    
    test_factory_returns_correct_parser_types()
    test_factory_case_insensitive()
    test_factory_unsupported_type_raises_error()
    test_factory_get_supported_types()
    test_parser_is_abstract()
    
    print("=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
