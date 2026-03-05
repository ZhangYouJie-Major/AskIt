# 需求文档 - 文档处理功能

## 简介

本功能旨在完善企业知识库 RAG 系统的文档处理流程，实现从文档上传到向量化存储的完整自动化处理。当前系统已具备文档上传 API 和向量检索能力，但缺少核心的文档解析、分块和向量化处理逻辑。本功能将填补这一空白，使系统能够自动处理多种格式的文档（PDF、Word、TXT 等），并将其转换为可检索的向量数据。系统支持多种 Embedding 提供商（OpenAI、智谱 AI GLM、阿里云 Qwen），以提供灵活的部署选择和成本优化。

## 术语表

- **Document_Processor**: 文档处理器，负责协调整个文档处理流程的核心组件
- **File_Parser**: 文件解析器，负责从不同格式的文件中提取文本内容
- **Document_Chunker**: 文档分块器，负责将长文本分割成适合向量化的文本块
- **Embedding_Service**: 嵌入服务，负责将文本转换为向量表示，支持多种提供商（OpenAI、GLM、Qwen）
- **Embedding_Provider**: 嵌入提供商，指提供 Embedding API 的服务商（如 OpenAI、智谱 AI GLM、阿里云 Qwen）
- **Vector_Store**: 向量存储，负责存储和检索文档向量（使用 Chroma）
- **Celery_Task**: 异步任务，使用 Celery 框架执行的后台任务
- **Document_Chunk**: 文档分块，文档被分割后的单个文本片段
- **Vector_ID**: 向量标识符，在向量数据库中唯一标识一个向量点的字符串
- **Metadata**: 元数据，描述文档或分块的附加信息（如文件名、页码、部门 ID 等）
- **GLM**: 智谱 AI 提供的大语言模型和 Embedding 服务
- **Qwen**: 阿里云通义千问提供的大语言模型和 Embedding 服务

## 需求

### 需求 1: 文档文件解析

**用户故事:** 作为系统管理员，我希望系统能够自动解析上传的文档文件，以便提取文本内容进行后续处理。

#### 验收标准

1. WHEN 接收到 PDF 文件，THE File_Parser SHALL 提取所有文本内容和页码信息
2. WHEN 接收到 Word 文档（.docx），THE File_Parser SHALL 提取所有文本内容和段落结构
3. WHEN 接收到纯文本文件（.txt），THE File_Parser SHALL 读取完整文本内容
4. WHEN 接收到 Markdown 文件（.md），THE File_Parser SHALL 读取完整文本内容并保留格式标记
5. IF 文件格式不受支持，THEN THE File_Parser SHALL 返回明确的错误信息
6. IF 文件损坏或无法读取，THEN THE File_Parser SHALL 返回描述性错误信息
7. WHEN 解析完成，THE File_Parser SHALL 返回包含文本内容和元数据的结构化对象

### 需求 2: 文档内容分块

**用户故事:** 作为系统开发者，我希望系统能够智能地将文档分割成合适大小的文本块，以便提高向量检索的准确性和效率。

#### 验收标准

1. WHEN 处理通用文本，THE Document_Chunker SHALL 按照配置的块大小（默认 500 字符）进行分割
2. WHEN 分割文本块，THE Document_Chunker SHALL 在相邻块之间保留重叠区域（默认 50 字符）
3. WHEN 分割点位于单词或句子中间，THE Document_Chunker SHALL 调整分割位置到最近的自然边界（空格、换行、句号）
4. WHEN 处理中文文本，THE Document_Chunker SHALL 在句号、问号、感叹号等标点符号处优先分割
5. WHEN 处理包含段落的文档，THE Document_Chunker SHALL 优先在段落边界处分割
6. WHEN 处理代码文档，THE Document_Chunker SHALL 尽量保持代码块的完整性
7. WHEN 单个段落超过最大块大小，THE Document_Chunker SHALL 强制分割并保留重叠
8. WHEN 分块完成，THE Document_Chunker SHALL 为每个块生成序号和元数据

### 需求 3: 文档向量化处理

**用户故事:** 作为系统开发者，我希望系统能够将文档分块转换为向量表示，并支持多种 Embedding 提供商，以便支持语义检索功能并提供灵活的部署选择。

