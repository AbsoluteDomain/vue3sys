"""系统管理-通知公告视图。

"""

from __future__ import annotations

from typing import Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.exceptions.business import BusinessException
from core.openapi import page_resp, resp
from core.viewsets import BaseModelViewSet
from core.permissions.decorators import permission_required
from core.permissions.perms import HasPerm
from apps.system.notices.models import Notice, UserNotice
from apps.system.roles.models import Role
from apps.system.users.models import User
from core.permissions.data_scope import data_permission_required
from core.response import error, success

from .serializers import (
    NoticeCreateSerializer,
    NoticeDetailSerializer,
    NoticeFormSerializer,
    NoticeMyPageSerializer,
    NoticePageSerializer,
    NoticeUpdateSerializer,
)
from .filters import NoticeFilter


def _check_notice_data_permission(*, notice: Notice, request, operation: str = "select") -> bool:
    """通知公告对象级数据权限校验。

    约定：仅允许访问自己数据范围内创建的通知。
    """

    user = getattr(request, "user", None)
    data_permission = data_permission_required(user, operation)

    if data_permission == "all":
        return True

    if not isinstance(data_permission, list):
        return False

    return notice.create_by in data_permission


def build_notice_page_query(*, title: str, publish_status, publish_time: str, data_permission):
    notice_query = Q(is_deleted=0)

    if isinstance(data_permission, list) and data_permission:
        notice_query &= Q(create_by__in=data_permission)

    if title:
        notice_query &= Q(title__icontains=title)

    if publish_status != "":
        try:
            publish_status_int = int(publish_status)
            notice_query &= Q(publish_status=publish_status_int)
        except ValueError:
            pass

    if publish_time:
        time_parts = publish_time.split(",")
        if len(time_parts) == 2:
            start_time, end_time = time_parts
            if start_time:
                try:
                    start_date = timezone.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                    notice_query &= Q(publish_time__gte=start_date)
                except ValueError:
                    pass
            if end_time:
                try:
                    end_date = timezone.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                    notice_query &= Q(publish_time__lte=end_date)
                except ValueError:
                    pass

    return notice_query


def _create_user_notices(*, notice: Notice, publisher_id: Optional[int], current_user):
    import logging
    logger = logging.getLogger(__name__)

    now = timezone.now()
    UserNotice.objects.filter(notice=notice).delete()

    if notice.target_type == 1:
        data_permission = data_permission_required(current_user, "select")
        logger.info(f"[通知发布] target_type=全体, data_permission={data_permission}")

        users = User.objects.filter(is_deleted=0, status=1)
        logger.info(f"[通知发布] 初始用户查询 count={users.count()}")

        if isinstance(data_permission, list) and data_permission:
            users = users.filter(id__in=data_permission)
            logger.info(f"[通知发布] 数据权限过滤后 count={users.count()}")

        user_notices = [
            UserNotice(notice=notice, user=user, is_read=0, create_time=now, is_deleted=0)
            for user in users
        ]
        logger.info(f"[通知发布] 准备插入 user_notices count={len(user_notices)}")

        if user_notices:
            UserNotice.objects.bulk_create(user_notices)
            logger.info(f"[通知发布] bulk_create 完成")
        else:
            logger.warning(f"[通知发布] user_notices 为空，未插入任何数据")
        return

    if notice.target_type == 2 and notice.target_user_ids:
        target_user_ids = [uid for uid in str(notice.target_user_ids).split(",") if uid]
        users = User.objects.filter(id__in=target_user_ids, is_deleted=0, status=1)
        user_notices = [
            UserNotice(notice=notice, user=user, is_read=0, create_time=now, is_deleted=0)
            for user in users
        ]
        if user_notices:
            UserNotice.objects.bulk_create(user_notices)


def _broadcast_notice_published(*, notice: Notice):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        "notice_broadcast",
        {
            "type": "notice_broadcast",
            "data": {
                "event": "NOTICE_PUBLISHED",
                "payload": {
                    "id": str(notice.id),
                    "title": notice.title,
                    "type": notice.type,
                    "level": notice.level,
                    "publishStatus": notice.publish_status,
                    "publishTime": notice.publish_time.isoformat() if notice.publish_time else None,
                },
            },
        },
    )


