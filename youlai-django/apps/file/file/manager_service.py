"""文件管理服务：目录与文件的查询、上传、回收站处理。

共享文件空间：所有登录用户看到同一份目录，上传人仅作记录。
"""
from __future__ import annotations

import mimetypes
import os
from pathlib import PurePosixPath

from django.utils import timezone

from apps.file.file.services import get_file_service
from apps.file.models import FileItem

ROOT_ID = 0
MAX_UPLOAD_SIZE = 200 * 1024 * 1024
SORT_FIELDS = {"name": "name", "size": "file_size", "time": "created_at"}

class FileManagerError(Exception):
    """文件管理业务异常，由视图转换为 400 响应。"""


def list_items(
    *,
    parent_id: int = ROOT_ID,
    keyword: str = "",
    sort_field: str = "name",
    sort_order: str = "asc",
    page: int = 1,
    size: int = 10,
    status: str = "normal",
):
    """分页查询目录内容。回收站模式下忽略 parent_id，平铺展示已删除条目。"""
    query = FileItem.objects.filter(is_del=1 if status == "recycle" else 0)
    if status != "recycle":
        query = query.filter(parent_id=int(parent_id))
    if keyword:
        query = query.filter(name__icontains=keyword)

    field = SORT_FIELDS.get(sort_field, "name")
    prefix = "-" if sort_order == "desc" else ""
    # 文件夹永远排在文件前面
    ordering = ["-is_dir", f"{prefix}{field}"]

    total = query.count()
    page = max(int(page), 1)
    size = max(int(size), 1)
    items = query.order_by(*ordering)[(page - 1) * size : page * size]
    return items, total


def get_breadcrumb(parent_id: int):
    """返回从根目录到当前目录的路径链。"""
    chain = []
    current_id = int(parent_id or ROOT_ID)
    guard = 0
    while current_id and guard < 20:
        item = FileItem.objects.filter(id=current_id, is_dir=1, is_del=0).first()
        if not item:
            break
        chain.insert(0, {"id": item.id, "name": item.name})
        current_id = item.parent_id
        guard += 1
    return [{"id": ROOT_ID, "name": "全部文件"}] + chain


def create_folder(*, name: str, parent_id: int = ROOT_ID, user_id=None, user_name: str = "") -> FileItem:
    folder_name = _validate_name(name)
    _ensure_parent(parent_id)
    if FileItem.objects.filter(parent_id=int(parent_id), name=folder_name, is_del=0).exists():
        raise FileManagerError("当前目录已存在同名文件或文件夹")

    now = timezone.now()
    return FileItem.objects.create(
        parent_id=int(parent_id),
        name=folder_name,
        is_dir=1,
        file_size=0,
        file_type="folder",
        uploader_id=user_id,
        uploader_name=user_name or "",
        is_del=0,
        created_at=now,
        updated_at=now,
    )


def save_upload(*, upload_file, parent_id: int = ROOT_ID, user_id=None, user_name: str = "") -> FileItem:
    """保存上传文件：文件本体落存储服务，元数据落 file_manager_item。"""
    if not upload_file:
        raise FileManagerError("请选择要上传的文件")
    if upload_file.size > MAX_UPLOAD_SIZE:
        limit_mb = MAX_UPLOAD_SIZE // (1024 * 1024)
        raise FileManagerError(f"单个文件大小不能超过 {limit_mb}MB")

    _ensure_parent(parent_id)
    file_name = _safe_name(upload_file.name)
    if FileItem.objects.filter(parent_id=int(parent_id), name=file_name, is_del=0).exists():
        raise FileManagerError("当前目录已存在同名文件，请先重命名或删除")

    suffix = PurePosixPath(file_name).suffix.lower().lstrip(".") or "unknown"
    mime_type, _ = mimetypes.guess_type(file_name)
    svc = get_file_service()
    uploaded = svc.upload_bytes(upload_file.read(), file_name, prefix="files")

    now = timezone.now()
    return FileItem.objects.create(
        parent_id=int(parent_id),
        name=file_name,
        is_dir=0,
        storage_path=uploaded.storage_path,
        file_url=uploaded.url,
        file_size=upload_file.size,
        mime_type=mime_type or "application/octet-stream",
        file_type=suffix,
        uploader_id=user_id,
        uploader_name=user_name or "",
        is_del=0,
        created_at=now,
        updated_at=now,
    )


