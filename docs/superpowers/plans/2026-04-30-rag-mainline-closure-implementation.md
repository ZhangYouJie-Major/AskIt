# RAG Mainline Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AskIt start reliably and close the path from uploading a supported document to querying it through RAG.

**Architecture:** Keep the current FastAPI, SQLAlchemy async, Celery, and Chroma structure. Add small service boundaries for file storage and document processing so API handlers stay thin and Celery tasks only orchestrate work.

**Tech Stack:** FastAPI, SQLAlchemy async, Celery, Chroma CloudClient/PersistentClient, OpenAI-compatible embeddings, Vue 3, Element Plus, uv, npm.

---

## File Structure

- Modify `backend/app/core/config.py`
  - Add upload storage directory config.
  - Keep Chroma Cloud and local config explicit.
- Modify `backend/app/services/vector_store.py`
  - Use `chromadb.CloudClient` for cloud mode.
  - Use `chromadb.PersistentClient` for local mode.
  - Remove unsupported tenant/database kwargs from collection operations when the bound client already owns that context.
- Create `backend/tests/test_startup_imports.py`
  - Verify `app.main`, `app.tasks.document_tasks`, and Chroma client selection are importable.
- Modify broken tests under `backend/tests/document_processing/`
  - Fix direct file-path imports that currently point to `tests/document_processing/app/...`.
- Create `backend/app/services/document_storage.py`
  - Local filesystem upload/save/delete/exists service.
- Create `backend/tests/test_document_storage.py`
  - Unit coverage for local file save/delete behavior.
- Modify `backend/app/api/documents.py`
  - Save real files.
  - Trigger `process_document`.
  - Add login and department checks to detail/delete.
  - Include `error_message` in response.
- Create `backend/tests/test_documents_api.py`
  - Upload, detail, delete, and department permission coverage.
- Create `backend/app/services/document_processor.py`
  - Parse, chunk, embed, write chunks, write Chroma, update document status.
- Create `backend/tests/test_document_processor.py`
  - Processing success/failure with fake embedding and fake vector store.
- Modify `backend/app/tasks/document_tasks.py`
  - Remove stale imports.
  - Call `DocumentProcessingService` from Celery.
- Modify `frontend/src/api/modules.ts`
  - Add `error_message` to document type.
- Modify `frontend/src/router/index.ts`
  - Add a real `/admin/documents` child route.
- Modify `frontend/src/layouts/AdminLayout.vue`
  - Add documents menu item.
- Modify or reuse `frontend/src/views/AdminView.vue`
  - Use it as the document management view, or rename in a separate cleanup after the mainline works.

## Task 1: Chroma And Startup Imports

**Files:**
- Modify: `backend/app/services/vector_store.py`
- Test: `backend/tests/test_startup_imports.py`

- [ ] **Step 1: Add failing tests for client selection and imports**

Create `backend/tests/test_startup_imports.py`:

