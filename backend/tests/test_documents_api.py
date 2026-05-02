from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from fastapi import HTTPException, UploadFile

from app.api import documents


def _scalar_one_or_none_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_all_result(values):
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


@pytest.mark.asyncio
async def test_upload_rejects_user_without_department(monkeypatch):
    """未分配部门的用户不能上传文档。"""
    db = AsyncMock()
    db.add = MagicMock()
    file = UploadFile(filename="askit.txt", file=BytesIO(b"hello askit"))
    user = SimpleNamespace(id=10, department_id=None)

    with pytest.raises(HTTPException) as exc_info:
        await documents.upload_document(file=file, db=db, current_user=user)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "当前用户未分配部门，无法上传文档"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_upload_saves_file_queues_processing_and_returns_error_message(monkeypatch):
    """上传成功后保存文件、写入文档记录，并投递处理任务。"""
    db = AsyncMock()
    db.add = MagicMock()
    file = UploadFile(
        filename="askit.txt",
        file=BytesIO(b"hello askit"),
        headers={"content-type": "text/plain"},
    )
    user = SimpleNamespace(id=10, department_id=3)
    saved_paths = []
    queued_ids = []

    async def fake_save_upload(upload_file, stored_filename):
        saved_paths.append((upload_file, stored_filename))
        return f"documents/{stored_filename}"

    async def fake_refresh(document):
        document.id = 42

    monkeypatch.setattr(documents.document_storage, "save_upload", fake_save_upload)
    monkeypatch.setattr(
        documents,
        "dispatch_document_processing",
        lambda document_id: queued_ids.append(document_id),
    )
    db.refresh.side_effect = fake_refresh

    document = await documents.upload_document(file=file, db=db, current_user=user)

    assert saved_paths[0][0] is file
    stored_filename = saved_paths[0][1]
    assert stored_filename.endswith(".txt")
    assert document.filename == stored_filename
    assert document.original_filename == "askit.txt"
    assert document.file_path == f"documents/{stored_filename}"
    assert document.file_size == len(b"hello askit")
    assert document.file_type == "txt"
    assert document.mime_type == "text/plain"
    assert document.status == "pending"
    assert document.department_id == 3
    assert document.uploaded_by == 10
    assert queued_ids == [42]

    response = documents.DocumentResponse.model_validate(document, from_attributes=True)
    assert response.error_message is None
    db.add.assert_called_once_with(document)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(document)


@pytest.mark.asyncio
async def test_upload_deletes_saved_file_when_db_commit_fails(monkeypatch):
    """数据库提交失败时删除已保存文件，且不派发处理任务。"""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit.side_effect = RuntimeError("db down")
    file = UploadFile(filename="askit.txt", file=BytesIO(b"hello askit"))
    user = SimpleNamespace(id=10, department_id=3)
    deleted_paths = []

    async def fake_save_upload(upload_file, stored_filename):
        return f"documents/{stored_filename}"

    monkeypatch.setattr(documents.document_storage, "save_upload", fake_save_upload)
    monkeypatch.setattr(
        documents.document_storage,
        "delete",
        lambda file_path: deleted_paths.append(file_path),
    )
    dispatch = MagicMock()
    monkeypatch.setattr(documents, "dispatch_document_processing", dispatch)

    with pytest.raises(RuntimeError, match="db down"):
        await documents.upload_document(file=file, db=db, current_user=user)

    saved_document = db.add.call_args.args[0]
    assert deleted_paths == [saved_document.file_path]
    dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_upload_marks_document_failed_when_dispatch_fails(monkeypatch):
    """处理任务派发失败时保留文档记录并标记失败。"""
    db = AsyncMock()
    db.add = MagicMock()
    file = UploadFile(filename="askit.txt", file=BytesIO(b"hello askit"))
    user = SimpleNamespace(id=10, department_id=3)
    deleted_paths = []

    async def fake_save_upload(upload_file, stored_filename):
        return f"documents/{stored_filename}"

    async def fake_refresh(document):
        document.id = 42

    def fake_dispatch(document_id):
        assert document_id == 42
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(documents.document_storage, "save_upload", fake_save_upload)
    monkeypatch.setattr(
        documents.document_storage,
        "delete",
        lambda file_path: deleted_paths.append(file_path),
    )
    monkeypatch.setattr(documents, "dispatch_document_processing", fake_dispatch)
    db.refresh.side_effect = fake_refresh

    with pytest.raises(HTTPException) as exc_info:
        await documents.upload_document(file=file, db=db, current_user=user)

    saved_document = db.add.call_args.args[0]
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "文档处理任务派发失败: broker unavailable"
    assert saved_document.status == "failed"
    assert saved_document.error_message == "文档处理任务派发失败: broker unavailable"
    assert saved_document.vectorized is False
    assert db.commit.await_count == 2
    assert deleted_paths == []


