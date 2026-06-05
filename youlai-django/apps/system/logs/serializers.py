"""系统管理-日志序列化器。

Author: Ray.Hao
Version: 0.0.1
"""

from rest_framework import serializers
from core.serializers import BigIntAsStringField, StandardModelSerializer

from apps.system.logs.models import Log
from apps.system.users.models import User

class LogPageSerializer(StandardModelSerializer):
    """日志分页列表序列化器"""
    operator = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    requestUri = serializers.CharField(source='request_uri')
    executionTime = serializers.IntegerField(source='execution_time')
    createBy = BigIntAsStringField(source='create_by')
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M:%S')
    
    class Meta:
        model = Log
        fields = ['id', 'module', 'content', 'requestUri', 'method', 'ip', 
                  'region', 'browser', 'os', 'executionTime', 'createBy', 
                  'createTime', 'operator']
    
    def get_operator(self, obj):
        """获取操作人名称"""
        if not obj.create_by:
            return None
            
        try:
            user = User.objects.get(id=obj.create_by)
            return user.nickname or user.username
        except User.DoesNotExist:
            return None
    
    def get_region(self, obj):
        """获取地区信息，合并省份和城市"""
        if obj.province and obj.city:
            return f"{obj.province} {obj.city}"
        elif obj.province:
            return obj.province
        elif obj.city:
            return obj.city
        return None


