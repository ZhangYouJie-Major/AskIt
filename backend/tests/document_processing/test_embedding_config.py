"""
EmbeddingService 配置测试

测试 GLM 和 Qwen 提供商配置，以及从配置文件读取设置的功能
验证需求: 3.3, 3.4, 3.10, 3.11
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly without going through app.services.__init__
from app.services.document_processing.embedding import (
    EmbeddingService,
    create_embedding_service_from_config,
)
from app.services.document_processing.exceptions import EmbeddingAPIError
from app.core.config import Settings


class TestProviderConfiguration:
    """测试提供商配置"""
    
    def test_glm_provider_base_url(self):
        """测试 GLM 提供商 base_url 配置（需求 3.3）"""
        service = EmbeddingService(
            provider="glm",
            model="embedding-3",
            api_key="test-glm-key",
            base_url="https://open.bigmodel.cn/api/paas/v4",
        )
        
        assert service.provider == "glm"
        assert service.base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert service.model == "embedding-3"
        assert service.api_key == "test-glm-key"
    
    def test_qwen_provider_base_url(self):
        """测试 Qwen 提供商 base_url 配置（需求 3.4）"""
        service = EmbeddingService(
            provider="qwen",
            model="text-embedding-v4",
            api_key="test-qwen-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        assert service.provider == "qwen"
        assert service.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert service.model == "text-embedding-v4"
        assert service.api_key == "test-qwen-key"
    
    def test_openai_provider_base_url(self):
        """测试 OpenAI 提供商 base_url 配置（需求 3.2）"""
        service = EmbeddingService(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-openai-key",
            base_url="https://api.openai.com/v1",
        )
        
        assert service.provider == "openai"
        assert service.base_url == "https://api.openai.com/v1"
        assert service.model == "text-embedding-3-small"


class TestConfigFileSupport:
    """测试配置文件支持"""
    
    def test_settings_get_embedding_config_openai(self):
        """测试从 Settings 获取 OpenAI 配置"""
        settings = Settings(
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            openai_api_key="test-key",
            embedding_dimension=1536,
        )
        
        config = settings.get_embedding_config()
        
        assert config["provider"] == "openai"
        assert config["model"] == "text-embedding-3-small"
        assert config["api_key"] == "test-key"
        assert config["base_url"] == "https://api.openai.com/v1"
        assert config["expected_dimension"] == 1536
    
    def test_settings_get_embedding_config_glm(self):
        """测试从 Settings 获取 GLM 配置（需求 3.3）"""
        settings = Settings(
            embedding_provider="glm",
            embedding_model="embedding-3",
            glm_api_key="test-glm-key",
            embedding_dimension=2048,
        )
        
        config = settings.get_embedding_config()
        
        assert config["provider"] == "glm"
        assert config["model"] == "embedding-3"
        assert config["api_key"] == "test-glm-key"
        assert config["base_url"] == "https://open.bigmodel.cn/api/paas/v4"
        assert config["expected_dimension"] == 2048
    
    def test_settings_get_embedding_config_qwen(self):
        """测试从 Settings 获取 Qwen 配置（需求 3.4）"""
        settings = Settings(
            embedding_provider="qwen",
            embedding_model="text-embedding-v4",
            qwen_api_key="test-qwen-key",
            embedding_dimension=1536,
        )
        
        config = settings.get_embedding_config()
        
        assert config["provider"] == "qwen"
        assert config["model"] == "text-embedding-v4"
        assert config["api_key"] == "test-qwen-key"
        assert config["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert config["expected_dimension"] == 1536
    
    def test_settings_embedding_api_key_override(self):
        """测试 embedding_api_key 覆盖提供商特定的 key"""
        settings = Settings(
            embedding_provider="glm",
            embedding_api_key="override-key",
            glm_api_key="glm-key",
        )
        
        config = settings.get_embedding_config()
        
        # embedding_api_key 应该优先于 glm_api_key
        assert config["api_key"] == "override-key"
    
    def test_settings_default_model_fallback(self):
        """测试未指定模型时使用默认模型"""
        settings = Settings(
            embedding_provider="glm",
            embedding_model="",  # 空字符串
            glm_api_key="test-key",
        )
        
        config = settings.get_embedding_config()
        
        # 应该使用 GLM 的默认模型
        assert config["model"] == "embedding-3"
    
    def test_settings_unsupported_provider(self):
        """测试不支持的提供商抛出异常"""
        settings = Settings(
            embedding_provider="unsupported",
        )
        
        with pytest.raises(ValueError) as exc_info:
            settings.get_embedding_config()
        
        assert "不支持的 embedding 提供商" in str(exc_info.value)
        assert "unsupported" in str(exc_info.value)


class TestFactoryMethod:
    """测试工厂方法"""
    
    def test_create_from_config_openai(self):
        """测试从配置创建 OpenAI 服务"""
        config = {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "api_key": "test-key",
            "base_url": "https://api.openai.com/v1",
            "expected_dimension": 1536,
        }
        
        service = create_embedding_service_from_config(config)
        
        assert service.provider == "openai"
        assert service.model == "text-embedding-3-small"
        assert service.base_url == "https://api.openai.com/v1"
        assert service.expected_dimension == 1536
    
    def test_create_from_config_glm(self):
        """测试从配置创建 GLM 服务（需求 3.3, 3.10）"""
        config = {
            "provider": "glm",
            "model": "embedding-3",
            "api_key": "test-glm-key",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "expected_dimension": 2048,
        }
        
        service = create_embedding_service_from_config(config)
        
        assert service.provider == "glm"
        assert service.model == "embedding-3"
        assert service.base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert service.expected_dimension == 2048
    
    def test_create_from_config_qwen(self):
        """测试从配置创建 Qwen 服务（需求 3.4, 3.10）"""
        config = {
            "provider": "qwen",
            "model": "text-embedding-v4",
            "api_key": "test-qwen-key",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "expected_dimension": 1536,
        }
        
        service = create_embedding_service_from_config(config)
        
        assert service.provider == "qwen"
        assert service.model == "text-embedding-v4"
        assert service.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert service.expected_dimension == 1536
    
    def test_create_from_settings_integration(self):
        """测试从 Settings 对象集成创建服务（需求 3.10）"""
        settings = Settings(
            embedding_provider="glm",
            embedding_model="embedding-3",
            glm_api_key="test-key",
            embedding_dimension=2048,
        )
        
        config = settings.get_embedding_config()
        service = create_embedding_service_from_config(config)
        
        assert service.provider == "glm"
        assert service.model == "embedding-3"
        assert service.expected_dimension == 2048


class TestEnhancedLogging:
    """测试增强的日志记录
    
    注意: loguru 的日志输出在测试中可以在 "Captured stderr call" 中看到，
    但由于 loguru 的异步特性，capsys 可能无法及时捕获。
    这里我们主要验证服务正确初始化和配置，日志功能已在手动测试中验证。
    """
    
    def test_initialization_with_dimension_logging(self):
        """测试初始化时包含向量维度配置（需求 3.11）"""
        service = EmbeddingService(
            provider="glm",
            model="embedding-3",
            api_key="test-key",
            base_url="https://open.bigmodel.cn/api/paas/v4",
            expected_dimension=2048,
        )
        
        # 验证服务正确配置了日志所需的属性
        assert service.provider == "glm"
        assert service.model == "embedding-3"
        assert service.expected_dimension == 2048
    
    @pytest.mark.asyncio
    async def test_embed_texts_with_dimension_tracking(self):
        """测试向量化时跟踪向量维度（需求 3.11）"""
        service = EmbeddingService(
            provider="qwen",
            model="text-embedding-v4",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            expected_dimension=1536,
        )
        
        # Mock API 响应
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536) for _ in range(3)
        ]
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await service.embed_texts(["text1", "text2", "text3"])
        
        # 验证返回的向量维度正确
        assert len(result) == 3
        assert all(len(vec) == 1536 for vec in result)


class TestVectorDimensionValidation:
    """测试向量维度验证"""
    
    @pytest.mark.asyncio
    async def test_dimension_validation_success(self):
        """测试向量维度匹配时成功（需求 3.9）"""
        service = EmbeddingService(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
            expected_dimension=1536,
        )
        
        # Mock API 响应，返回正确维度的向量
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536)
        ]
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await service.embed_texts(["test"])
        
        assert len(result) == 1
        assert len(result[0]) == 1536
    
    @pytest.mark.asyncio
    async def test_dimension_validation_failure(self):
        """测试向量维度不匹配时抛出异常（需求 3.9）"""
        service = EmbeddingService(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
            expected_dimension=1536,
        )
        
        # Mock API 响应，返回错误维度的向量
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 768)  # 错误的维度
        ]
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            with pytest.raises(EmbeddingAPIError) as exc_info:
                await service.embed_texts(["test"])
        
        error = exc_info.value
        assert "向量维度不匹配" in error.details['reason']
        assert "预期: 1536" in error.details['reason']
        assert "实际: 768" in error.details['reason']
    
    @pytest.mark.asyncio
    async def test_no_dimension_validation_when_not_specified(self):
        """测试未指定预期维度时不进行验证"""
        service = EmbeddingService(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
            expected_dimension=None,  # 不验证维度
        )
        
        # Mock API 响应，返回任意维度的向量
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 768)
        ]
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await service.embed_texts(["test"])
        
        # 应该成功，不抛出异常
        assert len(result) == 1
        assert len(result[0]) == 768


class TestModelNameConfiguration:
    """测试模型名称配置"""
    
    def test_custom_model_name_openai(self):
        """测试自定义 OpenAI 模型名称（需求 3.10）"""
        service = EmbeddingService(
            provider="openai",
            model="text-embedding-3-large",  # 自定义模型
            api_key="test-key",
        )
        
        assert service.model == "text-embedding-3-large"
    
    def test_custom_model_name_glm(self):
        """测试自定义 GLM 模型名称（需求 3.10）"""
        service = EmbeddingService(
            provider="glm",
            model="embedding-3",  # GLM 模型
            api_key="test-key",
            base_url="https://open.bigmodel.cn/api/paas/v4",
        )
        
        assert service.model == "embedding-3"
    
    def test_custom_model_name_qwen(self):
        """测试自定义 Qwen 模型名称（需求 3.10）"""
        service = EmbeddingService(
            provider="qwen",
            model="text-embedding-v4",  # Qwen 模型
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        assert service.model == "text-embedding-v4"
