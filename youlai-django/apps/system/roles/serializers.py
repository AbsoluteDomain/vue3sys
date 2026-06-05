"""系统管理-角色序列化器。

"""

from rest_framework import serializers
from core.serializers import BigIntAsStringField, StandardModelSerializer

from apps.system.menus.models import Menu
from apps.system.roles.models import Role, RoleDept
from django.utils import timezone


class RolePageSerializer(StandardModelSerializer):
    """角色分页列表序列化器"""
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M:%S')
    dataScope = serializers.IntegerField(source='data_scope', required=False)
    dataScopeLabel = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'code', 'sort', 'status', 'dataScope', 'dataScopeLabel', 'createTime']

    def get_dataScopeLabel(self, obj):
        """获取数据权限显示名称"""
        labels = {
            1: "所有数据",
            2: "部门及子部门数据",
            3: "本部门数据",
            4: "本人数据",
            5: "自定义部门数据",
        }
        return labels.get(obj.data_scope, "")


class RoleFormSerializer(StandardModelSerializer):
    """角色表单信息序列化器"""
    dataScope = serializers.IntegerField(source='data_scope', required=False)
    deptIds = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'code', 'sort', 'status', 'dataScope', 'deptIds']

    def get_deptIds(self, obj):
        dept_ids = RoleDept.objects.filter(role_id=obj.id).values_list('dept_id', flat=True)
        return [str(dept_id) for dept_id in dept_ids]

    def update(self, instance, validated_data):
        """更新角色信息"""
        # 设置更新时间
        validated_data['update_time'] = timezone.now()

        # 更新角色信息
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class RoleCreateSerializer(StandardModelSerializer):
    """角色创建序列化器"""
    dataScope = serializers.IntegerField(source='data_scope', required=False)

    class Meta:
        model = Role
        fields = ['id', 'name', 'code', 'sort', 'status', 'dataScope']
        extra_kwargs = {
            'name': {'required': True},
            'code': {'required': True},
            'sort': {'required': False},
            'status': {'required': False, 'default': 1},
        }

    @staticmethod
    def validate_name(value):
        """验证角色名称唯一性"""
        # 检查是否存在同名角色(未删除的)
        if Role.objects.filter(name=value, is_deleted=0).exists():
            raise serializers.ValidationError("角色名称已存在")
        return value

    @staticmethod
    def validate_code(value):
        """验证角色编码唯一性"""
        # 检查是否存在同编码角色(未删除的)
        if Role.objects.filter(code=value, is_deleted=0).exists():
            raise serializers.ValidationError("角色编码已存在")
        return value

    def create(self, validated_data):
        # 从请求中获取创建者ID
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['create_by'] = request.user.id

        # 设置创建时间
        validated_data['create_time'] = timezone.now()

        # 创建角色
        return super().create(validated_data)


class MenuOptionSerializer(StandardModelSerializer):
    """菜单选项序列化器"""
    value = BigIntAsStringField(source='id', read_only=True)
    label = serializers.CharField(source='name')
    children = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['value', 'label', 'children']

    @staticmethod
    def get_children(obj):
        """递归获取子菜单"""
        children = Menu.objects.filter(parent_id=obj.id, visible=1).order_by('sort', 'id')
        if children.exists():
            return MenuOptionSerializer(children, many=True).data
        return []
