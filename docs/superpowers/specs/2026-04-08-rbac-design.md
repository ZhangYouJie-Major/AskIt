# RBAC 权限系统设计

## 概述

为企业级 RAG 知识库系统实现基于功能的角色访问控制（RBAC）。

## 需求确认

- 功能级权限控制（9个基础权限）
- 完全自定义角色（管理员自由创建）
- 数据库驱动
- 多角色支持（用户可拥有多个角色，权限取并集）
- 全局权限，部门隔离在数据层

## 数据模型

### Permission（权限表）

9条固定记录，不可修改：

| 权限标识 | 说明 |
|---------|------|
| `user:read` | 查看用户 |
| `user:write` | 创建/编辑用户 |
| `user:delete` | 删除用户 |
| `document:read` | 查看文档 |
| `document:write` | 上传/编辑文档 |
| `document:delete` | 删除文档 |
| `query:execute` | 发起问答 |
| `settings:read` | 查看配置 |
| `settings:write` | 修改配置 |

### Role（角色表）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| name | String(50) | 角色名（唯一） |
| description | Text | 描述 |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### RolePermission（角色-权限关联表）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| role_id | Integer | 角色ID（外键） |
| permission_id | Integer | 权限ID（外键） |

唯一索引：(role_id, permission_id)

### UserRole（用户-角色关联表）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户ID（外键） |
| role_id | Integer | 角色ID（外键） |
| created_at | DateTime | 分配时间 |

唯一索引：(user_id, role_id)

### User 模型变更

保留现有 `is_superuser` 字段：
- `is_superuser=True` → 自动拥有全部权限（忽略 RolePermission 计算）

## API 设计

### 权限

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/permissions` | 获取所有权限列表 |

### 用户管理

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/users` | 用户列表（分页） |
| POST | `/api/users` | 创建用户 |
| GET | `/api/users/{id}` | 获取用户详情（含角色） |
| PUT | `/api/users/{id}` | 更新用户 |
| DELETE | `/api/users/{id}` | 删除用户 |
| GET | `/api/users/{id}/roles` | 获取用户角色 |
| POST | `/api/users/{id}/roles` | 分配角色（单/批量） |
| DELETE | `/api/users/{id}/roles/{role_id}` | 移除用户角色 |

### 角色管理

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/roles` | 角色列表 |
| POST | `/api/roles` | 创建角色 |
| GET | `/api/roles/{id}` | 获取角色详情（含权限） |
| PUT | `/api/roles/{id}` | 更新角色 |
| DELETE | `/api/roles/{id}` | 删除角色 |
| PUT | `/api/roles/{id}/permissions` | 更新角色权限 |

### 请求/响应示例

**POST /api/users/{id}/roles** (批量分配)
```json
// Request
{ "role_ids": [1, 2, 3] }

// Response
{ "success": true, "message": "已分配 3 个角色" }
```

**PUT /api/roles/{id}/permissions** (更新权限)
```json
// Request
{ "permission_ids": [1, 2, 3, 5] }

// Response
{ "success": true, "role": { "id": 1, "name": "编辑器", "permissions": [...] } }
```

## 权限检查机制

### 依赖注入

```python
# 单权限检查
@router.delete("/{id}")
async def delete_user(id: int, _: User = Depends(require_permission("user:delete"))):
    ...

# 多权限检查（需全部拥有）
@router.put("/{id}")
async def update_user(id: int, _: User = Depends(require_permissions(["user:read", "user:write"]))):
    ...

# 超级用户跳过检查
@require_permission("user:delete")
async def delete_user(...):
    # is_superuser=True 的用户直接通过
    ...
```

### 权限计算

```
用户权限 = {
    is_superuser=True → 全部权限
    is_superuser=False → 所有角色的权限并集
}
```

## 前端页面

### 用户管理 (/admin/users)

- 用户列表（表格）
  - 列：用户名、邮箱、部门、角色、状态、最后登录、操作
  - 支持分页、搜索
- 新建用户对话框
- 编辑用户对话框
- 角色分配抽屉

### 角色管理 (/admin/roles)

- 角色列表（表格）
  - 列：角色名、描述、权限数量、用户数、状态、操作
- 新建角色对话框
- 编辑角色抽屉
  - 权限配置（Checkbox 多选列表）

## 目录结构

```
backend/app/
├── models/
│   └── rbac.py          # Role, Permission, RolePermission, UserRole
├── api/
│   ├── users.py         # 用户管理 API
│   ├── roles.py         # 角色管理 API
│   └── permissions.py   # 权限查询 API
├── core/
│   └── rbac.py          # 权限检查依赖
└── services/
    └── rbac.py          # RBAC 业务逻辑

frontend/src/
├── views/
│   ├── UserManageView.vue
│   └── RoleManageView.vue
├── api/
│   └── rbac.ts          # RBAC API 调用
└── router/
    └── index.ts         # 添加路由
```

## 实现步骤

1. 创建数据模型（Permission, Role, RolePermission, UserRole）
2. 创建权限检查依赖
3. 实现权限 API
4. 实现用户管理 API（含角色分配）
5. 实现角色管理 API（含权限配置）
6. 创建数据库迁移
7. 实现前端 API 调用层
8. 实现前端用户管理页面
9. 实现前端角色管理页面
10. 添加路由和菜单
11. 测试

## 注意事项

- 权限标识使用 `resource:action` 格式（小写）
- 删除角色时检查是否有用户使用
- 删除用户时自动清理 UserRole 关联
- 超级用户（is_superuser）拥有全部权限
- 部门数据隔离在 Document 等其他模型中处理
