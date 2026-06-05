"""平台-文件服务。

"""

from __future__ import annotations

import hashlib
import hmac
import io
import mimetypes
import time
import uuid
from dataclasses import dataclass

from django.conf import settings
from minio import Minio


@dataclass(frozen=True)
class UploadedFileInfo:
    name: str
    url: str


class MinioFileService:
    def upload_file(self, upload_file) -> UploadedFileInfo:
        minio_client = Minio(
            settings.MINIO_HOST_PORT,
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

        file_content = upload_file.read()

        md5_hash = hashlib.md5()
        md5_hash.update(file_content)
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

        first_char = md5_code[0]
        second_char = md5_code[1]
        file_name = upload_file.name
        storage_path = f"{first_char}/{second_char}/{md5_code}__{security_part}__{file_name}"

        content_type, _ = mimetypes.guess_type(file_name)
        if content_type is None:
            content_type = 'application/octet-stream'

        file_size = len(file_content)

        minio_client.put_object(
            bucket_name,
            storage_path,
            io.BytesIO(file_content),
            file_size,
            content_type=content_type,
        )

        protocol = 'https' if settings.MINIO_SSL else 'http'
        url = f"{protocol}://{settings.MINIO_HOST_PORT}/{bucket_name}/{storage_path}"

        return UploadedFileInfo(name=file_name, url=url)

    def delete_file(self, file_path: str) -> None:
        minio_client = Minio(
            settings.MINIO_HOST_PORT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SSL,
        )
        bucket_name = settings.MINIO_BUCKET_NAME
        minio_client.remove_object(bucket_name, file_path)

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
