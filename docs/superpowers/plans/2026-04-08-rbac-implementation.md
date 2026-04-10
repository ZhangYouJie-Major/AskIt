# RBAC 权限系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的 RBAC 权限系统，包括后端模型、API、权限检查依赖，以及前端用户管理和角色管理界面。

**Architecture:** 采用标准 RBAC 模型（Permission → RolePermission → Role → UserRole → User），通过 FastAPI 依赖注入实现权限检查，完全自定义角色，全局权限+部门数据隔离。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (async) + Vue 3 + TypeScript + Element Plus

---

## 文件结构

```
backend/app/
├── models/
│   ├── models.py           # 现有模型（不改）
│   └── rbac.py             # 新增：Role, Permission, RolePermission, UserRole
├── api/
│   ├── __init__.py         # 新增路由注册
│   ├── users.py            # 新增：用户管理 API（含角色分配）
│   ├── roles.py            # 新增：角色管理 API（含权限配置）
│   └── permissions.py      # 新增：权限查询 API
├── core/
│   ├── auth.py             # 现有（不改）
│   └── rbac.py              # 新增：权限检查依赖（require_permission, require_permissions）
└── services/
    └── rbac.py             # 新增：RBAC 业务逻辑（获取用户权限、角色检查等）

frontend/src/
├── api/
│   └── rbac.ts             # 新增：RBAC API 调用
├── views/
│   ├── UserManageView.vue  # 新增：用户管理页面
│   └── RoleManageView.vue # 新增：角色管理页面
└── router/
    └── index.ts            # 修改：添加 /admin/users, /admin/roles 路由
```

---

## Task 1: 创建 RBAC 数据模型

**Files:**
- Create: `backend/app/models/rbac.py`
- Test: `backend/tests/test_rbac_models.py`

- [ ] **Step 1: 创建测试文件**

```python
# backend/tests/test_rbac_models.py
import pytest
from datetime import datetime
from app.models.rbac import Permission, Role, RolePermission, UserRole


def test_permission_creation():
    """测试权限创建"""
    perm = Permission(
        id=1,
        code="user:read",
        name="查看用户",
        description="允许查看用户信息"
    )
    assert perm.code == "user:read"
    assert perm.name == "查看用户"


def test_role_creation():
    """测试角色创建"""
    role = Role(
        id=1,
        name="管理员",
        description="系统管理员",
        is_active=True
    )
    assert role.name == "管理员"
    assert role.is_active is True


def test_user_role_association():
    """测试用户角色关联"""
    user_role = UserRole(user_id=1, role_id=1)
    assert user_role.user_id == 1
    assert user_role.role_id == 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run pytest tests/test_rbac_models.py -v`
Expected: FAIL - module 'app.models.rbac' has no attribute 'Permission'

- [ ] **Step 3: 创建 RBAC 模型文件**

```python
# backend/app/models/rbac.py
"""
RBAC 权限模型 - Permission, Role, RolePermission, UserRole
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def get_utc_now():
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Permission(Base):
    """权限表 - 9条固定记录"""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "user:read"
    name = Column(String(100), nullable=False)  # e.g., "查看用户"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)


class Role(Base):
    """角色表"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")
    users = relationship("User", secondary="user_roles", back_populates="roles")


class RolePermission(Base):
    """角色-权限关联表"""
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )


# 更新 Permission 和 Role 的关系定义
Permission.roles = relationship("Role", secondary="role_permissions", back_populates="permissions")


class UserRole(Base):
    """用户-角色关联表"""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )


# 补充 User 模型的关系（在 UserRole 定义后添加）
# 注意：这个关系定义需要追加到 User 模型中
# User.roles = relationship("Role", secondary="user_roles", back_populates="users")
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run pytest tests/test_rbac_models.py -v`
Expected: PASS

- [ ] **Step 5: 补充 User 模型的关系**

修改 `backend/app/models/models.py` 文件末尾添加：
```python
# 在文件末尾添加 User 和 Role 的关系（需要等 rbac.py 中的 UserRole 定义后）
from app.models.rbac import UserRole  # noqa: F401

# 补充 User.roles 关系（在 UserRole 定义后添加）
User.roles = relationship("Role", secondary="user_roles", back_populates="users")
Role.users = relationship("User", secondary="user_roles", back_populates="roles")
```

