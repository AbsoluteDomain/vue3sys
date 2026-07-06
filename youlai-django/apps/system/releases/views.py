import json

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.system.operation_logs.request_user import get_request_operator
from apps.system.users.models import User
from core.datetime import format_local_datetime

from .models import Release, ReleaseItem, UserReleaseRead

RELEASE_TYPE_LABELS = {
    Release.RELEASE_TYPE_NORMAL: "常规",
    Release.RELEASE_TYPE_IMPORTANT: "重要",
    Release.RELEASE_TYPE_URGENT: "紧急",
}

PUBLISH_STATUS_LABELS = {
    Release.PUBLISH_DRAFT: "未发布",
    Release.PUBLISH_PUBLISHED: "已发布",
    Release.PUBLISH_REVOKED: "已撤回",
}


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _require_operator(request):
    operator = get_request_operator(request)
    if not operator:
        return None, JsonResponse({"code": "A0301", "msg": "未登录或登录已过期", "data": None}, status=401)
    return operator, None


def _parse_page_params(request):
    try:
        page_num = int(request.GET.get("pageNum", 1))
    except (TypeError, ValueError):
        page_num = 1
    try:
        page_size = int(request.GET.get("pageSize", 10))
    except (TypeError, ValueError):
        page_size = 10
    page_num = max(page_num, 1)
    page_size = max(min(page_size, 100), 1)
    return page_num, page_size


def _serialize_release_brief(release, *, is_read=None):
    data = {
        "id": release.id,
        "version": release.version,
        "title": release.title,
        "summary": release.summary or "",
        "releaseType": release.release_type,
        "releaseTypeName": RELEASE_TYPE_LABELS.get(release.release_type, ""),
        "publishStatus": release.publish_status,
        "publishStatusName": PUBLISH_STATUS_LABELS.get(release.publish_status, ""),
        "publishTime": format_local_datetime(release.publish_time) or "",
        "forceNotify": release.force_notify,
        "createTime": format_local_datetime(release.create_time) or "",
    }
    if is_read is not None:
        data["isRead"] = is_read
    return data


def _serialize_release_detail(release):
    items = []
    for item in release.items.all().order_by("sort", "id"):
        items.append({
            "id": item.id,
            "itemType": item.item_type,
            "itemTypeName": ReleaseItem.ITEM_TYPE_LABELS.get(item.item_type, ""),
            "content": item.content,
            "sort": item.sort,
        })
    data = _serialize_release_brief(release)
    data.update({
        "revokeTime": format_local_datetime(release.revoke_time) or "",
        "items": items,
    })
    return data


def _save_release_items(release, items_data, now):
    ReleaseItem.objects.filter(release=release).delete()
    if not items_data:
        return
    to_create = []
    for idx, row in enumerate(items_data):
        content = str(row.get("content") or "").strip()
        if not content:
            continue
        try:
            item_type = int(row.get("itemType") or row.get("item_type") or ReleaseItem.ITEM_TYPE_FEATURE)
        except (TypeError, ValueError):
            item_type = ReleaseItem.ITEM_TYPE_FEATURE
        try:
            sort = int(row.get("sort", idx))
        except (TypeError, ValueError):
            sort = idx
        to_create.append(
            ReleaseItem(
                release=release,
                item_type=item_type,
                content=content,
                sort=sort,
                create_time=now,
            )
        )
    if to_create:
        ReleaseItem.objects.bulk_create(to_create)


def _init_user_read_records(release, now):
    """发布时为所有活跃用户创建未读记录。"""
    UserReleaseRead.objects.filter(release=release).delete()
    users = User.objects.filter(is_deleted=0, status=1).only("id")
    records = [
        UserReleaseRead(user_id=user.id, release=release, is_read=0, create_time=now)
        for user in users
    ]
    if records:
        UserReleaseRead.objects.bulk_create(records, batch_size=500)


def _mark_release_read(user_id, release_id, now=None):
    now = now or timezone.now()
    record, created = UserReleaseRead.objects.get_or_create(
        user_id=user_id,
        release_id=release_id,
        defaults={"is_read": 1, "read_time": now, "create_time": now},
    )
    if not created and record.is_read != 1:
        record.is_read = 1
        record.read_time = now
        record.save(update_fields=["is_read", "read_time"])


