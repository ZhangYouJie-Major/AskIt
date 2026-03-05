"""
文件解析器模块

提供文件解析的抽象基类和工厂类，支持多种文档格式的解析
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Type

from .types import ParsedDocument
from .exceptions import UnsupportedFileTypeError, FileParseError


class FileParser(ABC):
    """文件解析器抽象基类
    
    定义文件解析的统一接口，所有具体解析器必须继承此类
    """
    
    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        """解析文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            ParsedDocument: 包含文本内容和元数据的对象
            
        Raises:
            FileParseError: 文件解析失败
        """
        pass
    
    def _validate_file_exists(self, file_path: str) -> Path:
        """验证文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            Path: 文件路径对象
            
        Raises:
            FileParseError: 文件不存在
        """
        path = Path(file_path)
        if not path.exists():
            raise FileParseError(
                file_path=file_path,
                reason="文件不存在"
            )
        if not path.is_file():
            raise FileParseError(
                file_path=file_path,
                reason="路径不是文件"
            )
        return path


class PDFParser(FileParser):
    """PDF 文件解析器
    
    使用 PyPDF2 提取 PDF 文本内容和页码信息
    """
    
    def parse(self, file_path: str) -> ParsedDocument:
        """解析 PDF 文件
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            ParsedDocument: 包含文本内容和页码信息的对象
            
        Raises:
            FileParseError: 文件解析失败
        """
        # 实现将在任务 2.2 中完成
        raise NotImplementedError("PDFParser 将在任务 2.2 中实现")


class WordParser(FileParser):
    """Word 文档解析器
    
    使用 python-docx 提取 Word 文档文本内容和段落结构
    """
    
    def parse(self, file_path: str) -> ParsedDocument:
        """解析 Word 文档
        
        Args:
            file_path: Word 文档路径
            
        Returns:
            ParsedDocument: 包含文本内容和段落结构的对象
            
        Raises:
            FileParseError: 文件解析失败
        """
        # 实现将在任务 2.3 中完成
        raise NotImplementedError("WordParser 将在任务 2.3 中实现")


class TextParser(FileParser):
    """纯文本文件解析器
    
    读取纯文本文件的完整内容
    """
    
    def parse(self, file_path: str) -> ParsedDocument:
        """解析纯文本文件
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            ParsedDocument: 包含文本内容的对象
            
        Raises:
            FileParseError: 文件解析失败
        """
        # 实现将在任务 2.3 中完成
        raise NotImplementedError("TextParser 将在任务 2.3 中实现")


class MarkdownParser(FileParser):
    """Markdown 文件解析器
    
    读取 Markdown 文件的完整内容，保留格式标记
    """
    
    def parse(self, file_path: str) -> ParsedDocument:
        """解析 Markdown 文件
        
        Args:
            file_path: Markdown 文件路径
            
        Returns:
            ParsedDocument: 包含文本内容和格式标记的对象
            
        Raises:
            FileParseError: 文件解析失败
        """
        # 实现将在任务 2.3 中完成
        raise NotImplementedError("MarkdownParser 将在任务 2.3 中实现")


class FileParserFactory:
    """文件解析器工厂类
    
    根据文件扩展名返回对应的解析器实例
    """
    
    # 支持的文件类型到解析器类的映射
    _PARSERS: Dict[str, Type[FileParser]] = {
        "pdf": PDFParser,
        "docx": WordParser,
        "txt": TextParser,
        "md": MarkdownParser,
    }
    
    @classmethod
    def get_parser(cls, file_type: str) -> FileParser:
        """根据文件类型返回对应的解析器
        
        Args:
            file_type: 文件扩展名（不区分大小写）
            
        Returns:
            FileParser: 对应的解析器实例
            
        Raises:
            UnsupportedFileTypeError: 文件类型不支持
        """
        # 转换为小写以支持不区分大小写
        file_type_lower = file_type.lower()
        
        # 查找对应的解析器类
        parser_class = cls._PARSERS.get(file_type_lower)
        
        if parser_class is None:
            # 抛出不支持的文件类型错误
            raise UnsupportedFileTypeError(
                file_type=file_type,
                supported_types=list(cls._PARSERS.keys())
            )
        
        # 返回解析器实例
        return parser_class()
    
    @classmethod
    def get_supported_types(cls) -> list:
        """获取支持的文件类型列表
        
        Returns:
            list: 支持的文件扩展名列表
        """
        return list(cls._PARSERS.keys())