@pytest.mark.asyncio
async def test_get_document_returns_404_for_cross_department_document():
    """跨部门查看文档时按不存在处理。"""
    db = AsyncMock()
    document = SimpleNamespace(id=42, department_id=8)
    user = SimpleNamespace(id=10, department_id=3)
    db.execute.return_value = _scalar_one_or_none_result(document)

    with pytest.raises(HTTPException) as exc_info:
        await documents.get_document(document_id=42, db=db, current_user=user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "文档不存在"


@pytest.mark.asyncio
async def test_get_document_returns_404_for_unassigned_user_and_document():
    """未分配部门的用户不能查看未分配部门的文档。"""
    db = AsyncMock()
    document = SimpleNamespace(id=42, department_id=None)
    user = SimpleNamespace(id=10, department_id=None)
    db.execute.return_value = _scalar_one_or_none_result(document)

    with pytest.raises(HTTPException) as exc_info:
        await documents.get_document(document_id=42, db=db, current_user=user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "文档不存在"


@pytest.mark.asyncio
async def test_get_document_returns_same_department_document():
    """同部门用户可以查看文档详情。"""
    db = AsyncMock()
    document = SimpleNamespace(id=42, department_id=3)
    user = SimpleNamespace(id=10, department_id=3)
    db.execute.return_value = _scalar_one_or_none_result(document)

    result = await documents.get_document(document_id=42, db=db, current_user=user)

    assert result is document


@pytest.mark.asyncio
async def test_delete_document_cleans_vectors_file_and_row_for_same_department(monkeypatch):
    """同部门删除文档时清理向量、文件和文档记录。"""
    db = AsyncMock()
    document = SimpleNamespace(id=42, department_id=3, file_path="documents/askit.txt")
    chunks = [
        SimpleNamespace(vector_id="vec-1"),
        SimpleNamespace(vector_id=""),
        SimpleNamespace(vector_id=None),
        SimpleNamespace(vector_id="vec-2"),
    ]
    user = SimpleNamespace(id=10, department_id=3)
    db.execute.side_effect = [
        _scalar_one_or_none_result(document),
        _scalars_all_result(chunks),
    ]
    delete_points = AsyncMock()
    deleted_paths = []
    monkeypatch.setattr(documents.vector_store, "delete_points", delete_points)
    monkeypatch.setattr(
        documents.document_storage,
        "delete",
        lambda file_path: deleted_paths.append(file_path),
    )

    response = await documents.delete_document(document_id=42, db=db, current_user=user)

    assert response == {"message": "文档已删除"}
    delete_points.assert_awaited_once_with(["vec-1", "vec-2"])
    assert deleted_paths == ["documents/askit.txt"]
    assert db.delete.await_args_list == [
        call(chunks[0]),
        call(chunks[1]),
        call(chunks[2]),
        call(chunks[3]),
        call(document),
    ]
    db.commit.assert_awaited_once()
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_documents_returns_empty_for_user_without_department():
    """未分配部门用户不能默认看到部门 1 的文档。"""
    db = AsyncMock()
    user = SimpleNamespace(id=10, department_id=None)

    response = await documents.list_documents(db=db, current_user=user)

    assert response == {"total": 0, "documents": []}
    db.execute.assert_not_awaited()
    db.scalar.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_document_returns_404_for_cross_department_without_cleanup(monkeypatch):
    """跨部门删除文档时不清理向量、文件或数据库记录。"""
    db = AsyncMock()
    document = SimpleNamespace(id=42, department_id=8, file_path="documents/askit.txt")
    user = SimpleNamespace(id=10, department_id=3)
    db.execute.return_value = _scalar_one_or_none_result(document)
    delete_points = AsyncMock()
    delete_file = MagicMock()
    monkeypatch.setattr(documents.vector_store, "delete_points", delete_points)
    monkeypatch.setattr(documents.document_storage, "delete", delete_file)

    with pytest.raises(HTTPException) as exc_info:
        await documents.delete_document(document_id=42, db=db, current_user=user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "文档不存在"
    delete_points.assert_not_awaited()
    delete_file.assert_not_called()
    db.delete.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_document_returns_404_for_unassigned_user_without_cleanup(monkeypatch):
    """未分配部门用户删除未分配部门文档时不清理任何资源。"""
    db = AsyncMock()
    document = SimpleNamespace(id=42, department_id=None, file_path="documents/askit.txt")
    user = SimpleNamespace(id=10, department_id=None)
    db.execute.return_value = _scalar_one_or_none_result(document)
    delete_points = AsyncMock()
    delete_file = MagicMock()
    monkeypatch.setattr(documents.vector_store, "delete_points", delete_points)
    monkeypatch.setattr(documents.document_storage, "delete", delete_file)

    with pytest.raises(HTTPException) as exc_info:
        await documents.delete_document(document_id=42, db=db, current_user=user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "文档不存在"
    delete_points.assert_not_awaited()
    delete_file.assert_not_called()
    db.delete.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_document_does_not_delete_file_when_commit_fails(monkeypatch):
    """数据库提交失败时，已清理向量但不删除本地文件。"""
    db = AsyncMock()
    db.commit.side_effect = RuntimeError("commit down")
    document = SimpleNamespace(id=42, department_id=3, file_path="documents/askit.txt")
    chunks = [SimpleNamespace(vector_id="vec-1")]
    user = SimpleNamespace(id=10, department_id=3)
    db.execute.side_effect = [
        _scalar_one_or_none_result(document),
        _scalars_all_result(chunks),
    ]
    delete_points = AsyncMock()
    delete_file = MagicMock()
    monkeypatch.setattr(documents.vector_store, "delete_points", delete_points)
    monkeypatch.setattr(documents.document_storage, "delete", delete_file)

    with pytest.raises(RuntimeError, match="commit down"):
        await documents.delete_document(document_id=42, db=db, current_user=user)

    delete_points.assert_awaited_once_with(["vec-1"])
    assert db.delete.await_args_list == [call(chunks[0]), call(document)]
    db.commit.assert_awaited_once()
    delete_file.assert_not_called()


@pytest.mark.asyncio
async def test_delete_document_returns_500_when_file_delete_fails_after_commit(monkeypatch):
    """数据库提交成功后文件删除失败时返回 500。"""
    db = AsyncMock()
    document = SimpleNamespace(id=42, department_id=3, file_path="documents/askit.txt")
    user = SimpleNamespace(id=10, department_id=3)
    db.execute.side_effect = [
        _scalar_one_or_none_result(document),
        _scalars_all_result([]),
    ]
    delete_points = AsyncMock()
    monkeypatch.setattr(documents.vector_store, "delete_points", delete_points)
    monkeypatch.setattr(
        documents.document_storage,
        "delete",
        MagicMock(side_effect=RuntimeError("disk down")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await documents.delete_document(document_id=42, db=db, current_user=user)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "文档文件删除失败: disk down"
    delete_points.assert_not_awaited()
    db.delete.assert_awaited_once_with(document)
    db.commit.assert_awaited_once()