```python
import importlib
import sys
import types
from unittest.mock import MagicMock


def _install_fake_chromadb(monkeypatch):
    fake_chromadb = types.ModuleType("chromadb")
    fake_chromadb.CloudClient = MagicMock(name="CloudClient")
    fake_chromadb.PersistentClient = MagicMock(name="PersistentClient")
    fake_chromadb.CloudClient.return_value.get_collection.side_effect = Exception("missing")
    fake_chromadb.CloudClient.return_value.create_collection.return_value = MagicMock()
    fake_chromadb.PersistentClient.return_value.get_collection.side_effect = Exception("missing")
    fake_chromadb.PersistentClient.return_value.create_collection.return_value = MagicMock()

    fake_config = types.ModuleType("chromadb.config")
    fake_config.Settings = MagicMock(name="Settings")

    monkeypatch.setitem(sys.modules, "chromadb", fake_chromadb)
    monkeypatch.setitem(sys.modules, "chromadb.config", fake_config)
    return fake_chromadb


def _reload_vector_store(monkeypatch, chroma_mode):
    fake_chromadb = _install_fake_chromadb(monkeypatch)
    monkeypatch.setenv("CHROMA_MODE", chroma_mode)
    monkeypatch.setenv("CHROMA_API_KEY", "test-key")
    monkeypatch.setenv("CHROMA_TENANT", "test-tenant")
    monkeypatch.setenv("CHROMA_DATABASE", "test-db")

    for name in [
        "app.core.config",
        "app.services.vector_store",
    ]:
        sys.modules.pop(name, None)

    module = importlib.import_module("app.services.vector_store")
    return module, fake_chromadb


def test_cloud_mode_uses_chromadb_cloud_client(monkeypatch):
    module, fake_chromadb = _reload_vector_store(monkeypatch, "cloud")

    store = module.VectorStore()

    fake_chromadb.CloudClient.assert_called_once_with(
        api_key="test-key",
        tenant="test-tenant",
        database="test-db",
    )
    assert store.client is fake_chromadb.CloudClient.return_value


def test_local_mode_uses_chromadb_persistent_client(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_PERSIST_DIRECTORY", str(tmp_path / "chroma"))
    module, fake_chromadb = _reload_vector_store(monkeypatch, "local")

    store = module.VectorStore()

    fake_chromadb.PersistentClient.assert_called_once()
    assert store.client is fake_chromadb.PersistentClient.return_value


def test_document_tasks_module_is_importable_with_local_chroma(monkeypatch):
    _install_fake_chromadb(monkeypatch)
    monkeypatch.setenv("CHROMA_MODE", "local")

    for name in [
        "app.tasks.document_tasks",
        "app.tasks",
        "app.services.vector_store",
    ]:
        sys.modules.pop(name, None)

    module = importlib.import_module("app.tasks.document_tasks")

    assert hasattr(module, "process_document")
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_startup_imports.py
```

Expected before implementation:

```text
FAILED test_cloud_mode_uses_chromadb_cloud_client
FAILED test_document_tasks_module_is_importable_with_local_chroma
```

- [ ] **Step 3: Fix `VectorStore` Chroma client initialization**

In `backend/app/services/vector_store.py`, replace the cloud client branch with:

```python
if settings.chroma_mode == "cloud":
    self.client = chromadb.CloudClient(
        api_key=settings.chroma_api_key,
        tenant=settings.chroma_tenant,
        database=settings.chroma_database,
    )
else:
    import os
    persist_dir = settings.chroma_persist_directory
    os.makedirs(persist_dir, exist_ok=True)
    self.client = chromadb.PersistentClient(path=persist_dir)
```

Then simplify cloud collection calls so they use the bound client context:

```python
self.collection = self.client.get_collection(name=self.collection_name)
self.collection = self.client.create_collection(
    name=self.collection_name,
    metadata={"hnsw:space": "cosine"},
)
```

Keep `add`, `query`, `delete`, and `delete_collection` calls without `tenant=` and `database=` kwargs:

```python
self.collection.add(ids=ids, embeddings=vectors, metadatas=metadatas)
results = self.collection.query(
    query_embeddings=[vector],
    n_results=limit,
    where=where,
)
self.collection.delete(ids=ids)
self.client.delete_collection(name=self.collection_name)
```

- [ ] **Step 4: Replace stale task imports with new service placeholders**

In `backend/app/tasks/document_tasks.py`, remove these imports:

```python
from app.services.embeddings import embedding_service
from app.services.vector_store import vector_store
from app.utils.chunker import chunker
```

Use a temporary import target that will be created in Task 5:

```python
from app.core.database import AsyncSessionLocal
from app.services.document_processor import DocumentProcessingService
```

Update `process_document` to:

```python
@shared_task(name="process_document")
def process_document(document_id: int):
    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            service = DocumentProcessingService(db)
            result = await service.process(document_id)
            return {
                "document_id": result.document_id,
                "chunk_count": result.chunk_count,
                "status": result.status,
                "error_message": result.error_message,
            }

    return asyncio.run(_run())
```

Create the minimal temporary `backend/app/services/document_processor.py` so imports pass:

```python
from app.services.document_processing.types import ProcessingResult


class DocumentProcessingService:
    def __init__(self, db):
        self.db = db

    async def process(self, document_id: int) -> ProcessingResult:
        return ProcessingResult(
            document_id=document_id,
            status="failed",
            error_message="DocumentProcessingService is not wired yet",
        )
```