# ---------------------------------------------------------------------------
# 管理端
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(["GET"])
def release_admin_list(request):
    operator, err = _require_operator(request)
    if err:
        return err

    page_num, page_size = _parse_page_params(request)
    version = request.GET.get("version", "").strip()
    title = request.GET.get("title", "").strip()
    publish_status = request.GET.get("publishStatus", "").strip()

    qs = Release.objects.filter(is_deleted=0).order_by("-create_time", "-id")
    if version:
        qs = qs.filter(version__icontains=version)
    if title:
        qs = qs.filter(title__icontains=title)
    if publish_status != "":
        try:
            qs = qs.filter(publish_status=int(publish_status))
        except ValueError:
            pass

    total = qs.count()
    start = (page_num - 1) * page_size
    rows = qs[start : start + page_size]

    return JsonResponse({
        "code": "00000",
        "msg": "success",
        "data": {
            "list": [_serialize_release_brief(r) for r in rows],
            "total": total,
        },
    })


@csrf_exempt
@require_http_methods(["GET"])
def release_admin_detail(request, release_id):
    operator, err = _require_operator(request)
    if err:
        return err

    release = Release.objects.filter(id=release_id, is_deleted=0).first()
    if not release:
        return JsonResponse({"code": "C0113", "msg": "版本公告不存在", "data": None}, status=404)

    return JsonResponse({"code": "00000", "msg": "success", "data": _serialize_release_detail(release)})


@csrf_exempt
@require_http_methods(["POST"])
def release_admin_create(request):
    operator, err = _require_operator(request)
    if err:
        return err
    user_id, _ = operator

    body = _json_body(request)
    version = str(body.get("version") or "").strip()
    title = str(body.get("title") or "").strip()
    if not version or not title:
        return JsonResponse({"code": "A0400", "msg": "版本号和标题不能为空", "data": None}, status=400)

    now = timezone.now()
    try:
        release_type = int(body.get("releaseType", Release.RELEASE_TYPE_NORMAL))
    except (TypeError, ValueError):
        release_type = Release.RELEASE_TYPE_NORMAL
    force_notify = 1 if body.get("forceNotify", True) not in (False, 0, "0") else 0

    with transaction.atomic():
        release = Release.objects.create(
            version=version,
            title=title,
            summary=str(body.get("summary") or "").strip() or None,
            release_type=release_type,
            publish_status=Release.PUBLISH_DRAFT,
            force_notify=force_notify,
            create_by=user_id,
            create_time=now,
            is_deleted=0,
        )
        _save_release_items(release, body.get("items") or [], now)

    return JsonResponse({"code": "00000", "msg": "创建成功", "data": {"id": release.id}})


@csrf_exempt
@require_http_methods(["PUT"])
def release_admin_update(request, release_id):
    operator, err = _require_operator(request)
    if err:
        return err
    user_id, _ = operator

    release = Release.objects.filter(id=release_id, is_deleted=0).first()
    if not release:
        return JsonResponse({"code": "C0113", "msg": "版本公告不存在", "data": None}, status=404)
    if release.publish_status == Release.PUBLISH_PUBLISHED:
        return JsonResponse({"code": "A0400", "msg": "已发布的公告不可编辑，请先撤回", "data": None}, status=400)

    body = _json_body(request)
    version = str(body.get("version") or release.version).strip()
    title = str(body.get("title") or release.title).strip()
    if not version or not title:
        return JsonResponse({"code": "A0400", "msg": "版本号和标题不能为空", "data": None}, status=400)

    now = timezone.now()
    try:
        release_type = int(body.get("releaseType", release.release_type))
    except (TypeError, ValueError):
        release_type = release.release_type
    if "forceNotify" in body:
        force_notify = 1 if body.get("forceNotify") not in (False, 0, "0") else 0
    else:
        force_notify = release.force_notify

    with transaction.atomic():
        release.version = version
        release.title = title
        release.summary = str(body.get("summary") or "").strip() or None
        release.release_type = release_type
        release.force_notify = force_notify
        release.update_by = user_id
        release.update_time = now
        release.save()
        if "items" in body:
            _save_release_items(release, body.get("items") or [], now)

    return JsonResponse({"code": "00000", "msg": "更新成功", "data": {}})


@csrf_exempt
@require_http_methods(["DELETE"])
def release_admin_delete(request, release_id):
    operator, err = _require_operator(request)
    if err:
        return err
    user_id, _ = operator

    ids = [i for i in str(release_id).split(",") if i.strip()]
    now = timezone.now()
    qs = Release.objects.filter(id__in=ids, is_deleted=0)
    published = qs.filter(publish_status=Release.PUBLISH_PUBLISHED).exists()
    if published:
        return JsonResponse({"code": "A0400", "msg": "已发布的公告不可删除，请先撤回", "data": None}, status=400)

    qs.update(is_deleted=1, update_by=user_id, update_time=now)
    return JsonResponse({"code": "00000", "msg": "删除成功", "data": {}})