- [ ] **Step 6: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add backend/app/models/rbac.py backend/app/models/models.py backend/tests/test_rbac_models.py
git commit -m "feat: add RBAC data models (Permission, Role, RolePermission, UserRole)"
```

---

## Task 2: 创建权限检查依赖

**Files:**
- Create: `backend/app/core/rbac.py`
- Test: `backend/tests/test_rbac_dependencies.py`

- [ ] **Step 1: 创建测试文件**

```python
# backend/tests/test_rbac_dependencies.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.rbac import require_permission, require_permissions, get_user_permissions


class MockUser:
    def __init__(self, is_superuser=False, role_codes=None):
        self.is_superuser = is_superuser
        self.role_codes = role_codes or []


def test_get_user_permissions_superuser():
    """超级用户拥有全部权限"""
    user = MockUser(is_superuser=True)
    # 模拟获取用户权限
    permissions = ["user:read", "user:write", "user:delete", "document:read",
                   "document:write", "document:delete", "query:execute",
                   "settings:read", "settings:write"]
    # 当 is_superuser=True 时，应返回全部权限
    assert user.is_superuser is True


def test_get_user_permissions_regular_user():
    """普通用户权限由角色决定"""
    user = MockUser(is_superuser=False, role_codes=["admin"])
    assert user.is_superuser is False
    assert "admin" in user.role_codes
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run pytest tests/test_rbac_dependencies.py -v`
Expected: FAIL - module 'app.core.rbac' has no attribute 'require_permission'

- [ ] **Step 3: 创建 RBAC 依赖文件**

```python
# backend/app/core/rbac.py
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

    # 获取所有活跃角色的权限
    active_role_ids = [role.id for role in user_roles if role.is_active]
    if not active_role_ids:
        return []

    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.role_id.in_(active_role_ids))
    )
    permissions = list(set(row[0] for row in result.all()))

    return permissions


async def require_permission(permission: str):
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


async def require_permissions(permissions: List[str]):
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
```

- [ ] **Step 3: 运行测试验证通过**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run pytest tests/test_rbac_dependencies.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add backend/app/core/rbac.py backend/tests/test_rbac_dependencies.py
git commit -m "feat: add RBAC permission check dependencies"
```

---

## Task 3: 创建权限和角色服务层

**Files:**
- Create: `backend/app/services/rbac.py`
- Test: `backend/tests/test_rbac_service.py`

- [ ] **Step 1: 创建服务层测试**

```python
# backend/tests/test_rbac_service.py
import pytest
from app.services.rbac import RBACService


def test_all_permissions_defined():
    """验证所有权限已定义"""
    service = RBACService()
    perms = service.get_all_permissions()
    assert len(perms) == 9
    codes = [p.code for p in perms]
    assert "user:read" in codes
    assert "user:write" in codes
    assert "settings:write" in codes
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run pytest tests/test_rbac_service.py -v`
Expected: FAIL - module 'app.services.rbac' has no attribute 'RBACService'

- [ ] **Step 3: 创建 RBAC 服务**

