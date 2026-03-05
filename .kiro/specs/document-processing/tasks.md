# 实现计划：文档处理功能

## 概述

基于需求文档和技术设计，将文档处理流程分解为以下实现步骤。使用 Python + FastAPI + Celery 技术栈，按照解析 → 分块 → 向量化 → 存储 → 异步任务的顺序逐步实现。

## 任务列表

- [x] 1. 创建核心数据结构和异常类
  - 在 `backend/app/services/document_processing/` 目录下创建模块结构
  - 定义 `ParsedDocument`、`TextChunk`、`ProcessingResult` 数据类
  - 定义 `ChunkStrategy` 枚举（SIMPLE、SMART、PARAGRAPH）
  - 定义自定义异常类：`UnsupportedFileTypeError`、`FileParseError`、`EmbeddingAPIError`、`DocumentProcessingError`
  - _需求: 1.5, 1.6, 1.7, 2.8, 3.7, 5.9_

- [ ] 2. 实现文件解析器（File Parser）
  - [ ] 2.1 实现 `FileParser` 抽象基类和 `FileParserFactory` 工厂类
    - 创建 `backend/app/services/document_processing/parsers.py`
    - 实现工厂方法，根据文件扩展名返回对应解析器
    - _需求: 1.5, 1.7_

  - [ ] 2.2 实现 `PDFParser`
    - 使用 PyPDF2 提取 PDF 文本内容和页码信息
    - 处理损坏文件的异常，抛出 `FileParseError`
    - _需求: 1.1, 1.6_

  - [ ] 2.3 实现 `WordParser`、`TextParser`、`MarkdownParser`
    - `WordParser`: 使用 python-docx 提取段落结构
    - `TextParser` / `MarkdownParser`: 读取完整文本内容，保留格式标记
    - _需求: 1.2, 1.3, 1.4, 1.6_

  - [ ]* 2.4 为文件解析器编写单元测试
    - 测试各格式解析器的正常路径和错误路径
    - 测试不支持格式时抛出 `UnsupportedFileTypeError`
    - _需求: 1.5, 1.6_

- [ ] 3. 实现文档分块器（Document Chunker）
  - [ ] 3.1 实现 `DocumentChunker` 核心类和 SIMPLE 策略
    - 创建 `backend/app/services/document_processing/chunker.py`
    - 实现固定大小分块，支持 `chunk_size` 和 `chunk_overlap` 配置
    - 为每个块生成序号和元数据
    - _需求: 2.1, 2.2, 2.8_

  - [ ] 3.2 实现 SMART 分块策略
    - 在自然边界（空格、换行、句号）处调整分割点
    - 中文文本优先在句号、问号、感叹号等标点处分割
    - 超大段落强制分割并保留重叠区域
    - _需求: 2.3, 2.4, 2.7_

  - [ ] 3.3 实现 PARAGRAPH 分块策略和章节感知分割
    - 优先在段落边界处分割
    - 识别 Markdown 标题层级，在标题处优先分割
    - 识别代码块并保持完整性
    - 在日志中记录使用的策略类型
    - _需求: 2.5, 2.6, 9.1, 9.3, 9.4, 9.6_

  - [ ]* 3.4 为分块器编写属性测试
    - **属性 1：分块覆盖完整性** — 所有分块内容拼接（去除重叠）应覆盖原始文本的全部内容
    - **验证需求: 2.1, 2.2**

  - [ ]* 3.5 为分块器编写单元测试
    - 测试重叠区域是否正确保留
    - 测试中英文边界分割逻辑
    - 测试代码块完整性保持
    - _需求: 2.3, 2.4, 2.5, 2.6_

- [ ] 4. 检查点 — 确保所有测试通过，如有问题请告知用户

- [ ] 5. 实现 Embedding 服务（Embedding Service）
  - [ ] 5.1 实现 `EmbeddingService` 基础结构和 OpenAI 提供商支持
    - 创建 `backend/app/services/document_processing/embedding.py`
    - 使用 OpenAI SDK，通过 `base_url` 参数支持多提供商切换
    - 实现批量处理逻辑（每批最多 100 个文本）
    - _需求: 3.1, 3.2, 3.5_

  - [ ] 5.2 实现 GLM 和 Qwen 提供商配置
    - 配置 GLM base_url: `https://open.bigmodel.cn/api/paas/v4`
    - 配置 Qwen base_url: `https://dashscope.aliyuncs.com/compatible-mode/v1`
    - 支持通过配置文件指定 `embedding_model` 名称
    - 在日志中记录提供商、模型名称和向量维度
    - _需求: 3.3, 3.4, 3.10, 3.11_

  - [ ] 5.3 实现重试机制和向量维度验证
    - API 失败时重试最多 3 次，间隔递增（1s、2s、4s）
    - 验证返回向量维度与配置一致
    - 记录 API 响应状态码和错误消息
    - _需求: 3.6, 3.7, 3.8, 3.9_

  - [ ]* 5.4 为 Embedding 服务编写属性测试
    - **属性 2：向量输出数量一致性** — 输入 N 个文本，输出必须恰好 N 个向量
    - **验证需求: 3.8**

  - [ ]* 5.5 为 Embedding 服务编写单元测试（使用 mock）
    - 测试重试逻辑（模拟 API 失败场景）
    - 测试批次分割逻辑（超过 100 个文本时）
    - 测试向量维度不匹配时抛出异常
    - _需求: 3.6, 3.7, 3.9_

