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

    # 关系 - 使用 viewonly=True 避免循环依赖问题
    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        viewonly=True
    )


class RolePermission(Base):
    """角色-权限关联表"""
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )


# 更新 Permission 的关系定义
Permission.roles = relationship(
    "Role",
    secondary="role_permissions",
    back_populates="permissions",
    viewonly=True
)


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


# 预定义的9个权限数据（供迁移使用）
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


# 在模块级别添加 Role.users 关系（在所有模型定义完成后）
# 这样可以避免循环依赖问题
Role.users = relationship(
    "User",
    secondary="user_roles",
    back_populates="roles",
    viewonly=True
)