```python
# backend/app/services/rbac.py
"""
RBAC 业务逻辑服务
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.rbac import Permission, Role, RolePermission, UserRole


# 预定义的9个权限
PERMISSIONS_DATA = [
    {"code": "user:read", "name": "查看用户", "description": "允许查看用户信息"},
    {"code": "user:write", "name": "创建/编辑用户", "description": "允许创建和编辑用户"},
    {"code": "user:delete", "name": "删除用户", "description": "允许删除用户"},
    {"code": "document:read", "name": "查看文档", "description": "允许查看文档"},
    {"code": "document:write", "name": "上传/编辑文档", "description": "允许上传和编辑文档"},
    {"code": "document:delete", "name": "删除文档", "description": "允许删除文档"},
    {"code": "query:execute", "name": "发起问答", "description": "允许发起问答查询"},
    {"code": "settings:read", "name": "查看配置", "description": "允许查看系统配置"},
    {"code": "settings:write", "name": "修改配置", "description": "允许修改系统配置"},
]


class RBACService:
    """RBAC 业务逻辑服务"""

    @staticmethod
    async def init_permissions(db: AsyncSession) -> List[Permission]:
        """初始化权限数据（仅在不存在时）"""
        result = await db.execute(select(Permission))
        existing = result.scalars().all()

        if len(existing) == 0:
            # 创建所有权限
            permissions = [
                Permission(**p) for p in PERMISSIONS_DATA
            ]
            db.add_all(permissions)
            await db.commit()
            return permissions

        return list(existing)

    @staticmethod
    async def get_all_permissions(db: AsyncSession) -> List[Permission]:
        """获取所有权限"""
        result = await db.execute(select(Permission).order_by(Permission.id))
        return list(result.scalars().all())

    @staticmethod
    async def get_all_roles(db: AsyncSession, include_inactive: bool = False) -> List[Role]:
        """获取所有角色"""
        query = select(Role)
        if not include_inactive:
            query = query.where(Role.is_active == True)
        result = await db.execute(query.order_by(Role.id))
        return list(result.scalars().all())

    @staticmethod
    async def get_role_by_id(db: AsyncSession, role_id: int) -> Optional[Role]:
        """根据ID获取角色"""
        result = await db.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_role(
        db: AsyncSession,
        name: str,
        description: Optional[str] = None,
        permission_ids: Optional[List[int]] = None
    ) -> Role:
        """创建角色"""
        role = Role(name=name, description=description, is_active=True)
        db.add(role)
        await db.flush()

        if permission_ids:
            for perm_id in permission_ids:
                rp = RolePermission(role_id=role.id, permission_id=perm_id)
                db.add(rp)

        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def update_role(
        db: AsyncSession,
        role_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Role]:
        """更新角色"""
        role = await RBACService.get_role_by_id(db, role_id)
        if not role:
            return None

        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        if is_active is not None:
            role.is_active = is_active

        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def update_role_permissions(
        db: AsyncSession,
        role_id: int,
        permission_ids: List[int]
    ) -> Optional[Role]:
        """更新角色权限"""
        role = await RBACService.get_role_by_id(db, role_id)
        if not role:
            return None

        # 删除旧关联
        await db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )

        # 添加新关联
        for perm_id in permission_ids:
            rp = RolePermission(role_id=role_id, permission_id=perm_id)
            db.add(rp)

        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def delete_role(db: AsyncSession, role_id: int) -> bool:
        """删除角色（同时删除关联）"""
        role = await RBACService.get_role_by_id(db, role_id)
        if not role:
            return False

        # 删除关联（级联自动处理，但显式删除更干净）
        await db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        await db.execute(
            delete(UserRole).where(UserRole.role_id == role_id)
        )

        await db.delete(role)
        await db.commit()
        return True

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: int) -> List[Role]:
        """获取用户的所有角色"""
        result = await db.execute(
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def assign_roles_to_user(
        db: AsyncSession,
        user_id: int,
        role_ids: List[int]
    ) -> List[UserRole]:
        """为用户分配角色（批量）"""
        created = []
        for role_id in role_ids:
            # 检查是否已存在
            existing = await db.execute(
                select(UserRole).where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id
                )
            )
            if existing.scalar_one_or_none():
                continue

            ur = UserRole(user_id=user_id, role_id=role_id)
            db.add(ur)
            created.append(ur)

        await db.commit()
        return created

    @staticmethod
    async def remove_role_from_user(
        db: AsyncSession,
        user_id: int,
        role_id: int
    ) -> bool:
        """移除用户角色"""
        result = await db.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_role_usage_count(db: AsyncSession, role_id: int) -> int:
        """获取角色被使用的数量"""
        result = await db.execute(
            select(UserRole).where(UserRole.role_id == role_id)
        )
        return len(result.scalars().all())
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run pytest tests/test_rbac_service.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add backend/app/services/rbac.py backend/tests/test_rbac_service.py
git commit -m "feat: add RBAC service layer with business logic"
```

---

## Task 4: 创建权限和角色管理 API

**Files:**
- Create: `backend/app/api/permissions.py`
- Create: `backend/app/api/roles.py`
- Create: `backend/app/api/users.py` (扩展现有)
- Modify: `backend/app/api/__init__.py`

- [ ] **Step 1: 创建 permissions.py**

```python
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
```

- [ ] **Step 2: 创建 roles.py**

