"""
FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys
import traceback
import os

from app.core.config import settings
from app.core.database import init_db


# 配置 loguru
def setup_logger():
    """配置日志系统"""
    # 移除默认的 handler
    logger.remove()

    # 确保日志目录存在
    log_dir = os.path.dirname(settings.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 控制台输出 - 使用简单格式
    logger.add(
        sys.stdout,
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        level="INFO",
        colorize=False,
    )

    # 文件输出
    logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=settings.log_level,
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )

    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {settings.log_level}")
    logger.info(f"日志文件: {settings.log_file}")

# 立即配置日志
setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info(f"🚀 {settings.app_name} v{settings.app_version} 启动中...")
    await init_db()
    logger.info("✅ 数据库初始化完成")

    yield

    # 关闭时执行
    logger.info("👋 应用关闭中...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="企业级 RAG 知识库系统",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求"""
    logger.info(f"📥 收到请求: {request.method} {request.url}")
    logger.info(f"📋 Headers: {dict(request.headers)}")
    try:
        response = await call_next(request)
        logger.info(f"📤 响应状态: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"❌ 请求处理异常: {str(e)}")
        logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
        raise


# 根路由
@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"❌ 请求错误: {request.method} {request.url}")
    logger.error(f"异常类型: {type(exc).__name__}")
    logger.error(f"异常信息: {str(exc)}")
    logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )


# 健康检查
@app.get("/health")
async def health():
    return {"status": "healthy"}


# API 路由
from app.api import api_router
app.include_router(api_router)
