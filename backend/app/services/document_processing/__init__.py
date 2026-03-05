"""
文档处理模块

提供文档解析、分块、向量化等核心功能
"""
# 注意：这里不从父模块导入，避免触发数据库初始化
from app.services.document_processing.exceptions import (
    UnsupportedFileTypeError,
    FileParseError,
    EmbeddingAPIError,
    DocumentProcessingError,
)
from app.services.document_processing.types import (
    ParsedDocument,
    TextChunk,
    ProcessingResult,
    ChunkStrategy,
)

__all__ = [
    # 异常类
    "UnsupportedFileTypeError",
    "FileParseError",
    "EmbeddingAPIError",
    "DocumentProcessingError",
    # 数据类型
    "ParsedDocument",
    "TextChunk",
    "ProcessingResult",
    "ChunkStrategy",
]
