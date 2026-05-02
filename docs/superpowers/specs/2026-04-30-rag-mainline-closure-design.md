# AskIt RAG 主链路闭环设计

## 1. 目标

本设计覆盖下一阶段 `P0 + P1`，目标是把 AskIt 从“管理基础可用、RAG 链路半成品”推进到“本地可稳定启动，并且上传文档后可以被检索问答命中”。

本阶段只追求最短真实闭环：

- 后端服务可启动
- Celery 文档任务可导入、可执行
- 上传文件真实落盘并落库
- 文档解析、分块、Embedding、Chroma 入库串起来
- 查询接口能命中刚上传并处理完成的文档
- 删除文档时清理文件、分块和向量
- 文档接口补齐登录、部门权限校验
- 前端能看到文档处理状态和失败原因

## 2. 非目标

以下能力暂不进入本阶段，避免拉大范围：

- OCR 图片识别
- Excel / PPT 正式解析入库
- 联网增强检索
- MinIO 生产级对象存储接入
- 完整系统监控
- 会话持久化
- 复杂后台统计大屏

## 3. 当前问题

### 3.1 可运行性问题

- 默认 `CHROMA_MODE=cloud` 时，`app.services.vector_store.VectorStore` 在导入期调用 `chromadb.Client(api_key=...)`，当前依赖版本不接受该参数，导致 `app.main` 无法启动。
- `app.tasks.document_tasks` 引用了不存在的 `app.services.embeddings`，Celery worker 导入会失败。
- 部分旧测试手写源码相对路径，导致 `uv run pytest` 在收集阶段失败。

### 3.2 文档主链路问题

- 上传接口只创建 `documents` 记录，没有保存文件，也没有触发处理任务。
- 文档处理任务仍是示例逻辑，没有读取真实文件、解析、分块、写入 `document_chunks` 和 Chroma。
- 查询接口已经存在，但依赖向量库中有数据；当前上传链路无法产出可检索数据。
- 删除接口只删除 `documents` 主记录，没有同步删除文件、分块和向量。

### 3.3 权限问题

- 文档列表和查询按当前用户部门过滤。
- 文档详情、删除接口缺少登录依赖和部门校验，存在跨部门访问风险。

## 4. 推荐方案

采用“先真实闭环，再完善生产存储”的方案。

本阶段使用本地 `backend/uploads` 作为真实文件存储，保留 `DocumentStorageService` 边界，后续可替换为 MinIO。这样可以先把 RAG 主链路做实，不把对象存储桶初始化、鉴权、网络错误和主链路调试混在一起。

Chroma 本阶段同时支持 Cloud 和本地模式：

- `cloud` 模式使用 `chromadb.CloudClient(api_key=..., tenant=..., database=...)`，凭据只从 `.env` 读取，不硬编码到代码或文档。
- `local` 模式使用 `chromadb.PersistentClient(path=...)`，用于离线开发、单元测试和 CI fallback。

当前云端测试账号可作为 P0 集成验证环境，但不能写入仓库。

## 5. 后端设计

### 5.1 配置与启动

调整目标：

- Cloud 模式按当前 Chroma SDK 改为 `CloudClient`。
- 本地开发保留 `CHROMA_MODE=local` 可用路径。
- `VectorStore` 不应在模块导入时让整个应用启动失败；初始化失败要给出明确日志。
- `app.main`、`app.tasks`、`app.services.document_processing` 都必须可以直接导入。

验收：

- `uv run python -c "from app.main import app"` 成功。
- `uv run python -c "import app.tasks.document_tasks"` 成功。
- `uv run uvicorn app.main:app --reload` 可启动。
- `CHROMA_MODE=cloud` 且 `.env` 配置完整时，向量库使用 `chromadb.CloudClient` 初始化。
- `CHROMA_MODE=local` 时，向量库使用本地 `PersistentClient` 初始化。

### 5.2 文件存储服务

新增或整理一个很薄的文件存储边界：

- `save_upload(file, stored_filename) -> file_path`
- `delete(file_path) -> None`
- `exists(file_path) -> bool`

V1 使用本地文件系统：

- 存储目录来自配置，默认 `uploads/`
- 文件名使用 UUID + 原始扩展名
- 数据库 `Document.file_path` 保存相对路径或可解析的本地路径

失败处理：

- 文件保存失败时不创建数据库记录。
- 数据库提交失败时删除已保存文件，避免孤儿文件。

### 5.3 上传接口

`POST /api/v1/documents/upload` 流程：

1. 校验登录用户。
2. 校验文件名、扩展名、大小。
3. 保存文件。
4. 创建 `Document`，状态为 `pending`。
5. 触发 `process_document` Celery 任务。
6. 返回文档元数据。

部门规则：

- 文档归属当前用户 `department_id`。
- 当前用户没有部门时不再静默落到 `1`，应明确报错或通过配置指定默认部门。本阶段建议报错，避免隐藏权限归属。

### 5.4 文档处理服务

新增核心服务 `DocumentProcessingService`，Celery 任务只负责调用它，业务逻辑不写在任务函数里。

处理流程：

1. 加载 `Document`。
2. 将状态更新为 `processing`。
3. 根据 `file_type` 选择解析器。
4. 得到 `ParsedDocument`，回写 `content/title/page_count`。
5. 使用 `DocumentChunker` 分块。
6. 调用 `EmbeddingService` 批量生成向量。
7. 写入 `document_chunks`，保存 `vector_id`。
8. 写入 Chroma，metadata 至少包含：
   - `document_id`
   - `chunk_id`
   - `filename`
   - `department_id`
   - `content`
