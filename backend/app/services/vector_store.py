"""
向量存储服务 - 基于 Qdrant
"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.core.config import settings


class VectorStore:
    """向量存储服务"""

    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key or None,
            https=settings.qdrant_https,
        )
        self.collection_name = "documents"

    async def init_collection(self, vector_size: int = 1536):
        """初始化集合"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                )
            )

    async def insert_points(
        self,
        points: List[PointStruct],
    ):
        """插入向量点"""
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    async def search(
        self,
        vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.7,
        department_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """向量搜索"""
        # 构建过滤器
        query_filter = None
        if department_id is not None:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="department_id",
                        match=MatchValue(value=department_id),
                    )
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload,
            }
            for r in results
        ]

    async def delete_points(self, point_ids: List[str]):
        """删除向量点"""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=point_ids,
        )


# 全局实例
vector_store = VectorStore()
