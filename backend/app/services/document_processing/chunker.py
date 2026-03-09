"""
文档分块器模块

提供多种文档分块策略，将长文本分割成适合向量化的文本块
"""
import logging
from typing import Dict, Any, List, Optional

from app.services.document_processing.types import TextChunk, ChunkStrategy

logger = logging.getLogger(__name__)


class DocumentChunker:
    """文档分块器
    
    支持多种分块策略：
    - SIMPLE: 固定大小分块
    - SMART: 智能边界分块（句子、段落）
    - PARAGRAPH: 段落分块
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        strategy: ChunkStrategy = ChunkStrategy.SIMPLE
    ):
        """初始化分块器
        
        Args:
            chunk_size: 块大小（字符数），默认 500
            chunk_overlap: 重叠大小（字符数），默认 50
            strategy: 分块策略，默认 SIMPLE
            
        Raises:
            ValueError: 如果参数不合法
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 必须大于等于 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
        
        logger.info(
            f"初始化 DocumentChunker: chunk_size={chunk_size}, "
            f"chunk_overlap={chunk_overlap}, strategy={strategy.value}"
        )
    
    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """分块处理
        
        Args:
            text: 输入文本
            metadata: 文档元数据（可选）
            
        Returns:
            List[TextChunk]: 文本块列表
        """
        if not text:
            logger.warning("输入文本为空，返回空列表")
            return []
        
        metadata = metadata or {}
        
        # 根据策略选择分块方法
        if self.strategy == ChunkStrategy.SIMPLE:
            chunks = self._chunk_simple(text, metadata)
        elif self.strategy == ChunkStrategy.SMART:
            chunks = self._chunk_smart(text, metadata)
        elif self.strategy == ChunkStrategy.PARAGRAPH:
            chunks = self._chunk_paragraph(text, metadata)
        else:
            raise ValueError(f"不支持的分块策略: {self.strategy}")
        
        logger.info(
            f"分块完成: 策略={self.strategy.value}, "
            f"输入长度={len(text)}, 分块数量={len(chunks)}"
        )
        
        return chunks
    
    def _chunk_simple(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """简单固定大小分块策略
        
        按照配置的 chunk_size 进行固定大小分割，相邻块之间保留 chunk_overlap 重叠区域
        
        Args:
            text: 输入文本
            metadata: 文档元数据
            
        Returns:
            List[TextChunk]: 文本块列表
        """
        chunks = []
        text_length = len(text)
        chunk_index = 0
        start = 0
        
        while start < text_length:
            # 计算当前块的结束位置
            end = min(start + self.chunk_size, text_length)
            
            # 提取当前块的内容
            chunk_content = text[start:end]
            
            # 创建 TextChunk 对象
            chunk = TextChunk(
                content=chunk_content,
                chunk_index=chunk_index,
                page_number=metadata.get("page_number"),
                metadata={
                    **metadata,
                    "start_pos": start,
                    "end_pos": end,
                    "strategy": self.strategy.value,
                }
            )
            chunks.append(chunk)
            
            # 计算下一个块的起始位置（考虑重叠）
            # 如果已经到达文本末尾，则退出循环
            if end >= text_length:
                break
            
            # 下一个块的起始位置 = 当前块结束位置 - 重叠大小
            start = end - self.chunk_overlap
            chunk_index += 1
        
        return chunks
    
    def _chunk_smart(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """智能边界分块策略
        
        在自然边界（句子、段落）处调整分割点，优化中英文混合文本处理
        
        Args:
            text: 输入文本
            metadata: 文档元数据
            
        Returns:
            List[TextChunk]: 文本块列表
        """
        chunks = []
        text_length = len(text)
        chunk_index = 0
        start = 0
        
        # 定义中文标点符号（优先分割点）
        chinese_punctuation = {'。', '？', '！', '；'}
        # 定义英文句子结束符
        english_punctuation = {'.', '?', '!', ';'}
        # 定义次优分割点（段落和换行）
        paragraph_separators = {'\n\n', '\n'}
        # 定义最后的分割点（空格）
        space_separator = ' '
        
        while start < text_length:
            # 计算目标结束位置
            target_end = min(start + self.chunk_size, text_length)
            
            # 如果已经到达文本末尾，直接取到末尾
            if target_end >= text_length:
                chunk_content = text[start:text_length]
                chunk = TextChunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    page_number=metadata.get("page_number"),
                    metadata={
                        **metadata,
                        "start_pos": start,
                        "end_pos": text_length,
                        "strategy": self.strategy.value,
                    }
                )
                chunks.append(chunk)
                break
            
            # 寻找最佳分割点
            actual_end = self._find_best_split_point(
                text, start, target_end, 
                chinese_punctuation, english_punctuation,
                paragraph_separators, space_separator
            )
            
            # 提取当前块的内容
            chunk_content = text[start:actual_end]
            
            # 创建 TextChunk 对象
            chunk = TextChunk(
                content=chunk_content,
                chunk_index=chunk_index,
                page_number=metadata.get("page_number"),
                metadata={
                    **metadata,
                    "start_pos": start,
                    "end_pos": actual_end,
                    "strategy": self.strategy.value,
                }
            )
            chunks.append(chunk)
            
            # 计算下一个块的起始位置（考虑重叠）
            start = actual_end - self.chunk_overlap
            chunk_index += 1
        
        return chunks
    
    def _find_best_split_point(
        self,
        text: str,
        start: int,
        target_end: int,
        chinese_punctuation: set,
        english_punctuation: set,
        paragraph_separators: set,
        space_separator: str
    ) -> int:
        """寻找最佳分割点
        
        优先级：
        1. 中文标点符号（。？！；）
        2. 英文句子结束符（. ? ! ;）
        3. 段落分隔符（\n\n 或 \n）
        4. 空格
        5. 如果都找不到，强制在 target_end + chunk_overlap 处分割
        
        Args:
            text: 完整文本
            start: 当前块起始位置
            target_end: 目标结束位置
            chinese_punctuation: 中文标点符号集合
            english_punctuation: 英文标点符号集合
            paragraph_separators: 段落分隔符集合
            space_separator: 空格分隔符
            
        Returns:
            int: 实际分割位置
        """
        # 定义搜索窗口：在 target_end 前后搜索
        # 向前搜索范围：最多到 chunk_overlap 距离
        # 向后搜索范围：最多到 chunk_overlap 距离（用于超大段落强制分割）
        search_start = max(start, target_end - self.chunk_overlap)
        search_end = min(len(text), target_end + self.chunk_overlap)
        
        # 1. 优先寻找中文标点符号
        best_pos = self._find_punctuation_backward(
            text, search_start, target_end, chinese_punctuation
        )
        if best_pos is not None:
            return best_pos
        
        # 2. 寻找英文句子结束符
        best_pos = self._find_punctuation_backward(
            text, search_start, target_end, english_punctuation
        )
        if best_pos is not None:
            return best_pos
        
        # 3. 寻找段落分隔符（双换行优先）
        for separator in ['\n\n', '\n']:
            pos = text.rfind(separator, search_start, target_end)
            if pos != -1:
                # 分割点在分隔符之后
                return pos + len(separator)
        
        # 4. 寻找空格
        pos = text.rfind(space_separator, search_start, target_end)
        if pos != -1:
            # 分割点在空格之后
            return pos + 1
        
        # 5. 如果都找不到，强制分割
        # 允许超出 chunk_size，但不超过 chunk_size + chunk_overlap
        return search_end
    
    def _find_punctuation_backward(
        self,
        text: str,
        search_start: int,
        target_end: int,
        punctuation_set: set
    ) -> Optional[int]:
        """从目标位置向前查找标点符号
        
        Args:
            text: 完整文本
            search_start: 搜索起始位置
            target_end: 目标结束位置
            punctuation_set: 标点符号集合
            
        Returns:
            Optional[int]: 找到的分割位置（标点符号之后），未找到返回 None
        """
        # 从 target_end 向前搜索
        for i in range(target_end - 1, search_start - 1, -1):
            if text[i] in punctuation_set:
                # 分割点在标点符号之后
                return i + 1
        return None
    
    def _chunk_paragraph(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """段落分块策略
        
        优先在段落边界处分割，识别 Markdown 标题和代码块
        
        Args:
            text: 输入文本
            metadata: 文档元数据
            
        Returns:
            List[TextChunk]: 文本块列表
        """
        logger.info(f"使用 PARAGRAPH 分块策略处理文本，长度: {len(text)}")
        
        # 解析文本为段落单元（包括标题、代码块、普通段落）
        units = self._parse_text_units(text)
        
        chunks = []
        chunk_index = 0
        current_chunk_content = []
        current_chunk_length = 0
        current_chunk_start = 0
        
        for unit in units:
            unit_content = unit['content']
            unit_length = len(unit_content)
            unit_type = unit['type']
            
            # 如果是代码块或标题，且当前块不为空，检查是否需要先输出当前块
            if unit_type in ['heading', 'code_block']:
                # 如果当前块加上这个单元会超出大小，先输出当前块
                if current_chunk_content and current_chunk_length + unit_length > self.chunk_size:
                    chunk = self._create_chunk(
                        ''.join(current_chunk_content),
                        chunk_index,
                        current_chunk_start,
                        metadata
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    
                    # 重置当前块，考虑重叠
                    overlap_content = self._get_overlap_content(current_chunk_content, current_chunk_length)
                    current_chunk_content = [overlap_content] if overlap_content else []
                    current_chunk_length = len(overlap_content) if overlap_content else 0
                    current_chunk_start = unit['start'] - current_chunk_length
            
            # 如果单个单元超过 chunk_size，需要强制分割
            if unit_length > self.chunk_size:
                # 先输出当前累积的内容
                if current_chunk_content:
                    chunk = self._create_chunk(
                        ''.join(current_chunk_content),
                        chunk_index,
                        current_chunk_start,
                        metadata
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk_content = []
                    current_chunk_length = 0
                
                # 对超大单元使用 SMART 策略分割
                logger.debug(f"单元过大 ({unit_length} 字符)，使用 SMART 策略分割")
                sub_chunks = self._chunk_smart(unit_content, metadata)
                for sub_chunk in sub_chunks:
                    sub_chunk.chunk_index = chunk_index
                    sub_chunk.metadata['strategy'] = self.strategy.value
                    sub_chunk.metadata['start_pos'] = unit['start'] + sub_chunk.metadata.get('start_pos', 0)
                    chunks.append(sub_chunk)
                    chunk_index += 1
                
                current_chunk_start = unit['end']
                continue
            
            # 检查添加这个单元是否会超出 chunk_size
            if current_chunk_content and current_chunk_length + unit_length > self.chunk_size:
                # 输出当前块
                chunk = self._create_chunk(
                    ''.join(current_chunk_content),
                    chunk_index,
                    current_chunk_start,
                    metadata
                )
                chunks.append(chunk)
                chunk_index += 1
                
                # 重置当前块，考虑重叠
                overlap_content = self._get_overlap_content(current_chunk_content, current_chunk_length)
                current_chunk_content = [overlap_content] if overlap_content else []
                current_chunk_length = len(overlap_content) if overlap_content else 0
                current_chunk_start = unit['start'] - current_chunk_length
            
            # 添加当前单元到块中
            current_chunk_content.append(unit_content)
            current_chunk_length += unit_length
        
        # 输出最后一个块
        if current_chunk_content:
            chunk = self._create_chunk(
                ''.join(current_chunk_content),
                chunk_index,
                current_chunk_start,
                metadata
            )
            chunks.append(chunk)
        
        logger.info(f"PARAGRAPH 策略分块完成，生成 {len(chunks)} 个块")
        return chunks
    
    def _parse_text_units(self, text: str) -> List[Dict[str, Any]]:
        """解析文本为单元列表（标题、代码块、段落）
        
        Args:
            text: 输入文本
            
        Returns:
            List[Dict]: 单元列表，每个单元包含 type, content, start, end
        """
        units = []
        lines = text.split('\n')
        i = 0
        current_pos = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检查是否是 Markdown 标题
            if line.strip().startswith('#'):
                # 标题单独作为一个单元
                heading_content = line + '\n'
                start_pos = current_pos
                units.append({
                    'type': 'heading',
                    'content': heading_content,
                    'start': start_pos,
                    'end': start_pos + len(heading_content)
                })
                current_pos += len(heading_content)
                i += 1
                continue
            
            # 检查是否是代码块开始（```）
            if line.strip().startswith('```'):
                # 收集整个代码块
                code_lines = [line]
                start_pos = current_pos
                current_pos += len(line) + 1  # +1 for newline
                i += 1
                
                # 查找代码块结束
                while i < len(lines):
                    code_line = lines[i]
                    code_lines.append(code_line)
                    current_pos += len(code_line) + 1
                    
                    if code_line.strip().startswith('```'):
                        # 找到结束标记
                        i += 1
                        break
                    i += 1
                
                code_content = '\n'.join(code_lines) + '\n'
                units.append({
                    'type': 'code_block',
                    'content': code_content,
                    'start': start_pos,
                    'end': current_pos
                })
                continue
            
            # 检查是否是缩进代码块（4个空格或1个tab）
            if line.startswith('    ') or line.startswith('\t'):
                # 收集连续的缩进行
                code_lines = [line]
                start_pos = current_pos
                current_pos += len(line) + 1
                i += 1
                
                while i < len(lines):
                    next_line = lines[i]
                    # 空行或继续缩进
                    if not next_line.strip() or next_line.startswith('    ') or next_line.startswith('\t'):
                        code_lines.append(next_line)
                        current_pos += len(next_line) + 1
                        i += 1
                    else:
                        break
                
                code_content = '\n'.join(code_lines) + '\n'
                units.append({
                    'type': 'code_block',
                    'content': code_content,
                    'start': start_pos,
                    'end': current_pos
                })
                continue
            
            # 普通段落：收集连续的非空行
            if line.strip():
                para_lines = [line]
                start_pos = current_pos
                current_pos += len(line) + 1
                i += 1
                
                # 收集连续的非空行，直到遇到空行、标题或代码块
                while i < len(lines):
                    next_line = lines[i]
                    
                    # 遇到空行、标题或代码块，停止
                    if (not next_line.strip() or 
                        next_line.strip().startswith('#') or 
                        next_line.strip().startswith('```') or
                        next_line.startswith('    ') or 
                        next_line.startswith('\t')):
                        break
                    
                    para_lines.append(next_line)
                    current_pos += len(next_line) + 1
                    i += 1
                
                para_content = '\n'.join(para_lines) + '\n'
                units.append({
                    'type': 'paragraph',
                    'content': para_content,
                    'start': start_pos,
                    'end': current_pos
                })
                continue
            
            # 空行，跳过
            current_pos += len(line) + 1
            i += 1
        
        return units
    
    def _get_overlap_content(self, chunk_content: List[str], chunk_length: int) -> str:
        """从当前块内容中提取重叠部分
        
        Args:
            chunk_content: 当前块的内容列表
            chunk_length: 当前块的总长度
            
        Returns:
            str: 重叠内容
        """
        if chunk_length <= self.chunk_overlap:
            return ''.join(chunk_content)
        
        # 从末尾提取 chunk_overlap 长度的内容
        full_content = ''.join(chunk_content)
        return full_content[-self.chunk_overlap:]
    
    def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        start_pos: int,
        metadata: Dict[str, Any]
    ) -> TextChunk:
        """创建 TextChunk 对象
        
        Args:
            content: 块内容
            chunk_index: 块序号
            start_pos: 起始位置
            metadata: 元数据
            
        Returns:
            TextChunk: 文本块对象
        """
        return TextChunk(
            content=content,
            chunk_index=chunk_index,
            page_number=metadata.get("page_number"),
            metadata={
                **metadata,
                "start_pos": start_pos,
                "end_pos": start_pos + len(content),
                "strategy": self.strategy.value,
            }
        )
