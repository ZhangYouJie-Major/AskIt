"""
查询 API - RAG 问答接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.rag import rag_service
from app.core.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/query", tags=["Query"])


class QueryRequest(BaseModel):
    """查询请求"""
    question: str
    history: Optional[List[dict]] = None
    top_k: int = 5


class QueryResponse(BaseModel):
    """查询响应"""
    answer: str
    sources: List[dict]


@router.post("/", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    执行 RAG 查询（需要登录）

    - **question**: 用户问题
    - **history**: 对话历史（可选）
    - **top_k**: 返回的文档数量（默认5）
    
    部门ID自动从当前用户获取
    """
    try:
        # 使用当前用户的部门ID
        department_id = current_user.department_id or 1  # 默认部门为1
        
        result = await rag_service.query(
            question=request.question,
            department_id=department_id,
            history=request.history,
            top_k=request.top_k,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
