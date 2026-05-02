"""
文档处理服务。
"""
import json
import time
import uuid
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy import select

from app.core.config import settings
from app.models.models import Document, DocumentChunk
from app.services.document_processing.chunker import DocumentChunker
from app.services.document_processing.embedding import create_embedding_service_from_config
from app.services.document_processing.parsers import FileParserFactory
from app.services.document_processing.types import ChunkStrategy, ProcessingResult
from app.services.document_storage import document_storage


class DocumentProcessingService:
    """文档解析、分块、向量化和入库主链路。"""

    def __init__(
        self,
        db,
        embedding_service=None,
        vector_store=None,
        chunker: Optional[DocumentChunker] = None,
    ):
        self.db = db
        self.embedding_service = (
            embedding_service
            or create_embedding_service_from_config(settings.get_embedding_config())
        )
        if vector_store is None:
            from app.services.vector_store import vector_store as default_vector_store

            vector_store = default_vector_store
        self.vector_store = vector_store
        self.chunker = chunker or DocumentChunker(
            chunk_size=500,
            chunk_overlap=50,
            strategy=ChunkStrategy.PARAGRAPH,
        )

    async def process(self, document_id: int) -> ProcessingResult:
        """处理单个文档，返回处理结果。"""
        started_at = time.perf_counter()
        inserted_vector_ids: list[str] = []
        document = await self._get_document(document_id)
        if document is None:
            return ProcessingResult(
                document_id=document_id,
                status="failed",
                chunk_count=0,
                processing_time=self._elapsed(started_at),
                error_message="文档不存在",
            )

        try:
            document.status = "processing"
            document.error_message = None
            await self.db.commit()

            parse_path = self._resolve_parse_path(document.file_path)
            parsed = FileParserFactory.get_parser(document.file_type).parse(str(parse_path))
            display_filename = document.original_filename or document.filename
            chunks = self.chunker.chunk(
                parsed.content,
                metadata={
                    **(parsed.metadata or {}),
                    "document_id": document.id,
                    "filename": display_filename,
                    "stored_filename": document.filename,
                    "department_id": document.department_id,
                },
            )
            if not chunks:
                raise ValueError("文档未生成任何分块")

            texts = [chunk.content for chunk in chunks]
            vectors = await self.embedding_service.embed_texts(texts)
            if len(vectors) != len(chunks):
                raise ValueError("向量数量与分块数量不一致")

            chunk_rows = []
            for index, chunk in enumerate(chunks):
                vector_id = f"doc-{document.id}-chunk-{index}-{uuid.uuid4().hex}"
                chunk_rows.append(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=index,
                        content=chunk.content,
                        vector_id=vector_id,
                        page_number=chunk.page_number,
                        chunk_metadata=json.dumps(chunk.metadata, ensure_ascii=False),
                    )
                )

            self.db.add_all(chunk_rows)
            await self.db.flush()
            if any(chunk_row.id is None for chunk_row in chunk_rows):
                raise ValueError("文档分块ID未生成")

            vector_metadatas = []
            for chunk, chunk_row in zip(chunks, chunk_rows):
                vector_metadatas.append(
                    {
                        "document_id": document.id,
                        "chunk_id": chunk_row.id,
                        "filename": display_filename,
                        "stored_filename": document.filename,
                        "department_id": document.department_id,
                        "content": chunk.content,
                    }
                )

            vector_ids = [chunk.vector_id for chunk in chunk_rows]
            inserted_vector_ids = vector_ids
            await self.vector_store.insert_points(
                ids=vector_ids,
                vectors=vectors,
                metadatas=vector_metadatas,
            )

            document.content = parsed.content
            document.page_count = parsed.page_count
            document.status = "completed"
            document.error_message = None
            document.vectorized = True
            document.chunk_count = len(chunks)
            await self.db.commit()

            return ProcessingResult(
                document_id=document.id,
                status="completed",
                chunk_count=len(chunks),
                processing_time=self._elapsed(started_at),
            )
        except Exception as exc:
            logger.exception("文档处理失败 document_id={}", document_id)
            await self._delete_inserted_vectors(inserted_vector_ids, document_id)
            await self._mark_failed(document, str(exc))
            return ProcessingResult(
                document_id=document_id,
                status="failed",
                chunk_count=0,
                processing_time=self._elapsed(started_at),
                error_message=str(exc),
            )

    async def _get_document(self, document_id: int):
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    def _resolve_parse_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if path.is_absolute():
            return path
        return document_storage.resolve(file_path)

    async def _delete_inserted_vectors(
        self,
        vector_ids: list[str],
        document_id: int,
    ) -> None:
        if not vector_ids:
            return
        try:
            await self.vector_store.delete_points(vector_ids)
        except Exception:
            logger.exception("清理文档向量失败 document_id={}", document_id)

    async def _mark_failed(self, document: Document, error_message: str) -> None:
        if hasattr(self.db, "rollback"):
            await self.db.rollback()
        document.status = "failed"
        document.error_message = error_message
        document.vectorized = False
        await self.db.commit()

    @staticmethod
    def _elapsed(started_at: float) -> float:
        return time.perf_counter() - started_at