def publish_notice(*, notice_id: int, current_user, publisher_user_id: Optional[int]):
    notice = Notice.objects.filter(id=notice_id, is_deleted=0).first()
    if notice is None:
        raise BusinessException("通知公告不存在", code="C0113", status=404)

    has_permission = data_permission_required(current_user, "update", notice.create_by)
    if has_permission is False:
        raise BusinessException("无权限发布此通知公告", code="A0301", status=403)

    if notice.publish_status == 1:
        raise BusinessException("该通知公告已发布", code="A0400", status=400)

    now = timezone.now()
    notice.publish_status = 1
    notice.publish_time = now
    notice.publisher_id = publisher_user_id
    notice.save(update_fields=["publish_status", "publish_time", "publisher_id"])

    _create_user_notices(notice=notice, publisher_id=publisher_user_id, current_user=current_user)
    _broadcast_notice_published(notice=notice)

    return {"data": {}, "msg": "通知公告发布成功"}


def revoke_notice(*, notice_id: int, current_user, updater_user_id: Optional[int]):
    notice = Notice.objects.filter(id=notice_id, is_deleted=0).first()
    if notice is None:
        raise BusinessException("通知公告不存在", code="C0113", status=404)

    has_permission = data_permission_required(current_user, "update", notice.create_by)
    if has_permission is False:
        raise BusinessException("无权限撤销此通知公告", code="A0301", status=403)

    if notice.publish_status != 1:
        raise BusinessException("该通知公告未发布", code="A0400", status=400)

    now = timezone.now()
    notice.publish_status = -1
    notice.revoke_time = now
    notice.update_by = updater_user_id
    notice.update_time = now
    notice.save(update_fields=["publish_status", "revoke_time", "update_by", "update_time"])

    UserNotice.objects.filter(notice=notice).delete()
    return {"data": {}, "msg": "通知公告撤销成功"}


def delete_notices(*, ids: str, current_user, updater_user_id: Optional[int]):
    try:
        id_list = [int(i.strip()) for i in str(ids).split(",") if i.strip()]
    except ValueError:
        raise BusinessException("通知公告ID格式不正确", code="A0400", status=400)

    if not id_list:
        raise BusinessException("未指定要删除的通知公告ID", code="A0400", status=400)

    notices = list(Notice.objects.filter(id__in=id_list, is_deleted=0))
    found_ids = [n.id for n in notices]
    not_found_ids = sorted(set(id_list) - set(found_ids))
    if not_found_ids:
        raise BusinessException(
            f"通知公告ID {','.join(map(str, not_found_ids))} 不存在或已删除",
            code="A0400",
            status=400,
        )

    unauthorized_ids = []
    for notice in notices:
        has_permission = data_permission_required(current_user, "delete", notice.create_by)
        if has_permission is False:
            unauthorized_ids.append(str(notice.id))

    if unauthorized_ids:
        raise BusinessException(
            f"您没有权限删除以下通知公告: {','.join(unauthorized_ids)}",
            code="A0301",
            status=403,
        )

    now = timezone.now()
    Notice.objects.filter(id__in=found_ids, is_deleted=0).update(
        is_deleted=1,
        update_by=updater_user_id,
        update_time=now,
    )
    UserNotice.objects.filter(notice_id__in=found_ids).delete()
    return {"deleted_count": len(found_ids)}


