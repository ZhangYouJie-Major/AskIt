"""
认证 API - 注册、登录
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    get_current_user
)
from app.models.models import User, Department

router = APIRouter(prefix="/auth", tags=["Authentication"])


class UserRegister(BaseModel):
    """用户注册请求"""
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    department_id: int | None = None


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


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


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    用户注册
    """
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    # 检查部门是否存在（如果提供了 department_id）
    department_name = None
    if user_data.department_id:
        result = await db.execute(
            select(Department).where(Department.id == user_data.department_id)
        )
        dept = result.scalar_one_or_none()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="部门不存在"
            )
        department_name = dept.name
    
    # 创建用户
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        department_id=user_data.department_id,
        is_active=True,
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
        department_name=department_name
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录（OAuth2 格式）
    """
    # 查询用户
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    # 更新最后登录时间
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    
    # 获取部门信息
    department_name = None
    if user.department_id:
        result = await db.execute(
            select(Department).where(Department.id == user.department_id)
        )
        dept = result.scalar_one_or_none()
        if dept:
            department_name = dept.name
    
    # 创建 token
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "department_id": user.department_id,
            "department_name": department_name,
            "is_superuser": user.is_superuser
        }
    )


@router.post("/login/json", response_model=TokenResponse)
async def login_json(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    用户登录（JSON 格式，供前端使用）
    """
    # 查询用户
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 更新最后登录时间
    from datetime import datetime, timezone
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    
    # 获取部门信息
    department_name = None
    if user.department_id:
        result = await db.execute(
            select(Department).where(Department.id == user.department_id)
        )
        dept = result.scalar_one_or_none()
        if dept:
            department_name = dept.name
    
    # 创建 token
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "department_id": user.department_id,
            "department_name": department_name,
            "is_superuser": user.is_superuser
        }
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取当前登录用户信息
    """
    department_name = None
    if current_user.department_id:
        result = await db.execute(
            select(Department).where(Department.id == current_user.department_id)
        )
        dept = result.scalar_one_or_none()
        if dept:
            department_name = dept.name
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        department_id=current_user.department_id,
        department_name=department_name
    )
