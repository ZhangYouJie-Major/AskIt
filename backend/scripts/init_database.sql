-- ============================================================================
-- AskIt 数据库初始化脚本
-- ============================================================================
-- 用途: 创建 askit_db 数据库及所有表结构
-- 使用方式:
--   1. 本地 PostgreSQL:
--      PGPASSWORD=123456 psql -h localhost -p 5432 -U admin -f scripts/init_database.sql
--   2. Docker PostgreSQL:
--      docker exec -i askit-postgres psql -U askit < scripts/init_database.sql
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. 创建数据库
-- ----------------------------------------------------------------------------
\echo 'Creating database askit_db...'

DROP DATABASE IF EXISTS askit_db;
CREATE DATABASE askit_db
    WITH
    OWNER = admin
    ENCODING = 'UTF8'
    LC_COLLATE = 'C'
    LC_CTYPE = 'C'
    TEMPLATE = template0
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE askit_db IS 'AskIt 企业级 RAG 知识库系统数据库';

-- 连接到新创建的数据库
\c askit_db

-- ----------------------------------------------------------------------------
-- 2. 创建扩展
-- ----------------------------------------------------------------------------
\echo 'Installing extensions...'

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ----------------------------------------------------------------------------
-- 3. 创建表
-- ----------------------------------------------------------------------------

-- ----------------------------------------------------------------------------
-- 3.1 部门表 (departments)
-- ----------------------------------------------------------------------------
\echo 'Creating table: departments...'

CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_departments_name ON departments(name);
COMMENT ON TABLE departments IS '部门表';
COMMENT ON COLUMN departments.created_at IS '创建时间 (UTC)';
COMMENT ON COLUMN departments.updated_at IS '更新时间 (UTC)';

-- ----------------------------------------------------------------------------
-- 3.2 用户表 (users)
-- ----------------------------------------------------------------------------
\echo 'Creating table: users...'

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(200) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_department_id ON users(department_id);
COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.hashed_password IS '加密后的密码';
COMMENT ON COLUMN users.is_superuser IS '是否为超级管理员';

-- ----------------------------------------------------------------------------
-- 3.3 文档元数据表 (documents)
-- ----------------------------------------------------------------------------
\echo 'Creating table: documents...'

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(100),
    title VARCHAR(255),
    content TEXT,
    page_count INTEGER,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    uploaded_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    vectorized BOOLEAN DEFAULT FALSE,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_department_id ON documents(department_id);
CREATE INDEX idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX idx_documents_vectorized ON documents(vectorized);
CREATE INDEX idx_documents_file_type ON documents(file_type);
COMMENT ON TABLE documents IS '文档元数据表';
COMMENT ON COLUMN documents.status IS '处理状态: pending/processing/completed/failed';
COMMENT ON COLUMN documents.vectorized IS '是否已向量化';

-- ----------------------------------------------------------------------------
-- 3.4 文档分块表 (document_chunks)
-- ----------------------------------------------------------------------------
\echo 'Creating table: document_chunks...'

CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    vector_id VARCHAR(100),
    page_number INTEGER,
    chunk_metadata TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_vector_id ON document_chunks(vector_id);
CREATE INDEX idx_document_chunks_content_trgm ON document_chunks USING gin(content gin_trgm_ops);
COMMENT ON TABLE document_chunks IS '文档分块表';
COMMENT ON COLUMN document_chunks.vector_id IS '向量数据库中的向量 ID';
COMMENT ON COLUMN document_chunks.chunk_metadata IS '元数据 (JSON 格式)';

-- ----------------------------------------------------------------------------
-- 3.5 对话会话表 (conversations)
-- ----------------------------------------------------------------------------
\echo 'Creating table: conversations...'

CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_is_active ON conversations(is_active);
COMMENT ON TABLE conversations IS '对话会话表';

-- ----------------------------------------------------------------------------
-- 3.6 对话消息表 (conversation_messages)
-- ----------------------------------------------------------------------------
\echo 'Creating table: conversation_messages...'

CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    source_documents TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX idx_conversation_messages_created_at ON conversation_messages(created_at);
COMMENT ON TABLE conversation_messages IS '对话消息表';
COMMENT ON COLUMN conversation_messages.source_documents IS '引用的文档 (JSON 格式)';

-- ----------------------------------------------------------------------------
-- 4. 创建触发器 (自动更新 updated_at)
-- ----------------------------------------------------------------------------
\echo 'Creating triggers...'

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表创建触发器
CREATE TRIGGER update_departments_updated_at BEFORE UPDATE ON departments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 5. 插入初始数据
-- ----------------------------------------------------------------------------
\echo 'Inserting initial data...'

-- 创建默认部门
INSERT INTO departments (name, description, is_active) VALUES
    ('默认部门', '系统默认部门', TRUE),
    ('技术部', '负责技术研发', TRUE),
    ('产品部', '负责产品设计', TRUE),
    ('运营部', '负责产品运营', TRUE)
ON CONFLICT (name) DO NOTHING;

-- 创建默认超级管理员 (密码: admin123, 需要在应用中修改)
-- 注意: 这里的 hashed_password 是 'admin123' 的 bcrypt 哈希，仅用于开发测试
INSERT INTO users (username, email, hashed_password, full_name, is_superuser, department_id) VALUES
    ('admin', 'admin@askit.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEmc0i', '系统管理员', TRUE, 1),
    ('testuser', 'test@askit.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEmc0i', '测试用户', FALSE, 2)
ON CONFLICT (username) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 6. 完成信息
-- ----------------------------------------------------------------------------
\echo ''
\echo '========================================'
\echo '  数据库初始化完成！'
\echo '========================================'
\echo ''
\echo '数据库信息:'
\echo '  数据库名: askit_db'
\echo '  表数量:   6'
\echo '  默认用户: admin / admin123'
\echo ''
\echo '下一步:'
\echo '  1. 修改默认管理员密码'
\echo '  2. 启动后端服务: cd backend && python3 -m uvicorn app.main:app --reload'
\echo ''
