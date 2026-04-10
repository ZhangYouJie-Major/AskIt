"""
API 路由模块
"""
from fastapi import APIRouter
from app.api import health, query, documents, auth, users, roles, permissions

api_router = APIRouter(prefix="/api/v1")

# 注册路由
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(query.router)
api_router.include_router(documents.router)
api_router.include_router(permissions.router)  # 新增
api_router.include_router(roles.router)       # 新增
api_router.include_router(users.router)         # 扩展现有用户API