#### 验收标准

1. WHEN 接收到文档分块列表，THE Embedding_Service SHALL 使用 OpenAI SDK 调用 Embedding API 生成向量
2. WHEN 配置 OpenAI 提供商，THE Embedding_Service SHALL 使用默认 base_url（https://api.openai.com/v1）和对应的 API Key
3. WHEN 配置 GLM 提供商，THE Embedding_Service SHALL 使用智谱 AI 的 base_url（https://open.bigmodel.cn/api/paas/v4）和对应的 API Key
4. WHEN 配置 Qwen 提供商，THE Embedding_Service SHALL 使用阿里云的 base_url（https://dashscope.aliyuncs.com/compatible-mode/v1）和对应的 API Key
5. WHEN 批量处理分块，THE Embedding_Service SHALL 按批次调用 API（每批最多 100 个文本）以提高效率
6. IF API 调用失败，THEN THE Embedding_Service SHALL 重试最多 3 次，每次间隔递增（1s、2s、4s）
7. IF 重试仍然失败，THEN THE Embedding_Service SHALL 抛出异常并记录详细错误信息（包括 API 响应状态码和错误消息）
8. WHEN 向量生成成功，THE Embedding_Service SHALL 返回与输入分块对应的向量列表
9. THE Embedding_Service SHALL 验证返回的向量维度与预期一致（通过配置指定，如 OpenAI text-embedding-3-small: 1536 维）
10. THE Embedding_Service SHALL 支持通过配置文件指定 embedding_model 名称（如 text-embedding-3-small、embedding-3、text-embedding-v4）
11. THE Embedding_Service SHALL 在日志中记录使用的提供商、模型名称和向量维度

### 需求 4: 向量数据存储

**用户故事:** 作为系统开发者，我希望系统能够将文档向量和元数据存储到向量数据库，以便后续检索使用。

#### 验收标准

1. WHEN 接收到向量和元数据，THE Vector_Store SHALL 为每个向量生成唯一的 Vector_ID
2. WHEN 存储向量，THE Vector_Store SHALL 同时存储文档 ID、分块 ID、文件名、部门 ID 等元数据
3. WHEN 存储向量，THE Vector_Store SHALL 包含分块的文本内容用于检索结果展示
4. WHEN 存储向量，THE Vector_Store SHALL 包含页码信息（如果可用）
5. WHEN 批量存储向量，THE Vector_Store SHALL 使用批量插入操作以提高性能
6. IF 存储操作失败，THEN THE Vector_Store SHALL 抛出异常并保留详细错误信息
7. WHEN 存储成功，THE Vector_Store SHALL 返回已存储的向量数量

### 需求 5: 异步文档处理任务

**用户故事:** 作为系统用户，我希望文档上传后能够在后台自动处理，而不阻塞我的操作，以便我可以继续上传其他文档。

#### 验收标准

1. WHEN 文档上传成功，THE Document_Processor SHALL 创建异步 Celery_Task 进行处理
2. WHEN 任务开始执行，THE Document_Processor SHALL 更新文档状态为 "processing"
3. WHEN 任务执行过程中，THE Document_Processor SHALL 依次执行文件解析、分块、向量化、存储步骤
4. WHEN 所有步骤成功完成，THE Document_Processor SHALL 更新文档状态为 "completed"
5. WHEN 所有步骤成功完成，THE Document_Processor SHALL 更新文档的 vectorized 字段为 true
6. WHEN 所有步骤成功完成，THE Document_Processor SHALL 更新文档的 chunk_count 字段为实际分块数量
7. IF 任何步骤失败，THEN THE Document_Processor SHALL 更新文档状态为 "failed"
8. IF 任何步骤失败，THEN THE Document_Processor SHALL 记录错误信息到 error_message 字段
9. WHEN 任务完成（成功或失败），THE Document_Processor SHALL 记录处理日志包含文档 ID、耗时、状态

### 需求 6: 数据库记录管理

**用户故事:** 作为系统开发者，我希望系统能够正确维护文档和分块的数据库记录，以便追踪处理状态和支持数据管理。

#### 验收标准