- [ ] **Step 5: Run startup tests**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_startup_imports.py
```

Expected:

```text
3 passed
```

## Task 2: Fix Test Collection Paths

**Files:**
- Modify: `backend/pytest.ini`
- Modify: selected files in `backend/tests/document_processing/`

- [ ] **Step 1: Add project root to pytest config**

Modify `backend/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
addopts = -p no:html -p no:metadata
pythonpath = .
```

- [ ] **Step 2: Fix direct file imports that use the test directory as root**

In files that contain:

```python
backend_dir = Path(__file__).parent
types_path = backend_dir / "app/services/document_processing/types.py"
```

replace with:

```python
backend_dir = Path(__file__).resolve().parents[2]
types_path = backend_dir / "app" / "services" / "document_processing" / "types.py"
```

For `test_types_simple.py`, replace:

```python
os.path.join(os.path.dirname(__file__), "app/services/document_processing/types.py")
```

with:

```python
os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "app",
    "services",
    "document_processing",
    "types.py",
)
```

Apply the same pattern for `exceptions.py`, `parsers.py`, and `chunker.py` direct imports.

- [ ] **Step 3: Run full test collection**

Run:

```powershell
uv run pytest --collect-only -q
```

Expected:

```text
no collection errors
```

## Task 3: Local Document Storage Service

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/document_storage.py`
- Test: `backend/tests/test_document_storage.py`

- [ ] **Step 1: Write storage tests**

Create `backend/tests/test_document_storage.py`:

```python
import asyncio

from starlette.datastructures import UploadFile

from app.services.document_storage import LocalDocumentStorage


def test_save_upload_and_delete(tmp_path):
    storage = LocalDocumentStorage(base_dir=tmp_path)
    upload = UploadFile(filename="hello.txt", file=open(__file__, "rb"))

    try:
        saved_path = asyncio.run(storage.save_upload(upload, "stored.txt"))
    finally:
        upload.file.close()

    assert saved_path == "stored.txt"
    assert (tmp_path / "stored.txt").exists()

    storage.delete(saved_path)

    assert not (tmp_path / "stored.txt").exists()


def test_resolve_rejects_path_escape(tmp_path):
    storage = LocalDocumentStorage(base_dir=tmp_path)

    try:
        storage.resolve("../escape.txt")
    except ValueError as exc:
        assert str(exc) == "非法文件路径"
    else:
        raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Run storage tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_document_storage.py
```

Expected:

```text
ModuleNotFoundError: No module named 'app.services.document_storage'
```

- [ ] **Step 3: Add upload storage configuration**

In `backend/app/core/config.py`, add:

```python
upload_storage_dir: str = "uploads"
```

near the existing upload settings.

- [ ] **Step 4: Implement `LocalDocumentStorage`**

Create `backend/app/services/document_storage.py`:

```python
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class LocalDocumentStorage:
    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir or settings.upload_storage_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        target = (self.base_dir / relative_path).resolve()
        if self.base_dir not in target.parents and target != self.base_dir:
            raise ValueError("非法文件路径")
        return target

    async def save_upload(self, file: UploadFile, stored_filename: str) -> str:
        target = self.resolve(stored_filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        target.write_bytes(content)
        return stored_filename

    def delete(self, relative_path: str) -> None:
        target = self.resolve(relative_path)
        if target.exists():
            target.unlink()

    def exists(self, relative_path: str) -> bool:
        return self.resolve(relative_path).exists()


document_storage = LocalDocumentStorage()
```

- [ ] **Step 5: Run storage tests**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_document_storage.py
```

Expected:

```text
2 passed
```

## Task 4: Upload API Saves Files And Triggers Processing

**Files:**
- Modify: `backend/app/api/documents.py`
- Test: `backend/tests/test_documents_api.py`

- [ ] **Step 1: Write upload API tests**

Create `backend/tests/test_documents_api.py` with the same `app_module` fixture pattern used in `test_departments_api.py`, then add:

```python
from unittest.mock import AsyncMock, MagicMock

from app.core.auth import get_current_user


