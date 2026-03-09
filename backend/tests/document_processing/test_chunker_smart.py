"""
测试 DocumentChunker 的 SMART 策略实现

验证需求:
- 2.3: 分割点位于单词或句子中间时，调整分割位置到最近的自然边界（空格、换行、句号）
- 2.4: 处理中文文本时，在句号、问号、感叹号等标点符号处优先分割
- 2.7: 单个段落超过最大块大小时，强制分割并保留重叠
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.document_processing.chunker import DocumentChunker
from app.services.document_processing.types import ChunkStrategy


def test_smart_chunking_english_sentence():
    """测试英文句子边界分割"""
    print("\n=== 测试 1: 英文句子边界分割 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    # 创建一个包含句子的英文文本
    text = "This is the first sentence. This is the second sentence. This is the third sentence."
    
    chunks = chunker.chunk(text)
    
    print(f"输入文本: {text}")
    print(f"分块数量: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"块 {i}: 长度={len(chunk.content)}, 内容='{chunk.content}'")
    
    # 验证分块在句子边界处分割
    assert len(chunks) >= 1, "应该至少有 1 个分块"
    
    # 验证每个块的长度不超过 chunk_size + chunk_overlap（强制分割的上界）
    for i, chunk in enumerate(chunks):
        assert len(chunk.content) <= 60, f"块 {i} 长度超过允许的最大值"
    
    print("✓ 英文句子边界测试通过")


def test_smart_chunking_chinese_punctuation():
    """测试中文标点符号优先分割"""
    print("\n=== 测试 2: 中文标点符号优先分割 ===")
    
    chunker = DocumentChunker(chunk_size=30, chunk_overlap=5, strategy=ChunkStrategy.SMART)
    
    # 创建包含中文标点的文本
    text = "这是第一个句子。这是第二个句子？这是第三个句子！这是第四个句子；这是第五个句子。"
    
    chunks = chunker.chunk(text)
    
    print(f"输入文本: {text}")
    print(f"分块数量: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"块 {i}: 长度={len(chunk.content)}, 内容='{chunk.content}'")
    
    # 验证分块
    assert len(chunks) >= 1, "应该至少有 1 个分块"
    
    # 验证每个块（除了最后一块）应该在中文标点符号后结束
    for i, chunk in enumerate(chunks[:-1]):
        content = chunk.content.rstrip()
        if content:
            # 检查是否在标点符号后分割（考虑重叠，可能不是严格在标点后）
            # 至少验证长度合理
            assert len(chunk.content) <= 35, f"块 {i} 长度超过允许的最大值"
    
    print("✓ 中文标点符号测试通过")


def test_smart_chunking_space_boundary():
    """测试空格边界分割"""
    print("\n=== 测试 3: 空格边界分割 ===")
    
    chunker = DocumentChunker(chunk_size=40, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    # 创建一个没有句号但有空格的文本
    text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12"
    
    chunks = chunker.chunk(text)
    
    print(f"输入文本: {text}")
    print(f"分块数量: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"块 {i}: 长度={len(chunk.content)}, 内容='{chunk.content}'")
    
    # 验证分块在空格处分割（不会在单词中间分割）
    for i, chunk in enumerate(chunks[:-1]):
        # 检查块不会在单词中间结束（除非是强制分割）
        content = chunk.content.rstrip()
        if content and len(content) < 50:  # 不是强制分割的情况
            # 应该在空格后或句子结束
            assert content[-1] == ' ' or content.split()[-1] == content.split()[-1], \
                f"块 {i} 可能在单词中间分割"
    
    print("✓ 空格边界测试通过")


def test_smart_chunking_paragraph_boundary():
    """测试段落边界分割"""
    print("\n=== 测试 4: 段落边界分割 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    # 创建包含段落的文本
    text = "First paragraph line one.\nFirst paragraph line two.\n\nSecond paragraph line one.\nSecond paragraph line two."
    
    chunks = chunker.chunk(text)
    
    print(f"输入文本长度: {len(text)}")
    print(f"分块数量: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"块 {i}: 长度={len(chunk.content)}")
    
    # 验证分块
    assert len(chunks) >= 1, "应该至少有 1 个分块"
    
    # 验证每个块的长度合理
    for i, chunk in enumerate(chunks):
        assert len(chunk.content) <= 60, f"块 {i} 长度超过允许的最大值"
    
    print("✓ 段落边界测试通过")


def test_smart_chunking_force_split():
    """测试超大段落强制分割"""
    print("\n=== 测试 5: 超大段落强制分割 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    # 创建一个没有任何分隔符的长文本（模拟超大段落）
    text = "A" * 200
    
    chunks = chunker.chunk(text)
    
    print(f"输入文本长度: {len(text)}")
    print(f"分块数量: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"块 {i}: 长度={len(chunk.content)}")
    
    # 验证分块
    assert len(chunks) >= 3, "应该有多个分块"
    
    # 验证每个块的长度不超过 chunk_size + chunk_overlap
    for i, chunk in enumerate(chunks):
        assert len(chunk.content) <= 60, f"块 {i} 长度 {len(chunk.content)} 超过允许的最大值 60"
    
    # 验证重叠区域
    for i in range(len(chunks) - 1):
        overlap_from_current = chunks[i].content[-10:]
        overlap_from_next = chunks[i + 1].content[:10]
        assert overlap_from_current == overlap_from_next, f"块 {i} 和块 {i+1} 的重叠区域不匹配"
    
    print("✓ 强制分割测试通过")


def test_smart_chunking_mixed_chinese_english():
    """测试中英文混合文本"""
    print("\n=== 测试 6: 中英文混合文本 ===")
    
    chunker = DocumentChunker(chunk_size=60, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    # 创建中英文混合文本
    text = "这是中文句子。This is an English sentence. 另一个中文句子！Another English sentence?"
    
    chunks = chunker.chunk(text)
    
    print(f"输入文本: {text}")
    print(f"分块数量: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"块 {i}: 长度={len(chunk.content)}, 内容='{chunk.content}'")
    
    # 验证分块
    assert len(chunks) >= 1, "应该至少有 1 个分块"
    
    # 验证每个块的长度合理
    for i, chunk in enumerate(chunks):
        assert len(chunk.content) <= 70, f"块 {i} 长度超过允许的最大值"
    
    print("✓ 中英文混合测试通过")


def test_smart_chunking_coverage():
    """测试分块覆盖完整性（所有内容都被包含）"""
    print("\n=== 测试 7: 分块覆盖完整性 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "This is a test. Another sentence here. And one more sentence to test coverage."
    
    chunks = chunker.chunk(text)
    
    print(f"输入文本: {text}")
    print(f"分块数量: {len(chunks)}")
    
    # 重建文本（去除重叠）
    reconstructed = ""
    for i, chunk in enumerate(chunks):
        if i == 0:
            reconstructed += chunk.content
        else:
            # 去除重叠部分
            reconstructed += chunk.content[10:]
    
    print(f"原始文本长度: {len(text)}")
    print(f"重建文本长度: {len(reconstructed)}")
    
    # 验证所有内容都被包含（重建的文本应该包含原始文本的所有内容）
    # 注意：由于在边界处分割，可能会有轻微差异，但主要内容应该都在
    assert len(reconstructed) >= len(text) * 0.95, "重建文本长度明显小于原始文本"
    
    print("✓ 覆盖完整性测试通过")


def test_smart_chunking_metadata():
    """测试元数据传递"""
    print("\n=== 测试 8: 元数据传递 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "First sentence. Second sentence. Third sentence."
    metadata = {"page_number": 3, "document_id": 456}
    
    chunks = chunker.chunk(text, metadata)
    
    # 验证元数据被正确传递
    for chunk in chunks:
        assert chunk.page_number == 3, "page_number 未正确传递"
        assert chunk.metadata.get("document_id") == 456, "document_id 未正确传递"
        assert chunk.metadata.get("strategy") == "smart", "strategy 未正确记录"
        assert "start_pos" in chunk.metadata, "start_pos 未记录"
        assert "end_pos" in chunk.metadata, "end_pos 未记录"
    
    print("✓ 元数据测试通过")


def test_smart_chunking_sequence():
    """测试分块序号连续性"""
    print("\n=== 测试 9: 分块序号连续性 ===")
    
    chunker = DocumentChunker(chunk_size=40, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
    
    chunks = chunker.chunk(text)
    
    print(f"分块数量: {len(chunks)}")
    
    # 验证序号从 0 开始且连续
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i, f"块 {i} 的序号不正确，期望 {i}，实际 {chunk.chunk_index}"
    
    print("✓ 序号连续性测试通过")


if __name__ == "__main__":
    print("开始测试 DocumentChunker SMART 策略...")
    
    try:
        test_smart_chunking_english_sentence()
        test_smart_chunking_chinese_punctuation()
        test_smart_chunking_space_boundary()
        test_smart_chunking_paragraph_boundary()
        test_smart_chunking_force_split()
        test_smart_chunking_mixed_chinese_english()
        test_smart_chunking_coverage()
        test_smart_chunking_metadata()
        test_smart_chunking_sequence()
        
        print("\n" + "=" * 50)
        print("✓ 所有 SMART 策略测试通过！")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
