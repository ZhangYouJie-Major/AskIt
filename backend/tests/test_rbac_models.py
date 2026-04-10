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