- [ ] 6. 扩展 Vector Store（向量存储）
  - [ ] 6.1 在 `backend/app/services/vector_store.py` 中添加 `insert_document_chunks` 方法
    - 生成格式为 `doc_{document_id}_chunk_{chunk_index}` 的唯一 Vector_ID
    - 批量插入向量和元数据（document_id、chunk_id、filename、department_id、page_number、content）
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 6.2 添加 `delete_document_vectors` 方法
    - 根据 document_id 删除所有关联向量
    - 存储失败时抛出异常并保留详细错误信息
    - _需求: 4.6, 4.7, 6.6_

  - [ ]* 6.3 为 Vector Store 扩展方法编写单元测试
    - 测试批量插入返回正确数量
    - 测试删除操作的完整性
    - _需求: 4.5, 4.7_

- [ ] 7. 实现文档处理器（Document Processor）
  - [ ] 7.1 实现 `DocumentProcessor` 核心处理流程
    - 创建 `backend/app/services/document_processing/processor.py`
    - 实现 `process_document` 方法，按顺序执行：解析 → 分块 → 向量化 → 存储向量 → 创建分块记录 → 更新文档状态
    - 处理开始时更新状态为 "processing"，成功后更新为 "completed"
    - _需求: 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ] 7.2 实现错误处理和状态管理
    - 任何步骤失败时更新状态为 "failed" 并记录 `error_message`
    - 成功时更新 `vectorized=true` 和 `chunk_count` 字段
    - _需求: 5.7, 5.8, 6.1, 6.2, 6.3, 6.4_

  - [ ] 7.3 实现性能监控和结构化日志
    - 记录每个处理阶段的耗时（解析、分块、向量化、存储）
    - 记录总耗时和处理速度（字符数/秒）
    - 使用 INFO/WARNING/ERROR 不同日志级别
    - 日志包含文档 ID、文件名、处理阶段、时间戳
    - _需求: 5.9, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [ ]* 7.4 为文档处理器编写属性测试
    - **属性 3：处理幂等性** — 对同一文档重复处理，最终分块数量应保持一致
    - **验证需求: 5.4, 5.6**

  - [ ]* 7.5 为文档处理器编写单元测试
    - 测试成功流程中各字段的正确更新
    - 测试失败时状态正确回写为 "failed"
    - _需求: 5.7, 5.8_

- [ ] 8. 实现 Celery 异步任务
  - [ ] 8.1 创建 Celery 任务文件 `backend/app/tasks/document_tasks.py`
    - 定义 `process_document_task` Celery 任务
    - 任务内初始化 `DocumentProcessor` 并调用 `process_document`
    - _需求: 5.1_

  - [ ] 8.2 在文档上传 API 中触发异步任务
    - 修改 `backend/app/api/documents.py`（或对应上传接口）
    - 文档记录创建成功后调用 `process_document_task.delay(document_id)`
    - _需求: 5.1_

- [ ] 9. 实现文档删除级联清理
  - 修改文档删除接口，依次执行：删除 Chroma 向量 → 删除 `document_chunks` 记录 → 删除物理文件
  - _需求: 6.5, 6.6, 6.7_

- [ ] 10. 检查点 — 确保所有测试通过，如有问题请告知用户

- [ ] 11. 集成连接和端到端验证
  - [ ] 11.1 确认所有组件依赖注入正确连接
    - 验证 `DocumentProcessor` 能正确获取 `EmbeddingService`、`VectorStore`、DB session
    - 确认 Celery worker 配置中包含正确的 Redis broker URL
    - _需求: 5.1, 5.3_

  - [ ]* 11.2 编写集成测试验证完整处理流程
    - 使用测试文件（PDF、docx、txt、md）验证端到端流程
    - 验证处理完成后数据库状态和向量存储的一致性
    - _需求: 5.3, 5.4, 5.5, 5.6_

- [ ] 12. 最终检查点 — 确保所有测试通过，如有问题请告知用户

## 备注

- 标有 `*` 的子任务为可选项，可在 MVP 阶段跳过
- 每个任务均引用具体需求条款以保证可追溯性
- 检查点确保增量验证，避免问题积累
- 属性测试验证普遍正确性，单元测试验证具体示例和边界条件
