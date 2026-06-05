"""系统管理-通知公告序列化器。
 
 """
 
from rest_framework import serializers
from core.serializers import BigIntAsStringField, StandardModelSerializer

from apps.system.notices.models import Notice, UserNotice
from apps.system.users.models import User
from django.utils import timezone
import jwt
from django.conf import settings


class NoticePageSerializer(StandardModelSerializer):
    """通知公告分页列表序列化器"""
    publishStatus = serializers.IntegerField(source='publish_status')
    publishTime = serializers.DateTimeField(source='publish_time', format='%Y-%m-%d %H:%M', required=False, allow_null=True)
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M')
    revokeTime = serializers.DateTimeField(source='revoke_time', format='%Y-%m-%d %H:%M', required=False, allow_null=True)
    targetType = serializers.IntegerField(source='target_type')
    publisherName = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = ['id', 'title', 'publishStatus', 'type', 'publisherName', 'level', 
                 'publishTime', 'targetType', 'createTime', 'revokeTime']
    
    def get_publisherName(self, obj):
        """获取发布人名称"""
        publisher_id = getattr(obj, 'publisher_id', None)
        if publisher_id:
            try:
                publisher = User.objects.get(id=publisher_id)
                return publisher.nickname or publisher.username
            except User.DoesNotExist:
                return None
        return None


class NoticeDetailSerializer(StandardModelSerializer):
    """通知公告详情序列化器"""
    publishStatus = serializers.IntegerField(source='publish_status')
    publishTime = serializers.DateTimeField(source='publish_time', format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)
    publisherName = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = ['id', 'title', 'content', 'type', 'publisherName', 'level', 'publishStatus', 'publishTime']
    
    def get_publisherName(self, obj):
        """获取发布人名称"""
        publisher_id = getattr(obj, 'publisher_id', None)
        if publisher_id:
            try:
                publisher = User.objects.get(id=publisher_id)
                return publisher.nickname or publisher.username
            except User.DoesNotExist:
                return None
        return None


class NoticeFormSerializer(StandardModelSerializer):
    """通知公告表单序列化器"""
    targetType = serializers.IntegerField(source='target_type')
    targetUserIds = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = ['id', 'title', 'content', 'type', 'level', 'targetType', 'targetUserIds']
    
    def get_targetUserIds(self, obj):
        """获取目标用户ID列表"""
        if obj.target_type == 2 and obj.target_user_ids:
            return obj.target_user_ids.split(',')
        return []