class MockUser:
    def __init__(self, user_id=10, department_id=20):
        self.id = user_id
        self.department_id = department_id
        self.is_active = True
        self.is_superuser = False


def test_upload_rejects_user_without_department(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(department_id=None)

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("hello.txt", b"hello", "text/plain")},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "当前用户未分配部门，无法上传文档"}
    db_session.add.assert_not_called()


def test_upload_saves_document_and_dispatches_task(client_and_db, monkeypatch):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(user_id=10, department_id=20)

    app.dependency_overrides[get_current_user] = override_get_current_user

    saved_paths = []

    async def fake_save_upload(file, stored_filename):
        saved_paths.append(stored_filename)
        return stored_filename

    monkeypatch.setattr(
        "app.api.documents.document_storage.save_upload",
        fake_save_upload,
    )
    delay = MagicMock()
    monkeypatch.setattr("app.api.documents.process_document.delay", delay)

    async def fake_refresh(document):
        document.id = 99

    db_session.refresh = AsyncMock(side_effect=fake_refresh)

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("hello.txt", b"hello", "text/plain")},
        follow_redirects=False,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 99
    assert body["original_filename"] == "hello.txt"
    assert body["status"] == "pending"
    assert body["error_message"] is None
    assert saved_paths
    delay.assert_called_once_with(99)
```

- [ ] **Step 2: Run upload tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_documents_api.py
```

Expected before implementation:

```text
FAILED test_upload_rejects_user_without_department
FAILED test_upload_saves_document_and_dispatches_task
```

- [ ] **Step 3: Update document response model**

In `backend/app/api/documents.py`, change `DocumentResponse`:

```python
class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    vectorized: bool
    chunk_count: int
    error_message: str | None = None
```

- [ ] **Step 4: Save file and trigger processing**

In `backend/app/api/documents.py`, import:

```python
from app.services.document_storage import document_storage
from app.tasks.document_tasks import process_document
```

Replace the upload body after size validation with:

```python
if current_user.department_id is None:
    raise HTTPException(status_code=400, detail="当前用户未分配部门，无法上传文档")

stored_filename = f"{uuid.uuid4()}{file_ext}"
await file.seek(0)
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
)

try:
    db.add(document)
    await db.commit()
    await db.refresh(document)
except Exception:
    document_storage.delete(file_path)
    raise

process_document.delay(document.id)
return document
```

- [ ] **Step 5: Run upload tests**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_documents_api.py
```

Expected:

```text
2 passed
```

## Task 5: Document Processing Service

**Files:**
- Modify: `backend/app/services/document_processor.py`
- Modify: `backend/app/tasks/document_tasks.py`
- Test: `backend/tests/test_document_processor.py`

- [ ] **Step 1: Write processor success and failure tests**

Create `backend/tests/test_document_processor.py`:

```python
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from app.models.models import Document
from app.services.document_processor import DocumentProcessingService


class FakeEmbeddingService:
    async def embed_texts(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStore:
    def __init__(self):
        self.inserted = None
        self.deleted = None

    async def insert_points(self, ids, vectors, metadatas):
        self.inserted = (ids, vectors, metadatas)

    async def delete_points(self, ids):
        self.deleted = ids


def _result_with_document(document):
    result = MagicMock()
    result.scalar_one_or_none.return_value = document
    return result


async def test_process_txt_document_success(tmp_path):
    file_path = tmp_path / "doc.txt"
    file_path.write_text("AskIt supports reliable document search.", encoding="utf-8")

    document = Document(
        id=1,
        filename="doc.txt",
        original_filename="doc.txt",
        file_path=str(file_path),
        file_size=file_path.stat().st_size,
        file_type="txt",
        department_id=7,
        uploaded_by=3,
        status="pending",
    )

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result_with_document(document))
    vector_store = FakeVectorStore()

    service = DocumentProcessingService(
        db,
        embedding_service=FakeEmbeddingService(),
        vector_store=vector_store,
    )

    result = await service.process(1)

    assert result.status == "completed"
    assert result.chunk_count >= 1
    assert document.status == "completed"
    assert document.vectorized is True
    assert document.error_message is None
    assert vector_store.inserted is not None
    db.add_all.assert_called_once()
    assert db.commit.await_count >= 2


