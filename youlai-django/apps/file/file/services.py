"""平台-文件服务。

支持两种存储方式，由 OSS_TYPE 控制：
- minio：对象存储（默认）
- local：本地磁盘，配合 LOCAL_STORAGE_PATH / LOCAL_STORAGE_BASE_URL
"""

from __future__ import annotations

import hashlib
import hmac
import io
import mimetypes
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from minio import Minio


@dataclass(frozen=True)
class UploadedFileInfo:
    name: str
    url: str
    storage_path: str


def get_file_service():
    """根据 OSS_TYPE 返回对应的文件存储服务。"""
    if (getattr(settings, 'OSS_TYPE', 'minio') or '').lower() == 'local':
        return LocalFileService()
    return MinioFileService()


class MinioFileService:
    def upload_file(self, upload_file, prefix: str = "") -> UploadedFileInfo:
        """上传普通文件，按哈希规则生成存储路径。"""
        content = upload_file.read()
        file_name = safe_file_name(upload_file.name)
        storage_path = build_storage_path(content, file_name, prefix)
        self._put_object(content, storage_path, guess_content_type(file_name))
        return UploadedFileInfo(
            name=file_name,
            url=self._build_url(storage_path),
            storage_path=storage_path,
        )

    def upload_bytes(
        self,
        content: bytes,
        file_name: str,
        content_type: str | None = None,
        prefix: str = "",
    ) -> UploadedFileInfo:
        """上传字节内容，按哈希规则生成存储路径。"""
        file_name = safe_file_name(file_name)
        storage_path = build_storage_path(content, file_name, prefix)
        self._put_object(content, storage_path, content_type or guess_content_type(file_name))
        return UploadedFileInfo(
            name=file_name,
            url=self._build_url(storage_path),
            storage_path=storage_path,
        )

    def upload_bytes_at(
        self,
        content: bytes,
        storage_path: str,
        content_type: str | None = None,
    ) -> UploadedFileInfo:
        """按指定存储路径上传，用于需要保留相对目录结构的场景（如 URDF 压缩包）。"""
        storage_path = storage_path.lstrip("/")
        file_name = os.path.basename(storage_path)
        self._put_object(content, storage_path, content_type or guess_content_type(file_name))
        return UploadedFileInfo(
            name=file_name,
            url=self._build_url(storage_path),
            storage_path=storage_path,
        )

    def delete_file(self, file_path: str) -> None:
        self._client().remove_object(settings.MINIO_BUCKET_NAME, file_path)

    def delete_prefix(self, prefix: str) -> None:
        """删除指定目录下的全部对象。"""
        prefix = (prefix or "").strip("/")
        if not prefix:
            raise ValueError("拒绝删除空路径")
        minio_client = self._client()
        objects = minio_client.list_objects(
            settings.MINIO_BUCKET_NAME,
            prefix=f"{prefix}/",
            recursive=True,
        )
        for obj in objects:
            minio_client.remove_object(settings.MINIO_BUCKET_NAME, obj.object_name)

    def _client(self) -> Minio:
        minio_client = Minio(
            self._endpoint(),
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SSL,
        )
        bucket_name = settings.MINIO_BUCKET_NAME
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            self._set_bucket_public_policy(minio_client, bucket_name)
        elif not self._check_bucket_has_public_policy(minio_client, bucket_name):
            self._set_bucket_public_policy(minio_client, bucket_name)
        return minio_client

    def _put_object(self, content: bytes, storage_path: str, content_type: str) -> None:
        self._client().put_object(
            settings.MINIO_BUCKET_NAME,
            storage_path,
            io.BytesIO(content),
            len(content),
            content_type=content_type,
        )

    def _build_url(self, storage_path: str) -> str:
        host = (settings.MINIO_HOST_PORT or "").rstrip("/")
        if "://" in host:
            base = host
        else:
            protocol = 'https' if settings.MINIO_SSL else 'http'
            base = f"{protocol}://{host}"
        return f"{base}/{settings.MINIO_BUCKET_NAME}/{quote(storage_path, safe='/')}"

    @staticmethod
    def _endpoint() -> str:
        """MinIO SDK 要求 endpoint 不带协议和路径。"""
        endpoint = (settings.MINIO_HOST_PORT or "").strip()
        if "://" in endpoint:
            endpoint = endpoint.split("://", 1)[1]
        return endpoint.rstrip("/")

    def _set_bucket_public_policy(self, minio_client: Minio, bucket_name: str) -> None:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                }
            ],
        }
        import json

        minio_client.set_bucket_policy(bucket_name, json.dumps(policy))

    def _check_bucket_has_public_policy(self, minio_client: Minio, bucket_name: str) -> bool:
        import json

        try:
            policy = minio_client.get_bucket_policy(bucket_name)
            policy_dict = json.loads(policy)
            for statement in policy_dict.get("Statement", []):
                if (
                    statement.get("Effect") == "Allow"
                    and statement.get("Principal", {}).get("AWS") == "*"
                    and "s3:GetObject" in statement.get("Action", [])
                ):
                    return True
            return False
        except Exception:
            return False


