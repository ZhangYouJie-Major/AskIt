"""
文档 API - 文档上传和管理
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Document
from app.core.config import settings

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


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    documents: List[DocumentResponse]


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    department_id: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """
    上传文档

    - **file**: 文档文件
    - **department_id**: 部门ID
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

    # TODO: 实际的文件存储和解析逻辑
    # 这里先创建数据库记录
    document = Document(
        filename=f"{uuid.uuid4()}{file_ext}",
        original_filename=file.filename,
        file_path=f"uploads/{uuid.uuid4()}{file_ext}",
        file_size=len(content),
        file_type=file_ext.replace(".", ""),
        mime_type=file.content_type,
        status="pending",
        department_id=department_id,
        uploaded_by=1,  # TODO: 从 JWT 获取用户ID
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return document


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    department_id: int = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    获取文档列表

    - **department_id**: 部门ID（可选，用于过滤）
    - **skip**: 跳过的记录数
    - **limit**: 返回的记录数
    """
    from sqlalchemy import select, func

    query = select(Document)
    count_query = select(func.count(Document.id))

    if department_id:
        query = query.where(Document.department_id == department_id)
        count_query = count_query.where(Document.department_id == department_id)

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
):
    """获取文档详情"""
    from sqlalchemy import select

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    return document


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除文档"""
    from sqlalchemy import select

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # TODO: 删除文件和向量
    await db.delete(document)
    await db.commit()

    return {"message": "文档已删除"}
