# backend/tests/test_rbac_service.py
import pytest
from app.services.rbac import RBACService, PERMISSIONS_DATA


def test_all_permissions_defined():
    """验证所有权限已定义"""
    perms = PERMISSIONS_DATA
    assert len(perms) == 9
    codes = [p["code"] for p in perms]
    assert "user:read" in codes
    assert "user:write" in codes
    assert "settings:write" in codes
