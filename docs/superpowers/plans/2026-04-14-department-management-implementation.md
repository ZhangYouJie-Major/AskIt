# Department Management (V1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付可用的部门管理能力（新建、编辑、启停）并在用户管理支持按部门筛选，且仅超级管理员可管理部门。  
**Architecture:** 在现有 `Department`/`User.department_id` 模型上增量实现，后端新增独立 `departments` API，前端新增部门管理页并接入用户筛选。权限不扩展 RBAC 细粒度，仅通过 `is_superuser` 门禁控制。实现顺序采用后端先行、前端接入，避免联调阻塞。  
**Tech Stack:** FastAPI + SQLAlchemy Async + Pydantic、Vue 3 + TypeScript + Element Plus、pytest。

---

## File Structure

- Create: `backend/app/api/departments.py`  
  责任：部门列表/创建/更新/启停 API 与超级管理员访问控制。
- Modify: `backend/app/api/__init__.py`  
  责任：注册 departments 路由。
- Modify: `backend/app/api/users.py`  
  责任：`GET /users` 增加 `department_id` 过滤。
- Create: `backend/tests/test_departments_api.py`  
  责任：部门 API 的权限、校验、启停与过滤测试。
- Create: `backend/tests/test_users_department_filter.py`  
  责任：用户列表部门过滤测试。
- Create: `frontend/src/api/departments.ts`  
  责任：部门管理接口封装。
- Create: `frontend/src/views/DepartmentManageView.vue`  
  责任：部门管理页面（列表、创建、编辑、启停）。
- Modify: `frontend/src/layouts/AdminLayout.vue`  
  责任：新增“部门管理”菜单入口。
- Modify: `frontend/src/router/index.ts`  
  责任：新增 `/admin/departments` 路由。
- Modify: `frontend/src/views/UserManageView.vue`  
  责任：增加部门筛选并透传查询参数。

## Task 1: 后端部门 API 与超管门禁

**Files:**
- Create: `backend/app/api/departments.py`
- Modify: `backend/app/api/__init__.py`
- Test: `backend/tests/test_departments_api.py`

- [ ] **Step 1: 写失败测试（权限门禁 + 列表）**

```python
# backend/tests/test_departments_api.py
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app.api import departments as departments_api


class DummyUser:
    def __init__(self, is_superuser: bool):
        self.id = 1
        self.is_superuser = is_superuser


def create_test_app(user):
    app = FastAPI()
    app.include_router(departments_api.router, prefix="/api/v1")
    app.dependency_overrides[departments_api.get_current_user] = lambda: user
    app.dependency_overrides[departments_api.get_db] = lambda: None
    return app


def test_non_superuser_forbidden():
    app = create_test_app(DummyUser(is_superuser=False))
    client = TestClient(app)
    resp = client.get("/api/v1/departments")
    assert resp.status_code == 403


def test_superuser_can_access_departments_list():
    app = create_test_app(DummyUser(is_superuser=True))
    client = TestClient(app)
    resp = client.get("/api/v1/departments")
    # 初始可返回空数组，但必须成功
    assert resp.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd "backend" && PYTHONPATH=. pytest -q tests/test_departments_api.py -k "forbidden or access"`  
Expected: FAIL，提示 `app.api.departments` 或路由不存在。

- [ ] **Step 3: 最小实现 departments API 与超管校验**

```python
# backend/app/api/departments.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Department, User

router = APIRouter(prefix="/departments", tags=["Departments"])


class DepartmentListItem(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    user_count: int


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅超级管理员可操作")
    return current_user


@router.get("/", response_model=List[DepartmentListItem])
async def list_departments(
    is_active: Optional[bool] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superuser),
):
    query = select(Department)
    if is_active is not None:
        query = query.where(Department.is_active == is_active)
    if keyword:
        query = query.where(Department.name.ilike(f"%{keyword.strip()}%"))
    query = query.order_by(Department.id.asc())
    depts = (await db.execute(query)).scalars().all()

    rows: List[DepartmentListItem] = []
    for d in depts:
        count = await db.scalar(select(func.count(User.id)).where(User.department_id == d.id))
        rows.append(DepartmentListItem(
            id=d.id,
            name=d.name,
            description=d.description,
            is_active=d.is_active,
            user_count=count or 0,
        ))
    return rows
```

- [ ] **Step 4: 注册路由**

```python
# backend/app/api/__init__.py
from app.api import health, query, documents, auth, users, roles, permissions, departments

api_router.include_router(departments.router)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd "backend" && PYTHONPATH=. pytest -q tests/test_departments_api.py -k "forbidden or access"`  
Expected: PASS。

## Task 2: 完成部门创建/编辑/启停接口与校验

**Files:**
- Modify: `backend/app/api/departments.py`
- Test: `backend/tests/test_departments_api.py`

