"""
测试 DocumentChunker 的 SIMPLE 策略实现

验证需求:
- 2.1: 按照配置的块大小（默认 500 字符）进行分割
- 2.2: 在相邻块之间保留重叠区域（默认 50 字符）
- 2.8: 为每个块生成序号和元数据
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.document_processing import DocumentChunker, ChunkStrategy


def test_simple_chunking_basic():
    """测试基本的固定大小分块"""
    print("\n=== 测试 1: 基本固定大小分块 ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20, strategy=ChunkStrategy.SIMPLE)
    
    # 创建一个 150 字符的文本
    text = "A" * 150
    
    chunks = chunker.chunk(text)
    
    print(f"输入文本长度: {len(text)}")
    print(f"分块数量: {len(chunks)}")
    
    # 验证分块数量（应该是 2 块）
    assert len(chunks) == 2, f"期望 2 个分块，实际得到 {len(chunks)}"
    
    # 验证第一个块
    assert len(chunks[0].content) == 100, f"第一个块长度应为 100，实际为 {len(chunks[0].content)}"
    assert chunks[0].chunk_index == 0, "第一个块的序号应为 0"
    
    # 验证第二个块
    assert len(chunks[1].content) == 70, f"第二个块长度应为 70，实际为 {len(chunks[1].content)}"
    assert chunks[1].chunk_index == 1, "第二个块的序号应为 1"
    
    # 验证重叠区域（第一个块的最后 20 个字符应该等于第二个块的前 20 个字符）
    overlap_from_first = chunks[0].content[-20:]
    overlap_from_second = chunks[1].content[:20]
    assert overlap_from_first == overlap_from_second, "重叠区域不匹配"
    
    print("✓ 基本分块测试通过")


def test_simple_chunking_no_overlap_needed():
    """测试文本长度刚好等于 chunk_size 的情况"""
    print("\n=== 测试 2: 文本长度等于 chunk_size ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20, strategy=ChunkStrategy.SIMPLE)
    
    text = "B" * 100
    chunks = chunker.chunk(text)
    
    print(f"输入文本长度: {len(text)}")
    print(f"分块数量: {len(chunks)}")
    
    # 应该只有 1 个块
    assert len(chunks) == 1, f"期望 1 个分块，实际得到 {len(chunks)}"
    assert len(chunks[0].content) == 100, "块长度应为 100"
    assert chunks[0].chunk_index == 0, "块序号应为 0"
    
    print("✓ 单块测试通过")


def test_simple_chunking_small_text():
    """测试文本长度小于 chunk_size 的情况"""
    print("\n=== 测试 3: 文本长度小于 chunk_size ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20, strategy=ChunkStrategy.SIMPLE)
    
    text = "C" * 50
    chunks = chunker.chunk(text)
    
    print(f"输入文本长度: {len(text)}")
    print(f"分块数量: {len(chunks)}")
    
    # 应该只有 1 个块
    assert len(chunks) == 1, f"期望 1 个分块，实际得到 {len(chunks)}"
    assert len(chunks[0].content) == 50, "块长度应为 50"
    assert chunks[0].chunk_index == 0, "块序号应为 0"
    
    print("✓ 小文本测试通过")


def test_simple_chunking_multiple_chunks():
    """测试多个分块的情况"""
    print("\n=== 测试 4: 多个分块 ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20, strategy=ChunkStrategy.SIMPLE)
    
    # 创建一个 350 字符的文本
    text = "D" * 350
    chunks = chunker.chunk(text)
    
    print(f"输入文本长度: {len(text)}")
    print(f"分块数量: {len(chunks)}")
    
    # 验证分块数量
    # 第 1 块: 0-100 (100 字符)
    # 第 2 块: 80-180 (100 字符)
    # 第 3 块: 160-260 (100 字符)
    # 第 4 块: 240-340 (100 字符)
    # 第 5 块: 320-350 (30 字符)
    assert len(chunks) == 5, f"期望 5 个分块，实际得到 {len(chunks)}"
    
    # 验证序号连续性
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i, f"块 {i} 的序号不正确"
    
    # 验证每个块的长度
    assert len(chunks[0].content) == 100
    assert len(chunks[1].content) == 100
    assert len(chunks[2].content) == 100
    assert len(chunks[3].content) == 100
    assert len(chunks[4].content) == 30
    
    # 验证相邻块的重叠
    for i in range(len(chunks) - 1):
        overlap_from_current = chunks[i].content[-20:]
        overlap_from_next = chunks[i + 1].content[:20]
        assert overlap_from_current == overlap_from_next, f"块 {i} 和块 {i+1} 的重叠区域不匹配"
    
    print("✓ 多块测试通过")


def test_simple_chunking_metadata():
    """测试元数据传递"""
    print("\n=== 测试 5: 元数据传递 ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20, strategy=ChunkStrategy.SIMPLE)
    
    text = "E" * 150
    metadata = {"page_number": 5, "document_id": 123}
    
    chunks = chunker.chunk(text, metadata)
    
    # 验证元数据被正确传递
    for chunk in chunks:
        assert chunk.page_number == 5, "page_number 未正确传递"
        assert chunk.metadata.get("document_id") == 123, "document_id 未正确传递"
        assert chunk.metadata.get("strategy") == "simple", "strategy 未正确记录"
        assert "start_pos" in chunk.metadata, "start_pos 未记录"
        assert "end_pos" in chunk.metadata, "end_pos 未记录"
    
    print("✓ 元数据测试通过")


def test_simple_chunking_empty_text():
    """测试空文本"""
    print("\n=== 测试 6: 空文本 ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20, strategy=ChunkStrategy.SIMPLE)
    
    chunks = chunker.chunk("")
    
    # 空文本应该返回空列表
    assert len(chunks) == 0, "空文本应返回空列表"
    
    print("✓ 空文本测试通过")


def test_default_parameters():
    """测试默认参数（chunk_size=500, chunk_overlap=50）"""
    print("\n=== 测试 7: 默认参数 ===")
    
    chunker = DocumentChunker()  # 使用默认参数
    
    # 创建一个 1000 字符的文本
    text = "F" * 1000
    chunks = chunker.chunk(text)
    
    print(f"输入文本长度: {len(text)}")
    print(f"分块数量: {len(chunks)}")
    
    # 验证使用默认参数
    # 第 1 块: 0-500 (500 字符)
    # 第 2 块: 450-950 (500 字符)
    # 第 3 块: 900-1000 (100 字符)
    assert len(chunks) == 3, f"期望 3 个分块，实际得到 {len(chunks)}"
    
    assert len(chunks[0].content) == 500
    assert len(chunks[1].content) == 500
    assert len(chunks[2].content) == 100
    
    # 验证重叠区域（50 字符）
    overlap_0_1 = chunks[0].content[-50:]
    overlap_1_start = chunks[1].content[:50]
    assert overlap_0_1 == overlap_1_start, "块 0 和块 1 的重叠区域不匹配"
    
    print("✓ 默认参数测试通过")


def test_chinese_text():
    """测试中文文本分块"""
    print("\n=== 测试 8: 中文文本 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SIMPLE)
    
    # 创建一个中文文本（每个汉字算 1 个字符）
    text = "这是一个测试文本。" * 10  # 实际是 90 个字符
    
    chunks = chunker.chunk(text)
    
    print(f"输入文本长度: {len(text)}")
    print(f"分块数量: {len(chunks)}")
    
    # 验证分块
    # 第 1 块: 0-50 (50 字符)
    # 第 2 块: 40-90 (50 字符)
    assert len(chunks) == 2, f"期望 2 个分块，实际得到 {len(chunks)}"
    
    # 验证每个块的长度不超过 chunk_size
    for i, chunk in enumerate(chunks):
        assert len(chunk.content) <= 50, f"块 {i} 长度超过 chunk_size"
    
    print("✓ 中文文本测试通过")


if __name__ == "__main__":
    print("开始测试 DocumentChunker SIMPLE 策略...")
    
    try:
        test_simple_chunking_basic()
        test_simple_chunking_no_overlap_needed()
        test_simple_chunking_small_text()
        test_simple_chunking_multiple_chunks()
        test_simple_chunking_metadata()
        test_simple_chunking_empty_text()
        test_default_parameters()
        test_chinese_text()
        
        print("\n" + "=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