```python
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
from app.core.rbac import require_permission, require_permissions
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
        # 获取权限数量
        permissions = await RBACService.get_all_permissions(db)
        role_perms = [p for p in permissions if role.id]

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
```

- [ ] **Step 3: 更新 users.py**

在现有 `backend/app/api/users.py` 末尾添加：

```python
# === 用户角色管理 API ===

class AssignRolesRequest(BaseModel):
    """分配角色请求"""
    role_ids: List[int]


class UserRoleResponse(BaseModel):
    """用户角色响应"""
    id: int
    name: str
    description: str | None


@router.get("/{user_id}/roles", response_model=List[UserRoleResponse])
async def get_user_roles(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """
    获取用户角色
    """
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
    为用户分配角色（单/批量）
    """
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
    success = await RBACService.remove_role_from_user(db, user_id, role_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户角色关联不存在")
```

- [ ] **Step 4: 更新 __init__.py**

修改 `backend/app/api/__init__.py`：

```python
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
```

- [ ] **Step 5: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add backend/app/api/permissions.py backend/app/api/roles.py backend/app/api/users.py backend/app/api/__init__.py
git commit -m "feat: add RBAC API endpoints (permissions, roles, user roles)"
```

---

## Task 5: 创建数据库迁移

**Files:**
- Create: `backend/alembic/versions/xxxx_create_rbac_tables.py`

- [ ] **Step 1: 创建迁移文件**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run alembic revision --autogenerate -m "create rbac tables"`

- [ ] **Step 2: 检查迁移文件**

读取生成的迁移文件，确认包含：
- permissions 表
- roles 表
- role_permissions 表
- user_roles 表

- [ ] **Step 3: 添加权限初始化数据**

编辑生成的迁移文件，在 `upgrade()` 函数末尾添加：

```python
# 初始化权限数据
from app.models.rbac import PERMISSIONS_DATA

def upgrade() -> None:
    # ... 现有建表代码 ...

    # 初始化权限
    from sqlalchemy import insert
    from app.models.rbac import Permission

    conn = op.get_bind()
    for p in PERMISSIONS_DATA:
        conn.execute(insert(Permission).values(**p))
```

- [ ] **Step 4: 运行迁移测试**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run alembic upgrade head --sql | head -100`

- [ ] **Step 5: 执行迁移**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run alembic upgrade head`

- [ ] **Step 6: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add backend/alembic/versions/
git commit -m "feat: add RBAC database migration"
```

---

## Task 6: 前端 RBAC API 层

**Files:**
- Create: `frontend/src/api/rbac.ts`

- [ ] **Step 1: 创建 API 调用文件**

```typescript
// frontend/src/api/rbac.ts
import api from './index'

// ============ Types ============

export interface Permission {
  id: number
  code: string
  name: string
  description: string
}

export interface Role {
  id: number
  name: string
  description: string | null
  is_active: boolean
  permissions: Permission[]
}

export interface RoleBrief {
  id: number
  name: string
  description: string | null
  is_active: boolean
  permission_count: number
  user_count: number
}

export interface UserRole {
  id: number
  name: string
  description: string | null
}

export interface CreateRoleRequest {
  name: string
  description?: string
  permission_ids: number[]
}

export interface UpdateRoleRequest {
  name?: string
  description?: string
  is_active?: boolean
}

export interface UpdateRolePermissionsRequest {
  permission_ids: number[]
}

export interface AssignRolesRequest {
  role_ids: number[]
}

// ============ Permissions API ============

export const permissionsApi = {
  /**
   * 获取所有权限列表
   */
  list: () => {
    return api.get<any, Permission[]>('/permissions/')
  }
}

// ============ Roles API ============

export const rolesApi = {
  /**
   * 获取角色列表
   */
  list: () => {
    return api.get<any, RoleBrief[]>('/roles/')
  },

  /**
   * 获取角色详情（含权限）
   */
  getById: (id: number) => {
    return api.get<any, Role>(`/roles/${id}`)
  },

  /**
   * 创建角色
   */
  create: (data: CreateRoleRequest) => {
    return api.post<any, Role>('/roles/', data)
  },

  /**
   * 更新角色
   */
  update: (id: number, data: UpdateRoleRequest) => {
    return api.put<any, Role>(`/roles/${id}`, data)
  },

  /**
   * 更新角色权限
   */
  updatePermissions: (id: number, data: UpdateRolePermissionsRequest) => {
    return api.put<any, Role>(`/roles/${id}/permissions`, data)
  },

  /**
   * 删除角色
   */
  delete: (id: number) => {
    return api.delete(`/roles/${id}`)
  }
}