class NoticeUpdateSerializer(StandardModelSerializer):
    """通知公告更新序列化器"""
    targetUserIds = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="目标用户ID列表"
    )
    targetType = serializers.IntegerField(source='target_type')
    
    class Meta:
        model = Notice
        fields = ['id', 'title', 'content', 'type', 'level', 'targetType', 'targetUserIds']
        extra_kwargs = {
            'id': {'read_only': True},
            'title': {'required': True, 'max_length': 50},
            'content': {'required': True},
            'type': {'required': True},
            'level': {'required': True},
        }
    
    def to_internal_value(self, data):
        """
        转换前端数据格式为后端模型格式
        """
        # 检查前端是否传入了 targetType 和 targetUserIds
        if 'targetType' in data and not 'target_type' in data:
            data = data.copy()  # 避免修改原始数据
            data['target_type'] = data['targetType']
        
        # 将 ListField 值转换为 Python List
        if 'targetUserIds' in data and isinstance(data['targetUserIds'], str):
            data = data.copy()  # 避免修改原始数据
            try:
                import json
                data['targetUserIds'] = json.loads(data['targetUserIds'])
            except json.JSONDecodeError:
                # 非 JSON 格式时，按逗号分隔
                data['targetUserIds'] = [item.strip() for item in data['targetUserIds'].split(',') if item.strip()]
        
        # 调用父类继续处理
        return super().to_internal_value(data)
    
    def validate(self, attrs):
        """校验通知数据"""
        target_type = attrs.get('target_type')
        target_user_ids = attrs.get('targetUserIds', [])
        
        # 目标用户类型为 2 时，必须传入 targetUserIds
        if target_type == 2 and not target_user_ids:
            raise serializers.ValidationError("目标用户类型为 2 时，必须传入目标用户ID列表（targetUserIds）")
            
        # 目标用户类型为 2 时，校验 targetUserIds
        if target_type == 2 and target_user_ids:
            # 目标用户 ID 校验
            existing_user_ids = set(User.objects.filter(
                id__in=target_user_ids,
                is_deleted=0,
                status=1
            ).values_list('id', flat=True))
            
            # 非法用户 ID
            non_existing_user_ids = set(int(uid) for uid in target_user_ids) - existing_user_ids
            if non_existing_user_ids:
                raise serializers.ValidationError(
                    f"以下用户 ID 不存在或已被禁用：{', '.join(map(str, non_existing_user_ids))}"
                )
        
        return attrs
    
    def update(self, instance, validated_data):
        """更新通知公告"""
        # targetUserIds 不属于 Notice 模型字段
        target_user_ids = validated_data.pop('targetUserIds', [])
        
        # 目标用户类型为 2 时，处理 targetUserIds
        if validated_data.get('target_type') == 2 and target_user_ids:
            # 转换为逗号分隔字符串
            validated_data['target_user_ids'] = ','.join(target_user_ids)
        elif validated_data.get('target_type') == 1:
            # 全部用户：清空目标用户列表
            validated_data['target_user_ids'] = None
        
        # 设置更新时间和更新人
        user_id = self.context.get('user_id')
        if user_id:
            validated_data['update_by'] = user_id
        validated_data['update_time'] = timezone.now()
        
        # 已发布的通知公告，不允许修改部分字段
        if instance.publish_status == 1:  # 已发布
            # 移除不允许修改的字段
            for field in ['target_type', 'target_user_ids']:
                if field in validated_data:
                    validated_data.pop(field)
        
        # 更新通知公告
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class NoticeCreateSerializer(StandardModelSerializer):
    """通知公告创建序列化器"""
    targetUserIds = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="目标用户ID列表"
    )
    targetType = serializers.IntegerField(source='target_type')
    
    class Meta:
        model = Notice
        fields = ['id', 'title', 'content', 'type', 'level', 'targetType', 'targetUserIds']
        extra_kwargs = {
            'id': {'read_only': True},
            'title': {'required': True, 'max_length': 50},
            'content': {'required': True},
            'type': {'required': True},
            'level': {'required': True},
        }
    
    def to_internal_value(self, data):
        """
        转换前端数据格式为后端模型格式
        """
        # 检查前端是否传入了 targetType 和 targetUserIds
        if 'targetType' in data and not 'target_type' in data:
            data = data.copy()  # 避免修改原始数据
            data['target_type'] = data['targetType']
        
        # 将 ListField 值转换为 Python List
        if 'targetUserIds' in data and isinstance(data['targetUserIds'], str):
            data = data.copy()  # 避免修改原始数据
            try:
                import json
                data['targetUserIds'] = json.loads(data['targetUserIds'])
            except json.JSONDecodeError:
                # 非 JSON 格式时，按逗号分隔
                data['targetUserIds'] = [item.strip() for item in data['targetUserIds'].split(',') if item.strip()]
        
        # 调用父类继续处理
        return super().to_internal_value(data)
    
    def to_representation(self, instance):
        """
        转换通知公告数据为 API 响应格式
        """
        data = super().to_representation(instance)
        
        # 转换目标用户类型和目标用户 ID
        if 'target_type' in data:
            data['targetType'] = data.pop('target_type')
        
        # 转换目标用户 ID 列表
        if hasattr(instance, 'target_user_ids') and instance.target_user_ids:
            data['targetUserIds'] = instance.target_user_ids.split(',')
        else:
            data['targetUserIds'] = []
        
        return data
    
    def validate(self, attrs):
        """校验通知数据"""
        target_type = attrs.get('target_type')
        target_user_ids = attrs.get('targetUserIds', [])
        
        # 目标用户类型为 2 时，必须传入 targetUserIds
        if target_type == 2 and not target_user_ids:
            raise serializers.ValidationError("目标用户类型为 2 时，必须传入目标用户ID列表（targetUserIds）")
            
        # 目标用户类型为 2 时，校验 targetUserIds
        if target_type == 2 and target_user_ids:
            # 目标用户 ID 校验
            existing_user_ids = set(User.objects.filter(
                id__in=target_user_ids,
                is_deleted=0,
                status=1
            ).values_list('id', flat=True))
            
            # 非法用户 ID
            non_existing_user_ids = set(int(uid) for uid in target_user_ids) - existing_user_ids
            if non_existing_user_ids:
                raise serializers.ValidationError(
                    f"以下用户 ID 不存在或已被禁用：{', '.join(map(str, non_existing_user_ids))}"
                )
        
        return attrs
    
    def create(self, validated_data):
        """创建通知公告"""
        # targetUserIds 处理
        target_user_ids = validated_data.pop('targetUserIds', [])
        
        # 目标用户类型为 2 时，处理 targetUserIds
        if validated_data.get('target_type') == 2 and target_user_ids:
            # targetUserIds 转换为字符串
            validated_data['target_user_ids'] = ','.join(target_user_ids)
        
        # 创建时间和创建人
        validated_data['create_time'] = timezone.now()
        
        # 创建人
        user_id = self.context.get('user_id')
        if user_id:
            validated_data['create_by'] = user_id
        
        # 默认设置为未发布状态
        validated_data['publish_status'] = 0
        
        # 创建通知公告
        notice = Notice.objects.create(**validated_data)
        
        return notice


class NoticeMyPageSerializer(StandardModelSerializer):
    """我的通知公告分页列表序列化器"""
    id = BigIntAsStringField(source='notice.id')
    title = serializers.CharField(source='notice.title')
    type = serializers.IntegerField(source='notice.type')
    level = serializers.CharField(source='notice.level')
    publisherName = serializers.SerializerMethodField()
    publishTime = serializers.SerializerMethodField()
    isRead = serializers.IntegerField(source='is_read')
    
    class Meta:
        model = UserNotice
        fields = ['id', 'title', 'type', 'level', 'publisherName', 'publishTime', 'isRead']
    
    def get_publisherName(self, obj):
        """获取发布人名称"""
        publisher_id = getattr(obj.notice, 'publisher_id', None)
        if publisher_id:
            try:
                user = User.objects.get(id=publisher_id)
                return user.nickname or user.username
            except User.DoesNotExist:
                return "未知用户"
        return "系统"
    
    def get_publishTime(self, obj):
        """格式化发布时间"""
        if obj.notice.publish_time:
            return obj.notice.publish_time.strftime('%Y-%m-%d %H:%M')
        return None
