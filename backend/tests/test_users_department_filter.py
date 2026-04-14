"""
用户列表部门筛选测试
"""
import operator
import importlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pydantic.networks as pydantic_networks
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.sql.elements import BinaryExpression

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


class UserRecord:
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        department_id: int | None,
        department_name: str | None = None,
    ):
        self.id = user_id
        self.username = username
        self.email = email
        self.full_name = None
        self.is_active = True
        self.is_superuser = False
        self.department_id = department_id
        self.last_login = None
        self.department_name = department_name


class DepartmentRecord:
    def __init__(self, department_id: int, name: str):
        self.id = department_id
        self.name = name


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


def _make_user_result(users):
    result = MagicMock()
    result.scalars.return_value.all.return_value = users
    return result


def _make_department_result(department):
    result = MagicMock()
    result.scalar_one_or_none.return_value = department
    return result


def _extract_where_eq_value(statement, table_name: str, column_name: str):
    for criterion in getattr(statement, "_where_criteria", ()):
        if not isinstance(criterion, BinaryExpression):
            continue
        if criterion.operator is not operator.eq:
            continue

        left = criterion.left
        left_name = getattr(left, "name", None) or getattr(left, "key", None)
        left_table = getattr(getattr(left, "table", None), "name", None)
        if left_name != column_name or left_table != table_name:
            continue

        return getattr(criterion.right, "value", None)

    return None


def _user_list_execute_side_effect(all_users, departments, filtered_users):
    async def _execute(statement):
        entity = statement.column_descriptions[0].get("entity") if statement.column_descriptions else None

        if entity is not None and entity.__name__ == "User":
            department_id = _extract_where_eq_value(statement, "users", "department_id")
            if department_id is not None:
                matched_users = [user for user in all_users if user.department_id == department_id]
                return _make_user_result(matched_users)
            return _make_user_result(all_users)

        if entity is not None and entity.__name__ == "Department":
            department_id = _extract_where_eq_value(statement, "departments", "id")
            if department_id is not None:
                for department in departments:
                    if department.id == department_id:
                        return _make_department_result(department)
            return _make_department_result(None)

        return MagicMock()

    return _execute


def test_users_list_filters_by_department_id(client_and_db, monkeypatch):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user
    monkeypatch.setattr(rbac_module.RBACService, "get_user_roles", AsyncMock(return_value=[]))

    all_users = [
        UserRecord(1, "alice", "alice@example.com", department_id=10, department_name="研发部"),
        UserRecord(2, "bob", "bob@example.com", department_id=20, department_name="运营部"),
    ]
    departments = [
        DepartmentRecord(10, "研发部"),
        DepartmentRecord(20, "运营部"),
    ]
    db_session.execute = AsyncMock(
        side_effect=_user_list_execute_side_effect(all_users, departments, [])
    )

    response = client.get("/api/v1/users/", params={"department_id": 10}, follow_redirects=False)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "username": "alice",
            "email": "alice@example.com",
            "full_name": None,
            "is_active": True,
            "is_superuser": False,
            "department_id": 10,
            "department_name": "研发部",
            "last_login": None,
            "roles": [],
        }
    ]


def test_users_list_filters_to_empty_result_when_department_has_no_users(client_and_db, monkeypatch):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(is_superuser=True)

    app.dependency_overrides[get_current_user] = override_get_current_user
    monkeypatch.setattr(rbac_module.RBACService, "get_user_roles", AsyncMock(return_value=[]))

    all_users = [
        UserRecord(1, "alice", "alice@example.com", department_id=10, department_name="研发部"),
        UserRecord(2, "bob", "bob@example.com", department_id=20, department_name="运营部"),
    ]
    departments = [
        DepartmentRecord(10, "研发部"),
        DepartmentRecord(20, "运营部"),
    ]

    db_session.execute = AsyncMock(
        side_effect=_user_list_execute_side_effect(all_users, departments, [])
    )

    response = client.get("/api/v1/users/", params={"department_id": 99}, follow_redirects=False)

    assert response.status_code == 200
    assert response.json() == []
