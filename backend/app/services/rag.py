"""
RAG 服务 - 基于 LangChain 1.x
"""
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.agents import create_react_agent
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate

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
        # 1. 对问题进行向量化
        query_vector = await self.embeddings.aembed_query(question)

        # 2. 向量搜索
        search_results = await vector_store.search(
            vector=query_vector,
            limit=top_k,
            department_id=department_id,
        )

        # 3. 构建上下文
        context = self._build_context(search_results)

        # 4. 构建历史上下文
        history_context = self._build_history_context(history or [])

        # 5. 构建提示词
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

        # 6. 生成回答
        response = await self.llm.ainvoke(prompt)

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