- [ ] **Step 1: 写失败测试（重名、更新、启停）**

```python
def test_create_department_duplicate_name_returns_400(client_superuser):
    payload = {"name": "技术部", "description": "dup"}
    resp = client_superuser.post("/api/v1/departments", json=payload)
    assert resp.status_code == 400


def test_update_department_success(client_superuser):
    resp = client_superuser.put("/api/v1/departments/2", json={"name": "研发部", "description": "研发"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "研发部"


def test_toggle_department_status_success(client_superuser):
    resp = client_superuser.put("/api/v1/departments/2/status", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd "backend" && PYTHONPATH=. pytest -q tests/test_departments_api.py -k "duplicate or update or status"`  
Expected: FAIL，提示 POST/PUT 路由不存在。

- [ ] **Step 3: 最小实现创建/更新/启停逻辑**

```python
class DepartmentCreate(BaseModel):
    name: str
    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str
    description: str | None = None


class DepartmentStatusUpdate(BaseModel):
    is_active: bool


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


@router.post("/", response_model=DepartmentListItem)
async def create_department(data: DepartmentCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_superuser)):
    norm = normalize_name(data.name)
    if not norm:
        raise HTTPException(status_code=400, detail="部门名称不能为空")
    existed = await db.execute(select(Department).where(func.lower(Department.name) == norm.lower()))
    if existed.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="部门名称已存在")
    dept = Department(name=norm, description=data.description, is_active=True)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return DepartmentListItem(id=dept.id, name=dept.name, description=dept.description, is_active=dept.is_active, user_count=0)


@router.put("/{department_id}", response_model=DepartmentListItem)
async def update_department(department_id: int, data: DepartmentUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_superuser)):
    dept = (await db.execute(select(Department).where(Department.id == department_id))).scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")
    norm = normalize_name(data.name)
    existed = await db.execute(select(Department).where(func.lower(Department.name) == norm.lower(), Department.id != department_id))
    if existed.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="部门名称已存在")
    dept.name = norm
    dept.description = data.description
    await db.commit()
    await db.refresh(dept)
    count = await db.scalar(select(func.count(User.id)).where(User.department_id == dept.id))
    return DepartmentListItem(id=dept.id, name=dept.name, description=dept.description, is_active=dept.is_active, user_count=count or 0)


@router.put("/{department_id}/status", response_model=DepartmentListItem)
async def update_department_status(department_id: int, data: DepartmentStatusUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_superuser)):
    dept = (await db.execute(select(Department).where(Department.id == department_id))).scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")
    dept.is_active = data.is_active
    await db.commit()
    await db.refresh(dept)
    count = await db.scalar(select(func.count(User.id)).where(User.department_id == dept.id))
    return DepartmentListItem(id=dept.id, name=dept.name, description=dept.description, is_active=dept.is_active, user_count=count or 0)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd "backend" && PYTHONPATH=. pytest -q tests/test_departments_api.py`  
Expected: PASS。

## Task 3: 用户列表支持部门筛选

**Files:**
- Modify: `backend/app/api/users.py`
- Test: `backend/tests/test_users_department_filter.py`

- [ ] **Step 1: 写失败测试（department_id 过滤）**

```python
def test_list_users_filter_by_department(client_superuser):
    resp = client_superuser.get("/api/v1/users", params={"department_id": 2})
    assert resp.status_code == 200
    assert all(u["department_id"] == 2 for u in resp.json())
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd "backend" && PYTHONPATH=. pytest -q tests/test_users_department_filter.py -v`  
Expected: FAIL，返回未过滤全量数据。

- [ ] **Step 3: 在 users 列表 API 增加过滤参数**

```python
# backend/app/api/users.py
@router.get("/", response_model=List[UserListResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    department_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    query = select(User)
    if department_id is not None:
        query = query.where(User.department_id == department_id)
    result = await db.execute(query.offset(skip).limit(limit).order_by(User.id))
    users = result.scalars().all()
    ...
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd "backend" && PYTHONPATH=. pytest -q tests/test_users_department_filter.py -v`  
Expected: PASS。

## Task 4: 前端接入部门 API 与部门管理页面

**Files:**
- Create: `frontend/src/api/departments.ts`
- Create: `frontend/src/views/DepartmentManageView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/AdminLayout.vue`

- [ ] **Step 1: 新增前端 API 封装**

```ts
// frontend/src/api/departments.ts
import api from './index'

export interface DepartmentItem {
  id: number
  name: string
  description: string | null
  is_active: boolean
  user_count: number
}

export const departmentsApi = {
  list: (params?: { is_active?: boolean; keyword?: string }) =>
    api.get<any, DepartmentItem[]>('/departments/', { params }),
  create: (data: { name: string; description?: string }) =>
    api.post<any, DepartmentItem>('/departments/', data),
  update: (id: number, data: { name: string; description?: string }) =>
    api.put<any, DepartmentItem>(`/departments/${id}`, data),
  updateStatus: (id: number, data: { is_active: boolean }) =>
    api.put<any, DepartmentItem>(`/departments/${id}/status`, data)
}
```