async def test_process_missing_document_marks_failed_result():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result_with_document(None))

    service = DocumentProcessingService(db)

    result = await service.process(404)

    assert result.status == "failed"
    assert result.error_message == "文档不存在"
```

- [ ] **Step 2: Run processor tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_document_processor.py
```

Expected before implementation:

```text
FAILED test_process_txt_document_success
```

- [ ] **Step 3: Implement processor dependencies and constructor**

In `backend/app/services/document_processor.py`, use:

```python
import json
import time
import uuid
from pathlib import Path

from loguru import logger
from sqlalchemy import select

from app.core.config import settings
from app.models.models import Document, DocumentChunk
from app.services.document_processing import DocumentChunker, ChunkStrategy, ProcessingResult
from app.services.document_processing.embedding import create_embedding_service_from_config
from app.services.document_processing.exceptions import DocumentProcessingError
from app.services.document_processing.parsers import FileParserFactory
from app.services.vector_store import vector_store as default_vector_store
```

Constructor:

```python
class DocumentProcessingService:
    def __init__(self, db, embedding_service=None, vector_store=None, chunker=None):
        self.db = db
        self.embedding_service = embedding_service or create_embedding_service_from_config(
            settings.get_embedding_config()
        )
        self.vector_store = vector_store or default_vector_store
        self.chunker = chunker or DocumentChunker(
            chunk_size=500,
            chunk_overlap=50,
            strategy=ChunkStrategy.PARAGRAPH,
        )
```

- [ ] **Step 4: Implement document loading and status updates**

Add:

```python
    async def _get_document(self, document_id: int) -> Document | None:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def _mark_processing(self, document: Document) -> None:
        document.status = "processing"
        document.error_message = None
        await self.db.commit()

    async def _mark_failed(self, document: Document, message: str) -> None:
        document.status = "failed"
        document.error_message = message
        document.vectorized = False
        await self.db.commit()
```

- [ ] **Step 5: Implement successful processing**

Add:

```python
    async def process(self, document_id: int) -> ProcessingResult:
        started = time.perf_counter()
        document = await self._get_document(document_id)
        if document is None:
            return ProcessingResult(
                document_id=document_id,
                status="failed",
                error_message="文档不存在",
            )

        try:
            await self._mark_processing(document)
            parser = FileParserFactory.get_parser(document.file_type)
            parsed = parser.parse(document.file_path)
            chunks = self.chunker.chunk(
                parsed.content,
                metadata={
                    "document_id": document.id,
                    "filename": document.original_filename,
                    "department_id": document.department_id,
                },
            )
            texts = [chunk.content for chunk in chunks]
            vectors = await self.embedding_service.embed_texts(texts)
            vector_ids = [f"doc-{document.id}-chunk-{chunk.chunk_index}-{uuid.uuid4()}" for chunk in chunks]

            chunk_rows = [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    vector_id=vector_ids[index],
                    page_number=chunk.page_number,
                    chunk_metadata=json.dumps(chunk.metadata, ensure_ascii=False),
                )
                for index, chunk in enumerate(chunks)
            ]

            self.db.add_all(chunk_rows)
            metadatas = [
                {
                    "document_id": document.id,
                    "chunk_id": str(chunk_rows[index].chunk_index),
                    "filename": document.original_filename,
                    "department_id": document.department_id,
                    "content": chunk.content,
                }
                for index, chunk in enumerate(chunks)
            ]
            await self.vector_store.insert_points(vector_ids, vectors, metadatas)

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
                processing_time=time.perf_counter() - started,
            )
        except Exception as exc:
            logger.exception(f"文档处理失败 document_id={document.id}")
            await self._mark_failed(document, str(exc))
            return ProcessingResult(
                document_id=document.id,
                status="failed",
                error_message=str(exc),
                processing_time=time.perf_counter() - started,
            )
```

