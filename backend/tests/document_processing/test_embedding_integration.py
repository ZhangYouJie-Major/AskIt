"""
EmbeddingService 集成测试示例

演示如何使用 EmbeddingService 进行文本向量化
注意：这些测试需要真实的 API Key 才能运行
"""
import pytest
from app.services.document_processing.embedding import EmbeddingService


@pytest.mark.skip(reason="需要真实的 API Key")
@pytest.mark.asyncio
async def test_embed_with_real_openai_api():
    """使用真实的 OpenAI API 进行向量化测试
    
    要运行此测试，请：
    1. 设置环境变量 OPENAI_API_KEY
    2. 移除 @pytest.mark.skip 装饰器
    """
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("未设置 OPENAI_API_KEY 环境变量")
    
    service = EmbeddingService(
        provider="openai",
        model="text-embedding-3-small",
        api_key=api_key,
    )
    
    texts = [
        "这是一个测试文本",
        "This is a test text",
        "人工智能正在改变世界",
    ]
    
    embeddings = await service.embed_texts(texts)
    
    # 验证返回的向量数量
    assert len(embeddings) == 3
    
    # 验证向量维度（text-embedding-3-small 是 1536 维）
    for embedding in embeddings:
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
    
    print(f"成功生成 {len(embeddings)} 个向量")
    print(f"向量维度: {len(embeddings[0])}")


@pytest.mark.skip(reason="需要真实的 API Key")
@pytest.mark.asyncio
async def test_batch_processing_with_real_api():
    """测试批量处理（需求 3.5）
    
    要运行此测试，请：
    1. 设置环境变量 OPENAI_API_KEY
    2. 移除 @pytest.mark.skip 装饰器
    """
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("未设置 OPENAI_API_KEY 环境变量")
    
    service = EmbeddingService(
        provider="openai",
        model="text-embedding-3-small",
        api_key=api_key,
        batch_size=10,  # 小批次用于测试
    )
    
    # 创建 25 个文本，应该分成 3 批
    texts = [f"测试文本 {i}" for i in range(25)]
    
    embeddings = await service.embed_texts(texts)
    
    # 验证返回的向量数量
    assert len(embeddings) == 25
    
    # 验证所有向量维度一致
    for embedding in embeddings:
        assert len(embedding) == 1536
    
    print(f"成功处理 {len(texts)} 个文本，分成 3 批")


def test_service_configuration_examples():
    """演示不同提供商的配置方式"""
    
    # OpenAI 配置（需求 3.2）
    openai_service = EmbeddingService(
        provider="openai",
        model="text-embedding-3-small",
        api_key="your-openai-key",
        # base_url 使用默认值
    )
    assert openai_service.base_url == "https://api.openai.com/v1"
    
    # GLM 配置（需求 3.3）
    glm_service = EmbeddingService(
        provider="glm",
        model="embedding-3",
        api_key="your-glm-key",
        base_url="https://open.bigmodel.cn/api/paas/v4",
    )
    assert glm_service.base_url == "https://open.bigmodel.cn/api/paas/v4"
    
    # Qwen 配置（需求 3.4）
    qwen_service = EmbeddingService(
        provider="qwen",
        model="text-embedding-v4",
        api_key="your-qwen-key",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    assert qwen_service.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    print("所有提供商配置示例验证通过")


if __name__ == "__main__":
    # 运行配置示例测试
    test_service_configuration_examples()
    print("\n配置示例测试完成！")
    print("\n要运行真实 API 测试，请：")
    print("1. 设置环境变量: export OPENAI_API_KEY=your-key")
    print("2. 移除测试函数上的 @pytest.mark.skip 装饰器")
    print("3. 运行: pytest test_embedding_integration.py -v")
