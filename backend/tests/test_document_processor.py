import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import rbac  # noqa: F401 - load relationship targets for SQLAlchemy mappers
from app.models.models import Document, DocumentChunk
import app.services.document_processor as document_processor_module
from app.services.document_processor import DocumentProcessingService
from app.services.document_storage import LocalDocumentStorage


class _ExecuteResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeEmbeddingService:
    async def embed_texts(self, texts):
        return [[float(index), 0.1, 0.2] for index, _ in enumerate(texts)]


class FakeVectorStore:
    def __init__(self):
        self.inserted = None
        self.deleted_ids = []

    async def insert_points(self, ids, vectors, metadatas):
        self.inserted = {
            "ids": ids,
            "vectors": vectors,
            "metadatas": metadatas,
        }

    async def delete_points(self, ids):
        self.deleted_ids.append(ids)


class FailingDeleteVectorStore(FakeVectorStore):
    async def delete_points(self, ids):
        self.deleted_ids.append(ids)
        raise RuntimeError("cleanup failed")


class PartialInsertFailingVectorStore(FakeVectorStore):
    async def insert_points(self, ids, vectors, metadatas):
        self.inserted = {
            "ids": ids,
            "vectors": vectors,
            "metadatas": metadatas,
        }
        raise RuntimeError("partial insert failed")


def _mock_db(document):
    db = AsyncMock()
    db.add_all = MagicMock()
    db.execute.return_value = _ExecuteResult(document)

    async def flush():
        for index, chunk in enumerate(db.add_all.call_args.args[0], start=1000):
            chunk.id = index

    db.flush.side_effect = flush
    return db


def _document(file_path: str) -> Document:
    return Document(
        id=123,
        filename="askit.txt",
        original_filename="AskIt.txt",
        file_path=file_path,
        file_size=100,
        file_type="txt",
        department_id=7,
        uploaded_by=9,
        status="pending",
        error_message="old error",
        vectorized=False,
        chunk_count=0,
    )


@pytest.mark.asyncio
async def test_process_txt_document_completes_and_stores_chunks(tmp_path: Path):
    file_path = tmp_path / "askit.txt"
    file_path.write_text("AskIt 第一段。\n\nAskIt 第二段。", encoding="utf-8")
    document = _document(str(file_path))
    db = _mock_db(document)
    vector_store = FakeVectorStore()

    service = DocumentProcessingService(
        db,
        embedding_service=FakeEmbeddingService(),
        vector_store=vector_store,
    )

    result = await service.process(document.id)

    assert result.success is True
    assert result.document_id == document.id
    assert result.chunk_count > 0
    assert document.status == "completed"
    assert document.vectorized is True
    assert document.error_message is None
    assert document.content == "AskIt 第一段。\n\nAskIt 第二段。"
    assert document.chunk_count == result.chunk_count

    db.add_all.assert_called_once()
    added_chunks = db.add_all.call_args.args[0]
    assert added_chunks
    assert all(isinstance(chunk, DocumentChunk) for chunk in added_chunks)
    assert added_chunks[0].document_id == document.id
    assert added_chunks[0].chunk_index == 0
    assert added_chunks[0].content
    assert added_chunks[0].vector_id.startswith(f"doc-{document.id}-chunk-0-")
    chunk_metadata = json.loads(added_chunks[0].chunk_metadata)
    assert chunk_metadata["document_id"] == document.id
    assert chunk_metadata["filename"] == document.original_filename
    assert chunk_metadata["stored_filename"] == document.filename
    assert chunk_metadata["department_id"] == document.department_id

    assert vector_store.inserted is not None
    assert vector_store.inserted["ids"] == [chunk.vector_id for chunk in added_chunks]
    assert len(vector_store.inserted["vectors"]) == len(added_chunks)
    first_metadata = vector_store.inserted["metadatas"][0]
    assert first_metadata["document_id"] == document.id
    assert first_metadata["chunk_id"] == added_chunks[0].id
    assert first_metadata["filename"] == document.original_filename
    assert first_metadata["stored_filename"] == document.filename
    assert first_metadata["department_id"] == document.department_id
    assert first_metadata["content"] == added_chunks[0].content
    assert vector_store.deleted_ids == []
    assert db.commit.await_count >= 2


