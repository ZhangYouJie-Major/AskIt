"""
文档处理任务
"""
import asyncio
from typing import List

from celery import shared_task


_task_loop = None


def _get_task_loop():
    global _task_loop
    if _task_loop is None or _task_loop.is_closed():
        _task_loop = asyncio.new_event_loop()
    return _task_loop


def _run_async(coro):
    loop = _get_task_loop()
    return loop.run_until_complete(coro)


@shared_task(name="process_document")
def process_document(document_id: int):
    """
    处理文档：解析、分块、向量化、存储

    Args:
        document_id: 文档ID
    """

    async def _process():
        from app.core import database
        from app.services import document_processor

        async with database.AsyncSessionLocal() as db:
            service = document_processor.DocumentProcessingService(db)
            result = await service.process(document_id)
            return {
                "document_id": result.document_id,
                "chunk_count": result.chunk_count,
                "status": result.status,
                "error_message": result.error_message,
            }

    return _run_async(_process())


@shared_task(name="batch_process_documents")
def batch_process_documents(document_ids: List[int]):
    """批量处理文档"""
    results = []
    for doc_id in document_ids:
        result = process_document.delay(doc_id)
        results.append(result.id)
    return results


@shared_task(name="cleanup_old_documents")
def cleanup_old_documents(days: int = 30):
    """清理旧文档"""
    # TODO: 实现清理逻辑
    return {"cleaned": 0}


@shared_task(name="rebuild_vector_index")
def rebuild_vector_index():
    """重建向量索引"""
    # TODO: 实现重建逻辑
    return {"status": "completed"}
