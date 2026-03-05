"""
测试文档处理核心数据结构和异常类
"""
import sys
import os
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from app.services.document_processing import (
    ParsedDocument,
    TextChunk,
    ProcessingResult,
    ChunkStrategy,
    UnsupportedFileTypeError,
    FileParseError,
    EmbeddingAPIError,
    DocumentProcessingError,
)


class TestChunkStrategy:
    """测试 ChunkStrategy 枚举"""
    
    def test_chunk_strategy_values(self):
        """测试枚举值定义正确"""
        assert ChunkStrategy.SIMPLE.value == "simple"
        assert ChunkStrategy.SMART.value == "smart"
        assert ChunkStrategy.PARAGRAPH.value == "paragraph"
        assert ChunkStrategy.SEMANTIC.value == "semantic"


class TestParsedDocument:
    """测试 ParsedDocument 数据类"""
    
    def test_create_parsed_document_with_required_fields(self):
        """测试创建包含必填字段的 ParsedDocument"""
        doc = ParsedDocument(content="测试内容")
        assert doc.content == "测试内容"
        assert doc.page_count is None
        assert doc.metadata == {}
    
    def test_create_parsed_document_with_all_fields(self):
        """测试创建包含所有字段的 ParsedDocument"""
        metadata = {"author": "张三", "created_at": "2024-01-01"}
        doc = ParsedDocument(
            content="完整内容",
            page_count=10,
            metadata=metadata
        )
        assert doc.content == "完整内容"
        assert doc.page_count == 10
        assert doc.metadata == metadata
    
    def test_parsed_document_empty_content_raises_error(self):
        """测试空内容抛出异常"""
        with pytest.raises(ValueError, match="content 字段不能为空"):
            ParsedDocument(content="")


class TestTextChunk:
    """测试 TextChunk 数据类"""
    
    def test_create_text_chunk_with_required_fields(self):
        """测试创建包含必填字段的 TextChunk"""
        chunk = TextChunk(content="分块内容", chunk_index=0)
        assert chunk.content == "分块内容"
        assert chunk.chunk_index == 0
        assert chunk.page_number is None
        assert chunk.metadata == {}
    
    def test_create_text_chunk_with_all_fields(self):
        """测试创建包含所有字段的 TextChunk"""
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
    
    def test_text_chunk_length(self):
        """测试 TextChunk 长度计算"""
        chunk = TextChunk(content="测试内容", chunk_index=0)
        assert len(chunk) == 4  # 4 个中文字符
    
    def test_text_chunk_empty_content_raises_error(self):
        """测试空内容抛出异常"""
        with pytest.raises(ValueError, match="content 字段不能为空"):
            TextChunk(content="", chunk_index=0)
    
    def test_text_chunk_negative_index_raises_error(self):
        """测试负数索引抛出异常"""
        with pytest.raises(ValueError, match="chunk_index 必须大于等于 0"):
            TextChunk(content="内容", chunk_index=-1)


class TestProcessingResult:
    """测试 ProcessingResult 数据类"""
    
    def test_create_successful_result(self):
        """测试创建成功的处理结果"""
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
    
    def test_create_failed_result(self):
        """测试创建失败的处理结果"""
        result = ProcessingResult(
            document_id=2,
            status="failed",
            error_message="解析失败"
        )
        assert result.document_id == 2
        assert result.status == "failed"
        assert result.error_message == "解析失败"
        assert result.success is False
    
    def test_failed_status_without_error_message_raises_error(self):
        """测试失败状态但没有错误信息时抛出异常"""
        with pytest.raises(ValueError, match="状态为 failed 时必须提供 error_message"):
            ProcessingResult(document_id=1, status="failed")
    
    def test_invalid_status_raises_error(self):
        """测试无效状态抛出异常"""
        with pytest.raises(ValueError, match="status 必须是"):
            ProcessingResult(document_id=1, status="invalid")
    
    def test_performance_summary(self):
        """测试性能摘要"""
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


class TestExceptions:
    """测试自定义异常类"""
    
    def test_document_processing_error(self):
        """测试基础异常类"""
        error = DocumentProcessingError("测试错误", {"key": "value"})
        assert error.message == "测试错误"
        assert error.details == {"key": "value"}
        assert "测试错误" in str(error)
        assert "key" in str(error)
    
    def test_unsupported_file_type_error(self):
        """测试不支持的文件类型异常"""
        error = UnsupportedFileTypeError("xyz")
        assert "xyz" in str(error)
        assert error.details["file_type"] == "xyz"
        assert "pdf" in error.details["supported_types"]
        assert "docx" in error.details["supported_types"]
    
    def test_file_parse_error(self):
        """测试文件解析异常"""
        original = ValueError("原始错误")
        error = FileParseError("/path/to/file.pdf", "文件损坏", original)
        assert "/path/to/file.pdf" in str(error)
        assert error.details["file_path"] == "/path/to/file.pdf"
        assert error.details["reason"] == "文件损坏"
        assert error.original_error == original
    
    def test_embedding_api_error(self):
        """测试 Embedding API 异常"""
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