- [ ] **Step 6: Run processor tests**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_document_processor.py
```

Expected:

```text
2 passed
```

## Task 6: Document Detail/Delete Permissions And Cleanup

**Files:**
- Modify: `backend/app/api/documents.py`
- Test: `backend/tests/test_documents_api.py`

- [ ] **Step 1: Add detail/delete permission tests**

Append to `backend/tests/test_documents_api.py`:

```python
def _document_result(document):
    result = MagicMock()
    result.scalar_one_or_none.return_value = document
    return result


def test_get_document_rejects_cross_department(client_and_db):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(user_id=10, department_id=20)

    app.dependency_overrides[get_current_user] = override_get_current_user

    document = MagicMock()
    document.department_id = 99
    db_session.execute = AsyncMock(return_value=_document_result(document))

    response = client.get("/api/v1/documents/1", follow_redirects=False)

    assert response.status_code == 404
    assert response.json() == {"detail": "文档不存在"}


def test_delete_document_cleans_file_and_vectors(client_and_db, monkeypatch):
    client, db_session, app = client_and_db

    async def override_get_current_user():
        return MockUser(user_id=10, department_id=20)

    app.dependency_overrides[get_current_user] = override_get_current_user

    document = MagicMock()
    document.id = 1
    document.department_id = 20
    document.file_path = "stored.txt"

    chunk_a = MagicMock()
    chunk_a.vector_id = "vec-a"
    chunk_b = MagicMock()
    chunk_b.vector_id = "vec-b"

    document_result = _document_result(document)
    chunk_result = MagicMock()
    chunk_result.scalars.return_value.all.return_value = [chunk_a, chunk_b]
    db_session.execute = AsyncMock(side_effect=[document_result, chunk_result])

    delete_file = MagicMock()
    delete_vectors = AsyncMock()
    monkeypatch.setattr("app.api.documents.document_storage.delete", delete_file)
    monkeypatch.setattr("app.api.documents.vector_store.delete_points", delete_vectors)

    response = client.delete("/api/v1/documents/1", follow_redirects=False)

    assert response.status_code == 200
    assert response.json() == {"message": "文档已删除"}
    delete_vectors.assert_awaited_once_with(["vec-a", "vec-b"])
    delete_file.assert_called_once_with("stored.txt")
    db_session.delete.assert_awaited_once_with(document)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_documents_api.py
```

Expected:

```text
FAILED test_get_document_rejects_cross_department
FAILED test_delete_document_cleans_file_and_vectors
```

- [ ] **Step 3: Add helper to load same-department document**

In `backend/app/api/documents.py`, import:

```python
from sqlalchemy import select
from app.models import DocumentChunk
from app.services.vector_store import vector_store
```

Add:

```python
async def _get_department_document_or_404(
    document_id: int,
    db: AsyncSession,
    current_user: User,
) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document or document.department_id != current_user.department_id:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document
```

- [ ] **Step 4: Apply helper to detail endpoint**

Change `get_document` signature:

```python
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_department_document_or_404(document_id, db, current_user)
```

- [ ] **Step 5: Clean vectors and file in delete endpoint**

Change `delete_document`:

```python
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await _get_department_document_or_404(document_id, db, current_user)

    chunk_result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )
    chunks = chunk_result.scalars().all()
    vector_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]
    if vector_ids:
        await vector_store.delete_points(vector_ids)

    document_storage.delete(document.file_path)
    await db.delete(document)
    await db.commit()

    return {"message": "文档已删除"}
```

- [ ] **Step 6: Run document API tests**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_documents_api.py
```

Expected:

```text
all tests in tests\test_documents_api.py pass
```

## Task 7: Frontend Document Management Status

**Files:**
- Modify: `frontend/src/api/modules.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/AdminLayout.vue`
- Modify: `frontend/src/views/AdminView.vue`

- [ ] **Step 1: Update document API type**

In `frontend/src/api/modules.ts`, extend `Document`:

```ts
export interface Document {
  id: number
  filename: string
  original_filename: string
  file_type: string
  file_size: number
  status: string
  vectorized: boolean
  chunk_count: number
  error_message?: string | null
}
```

- [ ] **Step 2: Add documents route**

In `frontend/src/router/index.ts`, add child route:

