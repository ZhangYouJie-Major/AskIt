"""
Embedding 服务模块

提供文本向量化功能，支持多种 Embedding 提供商（OpenAI、GLM、Qwen）
通过 OpenAI SDK 的 base_url 参数实现提供商切换
"""
import asyncio
from typing import List
from loguru import logger

try:
    from openai import AsyncOpenAI
except ImportError:
    # 如果 openai 包不可用，尝试从 langchain-openai 导入
    try:
        from langchain_openai import OpenAIEmbeddings
        AsyncOpenAI = None
    except ImportError:
        raise ImportError(
            "需要安装 openai 包。请运行: uv add openai"
        )

from .exceptions import EmbeddingAPIError


def create_embedding_service_from_config(config: dict) -> "EmbeddingService":
    """从配置字典创建 EmbeddingService 实例
    
    这是一个工厂方法，用于从配置文件或 Settings 对象创建服务实例
    
    Args:
        config: 配置字典，应包含以下键:
            - provider: 提供商名称 (openai/glm/qwen)
            - model: 模型名称
            - api_key: API 密钥
            - base_url: API 基础 URL
            - expected_dimension: 预期向量维度（可选）
            
    Returns:
        EmbeddingService: 配置好的服务实例
        
    Example:
        >>> from app.core.config import settings
        >>> config = settings.get_embedding_config()
        >>> service = create_embedding_service_from_config(config)
    
    验证需求: 3.3, 3.4, 3.10
    """
    return EmbeddingService(
        provider=config["provider"],
        model=config["model"],
        api_key=config["api_key"],
        base_url=config["base_url"],
        expected_dimension=config.get("expected_dimension"),
    )


class EmbeddingService:
    """Embedding 服务
    
    使用 OpenAI SDK 调用 Embedding API，支持通过 base_url 切换提供商
    
    支持的提供商:
    - OpenAI: https://api.openai.com/v1
    - GLM (智谱AI): https://open.bigmodel.cn/api/paas/v4
    - Qwen (阿里云): https://dashscope.aliyuncs.com/compatible-mode/v1
    """
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "text-embedding-3-small",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        batch_size: int = 100,
        max_retries: int = 3,
        expected_dimension: int = None,
    ):
        """初始化 Embedding 服务
        
        Args:
            provider: 提供商名称 (openai/glm/qwen)
            model: 模型名称
            api_key: API 密钥
            base_url: API 基础 URL
            batch_size: 批处理大小（每批最多处理的文本数量）
            max_retries: 最大重试次数
            expected_dimension: 预期向量维度（用于验证）
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.expected_dimension = expected_dimension
        
        # 初始化 OpenAI 客户端
        if AsyncOpenAI is None:
            raise ImportError(
                "需要安装 openai 包以使用 EmbeddingService。请运行: uv add openai"
            )
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        
        # 需求 3.11: 在日志中记录使用的提供商、模型名称和向量维度
        logger.info(
            f"初始化 EmbeddingService | "
            f"提供商: {provider} | "
            f"模型: {model} | "
            f"base_url: {base_url} | "
            f"预期向量维度: {expected_dimension} | "
            f"批次大小: {batch_size}"
        )
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量向量化文本
        
        将文本列表转换为向量列表，自动处理批次分割
        
        Args:
            texts: 文本列表
            
        Returns:
            List[List[float]]: 向量列表，与输入文本一一对应
            
        Raises:
            EmbeddingAPIError: API 调用失败
            
        验证需求: 3.1, 3.2, 3.5, 3.8, 3.9, 3.11
        """
        if not texts:
            return []
        
        # 需求 3.11: 在日志中记录提供商、模型名称
        logger.info(
            f"开始向量化 | "
            f"提供商: {self.provider} | "
            f"模型: {self.model} | "
            f"文本数量: {len(texts)} | "
            f"批次大小: {self.batch_size}"
        )
        
        all_embeddings = []
        
        # 按批次处理（需求 3.5: 每批最多 100 个文本）
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
            
            logger.debug(
                f"处理批次 {batch_num}/{total_batches}，"
                f"包含 {len(batch)} 个文本"
            )
            
            # 调用 API 并处理重试
            batch_embeddings = await self._embed_batch_with_retry(batch)
            all_embeddings.extend(batch_embeddings)
        
        # 需求 3.9: 验证返回的向量维度与预期一致
        if all_embeddings and self.expected_dimension:
            actual_dimension = len(all_embeddings[0])
            if actual_dimension != self.expected_dimension:
                error_msg = (
                    f"向量维度不匹配 | "
                    f"预期: {self.expected_dimension} | "
                    f"实际: {actual_dimension} | "
                    f"提供商: {self.provider} | "
                    f"模型: {self.model}"
                )
                logger.error(error_msg)
                raise EmbeddingAPIError(
                    provider=self.provider,
                    reason=error_msg,
                    status_code=None,
                    response_body=None,
                    retry_count=0,
                )
        
        # 需求 3.11: 在日志中记录向量维度
        vector_dimension = len(all_embeddings[0]) if all_embeddings else 0
        logger.info(
            f"向量化完成 | "
            f"提供商: {self.provider} | "
            f"模型: {self.model} | "
            f"向量数量: {len(all_embeddings)} | "
            f"向量维度: {vector_dimension}"
        )
        
        return all_embeddings
    
    async def _embed_batch_with_retry(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """调用 API 向量化一批文本，带重试机制
        
        Args:
            texts: 文本列表（单批）
            
        Returns:
            List[List[float]]: 向量列表
            
        Raises:
            EmbeddingAPIError: 重试后仍然失败
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                # 调用 OpenAI SDK（需求 3.1, 3.2）
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
                
                # 提取向量
                embeddings = [item.embedding for item in response.data]
                
                if retry_count > 0:
                    logger.info(f"重试成功（第 {retry_count} 次重试）")
                
                return embeddings
                
            except Exception as e:
                last_error = e
                retry_count += 1
                
                if retry_count <= self.max_retries:
                    # 计算重试延迟（1s, 2s, 4s）
                    delay = 2 ** (retry_count - 1)
                    
                    logger.warning(
                        f"API 调用失败（第 {retry_count}/{self.max_retries} 次重试），"
                        f"{delay}秒后重试: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    # 超过最大重试次数
                    logger.error(
                        f"API 调用失败，已达到最大重试次数 {self.max_retries}: {str(e)}"
                    )
        
        # 构造详细的错误信息
        error_details = {
            "provider": self.provider,
            "model": self.model,
            "batch_size": len(texts),
            "retry_count": retry_count - 1,
        }
        
        # 尝试提取 HTTP 状态码和响应体
        status_code = None
        response_body = None
        
        if hasattr(last_error, "status_code"):
            status_code = last_error.status_code
        if hasattr(last_error, "response"):
            try:
                response_body = str(last_error.response)
            except:
                pass
        
        raise EmbeddingAPIError(
            provider=self.provider,
            reason=str(last_error),
            status_code=status_code,
            response_body=response_body,
            retry_count=retry_count - 1,
        )
    
    async def embed_query(self, text: str) -> List[float]:
        """向量化单个查询文本
        
        Args:
            text: 查询文本
            
        Returns:
            List[float]: 向量
            
        Raises:
            EmbeddingAPIError: API 调用失败
        """
        embeddings = await self.embed_texts([text])
        return embeddings[0]
