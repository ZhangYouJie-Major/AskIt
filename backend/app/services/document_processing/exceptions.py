"""
文档处理相关的自定义异常类
"""


class DocumentProcessingError(Exception):
    """文档处理通用错误基类"""
    
    def __init__(self, message: str, details: dict = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            details: 额外的错误详情字典
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} | 详情: {self.details}"
        return self.message


class UnsupportedFileTypeError(DocumentProcessingError):
    """不支持的文件类型错误
    
    当尝试解析不支持的文件格式时抛出此异常
    """
    
    def __init__(self, file_type: str, supported_types: list = None):
        """
        初始化异常
        
        Args:
            file_type: 不支持的文件类型
            supported_types: 支持的文件类型列表
        """
        supported = supported_types or ["pdf", "docx", "txt", "md"]
        message = f"不支持的文件类型: {file_type}"
        details = {
            "file_type": file_type,
            "supported_types": supported,
        }
        super().__init__(message, details)


class FileParseError(DocumentProcessingError):
    """文件解析错误
    
    当文件损坏、无法读取或解析失败时抛出此异常
    """
    
    def __init__(self, file_path: str, reason: str, original_error: Exception = None):
        """
        初始化异常
        
        Args:
            file_path: 文件路径
            reason: 失败原因
            original_error: 原始异常对象
        """
        message = f"文件解析失败: {file_path}"
        details = {
            "file_path": file_path,
            "reason": reason,
            "original_error": str(original_error) if original_error else None,
        }
        super().__init__(message, details)
        self.original_error = original_error


class EmbeddingAPIError(DocumentProcessingError):
    """Embedding API 调用错误
    
    当调用 Embedding API 失败时抛出此异常
    """
    
    def __init__(
        self,
        provider: str,
        reason: str,
        status_code: int = None,
        response_body: str = None,
        retry_count: int = 0,
    ):
        """
        初始化异常
        
        Args:
            provider: 提供商名称 (openai/glm/qwen)
            reason: 失败原因
            status_code: HTTP 状态码
            response_body: API 响应内容
            retry_count: 已重试次数
        """
        message = f"Embedding API 调用失败 ({provider}): {reason}"
        details = {
            "provider": provider,
            "reason": reason,
            "status_code": status_code,
            "response_body": response_body,
            "retry_count": retry_count,
        }
        super().__init__(message, details)