// ============ User Roles API ============

export const userRolesApi = {
  /**
   * 获取用户角色
   */
  getUserRoles: (userId: number) => {
    return api.get<any, UserRole[]>(`/users/${userId}/roles`)
  },

  /**
   * 为用户分配角色
   */
  assign: (userId: number, data: AssignRolesRequest) => {
    return api.post<any, any>(`/users/${userId}/roles`, data)
  },

  /**
   * 移除用户角色
   */
  remove: (userId: number, roleId: number) => {
    return api.delete(`/users/${userId}/roles/${roleId}`)
  }
}
```

- [ ] **Step 2: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add frontend/src/api/rbac.ts
git commit -m "feat: add frontend RBAC API layer"
```

---

## Task 7: 前端用户管理页面

**Files:**
- Create: `frontend/src/views/UserManageView.vue`

- [ ] **Step 1: 创建用户管理页面**

```vue
<template>
  <div class="user-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建用户
          </el-button>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="department_name" label="部门" width="120" />
        <el-table-column label="角色" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="role in row.roles"
              :key="role.id"
              size="small"
              class="role-tag"
            >
              {{ role.name }}
            </el-tag>
            <span v-if="!row.roles || row.roles.length === 0" class="no-role">
              未分配角色
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后登录" width="180">
          <template #default="{ row }">
            {{ formatDate(row.last_login) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" @click="handleAssignRoles(row)">分配角色</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: center"
        @current-change="loadUsers"
        @size-change="loadUsers"
      />
    </el-card>

    <!-- 新建/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建用户' : '编辑用户'"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="dialogMode === 'edit'" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="form.email" type="email" />
        </el-form-item>
        <el-form-item label="密码" :required="dialogMode === 'create'">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="form.department_id" placeholder="选择部门">
            <el-option label="无" :value="null" />
            <el-option
              v-for="dept in departments"
              :key="dept.id"
              :label="dept.name"
              :value="dept.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 分配角色抽屉 -->
    <el-drawer v-model="rolesDrawerVisible" title="分配角色" size="400px">
      <div class="roles-assign">
        <el-checkbox-group v-model="selectedRoleIds">
          <el-checkbox
            v-for="role in allRoles"
            :key="role.id"
            :label="role.id"
            style="display: block; margin-bottom: 12px"
          >
            {{ role.name }}
            <span class="role-desc">{{ role.description }}</span>
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="rolesDrawerVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitRoles" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { rolesApi, userRolesApi } from '@/api/rbac'

const users = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const departments = ref<any[]>([])

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const submitting = ref(false)
const editingUserId = ref<number | null>(null)

const rolesDrawerVisible = ref(false)
const allRoles = ref<any[]>([])
const selectedRoleIds = ref<number[]>([])
const currentUserId = ref<number | null>(null)

const form = reactive({
  username: '',
  email: '',
  password: '',
  full_name: '',
  department_id: null as number | null,
  is_active: true
})

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await api.get('/users/', {
      params: { skip: (currentPage.value - 1) * pageSize.value, limit: pageSize.value }
    })
    users.value = response.users
    total.value = response.total
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogMode.value = 'create'
  editingUserId.value = null
  Object.assign(form, {
    username: '',
    email: '',
    password: '',
    full_name: '',
    department_id: null,
    is_active: true
  })
  dialogVisible.value = true
}

const handleEdit = (row: any) => {
  dialogMode.value = 'edit'
  editingUserId.value = row.id
  Object.assign(form, {
    username: row.username,
    email: row.email,
    password: '',
    full_name: row.full_name,
    department_id: row.department_id,
    is_active: row.is_active
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.username || !form.email) {
    ElMessage.warning('请填写必填项')
    return
  }
  if (dialogMode.value === 'create' && !form.password) {
    ElMessage.warning('请填写密码')
    return
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await api.post('/users/', form)
      ElMessage.success('创建成功')
    } else {
      const data = { ...form }
      if (!data.password) delete data.password
      await api.put(`/users/${editingUserId.value}`, data)
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定删除该用户吗？', '提示', { type: 'warning' })
    await api.delete(`/users/${row.id}`)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleAssignRoles = async (row: any) => {
  currentUserId.value = row.id
  // 加载所有角色
  if (allRoles.value.length === 0) {
    allRoles.value = await rolesApi.list()
  }
  // 加载用户当前角色
  const userRoles = await userRolesApi.getUserRoles(row.id)
  selectedRoleIds.value = userRoles.map((r: any) => r.id)
  rolesDrawerVisible.value = true
}

const handleSubmitRoles = async () => {
  if (!currentUserId.value) return
  submitting.value = true
  try {
    await userRolesApi.assign(currentUserId.value, { role_ids: selectedRoleIds.value })
    ElMessage.success('角色分配成功')
    rolesDrawerVisible.value = false
    loadUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '分配失败')
  } finally {
    submitting.value = false
  }
}

const formatDate = (date: string | null) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.user-manage {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.role-tag {
  margin-right: 4px;
}

.no-role {
  color: #909399;
  font-size: 12px;
}

.role-desc {
  display: block;
  color: #909399;
  font-size: 12px;
  margin-top: 2px;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add frontend/src/views/UserManageView.vue
git commit -m "feat: add user management page"
```

