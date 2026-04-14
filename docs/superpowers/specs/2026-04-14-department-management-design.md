# 部门管理功能设计（V1）

## 1. 目标与范围

### 1.1 目标

在现有 RBAC 与用户体系上新增独立“部门管理”能力，支持部门新建、编辑、启用/停用，并在用户管理页面提供按部门筛选。

### 1.2 范围（In Scope）

- 后端新增独立部门管理 API：`/api/v1/departments`
- 前端新增部门管理页面（管理后台）
- 用户管理页面新增部门筛选
- 部门管理仅允许 `is_superuser=true` 用户访问

### 1.3 非范围（Out of Scope）

- 不做部门删除
- 不新增 RBAC 权限项（如 `department:write`）
- 不改动现有角色权限模型

## 2. 现状与约束

- 数据库已存在 `departments` 表，`users.department_id` 已关联部门。
- 当前用户创建/编辑已支持选择部门，但缺少独立部门管理接口与页面。
- 当前请求方已确认：
  - V1 只做启用/停用，不删除部门
  - 管理权限仅超级管理员
  - 用户列表需要支持按部门筛选

## 3. 表设计与迁移策略（V1）

### 3.1 表设计结论

V1 **不新增表、不改字段**，直接复用现有模型与关系：

- `departments`
  - `id` (PK)
  - `name` (unique)
  - `description`
  - `is_active`
  - `created_at`
  - `updated_at`
- `users`
  - `department_id` (FK -> `departments.id`, nullable)

### 3.2 数据约束

- 保持数据库唯一约束：`departments.name` 唯一。
- 业务层补充规范化校验：
  - 写入前 `trim(name)`
  - 名称比较按大小写不敏感处理（避免 `技术部` 与 `技术部 ` 或大小写变体重复）
- V1 不做“删除部门”，因此不引入级联删除策略变更。

### 3.3 索引与性能

- 当前已存在主键和 `name` 唯一索引，满足 V1 查询需求。
- 用户列表按 `department_id` 过滤依赖既有索引即可。
- V1 不新增索引；若后续出现慢查询，再补充评估（YAGNI）。

### 3.4 迁移策略

- V1 无 DDL 迁移脚本。
- 仅需要应用层接口与前端页面变更。
- 部署风险低，可按“后端先行 -> 前端接入”分步上线。

## 4. 架构设计

### 4.1 后端模块边界

- 新增：`backend/app/api/departments.py`
  - 职责：部门列表、新建、编辑、状态切换
- 复用：`backend/app/models/models.py` 中 `Department` 模型
- 扩展：`backend/app/api/users.py` 的列表接口增加 `department_id` 过滤参数

保持单一职责：部门管理由独立模块承担，不并入 users 路由。

### 4.2 前端模块边界

- 新增：`frontend/src/api/departments.ts`
- 新增：`frontend/src/views/DepartmentManageView.vue`
- 修改：`frontend/src/router/index.ts`（增加 `/admin/departments`）
- 修改：`frontend/src/views/UserManageView.vue`（新增部门筛选）

## 5. API 设计

### 5.1 权限策略

- 部门管理 API 统一使用“超级管理员门禁”：
  - 未登录：401
  - 已登录但非超级管理员：403

### 5.2 接口定义

#### GET `/api/v1/departments`

- Query：
  - `is_active`（可选）
  - `keyword`（可选，按名称模糊匹配）
- Response（数组）：
  - `id`
  - `name`
  - `description`
  - `is_active`
  - `user_count`
  - `created_at`
  - `updated_at`

#### POST `/api/v1/departments`

- Body：
  - `name`（必填，唯一）
  - `description`（可选）
- 校验：
  - 名称 `trim` 后不能为空
  - 名称比较按“大小写不敏感 + 去首尾空格”
  - 冲突返回 400

#### PUT `/api/v1/departments/{id}`

- Body：
  - `name`
  - `description`
- 校验：
  - 部门不存在返回 404
  - 名称冲突返回 400

#### PUT `/api/v1/departments/{id}/status`

- Body：
  - `is_active: boolean`
- 规则：
  - 仅启用/停用，不删除
  - 停用时不阻断已有用户关联（避免引入迁移流程），但返回 `warning` 提示

### 5.3 用户列表过滤扩展

#### GET `/api/v1/users`

- 新增 Query：
  - `department_id`（可选）
- 行为：
  - 传入时按部门过滤
  - 不传保持原行为

## 6. 前端交互设计

### 6.1 部门管理页

- 列表列：
  - 部门名称、描述、用户数、状态、创建时间、更新时间、操作
- 操作：
  - 新建部门
  - 编辑部门
  - 启用/停用开关
- 状态切换：
  - 停用成功后若后端返回 warning，UI 使用非阻断提示展示

### 6.2 用户管理页增强

- 在表格上方增加“部门筛选”下拉（默认“全部”）
- 选择后重新请求 `/users?department_id=...`

## 7. 数据一致性与校验规则

- 部门名称规范化：
  - 存储值保留用户输入（trim 后）
  - 唯一性比较使用 case-insensitive 语义
- 停用部门不影响历史数据读取
- 用户创建/编辑应仅允许选择“启用中的部门”（前端限制 + 后端校验）

## 8. 错误处理

- 401：未登录
- 403：非超级管理员访问部门管理接口
- 404：部门不存在
- 400：部门名称冲突、非法输入
- 422：请求体格式错误（沿用 FastAPI 默认）

## 9. 测试设计

### 9.1 后端测试

- `departments` API：
  - 列表（含过滤）
  - 新建成功
  - 新建重名失败
  - 编辑成功
  - 编辑重名失败
  - 启停成功
  - 非超级管理员访问 403
- `users` API：
  - `department_id` 过滤命中
  - `department_id` 过滤空结果

### 9.2 前端测试（手工/组件级）

- 部门管理页：
  - 列表加载与状态展示
  - 新建/编辑表单校验
  - 启停交互与提示
- 用户管理页：
  - 筛选条件切换后请求参数正确
  - 筛选结果与“全部”回退正确

## 10. 分阶段实施建议

### Phase 1：后端先行

- 完成 departments API
- 完成 users 列表部门过滤
- 完成后端单测

### Phase 2：前端接入

- 新增部门管理页与路由
- 用户页部门筛选
- 联调与验收

## 11. 验收标准

- 超级管理员可完成部门新建、编辑、启停
- 非超级管理员无法访问部门管理接口（403）
- 用户列表可按部门筛选并返回正确结果
- 停用部门后系统仍可稳定读取历史关联数据
