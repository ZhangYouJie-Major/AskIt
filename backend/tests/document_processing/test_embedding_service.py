"""
EmbeddingService 单元测试

测试 Embedding 服务的基础功能，包括批量处理和 OpenAI 提供商支持
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.document_processing.embedding import EmbeddingService
from app.services.document_processing.exceptions import EmbeddingAPIError


class TestEmbeddingServiceInitialization:
    """测试 EmbeddingService 初始化"""
    
    def test_init_with_default_params(self):
        """测试使用默认参数初始化"""
        service = EmbeddingService(api_key="test-key")
        
        assert service.provider == "openai"
        assert service.model == "text-embedding-3-small"
        assert service.base_url == "https://api.openai.com/v1"
        assert service.batch_size == 100
        assert service.max_retries == 3
    
    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化"""
        service = EmbeddingService(
            provider="glm",
            model="embedding-3",
            api_key="glm-key",
            base_url="https://open.bigmodel.cn/api/paas/v4",
            batch_size=50,
            max_retries=5,
        )
        
        assert service.provider == "glm"
        assert service.model == "embedding-3"
        assert service.base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert service.batch_size == 50
        assert service.max_retries == 5
    
    def test_init_openai_provider(self):
        """测试 OpenAI 提供商配置（需求 3.2）"""
        service = EmbeddingService(
            provider="openai",
            api_key="test-key",
        )
        
        # 验证默认使用 OpenAI 的 base_url
        assert service.base_url == "https://api.openai.com/v1"
        assert service.client is not None


class TestEmbeddingServiceBatchProcessing:
    """测试批量处理逻辑"""
    
    @pytest.mark.asyncio
    async def test_embed_empty_list(self):
        """测试空列表输入"""
        service = EmbeddingService(api_key="test-key")
        result = await service.embed_texts([])
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """测试单个文本向量化"""
        service = EmbeddingService(api_key="test-key")
        
        # Mock API 响应
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await service.embed_texts(["test text"])
        
        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]
    
    @pytest.mark.asyncio
    async def test_embed_multiple_texts_single_batch(self):
        """测试多个文本在单批次内处理（需求 3.1）"""
        service = EmbeddingService(api_key="test-key", batch_size=100)
        
        texts = [f"text {i}" for i in range(50)]
        
        # Mock API 响应
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[float(i)] * 3) for i in range(50)
        ]
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            return_value=mock_response
        ) as mock_create:
            result = await service.embed_texts(texts)
        
        # 验证只调用了一次 API（单批次）
        assert mock_create.call_count == 1
        
        # 验证返回的向量数量与输入文本数量一致（需求 3.8）
        assert len(result) == 50
        
        # 验证向量内容
        for i, embedding in enumerate(result):
            assert embedding == [float(i)] * 3
    
    @pytest.mark.asyncio
    async def test_embed_multiple_batches(self):
        """测试多批次处理（需求 3.5: 每批最多 100 个文本）"""
        service = EmbeddingService(api_key="test-key", batch_size=100)
        
        # 创建 250 个文本，应该分成 3 批
        texts = [f"text {i}" for i in range(250)]
        
        # Mock API 响应
        def create_mock_response(batch_size):
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1, 0.2, 0.3]) for _ in range(batch_size)
            ]
            return mock_response
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
        ) as mock_create:
            # 设置不同批次的返回值
            mock_create.side_effect = [
                create_mock_response(100),  # 第一批 100 个
                create_mock_response(100),  # 第二批 100 个
                create_mock_response(50),   # 第三批 50 个
            ]
            
            result = await service.embed_texts(texts)
        
        # 验证调用了 3 次 API（3 个批次）
        assert mock_create.call_count == 3
        
        # 验证返回的向量数量正确
        assert len(result) == 250
        
        # 验证每次调用的参数
        calls = mock_create.call_args_list
        assert len(calls[0][1]['input']) == 100  # 第一批
        assert len(calls[1][1]['input']) == 100  # 第二批
        assert len(calls[2][1]['input']) == 50   # 第三批
    
    @pytest.mark.asyncio
    async def test_embed_custom_batch_size(self):
        """测试自定义批次大小"""
        service = EmbeddingService(api_key="test-key", batch_size=10)
        
        texts = [f"text {i}" for i in range(25)]
        
        def create_mock_response(batch_size):
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1, 0.2, 0.3]) for _ in range(batch_size)
            ]
            return mock_response
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.side_effect = [
                create_mock_response(10),
                create_mock_response(10),
                create_mock_response(5),
            ]
            
            result = await service.embed_texts(texts)
        
        # 验证调用了 3 次（25 / 10 = 3 批）
        assert mock_create.call_count == 3
        assert len(result) == 25


