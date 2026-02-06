"""
向量存储服务 - 基于 Chroma (Cloud/Local)
"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings


class VectorStore:
    """向量存储服务 - 支持 Chroma Cloud 和本地模式"""

    def __init__(self):
        self.collection_name = "documents"
        self.collection = None

        # 根据配置选择客户端类型
        if settings.chroma_mode == "cloud":
            # Chroma Cloud 模式 - 使用 CloudClient
            # 参考: https://docs.trychroma.com/docs/run-chroma/cloud-client
            self.client = chromadb.Client(
                api_key=settings.chroma_api_key,
                tenant=settings.chroma_tenant,
                database=settings.chroma_database,
            )
            self.tenant = settings.chroma_tenant
            self.database = settings.chroma_database
        else:
            # 本地模式 - 使用 PersistentClient 进行持久化存储
            import os
            persist_dir = settings.chroma_persist_directory
            # 确保目录存在
            os.makedirs(persist_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.tenant = None
            self.database = None

    async def init_collection(self, vector_size: int = 1536):
        """初始化集合"""
        try:
            if settings.chroma_mode == "cloud":
                # Cloud 模式需要指定 tenant 和 database
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    tenant=self.tenant,
                    database=self.database,
                )
            else:
                self.collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            # 集合不存在，创建新集合
            if settings.chroma_mode == "cloud":
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    tenant=self.tenant,
                    database=self.database,
                    metadata={"hnsw:space": "cosine"}
                )
            else:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )

    async def insert_points(
        self,
        ids: List[str],
        vectors: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ):
        """插入向量点"""
        if self.collection is None:
            await self.init_collection()

        if settings.chroma_mode == "cloud":
            self.collection.add(
                ids=ids,
                embeddings=vectors,
                metadatas=metadatas,
                tenant=self.tenant,
                database=self.database,
            )
        else:
            self.collection.add(
                ids=ids,
                embeddings=vectors,
                metadatas=metadatas,
            )

    async def search(
        self,
        vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.0,
        department_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """向量搜索"""
        if self.collection is None:
            await self.init_collection()

        # 构建过滤条件
        where = None
        if department_id is not None:
            where = {"department_id": department_id}

        # 执行查询
        if settings.chroma_mode == "cloud":
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=limit,
                where=where,
                tenant=self.tenant,
                database=self.database,
            )
        else:
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=limit,
                where=where,
            )

        # 格式化结果
        formatted_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0
                # Chroma 返回的是距离，需要转换为相似度分数
                score = 1 - distance

                if score >= score_threshold:
                    formatted_results.append({
                        "id": doc_id,
                        "score": score,
                        "payload": results["metadatas"][0][i] if results.get("metadatas") else {},
                    })

        return formatted_results

    async def delete_points(self, ids: List[str]):
        """删除向量点"""
        if self.collection is None:
            await self.init_collection()

        if settings.chroma_mode == "cloud":
            self.collection.delete(
                ids=ids,
                tenant=self.tenant,
                database=self.database,
            )
        else:
            self.collection.delete(ids=ids)

    async def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        if self.collection is None:
            await self.init_collection()

        return {
            "name": self.collection.name,
            "count": self.collection.count(),
        }

    async def reset_collection(self):
        """重置集合（删除所有数据）"""
        try:
            if settings.chroma_mode == "cloud":
                self.client.delete_collection(
                    name=self.collection_name,
                    tenant=self.tenant,
                    database=self.database,
                )
            else:
                self.client.delete_collection(name=self.collection_name)
            self.collection = None
            await self.init_collection()
        except Exception:
            pass


# 全局实例
vector_store = VectorStore()
