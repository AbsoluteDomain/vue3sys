"""系统管理-统计视图。

"""

from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import action

#from rest_framework.permissions import AllowAnonymous, IsAuthenticated
try:
    # DRF 3.15+
    from rest_framework.permissions import AllowAnonymous, IsAuthenticated
except ImportError:
    # DRF < 3.15 (使用 AllowAny 作为 fallback)
    from rest_framework.permissions import AllowAny as AllowAnonymous, IsAuthenticated
    import warnings
    warnings.warn("Using AllowAny instead of AllowAnonymous due to old DRF version.")
    
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Count
from django.utils import timezone
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from apps.system.logs.models import Log
from core.response import error, success
from core.openapi import resp
from core.viewsets import BaseModelViewSet

@extend_schema(tags=["12.统计分析"])
class VisitViewSet(BaseModelViewSet):
    """系统管理-统计ViewSet。"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Log.objects.none()

    @extend_schema(
        summary="访问趋势统计",
        parameters=[
            OpenApiParameter(
                name="startDate",
                location=OpenApiParameter.QUERY,
                required=True,
                type=str,
                description="开始日期（YYYY-MM-DD）",
            ),
            OpenApiParameter(
                name="endDate",
                location=OpenApiParameter.QUERY,
                required=True,
                type=str,
                description="结束日期（YYYY-MM-DD）",
            ),
        ],
        responses=resp(
            "VisitTrendResult",
            inline_serializer(
                name="VisitTrendData",
                fields={
                    "dates": serializers.ListField(child=serializers.CharField()),
                    "pvList": serializers.ListField(child=serializers.IntegerField()),
                    "ipList": serializers.ListField(child=serializers.IntegerField()),
                },
            ),
        ),
    )
    @action(methods=["get"], detail=False, url_path="visits/trend", permission_classes=[AllowAnonymous])
    def trend(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('startDate', '')
        end_date_str = request.query_params.get('endDate', '')

        if not start_date_str or not end_date_str:
            return error("开始日期和结束日期不能为空")

        try:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
            end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d'))
            end_date = end_date + timedelta(days=1)
        except ValueError:
            return error("日期格式不正确，请使用 YYYY-MM-DD 格式")

        if start_date > end_date - timedelta(days=1):
            return error("开始日期不能晚于结束日期")

        # 生成连续的日期列表
        current_date = start_date
        date_list = []
        while current_date < end_date:
            date_list.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

        # 查询PV数据
        pv_data = Log.objects.filter(
            create_time__gte=start_date,
            create_time__lt=end_date
        ).annotate(
            date=TruncDate('create_time')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        # 查询IP数据
        ip_data = Log.objects.filter(
            create_time__gte=start_date,
            create_time__lt=end_date
        ).annotate(
            date=TruncDate('create_time')
        ).values('date').annotate(
            count=Count('ip', distinct=True)
        ).order_by('date')

        # pv_dict = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in pv_data}
        pv_dict = {
            item['date'].strftime('%Y-%m-%d'): item['count'] 
            for item in pv_data 
            if item['date'] is not None  # 增加这个判断，跳过日期为空的记录
        }

        # ip_dict = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in ip_data}
        ip_dict = {
            item['date'].strftime('%Y-%m-%d'): item['count'] 
            for item in ip_data 
            if item['date'] is not None  # 增加这个判断，跳过日期为空的记录
        }
        pv_list = [pv_dict.get(date, 0) for date in date_list]
        ip_list = [ip_dict.get(date, 0) for date in date_list]

        return success(
            {
                "dates": date_list,
                "pvList": pv_list,
                "ipList": ip_list,
            }
        )


    @extend_schema(
        summary="访问概览统计",
        responses=resp(
            "VisitOverviewResult",
            inline_serializer(
                name="VisitOverviewData",
                fields={
                    "todayUvCount": serializers.IntegerField(),
                    "totalUvCount": serializers.IntegerField(),
                    "uvGrowthRate": serializers.FloatField(),
                    "todayPvCount": serializers.IntegerField(),
                    "totalPvCount": serializers.IntegerField(),
                    "pvGrowthRate": serializers.FloatField(),
                },
            ),
        ),
    )
    @action(methods=["get"], detail=False, url_path="visits/overview", permission_classes=[AllowAnonymous])
    def overview(self, request, *args, **kwargs):
        """获取访问概览统计数据"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start

        # 今日数据
        today_pv_count = Log.objects.filter(
            create_time__gte=today_start,
            create_time__lt=today_end
        ).count()

        today_uv_count = Log.objects.filter(
            create_time__gte=today_start,
            create_time__lt=today_end
        ).values('ip').distinct().count()

        # 昨日数据
        yesterday_pv_count = Log.objects.filter(
            create_time__gte=yesterday_start,
            create_time__lt=yesterday_end
        ).count()

        yesterday_uv_count = Log.objects.filter(
            create_time__gte=yesterday_start,
            create_time__lt=yesterday_end
        ).values('ip').distinct().count()

        # 总数据
        total_pv_count = Log.objects.count()
        total_uv_count = Log.objects.values('ip').distinct().count()

        # 计算增长率
        pv_growth_rate = 0
        if yesterday_pv_count > 0:
            pv_growth_rate = round((today_pv_count - yesterday_pv_count) / yesterday_pv_count * 100, 2)

        uv_growth_rate = 0
        if yesterday_uv_count > 0:
            uv_growth_rate = round((today_uv_count - yesterday_uv_count) / yesterday_uv_count * 100, 2)

        return success(
            {
                "todayUvCount": today_uv_count,
                "totalUvCount": total_uv_count,
                "uvGrowthRate": uv_growth_rate,
                "todayPvCount": today_pv_count,
                "totalPvCount": total_pv_count,
                "pvGrowthRate": pv_growth_rate,
            }
        )
