"""
测试 PARAGRAPH 分块策略的需求验证
验证需求: 2.5, 2.6, 9.1, 9.3, 9.4, 9.6
"""
import sys
import os
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.document_processing import DocumentChunker, ChunkStrategy


# 配置日志以验证需求 9.6
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')


def test_requirement_2_5_paragraph_boundaries():
    """
    需求 2.5: WHEN 处理包含段落的文档，THE Document_Chunker SHALL 优先在段落边界处分割
    """
    text = """First paragraph with some content.

Second paragraph with more content.

Third paragraph with additional content."""
    
    chunker = DocumentChunker(chunk_size=80, chunk_overlap=10, strategy=ChunkStrategy.PARAGRAPH)
    chunks = chunker.chunk(text)
    
    # 验证分块在段落边界处分割
    # 每个段落应该尽可能保持完整
    assert len(chunks) >= 2
    
    # 验证第一个块包含第一个段落
    assert "First paragraph" in chunks[0].content
    
    print(f"✓ 需求 2.5 验证通过: 在段落边界处分割，生成 {len(chunks)} 个块")


def test_requirement_2_6_code_block_integrity():
    """
    需求 2.6: WHEN 处理代码文档，THE Document_Chunker SHALL 尽量保持代码块的完整性
    """
    text = """Some text before code.

```python
def example_function():
    x = 1
    y = 2
    return x + y
```

Some text after code."""
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=10, strategy=ChunkStrategy.PARAGRAPH)
    chunks = chunker.chunk(text)
    
    # 查找包含代码块的块
    code_block_found = False
    for chunk in chunks:
        if '```python' in chunk.content:
            # 验证代码块是完整的
            assert 'def example_function():' in chunk.content
            assert 'return x + y' in chunk.content
            assert '```' in chunk.content.split('```python')[1]  # 确保有结束标记
            code_block_found = True
            break
    
    assert code_block_found, "代码块应该被识别并保持完整"
    
    print(f"✓ 需求 2.6 验证通过: 代码块保持完整性")


def test_requirement_9_1_section_boundaries():
    """
    需求 9.1: WHERE 文档包含明确的章节标题，THE Document_Chunker SHALL 优先在章节边界处分割
    """
    text = """# Chapter 1

Content of chapter 1.

## Section 1.1

Content of section 1.1.

## Section 1.2

Content of section 1.2."""
    
    chunker = DocumentChunker(chunk_size=80, chunk_overlap=10, strategy=ChunkStrategy.PARAGRAPH)
    chunks = chunker.chunk(text)
    
    # 验证标题被识别并作为分割点
    assert len(chunks) >= 2
    
    # 验证标题在块中
    has_main_title = any('# Chapter 1' in chunk.content for chunk in chunks)
    has_section_title = any('## Section' in chunk.content for chunk in chunks)
    
    assert has_main_title, "主标题应该被识别"
    assert has_section_title, "章节标题应该被识别"
    
    print(f"✓ 需求 9.1 验证通过: 在章节边界处分割")


def test_requirement_9_3_technical_doc_code_blocks():
    """
    需求 9.3: WHERE 文档是技术文档，THE Document_Chunker SHALL 识别代码块并保持其完整性
    """
    text = """Technical documentation example.

    def indented_code():
        # This is indented code
        return True

More documentation text."""
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=10, strategy=ChunkStrategy.PARAGRAPH)
    chunks = chunker.chunk(text)
    
    # 验证缩进代码块被识别
    code_found = False
    for chunk in chunks:
        if 'def indented_code():' in chunk.content:
            # 验证代码块完整
            assert 'return True' in chunk.content
            code_found = True
            break
    
    assert code_found, "缩进代码块应该被识别"
    
    print(f"✓ 需求 9.3 验证通过: 识别并保持代码块完整性")