class LocalFileService:
    """本地磁盘存储，适合单机部署或本地开发。"""

    def __init__(self):
        self.root = Path(settings.LOCAL_STORAGE_PATH).resolve()

    def upload_file(self, upload_file, prefix: str = "") -> UploadedFileInfo:
        content = upload_file.read()
        return self.upload_bytes(content, upload_file.name, prefix=prefix)

    def upload_bytes(
        self,
        content: bytes,
        file_name: str,
        content_type: str | None = None,
        prefix: str = "",
    ) -> UploadedFileInfo:
        file_name = safe_file_name(file_name)
        storage_path = build_storage_path(content, file_name, prefix)
        self._write(storage_path, content)
        return UploadedFileInfo(
            name=file_name,
            url=self._build_url(storage_path),
            storage_path=storage_path,
        )

    def upload_bytes_at(
        self,
        content: bytes,
        storage_path: str,
        content_type: str | None = None,
    ) -> UploadedFileInfo:
        storage_path = storage_path.lstrip("/")
        self._write(storage_path, content)
        return UploadedFileInfo(
            name=os.path.basename(storage_path),
            url=self._build_url(storage_path),
            storage_path=storage_path,
        )

    def delete_file(self, file_path: str) -> None:
        target = self._resolve(file_path)
        if target.is_file():
            target.unlink()

    def delete_prefix(self, prefix: str) -> None:
        prefix = (prefix or "").strip("/")
        if not prefix:
            raise ValueError("拒绝删除空路径")
        target = self._resolve(prefix)
        if target.is_dir():
            shutil.rmtree(target)

    def _write(self, storage_path: str, content: bytes) -> None:
        target = self._resolve(storage_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def _resolve(self, storage_path: str) -> Path:
        target = (self.root / storage_path.lstrip("/")).resolve()
        if self.root not in target.parents and target != self.root:
            raise ValueError("非法的存储路径")
        return target

    def _build_url(self, storage_path: str) -> str:
        base = (settings.LOCAL_STORAGE_BASE_URL or "/storage").rstrip("/")
        return f"{base}/{quote(storage_path, safe='/')}"


def safe_file_name(file_name: str) -> str:
    name = os.path.basename((file_name or "").replace("\\", "/"))
    return name or "file"


def guess_content_type(file_name: str) -> str:
    content_type, _ = mimetypes.guess_type(file_name)
    return content_type or 'application/octet-stream'


def build_storage_path(content: bytes, file_name: str, prefix: str = "") -> str:
    md5_hash = hashlib.md5()
    md5_hash.update(content)
    md5_code = md5_hash.hexdigest()

    timestamp = str(int(time.time()))
    random_str = str(uuid.uuid4()).replace('-', '')[:12]
    signature_data = f"{md5_code}_{timestamp}_{random_str}"
    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        signature_data.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()[:16]

    security_part = f"{timestamp}{random_str}{signature}"
    directory = (prefix or "").strip("/")
    directory_part = f"{directory}/" if directory else ""
    return f"{directory_part}{md5_code[0]}/{md5_code[1]}/{md5_code}__{security_part}__{file_name}"
