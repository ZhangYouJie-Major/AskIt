"""
独立测试 DocumentChunker 的 SMART 策略实现
不依赖 app.services 的初始化
"""
import sys
import os
from pathlib import Path

# 添加 backend 目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# 使用 importlib 直接加载模块，避免触发 __init__.py
import importlib.util

# 加载 types 模块
types_path = backend_dir / "app" / "services" / "document_processing" / "types.py"
spec = importlib.util.spec_from_file_location("types_module", types_path)
types_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(types_module)

ChunkStrategy = types_module.ChunkStrategy
TextChunk = types_module.TextChunk

# 加载 chunker 模块
chunker_path = backend_dir / "app" / "services" / "document_processing" / "chunker.py"
spec = importlib.util.spec_from_file_location("chunker_module", chunker_path)
chunker_module = importlib.util.module_from_spec(spec)

# 注入依赖
sys.modules['app.services.document_processing.types'] = types_module
spec.loader.exec_module(chunker_module)

DocumentChunker = chunker_module.DocumentChunker


def test_smart_english_sentence():
    """测试英文句子边界分割 - 需求 2.3"""
    print("\n=== 测试 1: 英文句子边界分割 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "This is the first sentence. This is the second sentence. This is the third sentence."
    chunks = chunker.chunk(text)
    
    print(f"输入: {text}")
    print(f"分块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  块{i}: len={len(chunk.content)}, '{chunk.content[:40]}...'")
    
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.content) <= 60  # chunk_size + chunk_overlap
    
    print("✓ 通过")


def test_smart_chinese_punctuation():
    """测试中文标点符号优先分割 - 需求 2.4"""
    print("\n=== 测试 2: 中文标点符号优先分割 ===")
    
    chunker = DocumentChunker(chunk_size=30, chunk_overlap=5, strategy=ChunkStrategy.SMART)
    
    text = "这是第一个句子。这是第二个句子？这是第三个句子！这是第四个句子；这是第五个句子。"
    chunks = chunker.chunk(text)
    
    print(f"输入: {text}")
    print(f"分块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  块{i}: len={len(chunk.content)}, '{chunk.content}'")
    
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.content) <= 35  # chunk_size + chunk_overlap
    
    print("✓ 通过")


def test_smart_force_split():
    """测试超大段落强制分割 - 需求 2.7"""
    print("\n=== 测试 3: 超大段落强制分割 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    # 没有任何分隔符的长文本
    text = "A" * 200
    chunks = chunker.chunk(text)
    
    print(f"输入长度: {len(text)}")
    print(f"分块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  块{i}: len={len(chunk.content)}")
    
    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk.content) <= 60  # chunk_size + chunk_overlap
    
    # 验证重叠
    for i in range(len(chunks) - 1):
        overlap1 = chunks[i].content[-10:]
        overlap2 = chunks[i + 1].content[:10]
        assert overlap1 == overlap2, f"块{i}和块{i+1}重叠不匹配"
    
    print("✓ 通过")


def test_smart_space_boundary():
    """测试空格边界分割 - 需求 2.3"""
    print("\n=== 测试 4: 空格边界分割 ===")
    
    chunker = DocumentChunker(chunk_size=40, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12"
    chunks = chunker.chunk(text)
    
    print(f"输入: {text}")
    print(f"分块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  块{i}: '{chunk.content}'")
    
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.content) <= 50
    
    print("✓ 通过")


def test_smart_paragraph_boundary():
    """测试段落边界分割 - 需求 2.3"""
    print("\n=== 测试 5: 段落边界分割 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunker.chunk(text)
    
    print(f"输入长度: {len(text)}")
    print(f"分块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  块{i}: len={len(chunk.content)}")
    
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.content) <= 60
    
    print("✓ 通过")


def test_smart_mixed_text():
    """测试中英文混合 - 需求 2.3, 2.4"""
    print("\n=== 测试 6: 中英文混合 ===")
    
    chunker = DocumentChunker(chunk_size=60, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "这是中文句子。This is English. 另一个中文！Another one?"
    chunks = chunker.chunk(text)
    
    print(f"输入: {text}")
    print(f"分块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  块{i}: '{chunk.content}'")
    
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.content) <= 70
    
    print("✓ 通过")


def test_smart_metadata():
    """测试元数据传递"""
    print("\n=== 测试 7: 元数据传递 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "First. Second. Third."
    metadata = {"page_number": 3, "doc_id": 123}
    chunks = chunker.chunk(text, metadata)
    
    for chunk in chunks:
        assert chunk.page_number == 3
        assert chunk.metadata.get("doc_id") == 123
        assert chunk.metadata.get("strategy") == "smart"
        assert "start_pos" in chunk.metadata
        assert "end_pos" in chunk.metadata
    
    print("✓ 通过")


def test_smart_sequence():
    """测试序号连续性"""
    print("\n=== 测试 8: 序号连续性 ===")
    
    chunker = DocumentChunker(chunk_size=40, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "One. Two. Three. Four. Five. Six. Seven. Eight."
    chunks = chunker.chunk(text)
    
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i, f"期望序号{i}，实际{chunk.chunk_index}"
    
    print("✓ 通过")


def test_smart_empty():
    """测试空文本"""
    print("\n=== 测试 9: 空文本 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    chunks = chunker.chunk("")
    assert len(chunks) == 0
    
    print("✓ 通过")


def test_smart_short_text():
    """测试短文本（小于chunk_size）"""
    print("\n=== 测试 10: 短文本 ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    text = "Short text."
    chunks = chunker.chunk(text)
    
    assert len(chunks) == 1
    assert chunks[0].content == text
    assert chunks[0].chunk_index == 0
    
    print("✓ 通过")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 DocumentChunker SMART 策略")
    print("=" * 60)
    
    try:
        test_smart_english_sentence()
        test_smart_chinese_punctuation()
        test_smart_force_split()
        test_smart_space_boundary()
        test_smart_paragraph_boundary()
        test_smart_mixed_text()
        test_smart_metadata()
        test_smart_sequence()
        test_smart_empty()
        test_smart_short_text()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
