"""
测试本地文档存储服务。
"""
from io import BytesIO

import pytest
from starlette.datastructures import UploadFile

from app.services.document_storage import LocalDocumentStorage


@pytest.mark.asyncio
async def test_save_upload_and_delete(tmp_path):
    """保存上传文件后可以检查存在并删除。"""
    storage = LocalDocumentStorage(tmp_path)
    upload = UploadFile(BytesIO(b"hello askit"), filename="source.txt")

    stored_path = await storage.save_upload(upload, "documents/source.txt")

    assert stored_path == "documents/source.txt"
    saved_file = tmp_path / "documents" / "source.txt"
    assert saved_file.read_bytes() == b"hello askit"
    assert storage.exists("documents/source.txt") is True

    storage.delete("documents/source.txt")

    assert storage.exists("documents/source.txt") is False


@pytest.mark.asyncio
async def test_save_upload_rewinds_before_copying(tmp_path):
    """上传文件已被读取过时，保存仍从头写入完整内容。"""
    storage = LocalDocumentStorage(tmp_path)
    upload = UploadFile(BytesIO(b"complete content"), filename="source.txt")
    assert await upload.read() == b"complete content"

    await storage.save_upload(upload, "documents/source.txt")

    assert (tmp_path / "documents" / "source.txt").read_bytes() == b"complete content"


def test_resolve_rejects_path_escape(tmp_path):
    """拒绝解析到存储目录外的路径。"""
    storage = LocalDocumentStorage(tmp_path)

    outside_file = tmp_path.parent / "escape.txt"
    escape_paths = [
        "../escape.txt",
        "safe/../../escape.txt",
        str(outside_file),
    ]

    for escape_path in escape_paths:
        with pytest.raises(ValueError, match="非法文件路径"):
            storage.resolve(escape_path)


def test_exists_returns_false_for_directory(tmp_path):
    """目录路径不应被识别为文档文件。"""
    storage = LocalDocumentStorage(tmp_path)
    (tmp_path / "documents").mkdir()

    assert storage.exists("documents") is False
