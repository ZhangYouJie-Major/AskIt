"""
查询 API - RAG 问答接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.rag import rag_service

router = APIRouter(prefix="/query", tags=["Query"])


class QueryRequest(BaseModel):
    """查询请求"""
    question: str
    department_id: int
    history: Optional[List[dict]] = None
    top_k: int = 5


class QueryResponse(BaseModel):
    """查询响应"""
    answer: str
    sources: List[dict]


@router.post("/", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    执行 RAG 查询

    - **question**: 用户问题
    - **department_id**: 部门ID（用于权限过滤）
    - **history**: 对话历史（可选）
    - **top_k**: 返回的文档数量（默认5）
    """
    try:
        result = await rag_service.query(
            question=request.question,
            department_id=request.department_id,
            history=request.history,
            top_k=request.top_k,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
