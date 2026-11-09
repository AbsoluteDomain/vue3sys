"""BOM 附件服务：文件落 MinIO，元数据落 bom_attachment。"""

from __future__ import annotations

import zipfile
from pathlib import PurePosixPath
from uuid import uuid4

from django.utils import timezone

from apps.file.file.services import get_file_service

from .models import BomAttachment, BomList

MAX_FILE_SIZE = {
    BomAttachment.TYPE_EXCEL: 20 * 1024 * 1024,
    BomAttachment.TYPE_PDF: 20 * 1024 * 1024,
    BomAttachment.TYPE_URDF: 50 * 1024 * 1024,
}

ALLOWED_EXTENSIONS = {
    BomAttachment.TYPE_EXCEL: {".xls", ".xlsx"},
    BomAttachment.TYPE_PDF: {".pdf"},
    BomAttachment.TYPE_URDF: {".urdf", ".zip"},
}

# 压缩包解压后的总大小上限，避免 zip 炸弹
MAX_UNCOMPRESSED_SIZE = 200 * 1024 * 1024


class AttachmentValidationError(Exception):
    """附件校验失败，由视图转换为 400 响应。"""


def save_bom_attachment(
    bom_id,
    file_type,
    upload_file,
    uploader_id=None,
    uploader_name="",
) -> BomAttachment:
    if file_type not in MAX_FILE_SIZE:
        raise AttachmentValidationError("不支持的文件类型")
    if not upload_file:
        raise AttachmentValidationError("请选择要上传的文件")
    if upload_file.size > MAX_FILE_SIZE[file_type]:
        limit_mb = MAX_FILE_SIZE[file_type] // (1024 * 1024)
        raise AttachmentValidationError(f"文件大小不能超过 {limit_mb}MB")

    try:
        bom = BomList.objects.get(id=int(bom_id), is_del=0)
    except (BomList.DoesNotExist, TypeError, ValueError):
        raise AttachmentValidationError("BOM 不存在")

    file_name = _safe_name(upload_file.name)
    suffix = PurePosixPath(file_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS[file_type]:
        allowed = "、".join(sorted(ALLOWED_EXTENSIONS[file_type]))
        raise AttachmentValidationError(f"仅支持上传 {allowed} 格式")

    svc = get_file_service()
    entry_name = file_name

    if file_type == BomAttachment.TYPE_URDF and suffix == ".zip":
        url, storage_path, entry_name = _upload_urdf_zip(svc, bom.id, upload_file)
    else:
        uploaded = svc.upload_bytes(
            upload_file.read(),
            file_name,
            prefix=f"bom/{bom.id}/{file_type}",
        )
        url, storage_path = uploaded.url, uploaded.storage_path

    now = timezone.now()
    return BomAttachment.objects.create(
        bom_id=bom.id,
        file_type=file_type,
        file_name=entry_name if file_type == BomAttachment.TYPE_URDF else file_name,
        file_url=url,
        storage_path=storage_path,
        file_size=upload_file.size,
        mime_type=_guess_mime_type(file_name),
        uploader_id=uploader_id,
        uploader_name=uploader_name or "",
        is_del=0,
        created_at=now,
        updated_at=now,
    )


def delete_bom_attachment(attachment_id) -> BomAttachment:
    try:
        attachment = BomAttachment.objects.get(id=int(attachment_id), is_del=0)
    except (BomAttachment.DoesNotExist, TypeError, ValueError):
        raise AttachmentValidationError("附件不存在")

    svc = get_file_service()
    if attachment.file_type == BomAttachment.TYPE_URDF:
        # URDF 压缩包会解压出多个文件，按入口文件所在目录整体清理
        parent = PurePosixPath(attachment.storage_path).parent.as_posix()
        svc.delete_prefix(parent)
    else:
        svc.delete_file(attachment.storage_path)

    attachment.is_del = 1
    attachment.updated_at = timezone.now()
    attachment.save(update_fields=["is_del", "updated_at"])
    return attachment


def _upload_urdf_zip(svc, bom_id: int, upload_file):
    """上传 URDF 压缩包，按原目录结构写入 MinIO，返回入口 urdf 的地址与路径。"""
    try:
        archive = zipfile.ZipFile(upload_file)
    except zipfile.BadZipFile as exc:
        raise AttachmentValidationError("压缩包格式不正确") from exc

    with archive:
        files = [info for info in archive.infolist() if not info.is_dir()]
        if not files:
            raise AttachmentValidationError("压缩包为空")

        total_size = 0
        normalized = []
        for info in files:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                raise AttachmentValidationError("压缩包包含非法路径")
            total_size += info.file_size
            normalized.append((path.as_posix(), info))

        if total_size > MAX_UNCOMPRESSED_SIZE:
            limit_mb = MAX_UNCOMPRESSED_SIZE // (1024 * 1024)
            raise AttachmentValidationError(f"压缩包解压后不能超过 {limit_mb}MB")

        urdf_names = [name for name, _ in normalized if name.lower().endswith(".urdf")]
        if len(urdf_names) != 1:
            raise AttachmentValidationError("压缩包内必须且只能包含一个 .urdf 文件")
        entry_name = urdf_names[0]

        token = uuid4().hex[:12]
        prefix = f"bom/{bom_id}/urdf/{token}"
        entry_url = ""
        entry_path = ""

        for name, info in normalized:
            uploaded = svc.upload_bytes_at(
                archive.read(info),
                f"{prefix}/{name}",
            )
            if name == entry_name:
                entry_url = uploaded.url
                entry_path = uploaded.storage_path

    return entry_url, entry_path, PurePosixPath(entry_name).name


def _safe_name(file_name: str) -> str:
    name = PurePosixPath((file_name or "").replace("\\", "/")).name
    return name or "file"


def _guess_mime_type(file_name: str) -> str:
    import mimetypes

    mime_type, _ = mimetypes.guess_type(file_name)
    return mime_type or "application/octet-stream"
