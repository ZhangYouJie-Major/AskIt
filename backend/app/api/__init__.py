"""
API 路由模块
"""
from fastapi import APIRouter
from app.api import health, query, documents

api_router = APIRouter(prefix="/api/v1")

# 注册路由
api_router.include_router(health.router)
api_router.include_router(query.router)
api_router.include_router(documents.router)
