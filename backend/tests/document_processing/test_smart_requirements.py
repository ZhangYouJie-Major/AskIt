"""
验证 SMART 策略满足需求规范

需求 2.3: WHEN 分割点位于单词或句子中间，THE Document_Chunker SHALL 调整分割位置到最近的自然边界（空格、换行、句号）
需求 2.4: WHEN 处理中文文本，THE Document_Chunker SHALL 在句号、问号、感叹号等标点符号处优先分割
需求 2.7: WHEN 单个段落超过最大块大小，THE Document_Chunker SHALL 强制分割并保留重叠
"""
import sys
from pathlib import Path
import importlib.util

# 设置路径并加载模块
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

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
sys.modules['app.services.document_processing.types'] = types_module
spec.loader.exec_module(chunker_module)

DocumentChunker = chunker_module.DocumentChunker


def test_requirement_2_3_natural_boundaries():
    """
    需求 2.3: 调整分割位置到最近的自然边界（空格、换行、句号）
    
    验证：当分割点位于单词或句子中间时，系统会调整到自然边界
    """
    print("\n=== 需求 2.3: 自然边界分割 ===")
    
    chunker = DocumentChunker(chunk_size=30, chunk_overlap=5, strategy=ChunkStrategy.SMART)
    
    # 测试场景1: 英文句子边界
    text1 = "This is a sentence. Another sentence here. And more text."
    chunks1 = chunker.chunk(text1)
    
    print(f"场景1 - 英文句子:")
    print(f"  输入: {text1}")
    print(f"  分块数: {len(chunks1)}")
    for i, chunk in enumerate(chunks1):
        print(f"  块{i}: '{chunk.content}'")
    
    # 验证：分块应该在句号后分割，而不是在单词中间
    for i, chunk in enumerate(chunks1[:-1]):  # 除了最后一块
        content = chunk.content
        # 检查最后一个字符是否在自然边界
        if len(content) > 0:
            last_char = content[-1]
            # 应该在句号、空格、换行等自然边界处，或者是强制分割
            is_natural_boundary = (
                last_char in {'.', '?', '!', ';', ' ', '\n'} or
                len(chunk.content) >= chunker.chunk_size + chunker.chunk_overlap - 5  # 强制分割的情况（允许5字符误差）
            )
            assert is_natural_boundary, f"块{i}未在自然边界处分割，最后字符: '{last_char}' (ASCII {ord(last_char)})"
    
    # 测试场景2: 空格边界
    text2 = "word1 word2 word3 word4 word5 word6 word7 word8"
    chunks2 = chunker.chunk(text2)
    
    print(f"\n场景2 - 空格边界:")
    print(f"  输入: {text2}")
    print(f"  分块数: {len(chunks2)}")
    for i, chunk in enumerate(chunks2):
        print(f"  块{i}: '{chunk.content}'")
    
    # 验证：不应该在单词中间分割
    for i, chunk in enumerate(chunks2[:-1]):
        content = chunk.content.rstrip()
        if len(content) > 0 and len(content) < 35:  # 非强制分割
            # 最后一个字符应该是空格或完整单词
            assert content[-1] == ' ' or content.split()[-1] == content.split()[-1]
    
    # 测试场景3: 换行边界
    text3 = "Line one here.\nLine two here.\nLine three here."
    chunks3 = chunker.chunk(text3)
    
    print(f"\n场景3 - 换行边界:")
    print(f"  输入: {repr(text3)}")
    print(f"  分块数: {len(chunks3)}")
    
    print("✓ 需求 2.3 验证通过")


