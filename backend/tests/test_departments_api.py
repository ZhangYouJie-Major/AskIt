import importlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pydantic.networks as pydantic_networks
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core import database as database_module
from app.services import rbac as rbac_module


class MockUser:
    def __init__(self, is_superuser: bool = False):
        self.is_superuser = is_superuser


class DummyAsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture()
def app_module(monkeypatch):
    fake_email_validator = types.ModuleType("email_validator")

    class EmailNotValidError(ValueError):
        pass

    def validate_email(email, *args, **kwargs):
        return types.SimpleNamespace(email=email)

    fake_email_validator.EmailNotValidError = EmailNotValidError
    fake_email_validator.validate_email = validate_email
    fake_email_validator.__version__ = "2.0.0"

    monkeypatch.setitem(sys.modules, "email_validator", fake_email_validator)
    monkeypatch.setitem(sys.modules, "email_validator.exceptions", fake_email_validator)
    monkeypatch.setattr(pydantic_networks, "version", lambda package_name: "2.0.0")

    app_main = importlib.import_module("app.main")
    monkeypatch.setattr(app_main, "init_db", AsyncMock(return_value=None))
    monkeypatch.setattr(
        database_module,
        "AsyncSessionLocal",
        lambda: DummyAsyncSessionContext(AsyncMock()),
    )
    monkeypatch.setattr(
        rbac_module.RBACService,
        "init_permissions",
        AsyncMock(return_value=[]),
    )
    return app_main


@pytest.fixture()
def client_and_db(app_module):
    app = app_module.app
    original_overrides = app.dependency_overrides.copy()
    db_session = AsyncMock()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, db_session, app

    app.dependency_overrides = original_overrides


def test_departments_router_is_registered_through_app_main(client_and_db):
    client, _, app = client_and_db

    route_paths = {route.path for route in app.routes}

    assert "/api/v1/departments/" in route_paths
    assert "/api/v1/departments" in route_paths

    response = client.get("/api/v1/departments", follow_redirects=False)

    assert response.status_code != 307


def test_departments_list_forbidden_for_non_superuser(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=False)

    app.dependency_overrides[get_current_user] = override_get_current_user
    db_session.execute = AsyncMock(return_value=MagicMock())

    response = client.get("/api/v1/departments", follow_redirects=False)

    assert response.status_code == 403
    assert response.headers.get("location") is None
    assert response.json() == {"detail": "仅超级管理员可操作"}


def test_departments_list_access_for_superuser(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    mock_result = MagicMock()
    mock_result.all.return_value = [
        (1, "研发部", "负责产品研发", True, 3),
        (2, "运营部", None, False, 0),
    ]
    db_session.execute = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = client.get("/api/v1/departments", follow_redirects=False)

    assert response.status_code == 200
    assert response.headers.get("location") is None
    assert response.json() == [
        {
            "id": 1,
            "name": "研发部",
            "description": "负责产品研发",
            "is_active": True,
            "user_count": 3,
        },
        {
            "id": 2,
            "name": "运营部",
            "description": None,
            "is_active": False,
            "user_count": 0,
        },
    ]


def test_departments_create_duplicate_name_returns_400(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user

    existing_department = MagicMock()
    existing_department.id = 1
    existing_department.name = "研发部"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_department
    db_session.execute = AsyncMock(return_value=mock_result)

    response = client.post(
        "/api/v1/departments",
        json={"name": "  研发部  ", "description": "重复名称"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "部门名称已存在"}
    db_session.add.assert_not_called()
    db_session.commit.assert_not_called()


def test_departments_create_blank_name_returns_400(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = client.post(
        "/api/v1/departments",
        json={"name": "   ", "description": "空白名称"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "部门名称不能为空"}
    db_session.execute.assert_not_called()
    db_session.add.assert_not_called()
    db_session.commit.assert_not_called()


def test_departments_create_overlong_name_returns_400(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = client.post(
        "/api/v1/departments",
        json={"name": "测" * 101, "description": "超长名称"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "部门名称长度不能超过100个字符"}
    db_session.execute.assert_not_called()
    db_session.add.assert_not_called()
    db_session.commit.assert_not_called()


def test_departments_update_success(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user

    department = MagicMock()
    department.id = 1
    department.name = "研发部"
    department.description = "原描述"
    department.is_active = True

    user_count_result = MagicMock()
    user_count_result.scalar_one.return_value = 3

    department_result = MagicMock()
    department_result.scalar_one_or_none.return_value = department

    duplicate_result = MagicMock()
    duplicate_result.scalar_one_or_none.return_value = None

    db_session.execute = AsyncMock(
        side_effect=[department_result, duplicate_result, user_count_result]
    )

    response = client.put(
        "/api/v1/departments/1",
        json={"name": "产品部", "description": "负责产品"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "产品部",
        "description": "负责产品",
        "is_active": True,
        "user_count": 3,
    }


def test_departments_update_duplicate_name_returns_400(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user

    department = MagicMock()
    department.id = 1
    department.name = "研发部"
    department.description = "原描述"
    department.is_active = True

    department_result = MagicMock()
    department_result.scalar_one_or_none.return_value = department

    duplicate_result = MagicMock()
    duplicate_result.scalar_one_or_none.return_value = MagicMock()

    db_session.execute = AsyncMock(
        side_effect=[department_result, duplicate_result]
    )

    response = client.put(
        "/api/v1/departments/1",
        json={"name": "运营部", "description": "冲突更新"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "部门名称已存在"}
    db_session.commit.assert_not_called()


def test_departments_status_update_success(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user

    department = MagicMock()
    department.id = 1
    department.name = "研发部"
    department.description = "原描述"
    department.is_active = False

    department_result = MagicMock()
    department_result.scalar_one_or_none.return_value = department

    user_count_result = MagicMock()
    user_count_result.scalar_one.return_value = 2

    db_session.execute = AsyncMock(return_value=department_result)
    db_session.execute.side_effect = [department_result, user_count_result]

    response = client.put(
        "/api/v1/departments/1/status",
        json={"is_active": True},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "研发部",
        "description": "原描述",
        "is_active": True,
        "user_count": 2,
    }


def test_departments_create_integrity_error_falls_back_to_400(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_session.execute = AsyncMock(return_value=mock_result)
    db_session.add = MagicMock()
    db_session.commit = AsyncMock(
        side_effect=IntegrityError("INSERT", {}, Exception("duplicate"))
    )

    response = client.post(
        "/api/v1/departments",
        json={"name": "研发部", "description": "提交冲突"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "部门名称已存在"}
    db_session.rollback.assert_awaited()


@pytest.mark.parametrize(
    ("method", "url", "payload"),
    [
        ("post", "/api/v1/departments", {"name": "新部门", "description": "x"}),
        ("put", "/api/v1/departments/1", {"name": "新部门", "description": "x"}),
        ("put", "/api/v1/departments/1/status", {"is_active": True}),
    ],
)
def test_departments_write_routes_forbid_non_superuser(client_and_db, method, url, payload):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=False)

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = getattr(client, method)(url, json=payload, follow_redirects=False)

    assert response.status_code == 403
    assert response.json() == {"detail": "仅超级管理员可操作"}
    db_session.execute.assert_not_called()
    db_session.add.assert_not_called()
    db_session.commit.assert_not_called()


def test_departments_update_missing_returns_404(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_session.execute = AsyncMock(return_value=mock_result)

    response = client.put(
        "/api/v1/departments/404",
        json={"name": "不存在", "description": None},
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "部门不存在"}
