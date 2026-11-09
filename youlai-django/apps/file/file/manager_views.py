"""文件管理视图：共享文件空间的列表、上传、目录、回收站与下载。

"""
import json
import os

from django.conf import settings
from django.http import FileResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.system.operation_logs.request_user import get_request_operator

from .manager_service import (
    FileManagerError,
    create_folder,
    get_breadcrumb,
    get_download_target,
    list_items,
    local_file_path,
    move_to_recycle,
    purge,
    restore_from_recycle,
    save_upload,
    serialize_item,
)


def _ok(data=None, msg="成功"):
    return JsonResponse({"code": "00000", "msg": msg, "data": data})


def _error(msg, code="A0400", status=400):
    return JsonResponse({"code": code, "msg": msg, "data": None}, status=status)


def _parse_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        raise FileManagerError("请求参数格式不正确")


def _get_operator(request):
    operator = get_request_operator(request)
    return operator if operator else (None, "")


def _parse_ids(body):
    ids = body.get("ids")
    if ids is None and body.get("id") is not None:
        ids = [body.get("id")]
    if not isinstance(ids, list):
        raise FileManagerError("请选择要操作的文件")
    return ids


@require_http_methods(["GET"])
def file_list(request):
    """分页查询当前目录内容（status=recycle 时为回收站列表）。"""
    try:
        items, total = list_items(
            parent_id=request.GET.get("parent_id") or 0,
            keyword=(request.GET.get("keyword") or "").strip(),
            sort_field=request.GET.get("sort_field") or "name",
            sort_order=request.GET.get("sort_order") or "asc",
            page=request.GET.get("page") or 1,
            size=request.GET.get("size") or 10,
            status=request.GET.get("status") or "normal",
        )
    except FileManagerError as exc:
        return _error(str(exc))

    return _ok(
        {
            "list": [serialize_item(item) for item in items],
            "total": total,
            "page": int(request.GET.get("page") or 1),
            "size": int(request.GET.get("size") or 10),
        }
    )


@require_http_methods(["GET"])
def file_breadcrumb(request):
    """返回当前目录的面包屑路径。"""
    return _ok(get_breadcrumb(request.GET.get("parent_id") or 0))


@csrf_exempt
@require_http_methods(["POST"])
def file_upload(request):
    """上传文件到指定目录。"""
    upload_file = request.FILES.get("file")
    parent_id = request.POST.get("parent_id") or 0
    user_id, user_name = _get_operator(request)
    try:
        item = save_upload(
            upload_file=upload_file,
            parent_id=parent_id,
            user_id=user_id,
            user_name=user_name,
        )
    except FileManagerError as exc:
        return _error(str(exc))

    return _ok(serialize_item(item), msg="上传成功")


@csrf_exempt
@require_http_methods(["POST"])
def file_create_folder(request):
    """新建文件夹。"""
    try:
        body = _parse_body(request)
        user_id, user_name = _get_operator(request)
        item = create_folder(
            name=body.get("name") or "",
            parent_id=body.get("parent_id") or 0,
            user_id=user_id,
            user_name=user_name,
        )
    except FileManagerError as exc:
        return _error(str(exc))

    return _ok(serialize_item(item), msg="新建成功")


@csrf_exempt
@require_http_methods(["POST"])
def file_delete(request):
    """移入回收站（含子目录）。"""
    try:
        count = move_to_recycle(_parse_ids(_parse_body(request)))
    except FileManagerError as exc:
        return _error(str(exc))
    return _ok({"count": count}, msg="已移入回收站")


@csrf_exempt
@require_http_methods(["POST"])
def file_restore(request):
    """从回收站还原。"""
    try:
        count = restore_from_recycle(_parse_ids(_parse_body(request)))
    except FileManagerError as exc:
        return _error(str(exc))
    return _ok({"count": count}, msg="还原成功")


@csrf_exempt
@require_http_methods(["POST"])
def file_purge(request):
    """彻底删除（物理文件 + 数据库记录）。"""
    try:
        count = purge(_parse_ids(_parse_body(request)))
    except FileManagerError as exc:
        return _error(str(exc))
    return _ok({"count": count}, msg="彻底删除成功")


@require_http_methods(["GET"])
def file_download(request):
    """下载文件：本地存储直接返回文件流，MinIO 模式重定向到对象地址。"""
    try:
        item = get_download_target(request.GET.get("id") or 0)
    except FileManagerError as exc:
        return _error(str(exc))

    if (getattr(settings, "OSS_TYPE", "minio") or "").lower() == "local":
        path = local_file_path(item.storage_path)
        if not os.path.exists(path):
            return _error("文件已不存在", code="A0700", status=404)
        return FileResponse(open(path, "rb"), as_attachment=True, filename=item.name)

    return HttpResponseRedirect(item.file_url)
