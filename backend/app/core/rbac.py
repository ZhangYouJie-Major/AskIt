"""
RBAC 权限检查依赖
"""
from typing import List
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User
from app.models.rbac import Permission, Role, RolePermission, UserRole

# 所有权限标识
ALL_PERMISSIONS = [
    "user:read",
    "user:write",
    "user:delete",
    "document:read",
    "document:write",
    "document:delete",
    "query:execute",
    "settings:read",
    "settings:write",
]


async def get_user_permissions(user: User, db: AsyncSession) -> List[str]:
    """
    获取用户的权限列表

    规则：
    - is_superuser=True → 全部权限
    - is_superuser=False → 所有角色的权限并集
    """
    if user.is_superuser:
        return ALL_PERMISSIONS

    # 查询用户的角色
    result = await db.execute(
        select(Role.name, Role.is_active)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id)
    )
    user_roles = result.all()

    if not user_roles:
        return []

    # 获取所有活跃角色的ID
    active_role_ids = []
    for role_row in user_roles:
        role_name, is_active = role_row
        # 获取role对象
        role_result = await db.execute(
            select(Role).where(Role.name == role_name)
        )
        role = role_result.scalar_one_or_none()
        if role and role.is_active:
            active_role_ids.append(role.id)

    if not active_role_ids:
        return []

    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.role_id.in_(active_role_ids))
    )
    permissions = list(set(row[0] for row in result.all()))

    return permissions


def require_permission(permission: str):
    """
    权限检查依赖 - 单权限

    使用方式：
    @router.delete("/{id}")
    async def delete(id: int, _: User = Depends(require_permission("user:delete"))):
        ...
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # 超级用户直接通过
        if current_user.is_superuser:
            return current_user

        # 获取用户权限
        user_permissions = await get_user_permissions(current_user, db)

        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少必要权限: {permission}"
            )

        return current_user

    return dependency


def require_permissions(permissions: List[str]):
    """
    权限检查依赖 - 多权限（需全部拥有）

    使用方式：
    @router.put("/{id}")
    async def update(id: int, _: User = Depends(require_permissions(["user:read", "user:write"]))):
        ...
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # 超级用户直接通过
        if current_user.is_superuser:
            return current_user

        # 获取用户权限
        user_permissions = await get_user_permissions(current_user, db)

        missing = [p for p in permissions if p not in user_permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少必要权限: {', '.join(missing)}"
            )

        return current_user

    return dependency
