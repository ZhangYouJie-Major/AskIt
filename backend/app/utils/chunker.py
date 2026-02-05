"""
文档分块工具
"""
from typing import List


class DocumentChunker:
    """文档分块器"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """
        将文本分割成块

        Args:
            text: 输入文本

        Returns:
            文本块列表
        """
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size

            # 如果不是最后一块，尝试在单词边界处分割
            if end < text_length:
                # 寻找最近的空格或换行
                for i in range(end, start + self.chunk_size // 2, -1):
                    if text[i] in " \n\t":
                        end = i + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # 移动起始位置，考虑重叠
            start = end - self.chunk_overlap

        return chunks

    def chunk_by_paragraphs(self, text: str, max_paragraph_size: int = 1000) -> List[str]:
        """
        按段落分割文本

        Args:
            text: 输入文本
            max_paragraph_size: 单个段落的最大字符数

        Returns:
            段落列表
        """
        if not text:
            return []

        # 按换行符分割
        paragraphs = text.split("\n\n")

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= max_paragraph_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks


# 默认实例
chunker = DocumentChunker()