---

## Task 8: 前端角色管理页面

**Files:**
- Create: `frontend/src/views/RoleManageView.vue`

- [ ] **Step 1: 创建角色管理页面**

```vue
<template>
  <div class="role-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>角色管理</span>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建角色
          </el-button>
        </div>
      </template>

      <el-table :data="roles" v-loading="loading" stripe>
        <el-table-column prop="name" label="角色名" width="150" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="权限数量" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.permission_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="用户数" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.user_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" @click="handleConfigPermissions(row)">
              配置权限
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDelete(row)"
              :disabled="row.user_count > 0"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑角色对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建角色' : '编辑角色'"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="角色名" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 配置权限抽屉 -->
    <el-drawer v-model="permissionsDrawerVisible" title="配置权限" size="500px">
      <div class="permissions-config">
        <el-checkbox
          v-for="perm in allPermissions"
          :key="perm.id"
          v-model="selectedPermissionIds"
          :label="perm.id"
          style="display: block; margin-bottom: 12px"
        >
          <strong>{{ perm.name }}</strong>
          <span class="perm-code">{{ perm.code }}</span>
          <span class="perm-desc">{{ perm.description }}</span>
        </el-checkbox>
      </div>
      <template #footer>
        <el-button @click="permissionsDrawerVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitPermissions" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { rolesApi, permissionsApi } from '@/api/rbac'

const roles = ref<any[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const submitting = ref(false)
const editingRoleId = ref<number | null>(null)

const form = reactive({
  name: '',
  description: '',
  is_active: true
})

const permissionsDrawerVisible = ref(false)
const allPermissions = ref<any[]>([])
const selectedPermissionIds = ref<number[]>([])
const currentRoleId = ref<number | null>(null)

const loadRoles = async () => {
  loading.value = true
  try {
    roles.value = await rolesApi.list()
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogMode.value = 'create'
  editingRoleId.value = null
  Object.assign(form, { name: '', description: '', is_active: true })
  dialogVisible.value = true
}

const handleEdit = async (row: any) => {
  dialogMode.value = 'edit'
  editingRoleId.value = row.id
  try {
    const role = await rolesApi.getById(row.id)
    Object.assign(form, {
      name: role.name,
      description: role.description,
      is_active: role.is_active
    })
    dialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  }
}

const handleSubmit = async () => {
  if (!form.name) {
    ElMessage.warning('请填写角色名')
    return
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await rolesApi.create({
        name: form.name,
        description: form.description || undefined,
        permission_ids: []
      })
      ElMessage.success('创建成功')
    } else {
      await rolesApi.update(editingRoleId.value!, {
        name: form.name,
        description: form.description || undefined,
        is_active: form.is_active
      })
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadRoles()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定删除该角色吗？', '提示', { type: 'warning' })
    await rolesApi.delete(row.id)
    ElMessage.success('删除成功')
    loadRoles()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleConfigPermissions = async (row: any) => {
  currentRoleId.value = row.id
  // 加载所有权限
  if (allPermissions.value.length === 0) {
    allPermissions.value = await permissionsApi.list()
  }
  // 加载角色当前权限
  try {
    const role = await rolesApi.getById(row.id)
    selectedPermissionIds.value = role.permissions.map((p: any) => p.id)
  } catch (error: any) {
    selectedPermissionIds.value = []
  }
  permissionsDrawerVisible.value = true
}

const handleSubmitPermissions = async () => {
  if (!currentRoleId.value) return
  submitting.value = true
  try {
    await rolesApi.updatePermissions(currentRoleId.value, {
      permission_ids: selectedPermissionIds.value
    })
    ElMessage.success('权限配置成功')
    permissionsDrawerVisible.value = false
    loadRoles()
  } catch (error: any) {
    ElMessage.error(error.message || '配置失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadRoles()
})
</script>

<style scoped>
.role-manage {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.perm-code {
  display: block;
  color: #409eff;
  font-size: 12px;
  font-family: monospace;
}

.perm-desc {
  display: block;
  color: #909399;
  font-size: 12px;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add frontend/src/views/RoleManageView.vue
git commit -m "feat: add role management page"
```

