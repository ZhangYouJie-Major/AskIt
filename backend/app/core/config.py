"""
核心配置模块
"""
from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # Application
    app_name: str = "AskIt"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database - PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "askit"
    postgres_password: str = "askit_password"
    postgres_db: str = "askit_db"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Vector Database - Chroma Cloud
    chroma_mode: str = "cloud"  # "cloud" or "local"
    chroma_api_key: str = ""
    chroma_tenant: str = ""
    chroma_database: str = ""
    chroma_persist_directory: str = "./data/chroma"  # 仅用于本地模式

    # File Storage - MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "askit-docs"
    minio_secure: bool = False

    # Cache - Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    
    # Embedding Configuration
    embedding_provider: str = "openai"  # openai, glm, qwen
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""  # 如果为空，则使用对应提供商的 API key
    
    # Provider-specific API keys
    glm_api_key: str = ""
    qwen_api_key: str = ""
    
    # Expected vector dimensions for validation
    embedding_dimension: int = 1536  # OpenAI text-embedding-3-small default

    # JWT
    jwt_secret_key: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # File Upload
    upload_max_size: int = 104857600  # 100MB
    allowed_extensions_raw: str = ".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.png,.jpg,.jpeg"

    @property
    def allowed_extensions(self) -> List[str]:
        """允许的文件扩展名列表"""
        return [ext.strip() for ext in self.allowed_extensions_raw.split(",")]

    # OCR
    ocr_enabled: bool = True

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    def get_embedding_config(self) -> dict:
        """获取 Embedding 服务配置
        
        根据 embedding_provider 返回对应的配置信息
        
        Returns:
            dict: 包含 provider, model, api_key, base_url, expected_dimension
        """
        provider = self.embedding_provider.lower()
        
        # Provider-specific configurations
        provider_configs = {
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "api_key": self.embedding_api_key or self.openai_api_key,
                "default_model": "text-embedding-3-small",
                "default_dimension": 1536,
            },
            "glm": {
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "api_key": self.embedding_api_key or self.glm_api_key,
                "default_model": "embedding-3",
                "default_dimension": 2048,
            },
            "qwen": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "api_key": self.embedding_api_key or self.qwen_api_key,
                "default_model": "text-embedding-v4",
                "default_dimension": 1536,
            },
        }
        
        if provider not in provider_configs:
            raise ValueError(
                f"不支持的 embedding 提供商: {provider}. "
                f"支持的提供商: {', '.join(provider_configs.keys())}"
            )
        
        config = provider_configs[provider]
        
        return {
            "provider": provider,
            "model": self.embedding_model or config["default_model"],
            "api_key": config["api_key"],
            "base_url": config["base_url"],
            "expected_dimension": self.embedding_dimension or config["default_dimension"],
        }

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
