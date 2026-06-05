"""系统管理-菜单序列化器。

"""

from rest_framework import serializers
from core.serializers import BigIntAsStringField, StandardModelSerializer

from apps.system.menus.models import Menu
from apps.system.roles.models import RoleMenu
from apps.system.users.models import UserRole
from django.db.models import Q
from django.utils import timezone
import json


class MenuSerializer(StandardModelSerializer):
    """菜单序列化器，支持递归序列化子菜单"""
    id = BigIntAsStringField(read_only=True)
    parentId = BigIntAsStringField(source='parent_id', read_only=True)
    routeName = serializers.CharField(source='route_name', read_only=True, allow_null=True)
    routePath = serializers.CharField(source='route_path', read_only=True, allow_null=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['id', 'parentId', 'name', 'type', 'routeName', 'routePath', 'component',
                  'sort', 'visible', 'icon', 'redirect', 'perm', 'children']

    def get_children(self, obj):
        """获取子菜单"""
        # 获取上下文中的visible参数，用于过滤菜单状态
        visible = self.context.get('visible')

        # 构建查询条件
        query = Q(parent_id=obj.id)

        # 排除按钮
        query &= ~Q(type='B')

        # 如果指定了visible参数，则添加状态过滤
        if visible is not None:
            query &= Q(visible=visible)

        # 查询子菜单并按排序字段和ID排序
        children = Menu.objects.filter(query).order_by('sort', 'id')

        # 递归序列化子菜单
        return MenuSerializer(children, many=True, context=self.context).data

    def to_representation(self, instance):
        """重写to_representation方法，将id和parentId转换为字符串类型"""
        ret = super().to_representation(instance)
        # 将id和parentId转换为字符串类型
        ret['id'] = str(ret['id'])
        ret['parentId'] = str(ret['parentId'])

        # 如果children为空列表，则删除该字段
        if 'children' in ret and not ret['children']:
            del ret['children']

        return ret


class MenuOptionSerializer(StandardModelSerializer):
    """菜单下拉选项序列化器"""
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['value', 'label', 'children']

    def get_value(self, obj):
        """获取菜单ID作为value"""
        return str(obj.id)

    def get_label(self, obj):
        """获取菜单名称作为label"""
        return obj.name

    def get_children(self, obj):
        """获取子菜单选项"""
        # 获取上下文中的only_parent参数
        only_parent = self.context.get('only_parent', False)

        # 构建查询条件
        query = Q(parent_id=obj.id)

        # 如果只查询父级菜单，则排除类型为3(外链)和4(按钮)的菜单
        if only_parent:
            query &= ~Q(type='B')

        # 查询子菜单并按排序字段和ID排序
        children = Menu.objects.filter(query).order_by('sort', 'id')

        # 递归序列化子菜单
        return MenuOptionSerializer(children, many=True, context=self.context).data

    def to_representation(self, instance):
        """重写to_representation方法，处理value和children字段"""
        ret = super().to_representation(instance)

        # 如果children为空列表，则删除该字段
        if 'children' in ret and not ret['children']:
            del ret['children']

        return ret


class KeyValueSerializer(serializers.Serializer):
    """键值对序列化器，用于菜单参数"""
    key = serializers.CharField(required=True)
    value = serializers.CharField(required=True)


class MenuCreateSerializer(StandardModelSerializer):
    """菜单创建序列化器"""
    parentId = BigIntAsStringField(source='parent_id', required=False, default=0)
    routeName = serializers.CharField(source='route_name', required=False, allow_null=True, allow_blank=True)
    routePath = serializers.CharField(source='route_path', required=False, allow_null=True, allow_blank=True)
    keepAlive = serializers.IntegerField(source='keep_alive', required=False, allow_null=True, default=0)
    alwaysShow = serializers.IntegerField(source='always_show', required=False, allow_null=True, default=0)
    params = serializers.ListField(child=KeyValueSerializer(), required=False, allow_null=True, allow_empty=True)

    class Meta:
        model = Menu
        fields = ['id', 'parentId', 'name', 'type', 'routeName', 'routePath', 'component',
                  'perm', 'visible', 'sort', 'icon', 'redirect', 'keepAlive', 'alwaysShow',
                  'params']
        extra_kwargs = {
            'name': {'required': True},
            'type': {'required': True},
            'visible': {'required': False, 'default': 1},
            'sort': {'required': False, 'default': 0},
            'icon': {'required': False, 'allow_blank': True, 'allow_null': True},
            'redirect': {'required': False, 'allow_blank': True, 'allow_null': True},
            'component': {'required': False, 'allow_blank': True, 'allow_null': True},
            'perm': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate(self, attrs):
        """验证菜单属性"""
        if attrs.get('keep_alive') is None:
            attrs['keep_alive'] = 0
        if attrs.get('always_show') is None:
            attrs['always_show'] = 0

        menu_type = attrs.get('type')

        route_path = attrs.get('route_path')
        external_link = bool(route_path) and (route_path.startswith('http://') or route_path.startswith('https://'))

        # 根据菜单类型进行特定验证
        if menu_type == 'M':
            if not route_path:
                raise serializers.ValidationError({"routePath": "菜单类型必须设置路由路径"})

            if external_link:
                # 外链通过 routePath 识别，允许 routeName/component 为空
                return attrs

            if not attrs.get('route_name'):
                raise serializers.ValidationError({"routeName": "菜单类型必须设置路由名称"})

            route_name = attrs.get('route_name')
            if Menu.objects.filter(route_name=route_name).exists():
                raise serializers.ValidationError({"routeName": "路由名称已存在"})

            if not attrs.get('component'):
                raise serializers.ValidationError({"component": "菜单类型必须设置组件路径"})

        elif menu_type == 'C':
            if not route_path:
                raise serializers.ValidationError({"routePath": "目录类型必须设置路由路径"})

        elif menu_type == 'B':
            if not attrs.get('perm'):
                raise serializers.ValidationError({"perm": "按钮类型必须设置权限标识"})

        return attrs

    def create(self, validated_data):
        """创建菜单"""
        # 提取并移除params字段
        params_data = validated_data.pop('params', [])

        # 获取父菜单ID
        parent_id = validated_data.get('parent_id', 0)

        # 构建tree_path
        tree_path = ''
        if parent_id == 0:
            tree_path = '0'
        else:
            # 获取父菜单，如果父菜单不存在则抛出异常
            try:
                parent_menu = Menu.objects.get(id=parent_id)
                # 如果父菜单有tree_path，则在其基础上添加当前父菜单ID
                if parent_menu.tree_path:
                    tree_path = f"{parent_menu.tree_path},{parent_id}"
                else:
                    tree_path = str(parent_id)
            except Menu.DoesNotExist:
                raise serializers.ValidationError({"parentId": "父菜单不存在"})

        # 设置tree_path
        validated_data['tree_path'] = tree_path

        # 设置创建时间
        validated_data['create_time'] = timezone.now()

        # 处理params字段 - 转换为dict格式存储
        if params_data:
            validated_data['params'] = {item['key']: item['value'] for item in params_data}
        else:
            validated_data['params'] = None

        # 创建菜单
        menu = Menu.objects.create(**validated_data)
        return menu


class MenuUpdateSerializer(StandardModelSerializer):
    """菜单更新序列化器"""
    id = BigIntAsStringField(read_only=True)
    parentId = BigIntAsStringField(source='parent_id', required=False)
    routeName = serializers.CharField(source='route_name', required=False, allow_null=True, allow_blank=True)
    routePath = serializers.CharField(source='route_path', required=False, allow_null=True, allow_blank=True)
    keepAlive = serializers.IntegerField(source='keep_alive', required=False, allow_null=True)
    alwaysShow = serializers.IntegerField(source='always_show', required=False, allow_null=True)
    params = serializers.ListField(child=KeyValueSerializer(), required=False, allow_null=True, allow_empty=True)

    class Meta:
        model = Menu
        fields = ['id', 'parentId', 'name', 'type', 'routeName', 'routePath', 'component',
                  'perm', 'visible', 'sort', 'icon', 'redirect', 'keepAlive', 'alwaysShow',
                  'params']
        extra_kwargs = {
            'name': {'required': False},
            'type': {'required': False},
            'visible': {'required': False},
            'sort': {'required': False},
            'icon': {'required': False, 'allow_blank': True, 'allow_null': True},
            'redirect': {'required': False, 'allow_blank': True, 'allow_null': True},
            'component': {'required': False, 'allow_blank': True, 'allow_null': True},
            'perm': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate(self, attrs):
        """验证菜单属性"""
        if 'keep_alive' in attrs and attrs.get('keep_alive') is None:
            attrs['keep_alive'] = 0
        if 'always_show' in attrs and attrs.get('always_show') is None:
            attrs['always_show'] = 0

        menu_type = attrs.get('type')
        if menu_type is None and self.instance is not None:
            menu_type = getattr(self.instance, 'type', None)

        route_path = attrs.get('route_path')
        if route_path is None and self.instance is not None:
            route_path = getattr(self.instance, 'route_path', None)

        external_link = bool(route_path) and (route_path.startswith('http://') or route_path.startswith('https://'))

        # 根据菜单类型进行特定验证
        if menu_type == 'M':
            if 'route_path' in attrs and not attrs.get('route_path'):
                raise serializers.ValidationError({"routePath": "菜单类型必须设置路由路径"})

            if 'route_path' in attrs and attrs.get('route_path'):
                new_route_path = attrs.get('route_path')
                new_external_link = bool(new_route_path) and (
                    new_route_path.startswith('http://') or new_route_path.startswith('https://')
                )
                if new_external_link:
                    return attrs

            if external_link:
                return attrs

            if 'route_name' in attrs and not attrs.get('route_name'):
                raise serializers.ValidationError({"routeName": "菜单类型必须设置路由名称"})

            if 'route_name' in attrs:
                route_name = attrs.get('route_name')
                instance = self.instance
                if Menu.objects.filter(route_name=route_name).exclude(id=instance.id).exists():
                    raise serializers.ValidationError({"routeName": "路由名称已存在"})

            if 'component' in attrs and not attrs.get('component'):
                raise serializers.ValidationError({"component": "菜单类型必须设置组件路径"})

        elif menu_type == 'C':
            if 'route_path' in attrs and not attrs.get('route_path'):
                raise serializers.ValidationError({"routePath": "目录类型必须设置路由路径"})

        elif menu_type == 'B':
            if 'perm' in attrs and not attrs.get('perm'):
                raise serializers.ValidationError({"perm": "按钮类型必须设置权限标识"})

        return attrs

    def update(self, instance, validated_data):
        """更新菜单"""
        # 提取并移除params字段
        params_data = validated_data.pop('params', None)

        # 获取父菜单ID
        parent_id = validated_data.get('parent_id')

        # 如果父菜单ID发生变化，更新tree_path
        if parent_id is not None and parent_id != instance.parent_id:
            # 构建tree_path
            tree_path = ''
            if parent_id == 0:
                tree_path = '0'
            else:
                # 获取父菜单，如果父菜单不存在则抛出异常
                try:
                    parent_menu = Menu.objects.get(id=parent_id)
                    # 如果父菜单有tree_path，则在其基础上添加当前父菜单ID
                    if parent_menu.tree_path:
                        tree_path = f"{parent_menu.tree_path},{parent_id}"
                    else:
                        tree_path = str(parent_id)
                except Menu.DoesNotExist:
                    raise serializers.ValidationError({"parentId": "父菜单不存在"})

            # 设置tree_path
            validated_data['tree_path'] = tree_path

        # 设置更新时间
        validated_data['update_time'] = timezone.now()

        # 处理params字段 - 转换为dict格式存储
        if 'params' in self.initial_data:
            if params_data is None or params_data == []:
                validated_data['params'] = None
            else:
                validated_data['params'] = {item['key']: item['value'] for item in params_data}

        # 更新菜单
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class MenuRouteSerializer(serializers.ModelSerializer):
    """菜单路由序列化器"""
    path = serializers.SerializerMethodField()
    component = serializers.SerializerMethodField()
    redirect = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['path', 'component', 'redirect', 'name', 'meta', 'children']

    def get_path(self, obj):
        """获取路由路径"""
        return obj.route_path or ''

    def get_component(self, obj):
        """获取组件路径"""
        return obj.component or ''

    def get_redirect(self, obj):
        """获取跳转链接"""
        return obj.redirect or ''

    def get_name(self, obj):
        """获取路由名称"""
        return obj.route_name or obj.route_path or ''

    def get_meta(self, obj):
        """获取路由元数据"""
        return {
            'title': obj.name,
            'icon': obj.icon or '',
            'hidden': obj.visible == 0,
            'keepAlive': bool(obj.keep_alive),
            'alwaysShow': bool(obj.always_show),
            'params': obj.params
        }

    def get_children(self, obj):
        """获取子路由"""
        # 获取上下文中的menu_ids参数，用于过滤菜单
        menu_ids = self.context.get('menu_ids', [])

        # 构建查询条件
        query = Q(parent_id=obj.id)

        # routes 仅返回目录(C)/菜单(M)，按钮(B)只用于权限标识，不应出现在路由树
        query &= ~Q(type='B')

        # 如果指定了menu_ids参数，则添加ID过滤
        if menu_ids:
            query &= Q(id__in=menu_ids)

        # 查询子菜单并按排序字段和ID排序
        children = Menu.objects.filter(query).order_by('sort', 'id')

        # 递归序列化子菜单
        return MenuRouteSerializer(children, many=True, context=self.context).data


class MenuFormSerializer(StandardModelSerializer):
    """菜单表单序列化器"""
    id = BigIntAsStringField(read_only=True)
    parentId = BigIntAsStringField(source='parent_id')
    routeName = serializers.CharField(source='route_name', allow_null=True)
    routePath = serializers.CharField(source='route_path', allow_null=True)
    keepAlive = serializers.IntegerField(source='keep_alive', allow_null=True)
    alwaysShow = serializers.IntegerField(source='always_show', allow_null=True)

    class Meta:
        model = Menu
        fields = ['id', 'parentId', 'name', 'type', 'routeName', 'routePath',
                  'component', 'perm', 'visible', 'sort', 'icon', 'redirect',
                  'keepAlive', 'alwaysShow', 'params']

    def to_representation(self, instance):
        """重写to_representation方法，将id和parentId转换为字符串类型"""
        ret = super().to_representation(instance)

        # 将id转换为字符串类型
        if ret['id'] is not None:
            ret['id'] = str(ret['id'])

        # 将parentId转换为字符串类型
        if ret['parentId'] is not None:
            ret['parentId'] = str(ret['parentId'])

        if ret.get('keepAlive') is None:
            ret['keepAlive'] = 0

        if ret.get('alwaysShow') is None:
            ret['alwaysShow'] = 0

        # 处理params字段 - dict转换为KeyValue列表
        if instance.params:
            ret['params'] = [{"key": k, "value": v} for k, v in instance.params.items()]
        else:
            ret['params'] = None

        return ret
