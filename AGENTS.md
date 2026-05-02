# AskIt - 项目开发指南

## 项目概述

**AskIt** 是一个企业级 RAG（检索增强生成）知识库系统，支持多格式文档上传、智能检索和问答。

## 技术栈

### 后端
- **框架**: FastAPI + LangChain + LangGraph
- **包管理**: `uv`（优先使用，不要用 pip）
- **数据库**: PostgreSQL（关系数据）+ Chroma（向量数据库）
- **文件存储**: MinIO
- **缓存/任务队列**: Redis + Celery
- **ORM**: SQLAlchemy 2.0（异步）+ Alembic（迁移）
- **认证**: JWT（python-jose）+ passlib/bcrypt
- **日志**: loguru

### 前端
- **框架**: Vue 3 + TypeScript
- **UI 组件**: Element Plus
- **构建工具**: Vite
- **包管理**: npm

## 项目结构

```
AskIt/
├── backend/
│   ├── app/
│   │   ├── api/            # API 路由（auth, documents, query, health）
│   │   ├── core/           # 核心配置（config, database, auth）
│   │   ├── models/         # SQLAlchemy 数据模型
│   │   ├── services/       # 业务逻辑（RAG, 向量存储, 文档处理）
│   │   ├── tasks/          # Celery 异步任务
│   │   └── utils/          # 工具函数
│   ├── alembic/            # 数据库迁移
│   ├── scripts/            # 初始化脚本
│   ├── tests/              # 测试
│   └── pyproject.toml      # 依赖声明
├── frontend/
│   └── src/
│       ├── api/            # API 调用层
│       ├── components/     # 公共组件
│       ├── views/          # 页面（KnowledgeView, AdminView）
│       ├── stores/         # Pinia 状态管理
│       └── router/         # Vue Router
├── deploy/                 # 部署配置
└── docker-compose.yml
```

## 开发命令

### 后端

```bash
cd backend

# 安装依赖（使用 uv，不要用 pip install）
uv sync

# 启动开发服务器
uv run uvicorn app.main:app --reload

# 数据库迁移
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "描述"

# 运行测试
uv run pytest

# 启动 Celery Worker
uv run celery -A app.tasks worker --loglevel=info
```

### 前端

```bash
cd frontend

npm install
npm run dev
npm run build
```

### Docker（推荐）

```bash
docker-compose up -d       # 启动全部服务
docker-compose logs -f     # 查看日志
docker-compose down        # 停止服务
```

## 关键约定

### 后端

1. **包管理严格使用 `uv`**，不要使用 `pip install` 直接安装
2. **异步优先**：数据库操作使用 `async/await` + asyncpg
3. **响应格式**统一使用包含 `success`, `data`, `message` 字段的信封格式
4. **配置**统一从 `app.core.config.settings` 读取，不要硬编码
5. **日志**使用 `loguru` 的 `logger`，不要用 `print`
6. **API 路由**在 `app/api/` 下按功能模块划分

### 前端

1. Vue 3 Composition API（`<script setup>` 语法）
2. TypeScript 严格模式
3. API 调用封装在 `src/api/` 目录

## 默认账号

- 管理员: `admin` / `AskIt@2026!Admin`
- 测试用户: `testuser` / `Test@2026!User`

> ⚠️ 生产环境请立即修改默认密码！

## 环境变量

后端环境变量在 `backend/.env`（从 `.env.example` 复制），主要包括：
- 数据库连接（PostgreSQL, Redis, Chroma）
- MinIO 配置
- JWT 密钥
- OpenAI/LLM API Key

## 功能进度

### 已基本完成

- [x] 用户认证与授权（JWT）
- [x] 登录状态持久化
- [x] RBAC 用户、角色、权限管理
- [x] 部门管理基础能力

### 半成品 / 待闭环

- [ ] 多格式文档上传：接口和元数据记录已存在，但文件存储、解析、分块、向量化主链路尚未完整接通
- [ ] 文档解析与向量化：解析器、分块器、Embedding 组件已有雏形，尚未接入上传后的正式处理流水线
- [ ] 语义检索（RAG）：查询服务已存在，但依赖文档入库和向量检索链路闭环
- [ ] 部门级文档权限隔离：列表和查询已有部门过滤，文档详情、删除等接口仍需补齐权限校验
- [ ] 文档管理后台：已有页面雏形，未形成完整管理闭环

### 未真正完成

- [ ] OCR 图片识别
- [ ] Excel / PPT 正式解析入库
- [ ] 混合增强检索（文档 + 联网）
- [ ] 系统监控
