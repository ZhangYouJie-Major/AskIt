# backend/app/api/users.py
"""
用户管理 API - 用户 CRUD 和角色分配
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.auth import get_current_user, get_password_hash
from app.core.rbac import require_permission
from app.models.models import User, Department
from app.services.rbac import RBACService

router = APIRouter(prefix="/users", tags=["Users"])


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    department_id: int | None
    department_name: str | None
    last_login: str | None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    department_id: int | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    """更新用户请求"""
    email: EmailStr | None = None
    full_name: str | None = None
    department_id: int | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    """用户列表响应"""
    id: int
    username: str
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    department_id: int | None
    department_name: str | None
    last_login: str | None
    roles: List["UserRoleResponse"] = []

    class Config:
        from_attributes = True


class UserRoleResponse(BaseModel):
    """用户角色响应"""
    id: int
    name: str
    description: str | None


# === 用户 CRUD API ===

@router.get("/", response_model=List[UserListResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """
    获取用户列表
    """
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.id)
    )
    users = result.scalars().all()

    user_list = []
    for user in users:
        # 获取部门名称
        department_name = None
        if user.department_id:
            dept_result = await db.execute(
                select(Department).where(Department.id == user.department_id)
            )
            dept = dept_result.scalar_one_or_none()
            if dept:
                department_name = dept.name

        # 获取用户角色
        user_roles = await RBACService.get_user_roles(db, user.id)

        user_list.append(UserListResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            department_id=user.department_id,
            department_name=department_name,
            last_login=user.last_login.isoformat() if user.last_login else None,
            roles=[
                UserRoleResponse(id=r.id, name=r.name, description=r.description)
                for r in user_roles
            ]
        ))

    return user_list


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """
    获取用户详情
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    department_name = None
    if user.department_id:
        dept_result = await db.execute(
            select(Department).where(Department.id == user.department_id)
        )
        dept = dept_result.scalar_one_or_none()
        if dept:
            department_name = dept.name

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        department_id=user.department_id,
        department_name=department_name,
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:write"))
):
    """
    创建用户
    """
    # 检查用户名是否存在
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否存在
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已存在")

    # 检查部门是否存在
    department_name = None
    if data.department_id:
        result = await db.execute(
            select(Department).where(Department.id == data.department_id)
        )
        dept = result.scalar_one_or_none()
        if not dept:
            raise HTTPException(status_code=400, detail="部门不存在")
        department_name = dept.name

    hashed_password = get_password_hash(data.password)
    new_user = User(
        username=data.username,
        email=data.email,
        hashed_password=hashed_password,
        full_name=data.full_name,
        department_id=data.department_id,
        is_active=data.is_active,
        is_superuser=False
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        is_superuser=new_user.is_superuser,
        department_id=new_user.department_id,
        department_name=department_name,
        last_login=None
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:write"))
):
    """
    更新用户
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新字段
    if data.email is not None:
        # 检查邮箱是否被其他用户使用
        result = await db.execute(
            select(User).where(User.email == data.email, User.id != user_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被其他用户使用")
        user.email = data.email

    if data.full_name is not None:
        user.full_name = data.full_name

    if data.department_id is not None:
        if data.department_id:
            result = await db.execute(
                select(Department).where(Department.id == data.department_id)
            )
            dept = result.scalar_one_or_none()
            if not dept:
                raise HTTPException(status_code=400, detail="部门不存在")
        user.department_id = data.department_id

    if data.is_active is not None:
        user.is_active = data.is_active

    await db.commit()
    await db.refresh(user)

    department_name = None
    if user.department_id:
        result = await db.execute(
            select(Department).where(Department.id == user.department_id)
        )
        dept = result.scalar_one_or_none()
        if dept:
            department_name = dept.name

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        department_id=user.department_id,
        department_name=department_name,
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:delete"))
):
    """
    删除用户
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 不允许删除超级管理员
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="不能删除超级管理员")

    # 删除用户角色关联
    await db.execute(
        delete_from_user_roles(user_id)
    )

    await db.delete(user)
    await db.commit()


# === 用户角色管理 API ===

class AssignRolesRequest(BaseModel):
    """分配角色请求"""
    role_ids: List[int]


@router.get("/{user_id}/roles", response_model=List[UserRoleResponse])
async def get_user_roles(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """
    获取用户角色
    """
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="用户不存在")

    roles = await RBACService.get_user_roles(db, user_id)
    return [
        UserRoleResponse(id=r.id, name=r.name, description=r.description)
        for r in roles
    ]


@router.post("/{user_id}/roles", status_code=status.HTTP_201_CREATED)
async def assign_roles_to_user(
    user_id: int,
    data: AssignRolesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:write"))
):
    """
    为用户分配角色（批量）
    """
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="用户不存在")

    created = await RBACService.assign_roles_to_user(db, user_id, data.role_ids)
    return {
        "success": True,
        "message": f"已分配 {len(created)} 个角色",
        "count": len(created)
    }


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_role(
    user_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:write"))
):
    """
    移除用户角色
    """
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="用户不存在")

    success = await RBACService.remove_role_from_user(db, user_id, role_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户角色关联不存在")


# 辅助函数 - 需要从 sqlalchemy 导入 delete
from sqlalchemy import delete as delete_from_user_roles
