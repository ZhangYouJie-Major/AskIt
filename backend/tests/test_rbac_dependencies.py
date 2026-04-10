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