1. WHEN 文档处理完成，THE Document_Processor SHALL 在 document_chunks 表中创建所有分块记录
2. WHEN 创建分块记录，THE Document_Processor SHALL 存储分块序号、内容、Vector_ID
3. WHEN 创建分块记录，THE Document_Processor SHALL 存储页码信息（如果可用）
4. WHEN 创建分块记录，THE Document_Processor SHALL 关联正确的 document_id
5. WHEN 文档被删除，THE Document_Processor SHALL 同时删除所有关联的分块记录
6. WHEN 文档被删除，THE Document_Processor SHALL 从 Vector_Store 中删除所有关联的向量
7. WHEN 文档被删除，THE Document_Processor SHALL 从文件系统中删除物理文件

### 需求 7: 文件存储管理

**用户故事:** 作为系统管理员，我希望上传的文档文件能够安全地存储在服务器上，以便在需要时可以重新处理或下载。

#### 验收标准

1. WHEN 文档上传，THE Document_Processor SHALL 将文件保存到配置的上传目录
2. WHEN 保存文件，THE Document_Processor SHALL 使用 UUID 生成唯一文件名避免冲突
3. WHEN 保存文件，THE Document_Processor SHALL 保留原始文件扩展名
4. WHEN 保存文件，THE Document_Processor SHALL 创建必要的目录结构（如果不存在）
5. WHEN 保存文件，THE Document_Processor SHALL 更新数据库中的 file_path 字段为实际路径
6. WHEN 保存文件，THE Document_Processor SHALL 记录文件大小到 file_size 字段
7. IF 磁盘空间不足，THEN THE Document_Processor SHALL 返回明确的错误信息并拒绝上传

### 需求 8: 错误处理和日志记录

**用户故事:** 作为系统运维人员，我希望系统能够详细记录处理过程和错误信息，以便快速定位和解决问题。

#### 验收标准

1. WHEN 处理文档，THE Document_Processor SHALL 使用结构化日志记录每个处理步骤
2. WHEN 记录日志，THE Document_Processor SHALL 包含文档 ID、文件名、处理阶段、时间戳
3. WHEN 发生错误，THE Document_Processor SHALL 记录完整的错误堆栈信息
4. WHEN 发生错误，THE Document_Processor SHALL 记录导致错误的具体参数和上下文
5. WHEN API 调用失败，THE Document_Processor SHALL 记录 API 响应状态码和错误消息
6. WHEN 文件解析失败，THE Document_Processor SHALL 记录文件路径和文件类型
7. THE Document_Processor SHALL 使用不同的日志级别（INFO、WARNING、ERROR）区分消息重要性

### 需求 9: 分块策略优化

**用户故事:** 作为系统开发者，我希望系统能够根据文档类型采用不同的分块策略，以便提高检索质量和用户体验。

#### 验收标准

1. WHERE 文档包含明确的章节标题，THE Document_Chunker SHALL 优先在章节边界处分割
2. WHERE 文档包含列表或表格，THE Document_Chunker SHALL 尽量保持列表项和表格行的完整性
3. WHERE 文档是技术文档，THE Document_Chunker SHALL 识别代码块并保持其完整性
4. WHERE 文档是 Markdown 格式，THE Document_Chunker SHALL 识别标题层级并在标题处优先分割
5. WHERE 文档包含引用或脚注，THE Document_Chunker SHALL 将引用与正文保持在同一分块中
6. WHEN 分块策略选择完成，THE Document_Chunker SHALL 在日志中记录使用的策略类型

### 需求 10: 处理性能监控

**用户故事:** 作为系统管理员，我希望能够监控文档处理的性能指标，以便优化系统配置和资源分配。

#### 验收标准

1. WHEN 处理文档，THE Document_Processor SHALL 记录文件解析耗时
2. WHEN 处理文档，THE Document_Processor SHALL 记录分块处理耗时
3. WHEN 处理文档，THE Document_Processor SHALL 记录向量化耗时
4. WHEN 处理文档，THE Document_Processor SHALL 记录向量存储耗时
5. WHEN 处理文档，THE Document_Processor SHALL 记录总处理耗时
6. WHEN 处理完成，THE Document_Processor SHALL 在日志中输出性能摘要
7. WHEN 处理完成，THE Document_Processor SHALL 记录处理速度（字符数/秒）