9. 回写 `status=completed`、`vectorized=true`、`chunk_count`。

失败处理：

- 任一步骤失败，回写 `status=failed`、`error_message`。
- 如果已写入部分 chunk 或 vector，尽量清理已生成数据。
- 日志必须包含 `document_id`、文件名、处理阶段和异常信息。

### 5.5 Celery 任务

`process_document(document_id)` 只做三件事：

- 创建数据库 session。
- 调用 `DocumentProcessingService.process(document_id)`。
- 返回处理结果摘要。

保留任务：

- `process_document`
- `batch_process_documents`
- `rebuild_vector_index`

本阶段不实现 `cleanup_old_documents` 的定时清理逻辑，也不在 README 中声明为完成。

### 5.6 删除接口

`DELETE /api/v1/documents/{document_id}` 流程：

1. 校验登录用户。
2. 查询文档并校验部门权限。
3. 查询关联 `document_chunks` 的 `vector_id`。
4. 删除 Chroma 向量。
5. 删除本地文件。
6. 删除数据库记录，依赖 chunk 级联或显式删除。

失败策略：

- 文档不存在返回 404。
- 跨部门访问返回 404 或 403。本阶段建议返回 404，减少信息泄露。
- 向量删除失败时不应静默成功；需要返回错误或标记清理失败。

### 5.7 查询接口

保留现有 `POST /api/v1/query/` 合同。

增强点：

- 仅检索当前用户部门数据。
- Chroma metadata 中必须有 `department_id`，并在搜索时使用 where 过滤。
- sources 返回的 `document_id`、`chunk_id`、`filename`、`score` 保持不变。

本阶段不做会话持久化，前端继续传临时 history。

## 6. 前端设计

### 6.1 文档管理入口

把已有文档管理页纳入管理后台，最小目标是：

- 文档列表来自真实 `/documents`
- 上传后显示 `pending/processing/completed/failed`
- 展示 `chunk_count`、`vectorized`
- 失败时展示 `error_message`
- 删除按钮调用真实删除接口

### 6.2 状态刷新

V1 使用简单刷新策略：

- 上传成功后立即刷新列表。
- 如果存在 `pending/processing` 文档，页面每 3-5 秒轮询一次。
- 没有处理中任务时停止轮询。

不引入 WebSocket 或 SSE。

## 7. 测试设计

### 7.1 启动与导入测试

- `app.main` 可导入。
- `app.tasks.document_tasks` 可导入。
- `app.services.document_processing` 可导入。
- Chroma Cloud 初始化逻辑可通过 mock 验证使用 `CloudClient` 和环境变量参数。
- Chroma local 初始化逻辑可验证使用 `PersistentClient`。
- `uv run pytest` 能完成收集。

### 7.2 文档上传测试

- 未登录上传返回 401。
- 不支持扩展名返回 400。
- 超过大小限制返回 400。
- 正常 txt/md 上传后文件存在，数据库记录为 `pending`，任务被触发。
- 用户无部门时返回明确错误。

### 7.3 文档处理测试

使用 fake embedding 和 fake vector store：

- txt/md 文件可处理为 `completed`。
- 生成 `document_chunks`。
- `vector_id` 被保存。
- `chunk_count` 正确。
- 解析失败回写 `failed` 和 `error_message`。

### 7.4 删除与权限测试

- 同部门用户可查看、删除文档。
- 跨部门用户不能查看、删除文档。
- 删除后文件不存在，chunk 不存在，vector 删除被调用。

### 7.5 前端验证

- `npm run build` 通过。
- 上传、状态刷新、失败展示、删除在浏览器手工验证通过。

## 8. 实施顺序

### Phase 1：可运行性修复

- 修 Chroma CloudClient 初始化和 local fallback。
- 修 Celery 任务导入。
- 修 pytest 收集路径问题。

### Phase 2：上传与存储

- 新增文件存储服务。
- 上传接口保存真实文件。
- 上传成功后触发文档处理任务。

### Phase 3：处理流水线

- 实现 `DocumentProcessingService`。
- 接入解析、分块、Embedding、Chroma、chunk 入库。
- 完成失败状态回写。

### Phase 4：删除与权限

- 文档详情、删除接口补登录和部门校验。
- 删除文件、chunk、vector。

### Phase 5：前端状态闭环

- 接入文档管理入口。
- 展示真实状态和失败原因。
- 加最小轮询。

## 9. 验收标准

本阶段完成后，应满足：

- 后端服务和 Celery worker 可启动。
- 上传一个 txt 或 md 文档后，最终状态变为 `completed`。
- `document_chunks` 中有对应分块。
- Chroma 中有对应向量 metadata。
- 查询刚上传文档中的内容能返回相关答案和 sources。
- 删除文档后，文件、chunk、向量均被清理。
- 跨部门用户不能访问或删除他人部门文档。
- `uv run pytest` 可正常收集并通过本阶段核心测试。
- `npm run build` 通过。

## 10. 后续扩展

主链路稳定后再分阶段推进：

- Excel / PPT 解析器
- OCR 图片识别
- MinIO 生产存储
- 文档处理重试和后台重建索引
- 会话持久化
- 系统监控
- 联网增强检索
