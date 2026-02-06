"""
FastAPI 开发调试启动脚本
用于 IDE 断点调试
"""
import uvicorn

if __name__ == "__main__":
    # 开发模式启动
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 热重载
        log_level="info",
        access_log=True,
    )
