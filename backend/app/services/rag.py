"""
RAG 服务 - 基于 LangChain 1.x
"""
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from loguru import logger

from app.core.config import settings
from app.services.vector_store import vector_store


class RAGService:
    """RAG 问答服务 - LangChain 1.x"""

    def __init__(self):
        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_base_url,
            temperature=0.7,
        )

        # 初始化 Embeddings
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_base_url,
        )

    async def query(
        self,
        question: str,
        department_id: int,
        history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        执行 RAG 查询

        Args:
            question: 用户问题
            department_id: 部门ID（用于权限过滤）
            history: 对话历史
            top_k: 返回的文档数量

        Returns:
            包含答案和来源文档的字典
        """
        logger.info("=" * 60)
        logger.info("📋 RAG 查询开始")
        logger.info(f"👤 用户问题: {question}")
        logger.info(f"🏢 部门ID: {department_id}")
        logger.info(f"📊 返回文档数: {top_k}")

        # 1. 对问题进行向量化
        logger.info("🔄 步骤 1/6: 问题向量化...")
        query_vector = await self.embeddings.aembed_query(question)
        logger.info(f"✅ 向量化完成，维度: {len(query_vector)}")

        # 2. 向量搜索
        logger.info("🔍 步骤 2/6: 向量搜索...")
        search_results = await vector_store.search(
            vector=query_vector,
            limit=top_k,
            department_id=department_id,
        )
        logger.info(f"✅ 搜索完成，找到 {len(search_results)} 个相关文档")

        # 打印搜索结果详情
        if search_results:
            logger.info("📄 搜索结果详情:")
            for i, r in enumerate(search_results, 1):
                score = r.get("score", 0)
                filename = r["payload"].get("filename", "未知文件")
                content = r["payload"].get("content", "")
                logger.info(f"  [{i}] {filename} (相似度: {score:.4f})")
                logger.info(f"      内容预览: {content[:100]}...")
        else:
            logger.warning("⚠️  未找到任何相关文档")

        # 3. 构建上下文
        logger.info("📝 步骤 3/6: 构建上下文...")
        context = self._build_context(search_results)
        logger.info(f"✅ 上下文构建完成，长度: {len(context)} 字符")
        logger.debug(f"📖 上下文内容:\n{context}")

        # 4. 构建历史上下文
        logger.info("💬 步骤 4/6: 构建历史上下文...")
        history_context = self._build_history_context(history or [])
        if history_context:
            logger.info(f"✅ 历史上下文构建完成，轮数: {len(history or [])}")
            logger.debug(f"📖 历史内容:\n{history_context}")
        else:
            logger.info("✅ 无对话历史")

        # 5. 构建提示词
        logger.info("✍️  步骤 5/6: 构建提示词...")
        prompt = f"""你是一个专业的企业知识库助手。请基于以下上下文信息回答用户问题。

{history_context}

上下文信息：
{context}

用户问题：{question}

注意事项：
1. 如果上下文中有相关信息，请基于上下文回答
2. 如果上下文中没有相关信息，请诚实告知用户
3. 回答要准确、简洁、专业
4. 可以引用具体的文档内容

请用中文回答："""
        logger.info(f"✅ 提示词构建完成，长度: {len(prompt)} 字符")
        logger.debug(f"📖 完整提示词:\n{prompt}")

        # 6. 生成回答
        logger.info("🤖 步骤 6/6: 调用 LLM 生成回答...")
        response = await self.llm.ainvoke(prompt)
        logger.info("✅ LLM 回答生成完成")
        logger.info(f"💡 回答内容: {response.content}")
        logger.info("=" * 60)

        return {
            "answer": response.content,
            "sources": [
                {
                    "document_id": r["payload"]["document_id"],
                    "chunk_id": r["payload"]["chunk_id"],
                    "filename": r["payload"]["filename"],
                    "score": r["score"],
                }
                for r in search_results
            ],
        }

    def _build_context(self, search_results: List[Dict[str, Any]]) -> str:
        """构建上下文字符串"""
        if not search_results:
            return "知识库中没有找到相关信息"
        contexts = []
        for r in search_results:
            content = r["payload"].get("content", "")
            filename = r["payload"].get("filename", "")
            contexts.append(f"【{filename}】\n{content}")
        return "\n\n".join(contexts)

    def _build_history_context(self, history: List[Dict[str, str]]) -> str:
        """构建对话历史上下文"""
        if not history:
            return ""
        lines = ["对话历史："]
        for msg in history:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            lines.append(f"{role}：{content}")
        return "\n".join(lines)


# 全局实例
rag_service = RAGService()