@extend_schema(tags=["08.通知公告"])
class NoticeViewSet(BaseModelViewSet):
    """系统管理-通知公告ViewSet。"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    queryset = Notice.objects.filter(is_deleted=0).order_by("-create_time")
    filterset_class = NoticeFilter

    def get_queryset(self):
        qs = Notice.objects.filter(is_deleted=0)

        if getattr(self, "action", None) == "my":
            return qs

        data_permission = data_permission_required(getattr(self.request, "user", None), "select")

        if isinstance(data_permission, list) and data_permission:
            qs = qs.filter(create_by__in=data_permission)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return NoticePageSerializer
        if self.action == "create":
            return NoticeCreateSerializer
        if self.action in ["update", "partial_update"]:
            return NoticeUpdateSerializer
        if self.action == "form":
            return NoticeFormSerializer
        if self.action == "my":
            return NoticeMyPageSerializer
        return NoticeDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        user_id = getattr(getattr(self, "request", None), "user", None)
        user_id = getattr(user_id, "id", None)
        if user_id:
            ctx["user_id"] = user_id
        return ctx

    @permission_required(["sys:notice:list"])
    @extend_schema(
        summary="通知公告分页列表",
        parameters=[
            OpenApiParameter(
                name="title",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="标题关键字",
            ),
            OpenApiParameter(
                name="publishStatus",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="发布状态：1 已发布 / 0 未发布",
            ),
            OpenApiParameter(
                name="publishTime",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="发布时间范围：start,end（格式：YYYY-MM-DD HH:mm:ss）",
            ),
            OpenApiParameter(
                name="pageNum",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="页码（默认 1）",
            ),
            OpenApiParameter(
                name="pageSize",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="每页记录数（默认 10）",
            ),
        ],
        responses=page_resp("NoticePageResult", NoticePageSerializer(many=True)),
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @permission_required(["sys:notice:create"])
    @extend_schema(
        summary="新增通知公告",
        request=NoticeCreateSerializer,
        responses=resp("NoticeCreateResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @permission_required(["sys:notice:update"])
    @extend_schema(
        summary="更新通知公告",
        request=NoticeUpdateSerializer,
        responses=resp("NoticeUpdateResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @permission_required(["sys:notice:update"])
    @extend_schema(
        summary="部分更新通知公告",
        request=NoticeUpdateSerializer,
        responses=resp("NoticePartialUpdateResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @permission_required(["sys:notice:delete"])
    @extend_schema(
        summary="删除通知公告",
        parameters=[
            OpenApiParameter(
                name="ids",
                location=OpenApiParameter.PATH,
                required=True,
                type=str,
                description="通知公告ID，多个以英文逗号(,)分割",
            )
        ],
        responses=resp("NoticeDeleteResult", serializers.DictField(required=False)),
    )
    def destroy(self, request, *args, **kwargs):
        ids = kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        updater_user_id = request.user.id if hasattr(request, "user") and request.user else None

        result = delete_notices(ids=str(ids), current_user=request.user, updater_user_id=updater_user_id)
        return success({}, msg=f"成功删除 {result['deleted_count']} 条通知公告")

    @permission_required(["sys:notice:publish"])
    @extend_schema(
        summary="发布通知公告",
        responses=resp("NoticePublishResult", serializers.JSONField(required=False, allow_null=True)),
    )
    @action(methods=["put"], detail=True, url_path="publish")
    def publish(self, request, pk=None):
        publisher_user_id = request.user.id if hasattr(request, "user") and request.user else None

        result = publish_notice(notice_id=int(pk), current_user=request.user, publisher_user_id=publisher_user_id)
        return success(result.get("data", {}), msg=result.get("msg", "通知公告发布成功"))

    @permission_required(["sys:notice:revoke"])
    @extend_schema(
        summary="撤销通知公告",
        responses=resp("NoticeRevokeResult", serializers.JSONField(required=False, allow_null=True)),
    )
    @action(methods=["put"], detail=True, url_path="revoke")
    def revoke(self, request, pk=None):
        updater_user_id = request.user.id if hasattr(request, "user") and request.user else None

        result = revoke_notice(notice_id=int(pk), current_user=request.user, updater_user_id=updater_user_id)
        return success(result.get("data", {}), msg=result.get("msg", "通知公告撤销成功"))

    @permission_required(["sys:notice:list"])
    @extend_schema(
        summary="通知公告表单数据",
        responses=resp("NoticeFormResult", NoticeFormSerializer()),
    )
    @action(methods=["get"], detail=True, url_path="form")
    def form(self, request, pk=None):
        notice = get_object_or_404(Notice, id=pk, is_deleted=0)

        # Object-level access check (data scope)
        if not _check_notice_data_permission(notice=notice, request=request, operation="select"):
            raise PermissionDenied("无权限访问此通知公告")

        serializer = NoticeFormSerializer(notice)
        return success(serializer.data)

    @extend_schema(
        summary="阅读获取通知公告详情",
        responses=resp("NoticeDetailResult", NoticeDetailSerializer()),
    )
    @action(methods=["get"], detail=True, url_path="detail")
    def read_detail(self, request, pk=None):
        notice = get_object_or_404(Notice, id=pk, is_deleted=0)
        user_id = getattr(getattr(request, "user", None), "id", None)
        try:
            user_notice = UserNotice.objects.get(notice=notice, user_id=user_id, is_deleted=0)
            if user_notice and user_notice.is_read == 0:
                now = timezone.now()
                user_notice.is_read = 1
                user_notice.read_time = now
                user_notice.update_time = now
                user_notice.save()  # 修复：添加 save() 调用
            serializer = NoticeDetailSerializer(notice)
            return success(serializer.data)
        except UserNotice.DoesNotExist:
            raise PermissionDenied("无权限访问此通知公告")

    @extend_schema(
        summary="获取我的通知公告分页列表",
        parameters=[
            OpenApiParameter(
                name="title",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="标题关键字",
            ),
            OpenApiParameter(
                name="publishTime",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="发布时间范围：start,end（格式：YYYY-MM-DD HH:mm:ss）",
            ),
            OpenApiParameter(
                name="isRead",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="是否已读：1 已读 / 0 未读",
            ),
            OpenApiParameter(
                name="pageNum",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="页码（默认 1）",
            ),
            OpenApiParameter(
                name="pageSize",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="每页记录数（默认 10）",
            ),
        ],
        responses=page_resp("NoticeMyPageResult", NoticeMyPageSerializer(many=True)),
    )
    @action(methods=["get"], detail=False, url_path="my")
    def my(self, request):
        title = request.query_params.get("title", "")
        publish_time = request.query_params.get("publishTime", "")
        is_read = request.query_params.get("isRead", "")

        query = Q(
            user_id=request.user.id,
            is_deleted=0,
            notice__is_deleted=0,
            notice__publish_status=1,
        )
        if title:
            query &= Q(notice__title__icontains=title)
        if is_read != "":
            try:
                query &= Q(is_read=int(is_read))
            except ValueError:
                pass

        if publish_time:
            time_parts = publish_time.split(",")
            if len(time_parts) == 2:
                start_time, end_time = time_parts
                if start_time:
                    try:
                        start_date = timezone.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                        query &= Q(notice__publish_time__gte=start_date)
                    except ValueError:
                        pass
                if end_time:
                    try:
                        end_date = timezone.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                        query &= Q(notice__publish_time__lte=end_date)
                    except ValueError:
                        pass

        user_notices = (
            UserNotice.objects.filter(query)
            .select_related("notice")
            .order_by("-notice__publish_time")
        )

        page = self.paginate_queryset(user_notices)
        if page is not None:
            serializer = NoticeMyPageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = NoticeMyPageSerializer(user_notices, many=True)
        return success(serializer.data)

    @extend_schema(
        summary="全部已读",
        responses=resp(
            "NoticeReadAllResult",
            inline_serializer(
                name="NoticeReadAllData",
                fields={"count": serializers.IntegerField()},
            ),
        ),
    )
    @action(methods=["put"], detail=False, url_path="read-all")
    def read_all(self, request):
        now = timezone.now()
        unread_count = UserNotice.objects.filter(
            user_id=request.user.id,
            is_read=0,
            is_deleted=0,
            notice__is_deleted=0,
            notice__publish_status=1,
        ).update(is_read=1, read_time=now, update_time=now)

        return success({"count": unread_count}, msg=f"已将{unread_count}条通知公告标记为已读")
