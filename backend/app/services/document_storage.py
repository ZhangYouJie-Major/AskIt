"""
本地文档存储服务。
"""
from pathlib import Path

from starlette.datastructures import UploadFile

from app.core.config import settings


class LocalDocumentStorage:
    """基于本地文件系统的文档存储。"""

    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir or settings.upload_storage_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        """解析存储路径，并拒绝逃逸存储目录。"""
        target = (self.base_dir / relative_path).resolve()
        if target != self.base_dir and self.base_dir not in target.parents:
            raise ValueError("非法文件路径")
        return target

    async def save_upload(self, file: UploadFile, stored_filename: str) -> str:
        """保存上传文件，返回存储文件名。"""
        target = self.resolve(stored_filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        await file.seek(0)
        with target.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        return stored_filename

    def delete(self, relative_path: str) -> None:
        """删除存储文件。"""
        target = self.resolve(relative_path)
        if target.exists() and target.is_file():
            target.unlink()

    def exists(self, relative_path: str) -> bool:
        """检查存储文件是否存在。"""
        return self.resolve(relative_path).is_file()


document_storage = LocalDocumentStorage()
