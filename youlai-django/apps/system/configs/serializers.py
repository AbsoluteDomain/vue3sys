"""系统管理-系统配置序列化器。

"""

from rest_framework import serializers
from core.serializers import StandardModelSerializer

from apps.system.configs.models import SysConfig


class ConfigPageSerializer(StandardModelSerializer):
    """系统配置分页列表序列化器"""
    configName = serializers.CharField(source='config_name')
    configKey = serializers.CharField(source='config_key')
    configValue = serializers.CharField(source='config_value')
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M')
    updateTime = serializers.DateTimeField(source='update_time', format='%Y-%m-%d %H:%M', required=False, allow_null=True)
    
    class Meta:
        model = SysConfig
        fields = ['id', 'configName', 'configKey', 'configValue', 'remark', 'createTime', 'updateTime']


class ConfigFormSerializer(StandardModelSerializer):
    """系统配置表单序列化器"""
    configName = serializers.CharField(source='config_name')
    configKey = serializers.CharField(source='config_key')
    configValue = serializers.CharField(source='config_value')
    
    class Meta:
        model = SysConfig
        fields = ['id', 'configName', 'configKey', 'configValue', 'remark']


class ConfigCreateSerializer(StandardModelSerializer):
    """系统配置创建序列化器"""
    configName = serializers.CharField(source='config_name', required=True, help_text="配置名称")
    configKey = serializers.CharField(source='config_key', required=True, help_text="配置键")
    configValue = serializers.CharField(source='config_value', required=True, help_text="配置值")
    
    class Meta:
        model = SysConfig
        fields = ['configName', 'configKey', 'configValue', 'remark']
    
    def validate_configKey(self, value):
        """验证配置键唯一性"""
        if SysConfig.objects.filter(config_key=value, is_deleted=0).exists():
            raise serializers.ValidationError("配置键已存在")
        return value
    
    def create(self, validated_data):
        """创建系统配置"""
        request = self.context.get('request')
        user_id = request.user.id if request and request.user else None
        
        config = SysConfig.objects.create(
            config_name=validated_data.get('config_name'),
            config_key=validated_data.get('config_key'),
            config_value=validated_data.get('config_value'),
            remark=validated_data.get('remark', ''),
            create_by=user_id,
            update_by=user_id
        )
        return config


class ConfigUpdateSerializer(StandardModelSerializer):
    """系统配置更新序列化器"""
    configName = serializers.CharField(source='config_name', required=False, help_text="配置名称")
    configKey = serializers.CharField(source='config_key', required=False, help_text="配置键")
    configValue = serializers.CharField(source='config_value', required=False, help_text="配置值")
    
    class Meta:
        model = SysConfig
        fields = ['configName', 'configKey', 'configValue', 'remark']
    
    def validate_configKey(self, value):
        """验证配置键唯一性（排除自己）"""
        config_id = self.instance.id if self.instance else None
        if SysConfig.objects.filter(config_key=value, is_deleted=0).exclude(id=config_id).exists():
            raise serializers.ValidationError("配置键已存在")
        return value
    
    def update(self, instance, validated_data):
        """更新系统配置"""
        request = self.context.get('request')
        user_id = request.user.id if request and request.user else None
        
        instance.config_name = validated_data.get('config_name', instance.config_name)
        instance.config_key = validated_data.get('config_key', instance.config_key)
        instance.config_value = validated_data.get('config_value', instance.config_value)
        instance.remark = validated_data.get('remark', instance.remark)
        instance.update_by = user_id
        instance.save()
        return instance