- [ ] **Step 2: 新增部门管理页面（列表+创建/编辑+启停）**

```vue
<!-- frontend/src/views/DepartmentManageView.vue -->
<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>部门管理</span>
        <el-button type="primary" @click="openCreate">新建部门</el-button>
      </div>
    </template>
    <el-table :data="departments" v-loading="loading" stripe>
      <el-table-column prop="name" label="部门名称" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="user_count" label="用户数" width="100" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-switch :model-value="row.is_active" @change="(v:boolean) => onToggleStatus(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
```

- [ ] **Step 3: 路由与菜单接入**

```ts
// frontend/src/router/index.ts
{
  path: 'departments',
  name: 'DepartmentManage',
  component: () => import('@/views/DepartmentManageView.vue'),
  meta: { title: '部门管理' }
}
```

```vue
<!-- frontend/src/layouts/AdminLayout.vue -->
<el-menu-item index="/admin/departments">
  <el-icon><OfficeBuilding /></el-icon>
  <span>部门管理</span>
</el-menu-item>
```

- [ ] **Step 4: 本地运行验证**

Run:
- `cd "frontend" && npm run dev`
- 手工验证 `/admin/departments` 页面加载、创建、编辑、启停成功。  
Expected: 页面操作成功，失败时出现后端返回错误提示。

## Task 5: 用户管理页面增加部门筛选

**Files:**
- Modify: `frontend/src/views/UserManageView.vue`
- Modify: `frontend/src/api/auth.ts`（仅类型复用时）

- [ ] **Step 1: 增加筛选 UI 与请求参数**

```ts
const filterDepartmentId = ref<number | null>(null)

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await api.get('/users/', {
      params: {
        skip: (currentPage.value - 1) * pageSize.value,
        limit: pageSize.value,
        department_id: filterDepartmentId.value ?? undefined
      }
    })
    users.value = Array.isArray(response) ? response : []
    total.value = users.value.length
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 2: 在页面顶部添加筛选控件**

```vue
<el-select v-model="filterDepartmentId" placeholder="按部门筛选" clearable @change="loadUsers">
  <el-option v-for="dept in departments" :key="dept.id" :label="dept.name" :value="dept.id" />
</el-select>
```

- [ ] **Step 3: 运行与回归验证**

Run:
- `cd "frontend" && npm run dev`
- 登录超管，进入 `/admin/users`：
  - 选择部门后数据收敛到该部门
  - 清空筛选后恢复全量  
Expected: 筛选行为稳定，无控制台异常。

## Task 6: 验收测试与文档更新

**Files:**
- Modify: `README.md`（如需更新功能勾选）
- Modify: `docs/superpowers/specs/2026-04-14-department-management-design.md`（仅在实现偏差时回写）

- [ ] **Step 1: 后端回归**

Run: `cd "backend" && PYTHONPATH=. pytest -q tests/test_departments_api.py tests/test_users_department_filter.py tests/test_rbac_models.py tests/test_rbac_service.py tests/test_rbac_dependencies.py`  
Expected: 全部 PASS。

- [ ] **Step 2: 前端关键路径手测**

Run: `cd "frontend" && npm run dev`  
Checklist:
- 超管可访问部门管理页
- 非超管访问部门管理相关操作被后端拒绝（403）
- 用户页部门筛选生效
- 部门启停后用户编辑下拉只显示启用部门  
Expected: 与 spec 一致。

- [ ] **Step 3: 文档一致性检查**

```bash
cd "docs/superpowers"
rg -n "部门管理|departments|department_id" specs plans
```

Expected: 设计文档与实施结果一致，无冲突描述。

## 计划自检（Spec Coverage）

- 覆盖“独立部门管理 API”：Task 1、Task 2。  
- 覆盖“仅超级管理员可管理部门”：Task 1。  
- 覆盖“用户列表按部门筛选”：Task 3、Task 5。  
- 覆盖“前端部门管理页面”：Task 4。  
- 覆盖“启停不删除策略”：Task 2、Task 6。  

## 计划自检（Placeholder Scan）

- 已检查无 `TODO/TBD/implement later`。  
- 每个任务均包含具体文件、代码片段、命令与预期结果。  

## 计划自检（Type Consistency）

- 后端统一使用 `department_id` 作为筛选参数名。  
- 前端接口与视图统一使用 `DepartmentItem` 结构。  
- 状态字段统一为 `is_active`。  

