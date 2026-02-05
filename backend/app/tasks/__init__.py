"""
Celery 任务模块
"""
from celery import Celery

from app.core.config import settings

# 创建 Celery 应用
celery_app = Celery(
    "askit",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.document_tasks"],
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 分钟
    task_soft_time_limit=25 * 60,  # 25 分钟
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@celery_app.task(name="health_check")
def health_check():
    """健康检查任务"""
    return "OK"


# 导入任务模块
from app.tasks import document_tasks
