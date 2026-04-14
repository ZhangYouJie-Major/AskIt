"""
部门管理 API
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import Department, User

router = APIRouter(prefix="/departments", tags=["Departments"])


class DepartmentListResponse(BaseModel):
    """部门列表响应"""
    id: int
    name: str
    description: str | None
    is_active: bool
    user_count: int

    class Config:
        from_attributes = True


class DepartmentCreateRequest(BaseModel):
    """创建部门请求"""
    name: str
    description: str | None = None


class DepartmentUpdateRequest(BaseModel):
    """更新部门请求"""
    name: str
    description: str | None = None


class DepartmentStatusUpdateRequest(BaseModel):
    """更新部门状态请求"""
    is_active: bool


async def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """仅允许超级管理员访问"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可操作",
        )
    return current_user


def _normalize_department_name(name: str) -> str:
    """标准化部门名称"""
    return name.strip()


def _validate_department_name(name: str) -> str:
    """校验部门名称的基础约束"""
    normalized_name = _normalize_department_name(name)
    if not normalized_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部门名称不能为空",
        )
    if len(normalized_name) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部门名称长度不能超过100个字符",
        )
    return normalized_name


async def _get_department_response(
    db: AsyncSession,
    department: Department,
) -> DepartmentListResponse:
    """构造部门响应并补充用户数量"""
    result = await db.execute(
        select(func.count(User.id)).where(User.department_id == department.id)
    )
    user_count = result.scalar_one() or 0

    return DepartmentListResponse(
        id=department.id,
        name=department.name,
        description=department.description,
        is_active=department.is_active,
        user_count=int(user_count),
    )


async def _ensure_department_name_unique(
    db: AsyncSession,
    name: str,
    department_id: int | None = None,
) -> None:
    """检查部门名称是否重复"""
    normalized_name = _normalize_department_name(name)
    result = await db.execute(
        select(Department).where(
            func.lower(func.trim(Department.name)) == normalized_name.lower(),
            Department.id != department_id if department_id is not None else True,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部门名称已存在",
        )


async def _get_department_or_404(
    db: AsyncSession,
    department_id: int,
) -> Department:
    """获取部门，不存在时返回 404"""
    result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="部门不存在",
        )
    return department


async def _commit_department_changes(db: AsyncSession) -> None:
    """提交部门变更，兜底唯一约束冲突"""
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部门名称已存在",
        ) from exc


@router.get("/", response_model=List[DepartmentListResponse])
@router.get("", response_model=List[DepartmentListResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_superuser),
):
    """获取部门列表"""
    result = await db.execute(
        select(
            Department.id,
            Department.name,
            Department.description,
            Department.is_active,
            func.count(User.id).label("user_count"),
        )
        .outerjoin(User, User.department_id == Department.id)
        .group_by(
            Department.id,
            Department.name,
            Department.description,
            Department.is_active,
        )
        .order_by(Department.id)
    )

    departments = result.all()

    return [
        DepartmentListResponse(
            id=department_id,
            name=name,
            description=description,
            is_active=is_active,
            user_count=int(user_count or 0),
        )
        for department_id, name, description, is_active, user_count in departments
    ]


@router.post("/", response_model=DepartmentListResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=DepartmentListResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_superuser),
):
    """创建部门"""
    name = _validate_department_name(data.name)
    await _ensure_department_name_unique(db, name)

    department = Department(
        name=name,
        description=data.description,
        is_active=True,
    )
    db.add(department)
    await _commit_department_changes(db)
    await db.refresh(department)

    return await _get_department_response(db, department)


@router.put("/{department_id}", response_model=DepartmentListResponse)
async def update_department(
    department_id: int,
    data: DepartmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_superuser),
):
    """更新部门"""
    department = await _get_department_or_404(db, department_id)

    name = _validate_department_name(data.name)

    if name.lower() != department.name.strip().lower():
        await _ensure_department_name_unique(db, name, department_id=department_id)

    department.name = name
    department.description = data.description

    await _commit_department_changes(db)
    await db.refresh(department)

    return await _get_department_response(db, department)


@router.put("/{department_id}/status", response_model=DepartmentListResponse)
async def update_department_status(
    department_id: int,
    data: DepartmentStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_superuser),
):
    """更新部门启停状态"""
    department = await _get_department_or_404(db, department_id)

    department.is_active = data.is_active
    await _commit_department_changes(db)
    await db.refresh(department)

    return await _get_department_response(db, department)