@pytest.mark.asyncio
async def test_process_resolves_relative_storage_path_before_parsing(
    tmp_path: Path,
    monkeypatch,
):
    storage = LocalDocumentStorage(tmp_path / "uploads")
    storage.resolve("stored-askit.txt").write_text("AskIt 存储路径。", encoding="utf-8")
    document = _document("stored-askit.txt")
    db = _mock_db(document)
    vector_store = FakeVectorStore()
    monkeypatch.setattr(document_processor_module, "document_storage", storage, raising=False)

    service = DocumentProcessingService(
        db,
        embedding_service=FakeEmbeddingService(),
        vector_store=vector_store,
    )

    result = await service.process(document.id)

    assert result.success is True
    assert document.content == "AskIt 存储路径。"
    assert vector_store.inserted is not None


@pytest.mark.asyncio
async def test_process_missing_document_returns_failed_result():
    db = _mock_db(None)
    service = DocumentProcessingService(
        db,
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
    )

    result = await service.process(404)

    assert result.success is False
    assert result.document_id == 404
    assert result.error_message == "文档不存在"
    db.commit.assert_not_awaited()
    db.add_all.assert_not_called()


@pytest.mark.asyncio
async def test_process_parse_failure_marks_document_failed_and_commits(tmp_path: Path):
    missing_path = tmp_path / "missing.txt"
    document = _document(str(missing_path))
    db = _mock_db(document)
    service = DocumentProcessingService(
        db,
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
    )

    result = await service.process(document.id)

    assert result.success is False
    assert "文件不存在" in result.error_message
    assert document.status == "failed"
    assert document.vectorized is False
    assert document.error_message == result.error_message
    assert db.commit.await_count >= 2
    db.add_all.assert_not_called()


@pytest.mark.asyncio
async def test_process_final_commit_failure_deletes_inserted_vectors(tmp_path: Path):
    file_path = tmp_path / "askit.txt"
    file_path.write_text("AskIt 内容。", encoding="utf-8")
    document = _document(str(file_path))
    db = _mock_db(document)
    db.commit.side_effect = [None, RuntimeError("final commit failed"), None]
    vector_store = FakeVectorStore()
    service = DocumentProcessingService(
        db,
        embedding_service=FakeEmbeddingService(),
        vector_store=vector_store,
    )

    result = await service.process(document.id)

    assert result.success is False
    assert result.error_message == "final commit failed"
    assert document.status == "failed"
    assert document.vectorized is False
    assert vector_store.inserted is not None
    assert vector_store.deleted_ids == [vector_store.inserted["ids"]]
    assert db.rollback.await_count == 1
    assert db.commit.await_count == 3


@pytest.mark.asyncio
async def test_process_fails_when_chunk_ids_are_not_generated(tmp_path: Path):
    file_path = tmp_path / "askit.txt"
    file_path.write_text("AskIt 内容。", encoding="utf-8")
    document = _document(str(file_path))
    db = _mock_db(document)
    db.flush.side_effect = None
    vector_store = FakeVectorStore()
    service = DocumentProcessingService(
        db,
        embedding_service=FakeEmbeddingService(),
        vector_store=vector_store,
    )

    result = await service.process(document.id)

    assert result.success is False
    assert result.error_message == "文档分块ID未生成"
    assert document.status == "failed"
    assert vector_store.inserted is None
    assert vector_store.deleted_ids == []


@pytest.mark.asyncio
async def test_process_cleanup_failure_preserves_original_error(tmp_path: Path):
    file_path = tmp_path / "askit.txt"
    file_path.write_text("AskIt 内容。", encoding="utf-8")
    document = _document(str(file_path))
    db = _mock_db(document)
    db.commit.side_effect = [None, RuntimeError("final commit failed"), None]
    vector_store = FailingDeleteVectorStore()
    service = DocumentProcessingService(
        db,
        embedding_service=FakeEmbeddingService(),
        vector_store=vector_store,
    )

    result = await service.process(document.id)

    assert result.success is False
    assert result.error_message == "final commit failed"
    assert document.status == "failed"
    assert vector_store.deleted_ids == [vector_store.inserted["ids"]]
    assert db.commit.await_count == 3


@pytest.mark.asyncio
async def test_process_insert_failure_deletes_candidate_vectors(tmp_path: Path):
    file_path = tmp_path / "askit.txt"
    file_path.write_text("AskIt 内容。", encoding="utf-8")
    document = _document(str(file_path))
    db = _mock_db(document)
    vector_store = PartialInsertFailingVectorStore()
    service = DocumentProcessingService(
        db,
        embedding_service=FakeEmbeddingService(),
        vector_store=vector_store,
    )

    result = await service.process(document.id)

    assert result.success is False
    assert result.error_message == "partial insert failed"
    assert document.status == "failed"
    assert vector_store.inserted is not None
    assert vector_store.deleted_ids == [vector_store.inserted["ids"]]