def move_to_recycle(ids) -> int:
    """把选中条目及其所有子条目移入回收站。"""
    targets = _collect_with_descendants(ids, is_del=0)
    if not targets:
        raise FileManagerError("未找到要删除的文件")
    now = timezone.now()
    FileItem.objects.filter(id__in=targets).update(is_del=1, deleted_at=now, updated_at=now)
    return len(targets)


def restore_from_recycle(ids) -> int:
    """从回收站还原选中条目及其所有子条目。"""
    targets = _collect_with_descendants(ids, is_del=1)
    if not targets:
        raise FileManagerError("未找到要还原的文件")
    now = timezone.now()
    FileItem.objects.filter(id__in=targets).update(is_del=0, deleted_at=None, updated_at=now)
    return len(targets)


def purge(ids) -> int:
    """彻底删除（物理文件 + 数据库记录）。"""
    targets = _collect_with_descendants(ids, is_del=1)
    if not targets:
        raise FileManagerError("未找到要彻底删除的文件")

    svc = get_file_service()
    for item in FileItem.objects.filter(id__in=targets, is_dir=0):
        if item.storage_path:
            try:
                svc.delete_file(item.storage_path)
            except Exception:
                # 物理文件不存在时不影响元数据清理
                pass
    deleted_count = FileItem.objects.filter(id__in=targets).delete()[0]
    return deleted_count


def get_download_target(item_id: int) -> FileItem:
    item = FileItem.objects.filter(id=int(item_id), is_del=0, is_dir=0).first()
    if not item:
        raise FileManagerError("文件不存在或已被删除")
    FileItem.objects.filter(id=item.id).update(download_count=item.download_count + 1)
    return item


def local_file_path(storage_path: str) -> str:
    """把存储相对路径转换为本地磁盘绝对路径（仅 local 存储模式使用）。"""
    from django.conf import settings

    return os.path.join(settings.LOCAL_STORAGE_PATH, (storage_path or "").lstrip("/"))


def serialize_item(item: FileItem) -> dict:
    return {
        "id": item.id,
        "parent_id": item.parent_id,
        "name": item.name,
        "is_dir": bool(item.is_dir),
        "file_type": item.file_type or "",
        "file_size": item.file_size or 0,
        "size_text": _format_size(item.file_size or 0),
        "file_url": item.file_url or "",
        "uploader_name": item.uploader_name or "",
        "download_count": item.download_count or 0,
        "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else "",
        "deleted_at": item.deleted_at.strftime("%Y-%m-%d %H:%M:%S") if item.deleted_at else "",
    }


def _collect_with_descendants(ids, *, is_del: int) -> list[int]:
    """收集选中条目及其全部子孙条目 ID。"""
    try:
        root_ids = [int(i) for i in ids if str(i).strip()]
    except (TypeError, ValueError):
        raise FileManagerError("文件 ID 格式不正确")
    if not root_ids:
        raise FileManagerError("请选择要操作的文件")

    collected = set(
        FileItem.objects.filter(id__in=root_ids, is_del=is_del).values_list("id", flat=True)
    )
    if not collected:
        return []

    frontier = list(collected)
    while frontier:
        children = list(
            FileItem.objects.filter(parent_id__in=frontier, is_del=is_del).values_list("id", flat=True)
        )
        frontier = [child_id for child_id in children if child_id not in collected]
        collected.update(frontier)
    return list(collected)


def _ensure_parent(parent_id):
    if int(parent_id or ROOT_ID) == ROOT_ID:
        return
    parent = FileItem.objects.filter(id=int(parent_id), is_dir=1, is_del=0).first()
    if not parent:
        raise FileManagerError("目标目录不存在")


def _validate_name(name: str) -> str:
    folder_name = (name or "").strip()
    if not folder_name:
        raise FileManagerError("文件夹名称不能为空")
    if len(folder_name) > 100:
        raise FileManagerError("文件夹名称不能超过 100 个字符")
    if any(char in folder_name for char in ("/", "\\")) or ".." in folder_name:
        raise FileManagerError("文件夹名称不能包含 / \\ 或 ..")
    return folder_name


def _safe_name(file_name: str) -> str:
    name = PurePosixPath((file_name or "").replace("\\", "/")).name
    return name or "file"


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.2f} GB"
