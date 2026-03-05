# 文档处理模块

本模块提供文档解析、分块、向量化等核心功能，用于企业知识库 RAG 系统的文档处理流程。

## 模块结构

```
document_processing/
├── __init__.py          # 模块初始化，导出公共接口
├── exceptions.py        # 自定义异常类
├── types.py            # 核心数据类型定义
├── parsers.py          # 文件解析器（待实现）
├── chunker.py          # 文档分块器（待实现）
├── embedding.py        # Embedding 服务（待实现）
└── processor.py        # 文档处理器（待实现）
```

## 核心数据类型

### ChunkStrategy（分块策略枚举）

定义文档分块的策略：

- `SIMPLE`: 简单固定大小分块
- `SMART`: 智能边界分块（句子、段落）
- `PARAGRAPH`: 段落分块
- `SEMANTIC`: 语义分块（未来扩展）

### ParsedDocument（解析后的文档对象）

表示从文件中提取的文本内容和元数据：

- `content: str` - 文本内容（必填）
- `page_count: Optional[int]` - 页数（如果适用）
- `metadata: Dict[str, Any]` - 元数据字典

### TextChunk（文本块对象）

表示文档分块后的单个文本片段：

- `content: str` - 文本内容（必填）
- `chunk_index: int` - 块序号，从 0 开始（必填）
- `page_number: Optional[int]` - 页码（如果可用）
- `metadata: Dict[str, Any]` - 元数据字典

### ProcessingResult（处理结果）

包含文档处理完成后的状态和统计信息：

- `document_id: int` - 文档 ID
- `status: str` - 状态：completed/failed
- `chunk_count: int` - 分块数量
- `processing_time: float` - 总处理耗时（秒）
- `error_message: Optional[str]` - 错误信息（如果失败）
- `parse_time: float` - 解析耗时（秒）
- `chunk_time: float` - 分块耗时（秒）
- `embed_time: float` - 向量化耗时（秒）
- `store_time: float` - 存储耗时（秒）

## 自定义异常

### DocumentProcessingError（基类）

文档处理通用错误基类，所有其他异常都继承自此类。

### UnsupportedFileTypeError

当尝试解析不支持的文件格式时抛出。

**参数：**
- `file_type: str` - 不支持的文件类型
- `supported_types: list` - 支持的文件类型列表（默认：pdf, docx, txt, md）

### FileParseError

当文件损坏、无法读取或解析失败时抛出。

**参数：**
- `file_path: str` - 文件路径
- `reason: str` - 失败原因
- `original_error: Exception` - 原始异常对象（可选）

### EmbeddingAPIError

当调用 Embedding API 失败时抛出。

**参数：**
- `provider: str` - 提供商名称（openai/glm/qwen）
- `reason: str` - 失败原因
- `status_code: int` - HTTP 状态码（可选）
- `response_body: str` - API 响应内容（可选）
- `retry_count: int` - 已重试次数（默认：0）

## 使用示例

```python
from app.services.document_processing import (
    ParsedDocument,
    TextChunk,
    ProcessingResult,
    ChunkStrategy,
    UnsupportedFileTypeError,
    FileParseError,
)

# 创建解析后的文档对象
doc = ParsedDocument(
    content="这是文档内容",
    page_count=5,
    metadata={"author": "张三"}
)

# 创建文本块
chunk = TextChunk(
    content="这是第一个分块",
    chunk_index=0,
    page_number=1
)

# 创建处理结果
result = ProcessingResult(
    document_id=123,
    status="completed",
    chunk_count=10,
    processing_time=5.5
)

# 异常处理
try:
    # 某些处理逻辑
    pass
except FileParseError as e:
    print(f"文件解析失败: {e.message}")
    print(f"详情: {e.details}")
```

## 验证需求

本模块实现满足以下需求：

- **需求 1.5**: 不支持的文件格式返回明确错误（UnsupportedFileTypeError）
- **需求 1.6**: 文件损坏或无法读取返回描述性错误（FileParseError）
- **需求 1.7**: 解析完成返回结构化对象（ParsedDocument）
- **需求 2.8**: 分块生成序号和元数据（TextChunk）
- **需求 3.7**: API 失败抛出异常并记录详细错误（EmbeddingAPIError）
- **需求 5.9**: 记录处理日志包含文档 ID、耗时、状态（ProcessingResult）

## 测试

运行测试：

```bash
cd backend
python test_types_simple.py
```

所有数据类型和异常类都包含完整的验证逻辑和测试覆盖。