```ts
{
  path: 'documents',
  name: 'DocumentManage',
  component: () => import('@/views/AdminView.vue'),
  meta: { title: '文档管理' }
}
```

Change `/admin` redirect:

```ts
redirect: '/admin/documents'
```

- [ ] **Step 3: Add menu item**

In `frontend/src/layouts/AdminLayout.vue`, import `Document` icon:

```ts
import { User, Key, OfficeBuilding, Document } from '@element-plus/icons-vue'
```

Add menu item before user management:

```vue
<el-menu-item index="/admin/documents">
  <el-icon><Document /></el-icon>
  <span>文档管理</span>
</el-menu-item>
```

- [ ] **Step 4: Show failure reason and auto-refresh**

In `frontend/src/views/AdminView.vue`, add table column after status:

```vue
<el-table-column prop="error_message" label="失败原因" min-width="180">
  <template #default="{ row }">
    <span v-if="row.status === 'failed'">{{ row.error_message || '-' }}</span>
    <span v-else>-</span>
  </template>
</el-table-column>
```

Add polling state:

```ts
import { ref, onMounted, onUnmounted } from 'vue'

let pollingTimer: number | undefined

const hasProcessingDocuments = () => {
  return documents.value.some(doc => ['pending', 'processing'].includes(doc.status))
}

const syncPolling = () => {
  if (hasProcessingDocuments() && pollingTimer === undefined) {
    pollingTimer = window.setInterval(loadDocuments, 5000)
  }
  if (!hasProcessingDocuments() && pollingTimer !== undefined) {
    window.clearInterval(pollingTimer)
    pollingTimer = undefined
  }
}
```

Call `syncPolling()` at the end of successful `loadDocuments()`:

```ts
documents.value = response.documents
total.value = response.total
syncPolling()
```

Stop polling:

```ts
onUnmounted(() => {
  if (pollingTimer !== undefined) {
    window.clearInterval(pollingTimer)
  }
})
```

- [ ] **Step 5: Build frontend**

Run:

```powershell
npm run build
```

from `frontend`.

Expected:

```text
✓ built
```

## Task 8: End-To-End Verification

**Files:**
- No new source files.
- May update README only if behavior differs from the current feature-progress section.

- [ ] **Step 1: Run focused backend tests**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_startup_imports.py tests\test_document_storage.py tests\test_documents_api.py tests\test_document_processor.py
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 2: Run existing stable tests**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q tests\test_rbac_models.py tests\test_rbac_service.py tests\test_rbac_dependencies.py tests\test_departments_api.py tests\test_users_department_filter.py
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 3: Run full backend test suite**

Run:

```powershell
$env:PYTHONPATH='.'; uv run pytest -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 4: Run frontend build**

Run:

```powershell
npm run build
```

from `frontend`.

Expected:

```text
✓ built
```

- [ ] **Step 5: Manual cloud Chroma smoke test**

Use `.env` values for the Chroma test account. Do not commit credentials.

Run:

```powershell
$env:PYTHONPATH='.'; uv run python -c "from app.services.vector_store import VectorStore; store = VectorStore(); print(type(store.client).__name__)"
```

Expected with `CHROMA_MODE=cloud`:

```text
CloudClient
```

- [ ] **Step 6: Manual upload-query smoke test**

Start backend, worker, and frontend using project commands:

```powershell
uv run uvicorn app.main:app --reload
uv run celery -A app.tasks worker --loglevel=info
npm run dev
```

Manual acceptance:

- Login with the default admin account.
- Upload a small `.txt` document.
- Wait until status becomes `completed`.
- Ask a question whose answer appears in the uploaded text.
- Confirm response sources include the uploaded filename.
- Delete the document.
- Confirm it disappears from the list.

## Self-Review

- Spec coverage: startup, Chroma CloudClient/local, Celery import, upload, processing, delete cleanup, permissions, frontend status, and verification are covered by Tasks 1-8.
- Placeholder scan: the plan contains concrete task content and no intentionally unfinished sections.
- Type consistency: `DocumentProcessingService.process(document_id)` returns `ProcessingResult`; `process_document.delay(document.id)` matches the new task signature; document responses include `error_message` in both backend and frontend types.