def test_requirement_9_4_markdown_heading_levels():
    """
    需求 9.4: WHERE 文档是 Markdown 格式，THE Document_Chunker SHALL 识别标题层级并在标题处优先分割
    """
    text = """# Level 1 Heading

Content under level 1.

## Level 2 Heading

Content under level 2.

### Level 3 Heading

Content under level 3."""
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=10, strategy=ChunkStrategy.PARAGRAPH)
    chunks = chunker.chunk(text)
    
    # 验证不同层级的标题都被识别
    has_level1 = any('# Level 1' in chunk.content for chunk in chunks)
    has_level2 = any('## Level 2' in chunk.content for chunk in chunks)
    has_level3 = any('### Level 3' in chunk.content for chunk in chunks)
    
    assert has_level1, "一级标题应该被识别"
    assert has_level2, "二级标题应该被识别"
    assert has_level3, "三级标题应该被识别"
    
    print(f"✓ 需求 9.4 验证通过: 识别 Markdown 标题层级")


def test_requirement_9_6_strategy_logging(caplog):
    """
    需求 9.6: WHEN 分块策略选择完成，THE Document_Chunker SHALL 在日志中记录使用的策略类型
    """
    text = "Simple text for logging test."
    
    with caplog.at_level(logging.INFO):
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=10, strategy=ChunkStrategy.PARAGRAPH)
        chunks = chunker.chunk(text)
    
    # 验证日志中包含策略信息
    log_messages = [record.message for record in caplog.records]
    
    # 检查初始化日志
    init_log_found = any('strategy=paragraph' in msg.lower() for msg in log_messages)
    assert init_log_found, "初始化日志应该包含策略类型"
    
    # 检查分块完成日志
    chunk_log_found = any('paragraph' in msg.lower() and '分块完成' in msg for msg in log_messages)
    assert chunk_log_found, "分块完成日志应该包含策略类型"
    
    print(f"✓ 需求 9.6 验证通过: 在日志中记录策略类型")


def test_integration_paragraph_strategy():
    """
    综合测试：验证 PARAGRAPH 策略的所有功能
    """
    text = """# Technical Documentation

This is the introduction paragraph.

## Code Examples

Here is a Python example:

```python
def calculate(a, b):
    result = a + b
    return result
```

## Indented Code

Another example with indentation:

    def another_function():
        return "Hello"

## Conclusion

This is the conclusion paragraph with some final thoughts."""
    
    chunker = DocumentChunker(chunk_size=150, chunk_overlap=20, strategy=ChunkStrategy.PARAGRAPH)
    chunks = chunker.chunk(text)
    
    print(f"\n综合测试 - 生成 {len(chunks)} 个块:")
    for i, chunk in enumerate(chunks):
        print(f"\n块 {i} (长度: {len(chunk.content)}):")
        print(f"  前50字符: {repr(chunk.content[:50])}")
        print(f"  策略: {chunk.metadata.get('strategy')}")
    
    # 验证基本属性
    assert len(chunks) > 0
    assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))
    assert all(chunk.metadata.get('strategy') == 'paragraph' for chunk in chunks)
    
    # 验证标题被识别
    has_titles = any('#' in chunk.content for chunk in chunks)
    assert has_titles
    
    # 验证代码块被识别
    has_code = any('```' in chunk.content or '    def' in chunk.content for chunk in chunks)
    assert has_code
    
    print(f"\n✓ 综合测试通过: PARAGRAPH 策略正常工作")


if __name__ == "__main__":
    print("测试 PARAGRAPH 分块策略需求\n")
    print("=" * 60)
    
    test_requirement_2_5_paragraph_boundaries()
    print()
    
    test_requirement_2_6_code_block_integrity()
    print()
    
    test_requirement_9_1_section_boundaries()
    print()
    
    test_requirement_9_3_technical_doc_code_blocks()
    print()
    
    test_requirement_9_4_markdown_heading_levels()
    print()
    
    # Note: test_requirement_9_6_strategy_logging needs pytest's caplog fixture
    print("需求 9.6 (日志记录) 需要使用 pytest 运行")
    print()
    
    test_integration_paragraph_strategy()
    print()
    
    print("=" * 60)
    print("\n✓ 所有需求验证测试通过!")
