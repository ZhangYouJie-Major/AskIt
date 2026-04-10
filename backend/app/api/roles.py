# backend/app/api/roles.py
"""
角色管理 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.rbac import require_permission
from app.models.models import User
from app.services.rbac import RBACService

router = APIRouter(prefix="/roles", tags=["Roles"])


class PermissionBrief(BaseModel):
    """权限简要信息"""
    id: int
    code: str
    name: str

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """角色响应"""
    id: int
    name: str
    description: str | None
    is_active: bool
    permissions: List[PermissionBrief]

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    """角色列表响应"""
    id: int
    name: str
    description: str | None
    is_active: bool
    permission_count: int
    user_count: int

    class Config:
        from_attributes = True


class CreateRoleRequest(BaseModel):
    """创建角色请求"""
    name: str
    description: str | None = None
    permission_ids: List[int] = []


class UpdateRoleRequest(BaseModel):
    """更新角色请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class UpdateRolePermissionsRequest(BaseModel):
    """更新角色权限请求"""
    permission_ids: List[int]


@router.get("/", response_model=List[RoleListResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """
    获取角色列表
    """
    roles = await RBACService.get_all_roles(db, include_inactive=False)

    result = []
    for role in roles:
        # 获取用户数量
        user_count = await RBACService.get_role_usage_count(db, role.id)

        result.append(RoleListResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            permission_count=len(role.permissions) if role.permissions else 0,
            user_count=user_count
        ))

    return result


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: CreateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:write"))
):
    """
    创建角色
    """
    role = await RBACService.create_role(
        db=db,
        name=data.name,
        description=data.description,
        permission_ids=data.permission_ids
    )

    # 重新获取以加载关系
    role = await RBACService.get_role_by_id(db, role.id)

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_active=role.is_active,
        permissions=[
            PermissionBrief(id=p.id, code=p.code, name=p.name)
            for p in role.permissions
        ] if role.permissions else []
    )


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """
    获取角色详情（含权限）
    """
    role = await RBACService.get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_active=role.is_active,
        permissions=[
            PermissionBrief(id=p.id, code=p.code, name=p.name)
            for p in role.permissions
        ] if role.permissions else []
    )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:write"))
):
    """
    更新角色
    """
    role = await RBACService.update_role(
        db=db,
        role_id=role_id,
        name=data.name,
        description=data.description,
        is_active=data.is_active
    )

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 重新获取以加载关系
    role = await RBACService.get_role_by_id(db, role.id)

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_active=role.is_active,
        permissions=[
            PermissionBrief(id=p.id, code=p.code, name=p.name)
            for p in role.permissions
        ] if role.permissions else []
    )


@router.put("/{role_id}/permissions", response_model=RoleResponse)
async def update_role_permissions(
    role_id: int,
    data: UpdateRolePermissionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:write"))
):
    """
    更新角色权限
    """
    role = await RBACService.update_role_permissions(
        db=db,
        role_id=role_id,
        permission_ids=data.permission_ids
    )

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 重新获取以加载关系
    role = await RBACService.get_role_by_id(db, role.id)

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_active=role.is_active,
        permissions=[
            PermissionBrief(id=p.id, code=p.code, name=p.name)
            for p in role.permissions
        ] if role.permissions else []
    )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:delete"))
):
    """
    删除角色
    """
    # 检查是否有用户使用
    user_count = await RBACService.get_role_usage_count(db, role_id)
    if user_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该角色已被 {user_count} 个用户使用，无法删除"
        )

    success = await RBACService.delete_role(db, role_id)
    if not success:
        raise HTTPException(status_code=404, detail="角色不存在")
