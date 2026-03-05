"""
文档处理相关的数据类型定义
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ChunkStrategy(Enum):
    """文档分块策略枚举"""
    
    SIMPLE = "simple"         # 简单固定大小分块
    SMART = "smart"           # 智能边界分块（句子、段落）
    PARAGRAPH = "paragraph"   # 段落分块
    SEMANTIC = "semantic"     # 语义分块（未来扩展）


@dataclass
class ParsedDocument:
    """解析后的文档对象
    
    包含从文件中提取的文本内容和元数据
    """
    
    content: str                          # 文本内容
    page_count: Optional[int] = None      # 页数（如果适用）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def __post_init__(self):
        """验证必填字段"""
        if not self.content:
            raise ValueError("content 字段不能为空")
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TextChunk:
    """文本块对象
    
    表示文档分块后的单个文本片段
    """
    
    content: str                          # 文本内容
    chunk_index: int                      # 块序号（从 0 开始）
    page_number: Optional[int] = None     # 页码（如果可用）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def __post_init__(self):
        """验证必填字段"""
        if not self.content:
            raise ValueError("content 字段不能为空")
        if self.chunk_index < 0:
            raise ValueError("chunk_index 必须大于等于 0")
        if self.metadata is None:
            self.metadata = {}
    
    def __len__(self):
        """返回文本块的字符长度"""
        return len(self.content)


@dataclass
class ProcessingResult:
    """文档处理结果
    
    包含处理完成后的状态和统计信息
    """
    
    document_id: int                      # 文档 ID
    status: str                           # 状态: completed/failed
    chunk_count: int = 0                  # 分块数量
    processing_time: float = 0.0          # 处理耗时（秒）
    error_message: Optional[str] = None   # 错误信息（如果失败）
    
    # 性能指标（可选）
    parse_time: float = 0.0               # 解析耗时（秒）
    chunk_time: float = 0.0               # 分块耗时（秒）
    embed_time: float = 0.0               # 向量化耗时（秒）
    store_time: float = 0.0               # 存储耗时（秒）
    
    def __post_init__(self):
        """验证状态字段"""
        valid_statuses = ["completed", "failed"]
        if self.status not in valid_statuses:
            raise ValueError(f"status 必须是 {valid_statuses} 之一")
        
        # 如果状态为 failed，必须有错误信息
        if self.status == "failed" and not self.error_message:
            raise ValueError("状态为 failed 时必须提供 error_message")
    
    @property
    def success(self) -> bool:
        """是否处理成功"""
        return self.status == "completed"
    
    def get_performance_summary(self) -> Dict[str, float]:
        """获取性能摘要
        
        Returns:
            包含各阶段耗时的字典
        """
        return {
            "total_time": self.processing_time,
            "parse_time": self.parse_time,
            "chunk_time": self.chunk_time,
            "embed_time": self.embed_time,
            "store_time": self.store_time,
        }