class TestEmbeddingServiceRetry:
    """测试重试机制"""
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """测试 API 失败时的重试（需求 3.6）"""
        service = EmbeddingService(api_key="test-key", max_retries=3)
        
        # Mock API 响应：前两次失败，第三次成功
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        
        call_count = 0
        
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("API Error")
            return mock_response
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            side_effect=mock_create
        ):
            result = await service.embed_texts(["test"])
        
        # 验证重试了 2 次后成功（总共调用 3 次）
        assert call_count == 3
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """测试超过最大重试次数（需求 3.7）"""
        service = EmbeddingService(api_key="test-key", max_retries=3)
        
        # Mock API 响应：持续失败
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            side_effect=Exception("Persistent API Error")
        ) as mock_create:
            with pytest.raises(EmbeddingAPIError) as exc_info:
                await service.embed_texts(["test"])
        
        # 验证调用了 4 次（1 次初始 + 3 次重试）
        assert mock_create.call_count == 4
        
        # 验证异常信息
        error = exc_info.value
        assert error.details['provider'] == "openai"
        assert error.details['retry_count'] == 3
        assert "Persistent API Error" in error.details['reason']
    
    @pytest.mark.asyncio
    async def test_retry_delay_progression(self):
        """测试重试延迟递增（1s, 2s, 4s）"""
        service = EmbeddingService(api_key="test-key", max_retries=3)
        
        delays = []
        
        async def mock_sleep(delay):
            delays.append(delay)
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            side_effect=Exception("API Error")
        ):
            with patch('asyncio.sleep', new_callable=AsyncMock, side_effect=mock_sleep):
                with pytest.raises(EmbeddingAPIError):
                    await service.embed_texts(["test"])
        
        # 验证延迟递增：1s, 2s, 4s
        assert delays == [1, 2, 4]


class TestEmbeddingServiceQuery:
    """测试单个查询向量化"""
    
    @pytest.mark.asyncio
    async def test_embed_query(self):
        """测试单个查询文本向量化"""
        service = EmbeddingService(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await service.embed_query("test query")
        
        assert result == [0.1, 0.2, 0.3]


class TestEmbeddingServiceProviders:
    """测试多提供商支持"""
    
    def test_openai_provider_config(self):
        """测试 OpenAI 提供商配置（需求 3.2）"""
        service = EmbeddingService(
            provider="openai",
            api_key="test-key",
        )
        
        assert service.base_url == "https://api.openai.com/v1"
        assert service.model == "text-embedding-3-small"
    
    def test_glm_provider_config(self):
        """测试 GLM 提供商配置（需求 3.3）"""
        service = EmbeddingService(
            provider="glm",
            model="embedding-3",
            api_key="glm-key",
            base_url="https://open.bigmodel.cn/api/paas/v4",
        )
        
        assert service.base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert service.model == "embedding-3"
    
    def test_qwen_provider_config(self):
        """测试 Qwen 提供商配置（需求 3.4）"""
        service = EmbeddingService(
            provider="qwen",
            model="text-embedding-v4",
            api_key="qwen-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        assert service.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert service.model == "text-embedding-v4"


class TestEmbeddingServiceErrorHandling:
    """测试错误处理"""
    
    @pytest.mark.asyncio
    async def test_api_error_with_status_code(self):
        """测试包含状态码的 API 错误"""
        service = EmbeddingService(api_key="test-key", max_retries=0)
        
        # 创建带状态码的异常
        error = Exception("API Error")
        error.status_code = 429
        error.response = "Rate limit exceeded"
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            side_effect=error
        ):
            with pytest.raises(EmbeddingAPIError) as exc_info:
                await service.embed_texts(["test"])
        
        # 验证异常包含状态码
        assert exc_info.value.details['status_code'] == 429
    
    @pytest.mark.asyncio
    async def test_error_message_format(self):
        """测试错误消息格式（需求 3.7）"""
        service = EmbeddingService(api_key="test-key", max_retries=0)
        
        with patch.object(
            service.client.embeddings,
            'create',
            new_callable=AsyncMock,
            side_effect=Exception("Connection timeout")
        ):
            with pytest.raises(EmbeddingAPIError) as exc_info:
                await service.embed_texts(["test"])
        
        error = exc_info.value
        
        # 验证错误消息包含提供商和原因
        assert "openai" in str(error).lower()
        assert "Connection timeout" in error.details['reason']
        
        # 验证包含重试次数
        assert error.details['retry_count'] == 0
