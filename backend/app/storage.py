"""
Binary storage for plant images.

Routers talk to this interface instead of GridFS directly, so the backend can be
moved to S3/MinIO later and tests can run without a real MongoDB.
"""
import io
from typing import Optional

from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from app.database import get_db_dep


class StorageNotFound(Exception):
    pass


class GridFSStorage:
    def __init__(self, db):
        self._fs = AsyncIOMotorGridFSBucket(db)

    async def put(self, filename: str, data: bytes, metadata: Optional[dict] = None) -> str:
        file_id = await self._fs.upload_from_stream(filename or "unnamed", io.BytesIO(data), metadata=metadata or {})
        return str(file_id)

    async def get(self, file_id: str) -> bytes:
        try:
            stream = await self._fs.open_download_stream(ObjectId(file_id))
            return await stream.read()
        except Exception as e:
            raise StorageNotFound(file_id) from e

    async def delete(self, file_id: str) -> None:
        try:
            await self._fs.delete(ObjectId(file_id))
        except Exception:
            pass


class MemoryStorage:
    """In-process storage for tests and local demos."""

    def __init__(self):
        self.files: dict = {}

    async def put(self, filename: str, data: bytes, metadata: Optional[dict] = None) -> str:
        file_id = str(ObjectId())
        self.files[file_id] = {"filename": filename, "data": bytes(data), "metadata": metadata or {}}
        return file_id

    async def get(self, file_id: str) -> bytes:
        if file_id not in self.files:
            raise StorageNotFound(file_id)
        return self.files[file_id]["data"]

    async def delete(self, file_id: str) -> None:
        self.files.pop(file_id, None)


async def get_storage_dep(db=Depends(get_db_dep)):
    return GridFSStorage(db)
