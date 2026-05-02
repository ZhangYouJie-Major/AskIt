"""
文档 API - 文档上传和管理
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Document, DocumentChunk, User
from app.core.config import settings
from app.core.auth import get_current_user
from app.services.document_storage import document_storage
from app.services.vector_store import vector_store

router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentResponse(BaseModel):
    """文档响应"""
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    vectorized: bool
    chunk_count: int
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    documents: List[DocumentResponse]


def dispatch_document_processing(document_id: int) -> None:
    """派发文档处理任务，延迟导入以避免 API 启动加载重依赖。"""
    from app.tasks.document_tasks import process_document

    process_document.delay(document_id)


async def _get_department_document_or_404(
    document_id: int,
    db: AsyncSession,
    current_user: User,
) -> Document:
    """获取当前用户部门内的文档，不存在或跨部门时统一返回 404。"""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if (
        not document
        or current_user.department_id is None
        or document.department_id != current_user.department_id
    ):
        raise HTTPException(status_code=404, detail="文档不存在")

    return document


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    上传文档（需要登录）

    - **file**: 文档文件
    - 部门ID和用户ID自动从当前登录用户获取
    """
    # 验证文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持的类型: {', '.join(settings.allowed_extensions)}"
        )

    # 验证文件大小
    content = await file.read()
    if len(content) > settings.upload_max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({settings.upload_max_size} bytes)"
        )

    if current_user.department_id is None:
        raise HTTPException(status_code=400, detail="当前用户未分配部门，无法上传文档")

    stored_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = await document_storage.save_upload(file, stored_filename)
    document = Document(
        filename=stored_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        file_type=file_ext.replace(".", ""),
        mime_type=file.content_type,
        status="pending",
        department_id=current_user.department_id,
        uploaded_by=current_user.id,
        vectorized=False,
        chunk_count=0,
    )

    try:
        db.add(document)
        await db.commit()
        await db.refresh(document)
    except Exception:
        document_storage.delete(file_path)
        raise

    try:
        dispatch_document_processing(document.id)
    except Exception as exc:
        error_message = f"文档处理任务派发失败: {exc}"
        document.status = "failed"
        document.error_message = error_message
        document.vectorized = False
        await db.commit()
        raise HTTPException(status_code=500, detail=error_message) from exc

    return document


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取文档列表（需要登录）

    只显示当前用户所在部门的文档
    - **skip**: 跳过的记录数
    - **limit**: 返回的记录数
    """
    from sqlalchemy import func

    if current_user.department_id is None:
        return {
            "total": 0,
            "documents": [],
        }

    department_id = current_user.department_id

    query = select(Document).where(Document.department_id == department_id)
    count_query = select(func.count(Document.id)).where(Document.department_id == department_id)

    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    documents = result.scalars().all()

    total = await db.scalar(count_query)

    return {
        "total": total or 0,
        "documents": documents,
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档详情"""
    return await _get_department_document_or_404(document_id, db, current_user)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文档"""
    document = await _get_department_document_or_404(document_id, db, current_user)

    chunk_result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    chunks = chunk_result.scalars().all()
    vector_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]

    if vector_ids:
        await vector_store.delete_points(vector_ids)

    for chunk in chunks:
        await db.delete(chunk)
    await db.delete(document)
    await db.commit()

    try:
        document_storage.delete(document.file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"文档文件删除失败: {exc}",
        ) from exc

    return {"message": "文档已删除"}
