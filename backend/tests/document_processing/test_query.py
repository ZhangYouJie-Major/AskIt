"""
测试问答 API
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from app.services.rag import rag_service
from app.core.config import settings
from loguru import logger


async def test_rag_service():
    """测试 RAG 服务"""
    logger.info("=== 开始测试 RAG 服务 ===")
    logger.info(f"OpenAI Base URL: {settings.openai_base_url}")
    logger.info(f"LLM Model: {settings.llm_model}")
    logger.info(f"Embedding Model: {settings.embedding_model}")
    logger.info(f"Chroma Mode: {settings.chroma_mode}")

    try:
        # 测试简单的嵌入生成
        logger.info("\n1. 测试嵌入生成...")
        test_text = "这是一个测试文本"
        embedding = await rag_service.embeddings.aembed_query(test_text)
        logger.info(f"✅ 嵌入生成成功，维度: {len(embedding)}")

        # 测试向量搜索
        logger.info("\n2. 测试向量搜索...")
        from app.services.vector_store import vector_store
        results = await vector_store.search(
            vector=embedding,
            limit=5,
            department_id=1
        )
        logger.info(f"✅ 向量搜索完成，找到 {len(results)} 个结果")

        # 测试完整查询（如果有数据）
        if results:
            logger.info("\n3. 测试完整 RAG 查询...")
            response = await rag_service.query(
                question="测试问题",
                department_id=1,
                top_k=5
            )
            logger.info(f"✅ 查询成功")
            logger.info(f"答案: {response['answer'][:100]}...")
        else:
            logger.warning("⚠️  向量数据库中没有数据，跳过完整查询测试")

        logger.info("\n=== 所有测试通过 ===")

    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        import traceback
        logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_rag_service())
