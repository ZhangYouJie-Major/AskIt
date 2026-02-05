"""
健康检查 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import User, Document, Department

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "message": "AskIt API is running"
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取系统统计信息"""
    user_count = await db.scalar(select(func.count(User.id)))
    doc_count = await db.scalar(select(func.count(Document.id)))
    dept_count = await db.scalar(select(func.count(Department.id)))

    return {
        "users": user_count or 0,
        "documents": doc_count or 0,
        "departments": dept_count or 0
    }
