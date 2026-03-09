"""
简单测试文档处理核心数据结构和异常类
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

# 直接导入模块文件，避免触发 app.services.__init__ 中的数据库初始化
import importlib.util

# 加载 types 模块
types_spec = importlib.util.spec_from_file_location(
    "types_module",
    os.path.join(os.path.dirname(__file__), "app/services/document_processing/types.py")
)
types_module = importlib.util.module_from_spec(types_spec)
types_spec.loader.exec_module(types_module)

ParsedDocument = types_module.ParsedDocument
TextChunk = types_module.TextChunk
ProcessingResult = types_module.ProcessingResult
ChunkStrategy = types_module.ChunkStrategy

# 加载 exceptions 模块
exceptions_spec = importlib.util.spec_from_file_location(
    "exceptions_module",
    os.path.join(os.path.dirname(__file__), "app/services/document_processing/exceptions.py")
)
exceptions_module = importlib.util.module_from_spec(exceptions_spec)
exceptions_spec.loader.exec_module(exceptions_module)

UnsupportedFileTypeError = exceptions_module.UnsupportedFileTypeError
FileParseError = exceptions_module.FileParseError
EmbeddingAPIError = exceptions_module.EmbeddingAPIError
DocumentProcessingError = exceptions_module.DocumentProcessingError


def test_chunk_strategy():
    """测试 ChunkStrategy 枚举"""
    print("测试 ChunkStrategy 枚举...")
    assert ChunkStrategy.SIMPLE.value == "simple"
    assert ChunkStrategy.SMART.value == "smart"
    assert ChunkStrategy.PARAGRAPH.value == "paragraph"
    assert ChunkStrategy.SEMANTIC.value == "semantic"
    print("✅ ChunkStrategy 枚举测试通过")


def test_parsed_document():
    """测试 ParsedDocument 数据类"""
    print("\n测试 ParsedDocument 数据类...")
    
    # 测试基本创建
    doc = ParsedDocument(content="测试内容")
    assert doc.content == "测试内容"
    assert doc.page_count is None
    assert doc.metadata == {}
    
    # 测试完整字段
    metadata = {"author": "张三", "created_at": "2024-01-01"}
    doc = ParsedDocument(content="完整内容", page_count=10, metadata=metadata)
    assert doc.content == "完整内容"
    assert doc.page_count == 10
    assert doc.metadata == metadata
    
    # 测试空内容异常
    try:
        ParsedDocument(content="")
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "content 字段不能为空" in str(e)
    
    print("✅ ParsedDocument 测试通过")


def test_text_chunk():
    """测试 TextChunk 数据类"""
    print("\n测试 TextChunk 数据类...")
    
    # 测试基本创建
    chunk = TextChunk(content="分块内容", chunk_index=0)
    assert chunk.content == "分块内容"
    assert chunk.chunk_index == 0
    assert chunk.page_number is None
    assert chunk.metadata == {}
    
    # 测试长度
    assert len(chunk) == 4  # 4 个中文字符
    
    # 测试完整字段
    metadata = {"start_pos": 0, "end_pos": 100}
    chunk = TextChunk(
        content="完整分块",
        chunk_index=5,
        page_number=3,
        metadata=metadata
    )
    assert chunk.content == "完整分块"
    assert chunk.chunk_index == 5
    assert chunk.page_number == 3
    assert chunk.metadata == metadata
    
    # 测试空内容异常
    try:
        TextChunk(content="", chunk_index=0)
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "content 字段不能为空" in str(e)
    
    # 测试负数索引异常
    try:
        TextChunk(content="内容", chunk_index=-1)
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "chunk_index 必须大于等于 0" in str(e)
    
    print("✅ TextChunk 测试通过")


def test_processing_result():
    """测试 ProcessingResult 数据类"""
    print("\n测试 ProcessingResult 数据类...")
    
    # 测试成功结果
    result = ProcessingResult(
        document_id=1,
        status="completed",
        chunk_count=10,
        processing_time=5.5
    )
    assert result.document_id == 1
    assert result.status == "completed"
    assert result.chunk_count == 10
    assert result.processing_time == 5.5
    assert result.error_message is None
    assert result.success is True
    
    # 测试失败结果
    result = ProcessingResult(
        document_id=2,
        status="failed",
        error_message="解析失败"
    )
    assert result.document_id == 2
    assert result.status == "failed"
    assert result.error_message == "解析失败"
    assert result.success is False
    
    # 测试性能摘要
    result = ProcessingResult(
        document_id=1,
        status="completed",
        processing_time=10.0,
        parse_time=2.0,
        chunk_time=1.5,
        embed_time=5.0,
        store_time=1.5
    )
    summary = result.get_performance_summary()
    assert summary["total_time"] == 10.0
    assert summary["parse_time"] == 2.0
    assert summary["chunk_time"] == 1.5
    assert summary["embed_time"] == 5.0
    assert summary["store_time"] == 1.5
    
    # 测试失败状态但没有错误信息
    try:
        ProcessingResult(document_id=1, status="failed")
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "状态为 failed 时必须提供 error_message" in str(e)
    
    # 测试无效状态
    try:
        ProcessingResult(document_id=1, status="invalid")
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "status 必须是" in str(e)
    
    print("✅ ProcessingResult 测试通过")


def test_exceptions():
    """测试自定义异常类"""
    print("\n测试自定义异常类...")
    
    # 测试基础异常
    error = DocumentProcessingError("测试错误", {"key": "value"})
    assert error.message == "测试错误"
    assert error.details == {"key": "value"}
    assert "测试错误" in str(error)
    assert "key" in str(error)
    
    # 测试不支持的文件类型异常
    error = UnsupportedFileTypeError("xyz")
    assert "xyz" in str(error)
    assert error.details["file_type"] == "xyz"
    assert "pdf" in error.details["supported_types"]
    assert "docx" in error.details["supported_types"]
    
    # 测试文件解析异常
    original = ValueError("原始错误")
    error = FileParseError("/path/to/file.pdf", "文件损坏", original)
    assert "/path/to/file.pdf" in str(error)
    assert error.details["file_path"] == "/path/to/file.pdf"
    assert error.details["reason"] == "文件损坏"
    assert error.original_error == original
    
    # 测试 Embedding API 异常
    error = EmbeddingAPIError(
        provider="openai",
        reason="API 超时",
        status_code=500,
        response_body='{"error": "timeout"}',
        retry_count=3
    )
    assert "openai" in str(error)
    assert error.details["provider"] == "openai"
    assert error.details["status_code"] == 500
    assert error.details["retry_count"] == 3
    
    print("✅ 异常类测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试文档处理核心数据结构和异常类")
    print("=" * 60)
    
    try:
        test_chunk_strategy()
        test_parsed_document()
        test_text_chunk()
        test_processing_result()
        test_exceptions()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
