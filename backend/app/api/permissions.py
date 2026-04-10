# backend/app/api/permissions.py
"""
权限管理 API - 仅查询，无修改权限（固定9条）
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.rbac import get_user_permissions
from app.models.models import User
from app.services.rbac import RBACService

router = APIRouter(prefix="/permissions", tags=["Permissions"])


class PermissionResponse(BaseModel):
    """权限响应"""
    id: int
    code: str
    name: str
    description: str | None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有权限列表
    """
    permissions = await RBACService.get_all_permissions(db)
    return [
        PermissionResponse(
            id=p.id,
            code=p.code,
            name=p.name,
            description=p.description
        )
        for p in permissions
    ]


class UserPermissionsResponse(BaseModel):
    """当前用户权限响应"""
    permissions: List[str]
    is_superuser: bool


@router.get("/my", response_model=UserPermissionsResponse)
async def get_my_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的权限列表
    """
    permissions = await get_user_permissions(current_user, db)
    return UserPermissionsResponse(
        permissions=permissions,
        is_superuser=current_user.is_superuser
    )
