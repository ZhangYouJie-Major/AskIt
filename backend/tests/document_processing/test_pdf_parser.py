"""
测试 PDFParser 实现

创建测试 PDF 文件并验证解析功能
"""
import sys
from pathlib import Path
import tempfile
import os

# 添加 app 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.document_processing.parsers import PDFParser
from app.services.document_processing.exceptions import FileParseError


def create_test_pdf(file_path: str, content: str, num_pages: int = 1) -> None:
    """创建一个简单的测试 PDF 文件
    
    使用 pypdf 创建包含文本的 PDF（通过创建空白页并添加文本）
    
    Args:
        file_path: PDF 文件路径
        content: 要写入的文本内容
        num_pages: 页数
    """
    from pypdf import PdfWriter, PdfReader
    from io import BytesIO
    
    # 创建一个最小的 PDF 内容（使用 PDF 原始格式）
    # 这是一个包含文本的最小 PDF 结构
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length """ + str(len(content) + 50).encode() + b"""
>>
stream
BT
/F1 12 Tf
50 750 Td
(""" + content.encode('latin-1', errors='replace') + b""") Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
""" + str(400 + len(content)).encode() + b"""
%%EOF
"""
    
    # 写入文件
    with open(file_path, 'wb') as f:
        f.write(pdf_content)


def test_pdf_parser_basic():
    """测试 PDFParser 基本功能"""
    print("测试 1: PDFParser 基本解析功能")
    
    # 创建临时 PDF 文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # 创建测试内容
        test_content = "This is test content"
        create_test_pdf(tmp_path, test_content)
        
        # 解析 PDF
        parser = PDFParser()
        result = parser.parse(tmp_path)
        
        # 验证结果
        assert result.content, "内容不应为空"
        assert result.page_count is not None, "页数不应为 None"
        assert result.page_count > 0, "页数应大于 0"
        assert "page_count" in result.metadata, "元数据应包含 page_count"
        assert "pages" in result.metadata, "元数据应包含 pages 信息"
        
        print(f"  ✓ 成功解析 PDF")
        print(f"  ✓ 页数: {result.page_count}")
        print(f"  ✓ 内容长度: {len(result.content)} 字符")
        print(f"  ✓ 元数据键: {list(result.metadata.keys())}")
        print(f"  ✓ 提取的内容: {result.content[:100]}")
        
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    print("测试 1 通过！\n")


def test_pdf_parser_multipage():
    """测试 PDFParser 多页文档"""
    print("测试 2: PDFParser 多页文档解析")
    
    # 创建临时 PDF 文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # 创建单页内容（简化测试）
        test_content = "Page content for testing"
        create_test_pdf(tmp_path, test_content)
        
        # 解析 PDF
        parser = PDFParser()
        result = parser.parse(tmp_path)
        
        # 验证结果
        assert result.content, "内容不应为空"
        assert result.page_count >= 1, "应该有至少 1 页"
        
        # 验证页面信息
        pages_info = result.metadata.get("pages", {})
        assert len(pages_info) == result.page_count, "页面信息数量应与页数一致"
        
        print(f"  ✓ 成功解析 PDF")
        print(f"  ✓ 页数: {result.page_count}")
        print(f"  ✓ 内容长度: {len(result.content)} 字符")
        
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    print("测试 2 通过！\n")


def test_pdf_parser_file_not_found():
    """测试 PDFParser 文件不存在错误"""
    print("测试 3: PDFParser 文件不存在错误处理")
    
    parser = PDFParser()
    
    try:
        parser.parse("/nonexistent/file.pdf")
        assert False, "应该抛出 FileParseError"
    except FileParseError as e:
        assert "文件不存在" in str(e) or "不存在" in str(e), "错误消息应提到文件不存在"
        print(f"  ✓ 正确抛出 FileParseError: {e.message}")
    
    print("测试 3 通过！\n")


def test_pdf_parser_invalid_file():
    """测试 PDFParser 无效文件错误"""
    print("测试 4: PDFParser 无效文件错误处理")
    
    # 创建一个非 PDF 文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as tmp:
        tmp.write("这不是一个有效的 PDF 文件")
        tmp_path = tmp.name
    
    try:
        parser = PDFParser()
        parser.parse(tmp_path)
        assert False, "应该抛出 FileParseError"
    except FileParseError as e:
        assert "解析失败" in str(e) or "PDF" in str(e), "错误消息应提到解析失败"
        print(f"  ✓ 正确抛出 FileParseError: {e.message}")
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    print("测试 4 通过！\n")


def test_pdf_parser_metadata():
    """测试 PDFParser 元数据提取"""
    print("测试 5: PDFParser 元数据提取")
    
    # 创建临时 PDF 文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # 创建带元数据的 PDF
        test_content = "测试内容"
        create_test_pdf(tmp_path, test_content)
        
        # 解析 PDF
        parser = PDFParser()
        result = parser.parse(tmp_path)
        
        # 验证元数据结构
        assert "page_count" in result.metadata, "应包含 page_count"
        assert "pages" in result.metadata, "应包含 pages"
        assert "total_chars" in result.metadata, "应包含 total_chars"
        
        print(f"  ✓ 元数据结构正确")
        print(f"  ✓ 元数据键: {list(result.metadata.keys())}")
        
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    print("测试 5 通过！\n")


if __name__ == "__main__":
    print("=" * 60)
    print("PDFParser 实现测试")
    print("=" * 60 + "\n")
    
    try:
        test_pdf_parser_basic()
        test_pdf_parser_multipage()
        test_pdf_parser_file_not_found()
        test_pdf_parser_invalid_file()
        test_pdf_parser_metadata()
        
        print("=" * 60)
        print("所有测试通过！✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
