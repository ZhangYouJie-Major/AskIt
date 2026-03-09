"""
验证 DocumentChunker SIMPLE 策略满足需求规范

需求验证:
- 需求 2.1: WHEN 处理通用文本，THE Document_Chunker SHALL 按照配置的块大小（默认 500 字符）进行分割
- 需求 2.2: WHEN 分割文本块，THE Document_Chunker SHALL 在相邻块之间保留重叠区域（默认 50 字符）
- 需求 2.8: WHEN 分块完成，THE Document_Chunker SHALL 为每个块生成序号和元数据
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.document_processing import DocumentChunker, ChunkStrategy


def verify_requirement_2_1():
    """验证需求 2.1: 按照配置的块大小进行分割"""
    print("\n=== 验证需求 2.1: 按照配置的块大小进行分割 ===")
    
    # 测试默认块大小 500
    chunker_default = DocumentChunker()
    text = "X" * 1500
    chunks = chunker_default.chunk(text)
    
    # 验证每个块（除了最后一个）的大小都是 500
    for i, chunk in enumerate(chunks[:-1]):
        assert len(chunk.content) == 500, f"块 {i} 的大小应为 500，实际为 {len(chunk.content)}"
    
    print(f"✓ 默认块大小 500 验证通过，生成 {len(chunks)} 个块")
    
    # 测试自定义块大小
    chunker_custom = DocumentChunker(chunk_size=200, chunk_overlap=20)
    chunks_custom = chunker_custom.chunk(text)
    
    for i, chunk in enumerate(chunks_custom[:-1]):
        assert len(chunk.content) == 200, f"块 {i} 的大小应为 200，实际为 {len(chunk.content)}"
    
    print(f"✓ 自定义块大小 200 验证通过，生成 {len(chunks_custom)} 个块")
    print("✓ 需求 2.1 验证通过")


def verify_requirement_2_2():
    """验证需求 2.2: 在相邻块之间保留重叠区域"""
    print("\n=== 验证需求 2.2: 在相邻块之间保留重叠区域 ===")
    
    # 测试默认重叠大小 50
    chunker_default = DocumentChunker()
    
    # 创建一个可识别的文本模式
    text = ""
    for i in range(30):
        text += f"BLOCK_{i:03d}_" + "X" * 40
    
    chunks = chunker_default.chunk(text)
    
    print(f"生成 {len(chunks)} 个块")
    
    # 验证相邻块之间的重叠
    overlap_count = 0
    for i in range(len(chunks) - 1):
        current_chunk = chunks[i]
        next_chunk = chunks[i + 1]
        
        # 获取当前块的最后 50 个字符
        overlap_from_current = current_chunk.content[-50:]
        # 获取下一个块的前 50 个字符
        overlap_from_next = next_chunk.content[:50]
        
        # 验证重叠区域相同
        assert overlap_from_current == overlap_from_next, \
            f"块 {i} 和块 {i+1} 的重叠区域不匹配"
        
        overlap_count += 1
    
    print(f"✓ 验证了 {overlap_count} 对相邻块的重叠区域（默认 50 字符）")
    
    # 测试自定义重叠大小
    chunker_custom = DocumentChunker(chunk_size=100, chunk_overlap=30)
    chunks_custom = chunker_custom.chunk(text)
    
    overlap_count_custom = 0
    for i in range(len(chunks_custom) - 1):
        overlap_from_current = chunks_custom[i].content[-30:]
        overlap_from_next = chunks_custom[i + 1].content[:30]
        
        assert overlap_from_current == overlap_from_next, \
            f"块 {i} 和块 {i+1} 的重叠区域不匹配（自定义 30 字符）"
        
        overlap_count_custom += 1
    
    print(f"✓ 验证了 {overlap_count_custom} 对相邻块的重叠区域（自定义 30 字符）")
    print("✓ 需求 2.2 验证通过")


def verify_requirement_2_8():
    """验证需求 2.8: 为每个块生成序号和元数据"""
    print("\n=== 验证需求 2.8: 为每个块生成序号和元数据 ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    
    text = "Y" * 500
    metadata = {
        "document_id": 123,
        "filename": "test.txt",
        "page_number": 5,
    }
    
    chunks = chunker.chunk(text, metadata)
    
    print(f"生成 {len(chunks)} 个块")
    
    # 验证序号连续性
    for i, chunk in enumerate(chunks):
        # 验证序号从 0 开始且连续
        assert chunk.chunk_index == i, \
            f"块 {i} 的序号应为 {i}，实际为 {chunk.chunk_index}"
        
        # 验证元数据存在
        assert chunk.metadata is not None, f"块 {i} 缺少元数据"
        
        # 验证传入的元数据被保留
        assert chunk.metadata.get("document_id") == 123, \
            f"块 {i} 的 document_id 不正确"
        assert chunk.metadata.get("filename") == "test.txt", \
            f"块 {i} 的 filename 不正确"
        
        # 验证 page_number 被正确设置
        assert chunk.page_number == 5, \
            f"块 {i} 的 page_number 应为 5，实际为 {chunk.page_number}"
        
        # 验证自动生成的元数据
        assert "start_pos" in chunk.metadata, f"块 {i} 缺少 start_pos"
        assert "end_pos" in chunk.metadata, f"块 {i} 缺少 end_pos"
        assert "strategy" in chunk.metadata, f"块 {i} 缺少 strategy"
        assert chunk.metadata["strategy"] == "simple", \
            f"块 {i} 的 strategy 应为 'simple'"
        
        print(f"  块 {i}: index={chunk.chunk_index}, "
              f"start={chunk.metadata['start_pos']}, "
              f"end={chunk.metadata['end_pos']}, "
              f"length={len(chunk.content)}")
    
    print("✓ 所有块的序号连续且从 0 开始")
    print("✓ 所有块都包含完整的元数据")
    print("✓ 需求 2.8 验证通过")


def verify_edge_cases():
    """验证边界情况"""
    print("\n=== 验证边界情况 ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    
    # 空文本
    chunks_empty = chunker.chunk("")
    assert len(chunks_empty) == 0, "空文本应返回空列表"
    print("✓ 空文本处理正确")
    
    # 单字符
    chunks_single = chunker.chunk("A")
    assert len(chunks_single) == 1, "单字符应返回 1 个块"
    assert chunks_single[0].content == "A", "单字符内容不正确"
    assert chunks_single[0].chunk_index == 0, "单字符块序号应为 0"
    print("✓ 单字符处理正确")
    
    # 文本长度刚好等于 chunk_size
    text_exact = "B" * 100
    chunks_exact = chunker.chunk(text_exact)
    assert len(chunks_exact) == 1, "长度等于 chunk_size 应返回 1 个块"
    assert len(chunks_exact[0].content) == 100, "块长度应为 100"
    print("✓ 长度等于 chunk_size 处理正确")
    
    # 文本长度刚好等于 chunk_size + 1
    text_plus_one = "C" * 101
    chunks_plus_one = chunker.chunk(text_plus_one)
    assert len(chunks_plus_one) == 2, "长度为 chunk_size + 1 应返回 2 个块"
    assert len(chunks_plus_one[0].content) == 100, "第一个块长度应为 100"
    assert len(chunks_plus_one[1].content) == 21, "第二个块长度应为 21"
    print("✓ 长度为 chunk_size + 1 处理正确")
    
    print("✓ 所有边界情况验证通过")


def verify_coverage_property():
    """验证分块覆盖完整性属性
    
    属性: 所有分块内容拼接（去除重叠）后应覆盖原始文本的全部内容
    """
    print("\n=== 验证分块覆盖完整性属性 ===")
    
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    
    # 测试多种文本
    test_texts = [
        "A" * 500,
        "这是中文测试" * 50,
        "Mixed 中英文 text 测试" * 30,
        "Line1\nLine2\nLine3\n" * 20,
    ]
    
    for idx, text in enumerate(test_texts):
        chunks = chunker.chunk(text)
        
        # 重建文本（去除重叠）
        reconstructed = ""
        for i, chunk in enumerate(chunks):
            if i == 0:
                # 第一个块完整添加
                reconstructed += chunk.content
            else:
                # 后续块跳过重叠部分
                overlap_size = min(20, len(chunk.content))
                reconstructed += chunk.content[overlap_size:]
        
        # 验证重建的文本与原始文本相同
        assert reconstructed == text, \
            f"测试 {idx + 1}: 重建文本与原始文本不匹配"
        
        print(f"✓ 测试 {idx + 1}: 文本长度 {len(text)}, "
              f"分块数 {len(chunks)}, 覆盖完整性验证通过")
    
    print("✓ 分块覆盖完整性属性验证通过")


if __name__ == "__main__":
    print("=" * 60)
    print("DocumentChunker SIMPLE 策略需求验证")
    print("=" * 60)
    
    try:
        verify_requirement_2_1()
        verify_requirement_2_2()
        verify_requirement_2_8()
        verify_edge_cases()
        verify_coverage_property()
        
        print("\n" + "=" * 60)
        print("✓ 所有需求验证通过！")
        print("=" * 60)
        print("\n需求覆盖:")
        print("  ✓ 需求 2.1: 按照配置的块大小进行分割")
        print("  ✓ 需求 2.2: 在相邻块之间保留重叠区域")
        print("  ✓ 需求 2.8: 为每个块生成序号和元数据")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ 验证失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