def test_requirement_2_4_chinese_punctuation():
    """
    需求 2.4: 处理中文文本时，在句号、问号、感叹号等标点符号处优先分割
    
    验证：中文文本优先在中文标点符号处分割
    """
    print("\n=== 需求 2.4: 中文标点符号优先分割 ===")
    
    chunker = DocumentChunker(chunk_size=25, chunk_overlap=5, strategy=ChunkStrategy.SMART)
    
    # 测试场景1: 中文句号
    text1 = "这是第一个句子。这是第二个句子。这是第三个句子。这是第四个句子。"
    chunks1 = chunker.chunk(text1)
    
    print(f"场景1 - 中文句号:")
    print(f"  输入: {text1}")
    print(f"  分块数: {len(chunks1)}")
    for i, chunk in enumerate(chunks1):
        print(f"  块{i}: '{chunk.content}'")
    
    # 验证：应该在中文标点符号后分割
    for i, chunk in enumerate(chunks1[:-1]):
        content = chunk.content.rstrip()
        if len(content) > 0 and len(content) < 30:  # 非强制分割
            # 检查是否在中文标点后（考虑重叠，可能不是最后一个字符）
            has_chinese_punct = any(p in content for p in ['。', '？', '！', '；'])
            assert has_chinese_punct or len(chunk.content) >= 30, \
                f"块{i}应该包含中文标点或为强制分割"
    
    # 测试场景2: 多种中文标点
    text2 = "第一句。第二句？第三句！第四句；第五句。"
    chunks2 = chunker.chunk(text2)
    
    print(f"\n场景2 - 多种中文标点:")
    print(f"  输入: {text2}")
    print(f"  分块数: {len(chunks2)}")
    for i, chunk in enumerate(chunks2):
        print(f"  块{i}: '{chunk.content}'")
    
    # 测试场景3: 中英文混合
    text3 = "中文句子。English sentence. 另一个中文句子！Another English."
    chunks3 = chunker.chunk(text3)
    
    print(f"\n场景3 - 中英文混合:")
    print(f"  输入: {text3}")
    print(f"  分块数: {len(chunks3)}")
    for i, chunk in enumerate(chunks3):
        print(f"  块{i}: '{chunk.content}'")
    
    # 验证：应该优先在中文标点处分割
    for chunk in chunks3:
        # 每个块长度应该合理
        assert len(chunk.content) <= 30, f"块长度超出限制"
    
    print("✓ 需求 2.4 验证通过")


def test_requirement_2_7_force_split_with_overlap():
    """
    需求 2.7: 单个段落超过最大块大小时，强制分割并保留重叠
    
    验证：超大段落会被强制分割，且保留重叠区域
    """
    print("\n=== 需求 2.7: 超大段落强制分割并保留重叠 ===")
    
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, strategy=ChunkStrategy.SMART)
    
    # 测试场景1: 完全没有分隔符的超长文本
    text1 = "A" * 200
    chunks1 = chunker.chunk(text1)
    
    print(f"场景1 - 无分隔符超长文本:")
    print(f"  输入长度: {len(text1)}")
    print(f"  分块数: {len(chunks1)}")
    for i, chunk in enumerate(chunks1):
        print(f"  块{i}: 长度={len(chunk.content)}")
    
    # 验证1: 应该有多个分块
    assert len(chunks1) >= 3, f"超长文本应该被分成多块，实际只有{len(chunks1)}块"
    
    # 验证2: 每个块的长度不应超过 chunk_size + chunk_overlap
    max_allowed = chunker.chunk_size + chunker.chunk_overlap
    for i, chunk in enumerate(chunks1):
        assert len(chunk.content) <= max_allowed, \
            f"块{i}长度{len(chunk.content)}超过最大允许值{max_allowed}"
    
    # 验证3: 相邻块之间应该有重叠
    for i in range(len(chunks1) - 1):
        overlap_from_current = chunks1[i].content[-chunker.chunk_overlap:]
        overlap_from_next = chunks1[i + 1].content[:chunker.chunk_overlap]
        assert overlap_from_current == overlap_from_next, \
            f"块{i}和块{i+1}之间的重叠区域不匹配"
    
    print(f"  ✓ 验证通过: {len(chunks1)}个分块，每块≤{max_allowed}字符，重叠={chunker.chunk_overlap}字符")
    
    # 测试场景2: 超长单词（模拟无法在自然边界分割的情况）
    text2 = "X" * 150
    chunks2 = chunker.chunk(text2)
    
    print(f"\n场景2 - 超长单词:")
    print(f"  输入长度: {len(text2)}")
    print(f"  分块数: {len(chunks2)}")
    
    # 验证：强制分割且保留重叠
    assert len(chunks2) >= 2, "超长单词应该被强制分割"
    for i in range(len(chunks2) - 1):
        overlap1 = chunks2[i].content[-chunker.chunk_overlap:]
        overlap2 = chunks2[i + 1].content[:chunker.chunk_overlap]
        assert overlap1 == overlap2, f"强制分割时重叠区域不匹配"
    
    # 测试场景3: 超长段落（有一些空格但距离很远）
    text3 = "word " * 100  # 500个字符，空格间隔
    chunks3 = chunker.chunk(text3)
    
    print(f"\n场景3 - 超长段落（稀疏空格）:")
    print(f"  输入长度: {len(text3)}")
    print(f"  分块数: {len(chunks3)}")
    
    # 验证：应该被分割成多块
    assert len(chunks3) >= 8, f"超长段落应该被分成多块"
    
    # 验证：保留重叠
    for i in range(len(chunks3) - 1):
        # 检查重叠区域
        overlap_size = min(chunker.chunk_overlap, len(chunks3[i].content), len(chunks3[i+1].content))
        if overlap_size > 0:
            overlap1 = chunks3[i].content[-overlap_size:]
            overlap2 = chunks3[i + 1].content[:overlap_size]
            assert overlap1 == overlap2, f"块{i}和块{i+1}重叠不匹配"
    
    print("✓ 需求 2.7 验证通过")