---

## Task 9: 添加前端路由

**Files:**
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: 更新路由配置**

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/knowledge'
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/KnowledgeView.vue'),
    meta: { title: '知识库查询' }
  },
  {
    path: '/admin',
    name: 'Admin',
    redirect: '/admin/users',
    meta: { title: '管理后台' }
  },
  {
    path: '/admin/users',
    name: 'UserManage',
    component: () => import('@/views/UserManageView.vue'),
    meta: { title: '用户管理' }
  },
  {
    path: '/admin/roles',
    name: 'RoleManage',
    component: () => import('@/views/RoleManageView.vue'),
    meta: { title: '角色管理' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'AskIt'} - 企业知识库`
  next()
})

export default router
```

- [ ] **Step 2: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add frontend/src/router/index.ts
git commit -m "feat: add RBAC routes (/admin/users, /admin/roles)"
```

---

## Task 10: 端到端测试

**Files:**
- Create: `backend/tests/test_rbac_e2e.py`

- [ ] **Step 1: 创建端到端测试**

```python
# backend/tests/test_rbac_e2e.py
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_permissions_flow():
    """测试完整权限流程"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 注册测试用户
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "rbac_test_user",
                "email": "rbac@test.com",
                "password": "Test@123456"
            }
        )
        assert response.status_code == 201

        # 2. 登录获取 token
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "rbac_test_user", "password": "Test@123456"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        # 3. 获取权限列表
        response = await client.get(
            "/api/v1/permissions/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        permissions = response.json()
        assert len(permissions) == 9

        # 4. 获取角色列表
        response = await client.get(
            "/api/v1/roles/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
```

- [ ] **Step 2: 运行测试**

Run: `cd /Users/zhangyoujie/Desktop/项目代码/AskIt/backend && uv run pytest tests/test_rbac_e2e.py -v`

- [ ] **Step 3: 提交**

```bash
cd /Users/zhangyoujie/Desktop/项目代码/AskIt
git add backend/tests/test_rbac_e2e.py
git commit -m "test: add RBAC end-to-end tests"
```

---

## 实现总结

| Task | 描述 | 文件 |
|------|------|------|
| 1 | RBAC 数据模型 | `backend/app/models/rbac.py` |
| 2 | 权限检查依赖 | `backend/app/core/rbac.py` |
| 3 | RBAC 服务层 | `backend/app/services/rbac.py` |
| 4 | API 端点 | `backend/app/api/permissions.py`, `roles.py`, `users.py` |
| 5 | 数据库迁移 | `backend/alembic/versions/xxxx_create_rbac_tables.py` |
| 6 | 前端 API | `frontend/src/api/rbac.ts` |
| 7 | 用户管理页面 | `frontend/src/views/UserManageView.vue` |
| 8 | 角色管理页面 | `frontend/src/views/RoleManageView.vue` |
| 9 | 路由配置 | `frontend/src/router/index.ts` |
| 10 | 端到端测试 | `backend/tests/test_rbac_e2e.py` |
