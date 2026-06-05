"""系统管理-字典序列化器。
 
"""
 
from rest_framework import serializers
from core.serializers import StandardModelSerializer

from apps.system.dicts.models import Dictionary, DictionaryItem
from django.utils import timezone
 
 
class DictListSerializer(StandardModelSerializer):
    """字典列表序列化器"""
    dictCode = serializers.CharField(source='dict_code')
    
    class Meta:
        model = Dictionary
        fields = ['id', 'name', 'dictCode', 'status']
    
    def to_representation(self, instance):
        """将id转为字符串类型"""
        ret = super().to_representation(instance)
        ret['id'] = str(instance.id)
        return ret


class DictDetailSerializer(StandardModelSerializer):
    """字典详情序列化器"""
    dictCode = serializers.CharField(source='dict_code')
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M', required=False, allow_null=True)
    updateTime = serializers.DateTimeField(source='update_time', format='%Y-%m-%d %H:%M', required=False, allow_null=True)
    
    class Meta:
        model = Dictionary
        fields = ['id', 'name', 'dictCode', 'status', 'remark', 'createTime', 'updateTime']
    
    def to_representation(self, instance):
        """将id转为字符串类型"""
        ret = super().to_representation(instance)
        ret['id'] = str(instance.id)
        return ret


class DictCreateSerializer(StandardModelSerializer):
    """字典创建序列化器"""
    dictCode = serializers.CharField(source='dict_code')
    
    class Meta:
        model = Dictionary
        fields = ['id', 'name', 'dictCode', 'status', 'remark']
        extra_kwargs = {
            'id': {'required': False},
            'status': {'required': False, 'default': 1},
            'remark': {'required': False, 'allow_null': True, 'allow_blank': True}
        }
    
    def validate_dictCode(self, value):
        """验证字典编码唯一性"""
        if Dictionary.objects.filter(dict_code=value, is_deleted=0).exists():
            raise serializers.ValidationError("字典编码已存在")
        return value
    
    def validate_name(self, value):
        """验证字典名称不为空"""
        if not value or not value.strip():
            raise serializers.ValidationError("字典名称不能为空")
        return value
    
    def create(self, validated_data):
        """创建字典"""
        # 设置创建时间
        validated_data['create_time'] = timezone.now()
        
        # 设置创建人
        user_id = self.context.get('user_id')
        if user_id:
            validated_data['create_by'] = user_id
        
        # 创建字典
        return Dictionary.objects.create(**validated_data)


class DictUpdateSerializer(StandardModelSerializer):
    """字典更新序列化器"""
    dictCode = serializers.CharField(source='dict_code')
    
    class Meta:
        model = Dictionary
        fields = ['id', 'name', 'dictCode', 'status', 'remark']
        extra_kwargs = {
            'id': {'required': False, 'read_only': True},
            'status': {'required': False},
            'remark': {'required': False, 'allow_null': True, 'allow_blank': True}
        }
    
    def validate_dictCode(self, value):
        """验证字典编码唯一性，排除当前记录"""
        instance = self.instance
        # 如果编码已更改，检查是否与其他记录冲突
        if instance and instance.dict_code != value:
            if Dictionary.objects.filter(dict_code=value, is_deleted=0).exclude(id=instance.id).exists():
                raise serializers.ValidationError("字典编码已存在")
        return value
    
    def validate_name(self, value):
        """验证字典名称不为空"""
        if not value or not value.strip():
            raise serializers.ValidationError("字典名称不能为空")
        return value
    
    def update(self, instance, validated_data):
        """更新字典"""
        # 设置更新时间
        validated_data['update_time'] = timezone.now()
        
        # 设置更新人
        user_id = self.context.get('user_id')
        if user_id:
            validated_data['update_by'] = user_id
        
        # 更新字典字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # 保存更新
        instance.save()
        
        return instance


class DictItemSerializer(StandardModelSerializer):
    """字典项序列化器"""
    dictCode = serializers.CharField(source='dict_code')
    tagType = serializers.CharField(source='tag_type', required=False, allow_null=True)
    
    class Meta:
        model = DictionaryItem
        fields = ['id', 'dictCode', 'value', 'label', 'tagType', 'status', 'sort']
    
    def to_representation(self, instance):
        """将id转为字符串类型"""
        ret = super().to_representation(instance)
        ret['id'] = str(instance.id)
        return ret


class DictItemCreateSerializer(StandardModelSerializer):
    """字典项创建序列化器"""
    dictCode = serializers.CharField(source='dict_code')
    tagType = serializers.CharField(source='tag_type', required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = DictionaryItem
        fields = ['id', 'dictCode', 'value', 'label', 'tagType', 'status', 'sort']
        extra_kwargs = {
            'id': {'required': False},
            'status': {'required': False, 'default': 1},
            'sort': {'required': False, 'default': 0},
        }
    
    def validate_dictCode(self, value):
        """验证字典编码是否存在"""
        if not Dictionary.objects.filter(dict_code=value, is_deleted=0).exists():
            raise serializers.ValidationError(f"字典编码 '{value}' 不存在")
        return value
    
    def validate(self, attrs):
        """验证字典项值的唯一性"""
        dict_code = attrs.get('dict_code')
        value = attrs.get('value')
        
        # 检查同一字典下是否已存在相同值的字典项
        if DictionaryItem.objects.filter(dict_code=dict_code, value=value).exists():
            raise serializers.ValidationError({"value": f"字典项值 '{value}' 在字典 '{dict_code}' 中已存在"})
        
        return attrs
    
    def create(self, validated_data):
        """创建字典项"""
        # 设置创建时间
        validated_data['create_time'] = timezone.now()
        
        # 设置创建人
        user_id = self.context.get('user_id')
        if user_id:
            validated_data['create_by'] = user_id
        
        # 创建字典项
        return DictionaryItem.objects.create(**validated_data)


class DictItemUpdateSerializer(StandardModelSerializer):
    """字典项更新序列化器"""
    dictCode = serializers.CharField(source='dict_code')
    tagType = serializers.CharField(source='tag_type', required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = DictionaryItem
        fields = ['id', 'dictCode', 'value', 'label', 'tagType', 'status', 'sort']
        extra_kwargs = {
            'id': {'required': False, 'read_only': True},
            'dictCode': {'required': False},
            'value': {'required': False},
            'label': {'required': False},
            'status': {'required': False},
            'sort': {'required': False},
        }
    
    def validate_dictCode(self, value):
        """验证字典编码是否存在"""
        if not Dictionary.objects.filter(dict_code=value, is_deleted=0).exists():
            raise serializers.ValidationError(f"字典编码 '{value}' 不存在")
        return value
    
    def validate(self, attrs):
        """验证字典项值的唯一性，排除当前记录"""
        instance = self.instance
        dict_code = attrs.get('dict_code', instance.dict_code)
        value = attrs.get('value', instance.value)
        
        # 检查同一字典下是否已存在相同值的字典项（排除当前记录）
        if DictionaryItem.objects.filter(dict_code=dict_code, value=value).exclude(id=instance.id).exists():
            raise serializers.ValidationError({"value": f"字典项值 '{value}' 在字典 '{dict_code}' 中已存在"})
        
        return attrs
    
    def update(self, instance, validated_data):
        """更新字典项"""
        # 设置更新时间
        validated_data['update_time'] = timezone.now()
        
        # 设置更新人
        user_id = self.context.get('user_id')
        if user_id:
            validated_data['update_by'] = user_id
        
        # 更新字典项字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # 保存更新
        instance.save()
        
        return instance