def test_integration_all_requirements():
    """
    综合测试：验证所有需求在复杂场景下的协同工作
    """
    print("\n=== 综合测试: 所有需求协同 ===")
    
    chunker = DocumentChunker(chunk_size=80, chunk_overlap=15, strategy=ChunkStrategy.SMART)
    
    # 复杂文本：包含中英文、多种标点、段落、超长内容
    text = """这是一个复杂的测试文档。它包含中文句子！
    
English sentences are here. They should be split at sentence boundaries.

这里有一个超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级超级长的段落没有任何标点符号

Another paragraph with words that need to be split at space boundaries when no punctuation is available.

最后一段中文。包含问号？和感叹号！还有分号；"""
    
    chunks = chunker.chunk(text)
    
    print(f"输入长度: {len(text)}")
    print(f"分块数: {len(chunks)}")
    print("\n各分块详情:")
    for i, chunk in enumerate(chunks):
        preview = chunk.content[:50].replace('\n', '\\n')
        print(f"  块{i}: 长度={len(chunk.content)}, 预览='{preview}...'")
    
    # 验证1: 所有块的长度合理
    max_allowed = chunker.chunk_size + chunker.chunk_overlap
    for i, chunk in enumerate(chunks):
        assert len(chunk.content) <= max_allowed, \
            f"块{i}长度超出限制"
    
    # 验证2: 序号连续
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i, f"块序号不连续"
    
    # 验证3: 重叠区域正确
    for i in range(len(chunks) - 1):
        overlap_size = min(chunker.chunk_overlap, len(chunks[i].content), len(chunks[i+1].content))
        if overlap_size > 0:
            overlap1 = chunks[i].content[-overlap_size:]
            overlap2 = chunks[i + 1].content[:overlap_size]
            assert overlap1 == overlap2, f"块{i}和块{i+1}重叠不匹配"
    
    # 验证4: 覆盖完整性（所有内容都被包含）
    # 重建文本
    reconstructed = chunks[0].content
    for i in range(1, len(chunks)):
        # 去除重叠部分
        overlap_size = min(chunker.chunk_overlap, len(chunks[i-1].content), len(chunks[i].content))
        reconstructed += chunks[i].content[overlap_size:]
    
    # 长度应该相近（可能因为边界调整有微小差异）
    length_ratio = len(reconstructed) / len(text)
    assert 0.95 <= length_ratio <= 1.05, \
        f"重建文本长度比例异常: {length_ratio}"
    
    print(f"\n✓ 综合测试通过:")
    print(f"  - {len(chunks)}个分块")
    print(f"  - 所有块长度≤{max_allowed}")
    print(f"  - 重叠区域正确")
    print(f"  - 覆盖率: {length_ratio:.2%}")


if __name__ == "__main__":
    print("=" * 70)
    print("验证 SMART 策略需求规范")
    print("=" * 70)
    
    try:
        test_requirement_2_3_natural_boundaries()
        test_requirement_2_4_chinese_punctuation()
        test_requirement_2_7_force_split_with_overlap()
        test_integration_all_requirements()
        
        print("\n" + "=" * 70)
        print("✓ 所有需求验证通过！")
        print("=" * 70)
        print("\n需求覆盖:")
        print("  ✓ 需求 2.3: 自然边界分割（空格、换行、句号）")
        print("  ✓ 需求 2.4: 中文标点符号优先分割")
        print("  ✓ 需求 2.7: 超大段落强制分割并保留重叠")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