@csrf_exempt
@require_http_methods(["PUT"])
def release_admin_publish(request, release_id):
    operator, err = _require_operator(request)
    if err:
        return err
    user_id, _ = operator

    release = Release.objects.filter(id=release_id, is_deleted=0).first()
    if not release:
        return JsonResponse({"code": "C0113", "msg": "版本公告不存在", "data": None}, status=404)
    if release.publish_status == Release.PUBLISH_PUBLISHED:
        return JsonResponse({"code": "A0400", "msg": "该公告已发布", "data": None}, status=400)

    now = timezone.now()
    with transaction.atomic():
        release.publish_status = Release.PUBLISH_PUBLISHED
        release.publish_time = now
        release.revoke_time = None
        release.update_by = user_id
        release.update_time = now
        release.save(update_fields=["publish_status", "publish_time", "revoke_time", "update_by", "update_time"])
        if release.force_notify:
            _init_user_read_records(release, now)

    return JsonResponse({"code": "00000", "msg": "发布成功", "data": {}})


@csrf_exempt
@require_http_methods(["PUT"])
def release_admin_revoke(request, release_id):
    operator, err = _require_operator(request)
    if err:
        return err
    user_id, _ = operator

    release = Release.objects.filter(id=release_id, is_deleted=0).first()
    if not release:
        return JsonResponse({"code": "C0113", "msg": "版本公告不存在", "data": None}, status=404)
    if release.publish_status != Release.PUBLISH_PUBLISHED:
        return JsonResponse({"code": "A0400", "msg": "该公告未发布或已撤回", "data": None}, status=400)

    now = timezone.now()
    release.publish_status = Release.PUBLISH_REVOKED
    release.revoke_time = now
    release.update_by = user_id
    release.update_time = now
    release.save(update_fields=["publish_status", "revoke_time", "update_by", "update_time"])

    return JsonResponse({"code": "00000", "msg": "撤回成功", "data": {}})


# ---------------------------------------------------------------------------
# 用户端
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(["GET"])
def release_published_list(request):
    """导航栏下拉：已发布版本列表。"""
    operator, err = _require_operator(request)
    if err:
        return err
    user_id, _ = operator

    try:
        limit = int(request.GET.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(min(limit, 50), 1)

    releases = (
        Release.objects.filter(is_deleted=0, publish_status=Release.PUBLISH_PUBLISHED)
        .order_by("-publish_time", "-id")[:limit]
    )
    read_map = {
        r.release_id: r.is_read
        for r in UserReleaseRead.objects.filter(user_id=user_id, release_id__in=[r.id for r in releases])
    }

    data = []
    for release in releases:
        item = _serialize_release_brief(release, is_read=read_map.get(release.id, 0))
        data.append(item)

    return JsonResponse({"code": "00000", "msg": "success", "data": data})


@csrf_exempt
@require_http_methods(["GET"])
def release_user_detail(request, release_id):
    """用户查看版本详情（历史查看，不强制标记已读）。"""
    operator, err = _require_operator(request)
    if err:
        return err

    release = Release.objects.filter(
        id=release_id,
        is_deleted=0,
        publish_status=Release.PUBLISH_PUBLISHED,
    ).first()
    if not release:
        return JsonResponse({"code": "C0113", "msg": "版本公告不存在或未发布", "data": None}, status=404)

    return JsonResponse({"code": "00000", "msg": "success", "data": _serialize_release_detail(release)})


@csrf_exempt
@require_http_methods(["GET"])
def release_latest_unread(request):
    """登录后弹窗：最新未读且需弹窗提醒的版本。"""
    operator, err = _require_operator(request)
    if err:
        return err
    user_id, _ = operator

    unread_records = (
        UserReleaseRead.objects.filter(
            user_id=user_id,
            is_read=0,
            release__is_deleted=0,
            release__publish_status=Release.PUBLISH_PUBLISHED,
            release__force_notify=1,
        )
        .select_related("release")
        .order_by("-release__publish_time", "-release_id")
    )

    record = unread_records.first()
    if not record:
        return JsonResponse({"code": "00000", "msg": "success", "data": None})

    return JsonResponse({
        "code": "00000",
        "msg": "success",
        "data": _serialize_release_detail(record.release),
    })


@csrf_exempt
@require_http_methods(["PUT"])
def release_mark_read(request, release_id):
    """标记版本公告为已读（关闭登录弹窗时调用）。"""
    operator, err = _require_operator(request)
    if err:
        return err
    user_id, _ = operator

    release = Release.objects.filter(
        id=release_id,
        is_deleted=0,
        publish_status=Release.PUBLISH_PUBLISHED,
    ).first()
    if not release:
        return JsonResponse({"code": "C0113", "msg": "版本公告不存在", "data": None}, status=404)

    _mark_release_read(user_id, release_id)
    return JsonResponse({"code": "00000", "msg": "success", "data": {}})
