"""系统管理-部门序列化器。

"""

from rest_framework import serializers
from core.serializers import BigIntAsStringField, StandardModelSerializer

from apps.system.dept.models import Department
from django.utils import timezone


class DeptSerializer(StandardModelSerializer):
    """部门序列化器"""
    id = BigIntAsStringField(read_only=True)
    parentId = BigIntAsStringField(source='parent_id')
    createTime = serializers.DateTimeField(source='create_time', format='%Y-%m-%d %H:%M', required=False, allow_null=True)
    updateTime = serializers.DateTimeField(source='update_time', format='%Y-%m-%d %H:%M', required=False, allow_null=True)
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = ['id', 'parentId', 'name', 'code', 'sort', 'status', 'children', 'createTime', 'updateTime']
    
    def get_children(self, obj):
        """递归获取子部门"""
        # 如果使用扁平模式，不加载子部门
        if self.context.get('flat_mode', False):
            return []

        allowed_ids = self.context.get('allowed_ids', None)
        
        # 获取状态过滤条件
        status = self.context.get('status', None)
        
        # 构建查询子部门的条件
        query = {'parent_id': obj.id, 'is_deleted': 0}
        
        # 如果指定了状态，则添加状态过滤
        if status is not None:
            query['status'] = status
        
        children = Department.objects.filter(**query)
        if allowed_ids is not None:
            children = children.filter(id__in=allowed_ids)
        children = children.order_by('sort', 'id')
        
        # 如果没有子部门，返回空列表
        if not children.exists():
            return []
        
        # 递归序列化子部门
        return DeptSerializer(children, many=True, context=self.context).data
    
    def _has_matching_descendant(self, dept_id, matching_ids):
        """检查部门是否有匹配的子孙部门"""
        # 获取直接子部门
        children = Department.objects.filter(parent_id=dept_id, is_deleted=0)
        
        # 检查子部门是否在匹配列表中
        for child in children:
            if child.id in matching_ids:
                return True
            # 递归检查子部门的子部门
            if self._has_matching_descendant(child.id, matching_ids):
                return True
        
        return False
    
    def to_representation(self, instance):
        """重写to_representation方法，将id和parentId转换为字符串类型"""
        ret = super().to_representation(instance)
        
        # 将id转换为字符串类型
        if ret['id'] is not None:
            ret['id'] = str(ret['id'])
        
        # 将parentId转换为字符串类型
        if ret['parentId'] is not None:
            ret['parentId'] = str(ret['parentId'])
            
        return ret


class DeptCreateSerializer(StandardModelSerializer):
    """部门创建序列化器"""
    parentId = BigIntAsStringField(source='parent_id', required=True)
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'parentId', 'status', 'sort']
        extra_kwargs = {
            'sort': {'required': False, 'default': 1},
            'status': {'required': False, 'default': 1}
        }
    
    def validate_code(self, value):
        """验证部门编码唯一性"""
        if Department.objects.filter(code=value, is_deleted=0).exists():
            raise serializers.ValidationError("部门编码已存在")
        return value
    
    def validate_parentId(self, value):
        """验证父部门是否存在"""
        if value != 0 and not Department.objects.filter(id=value, is_deleted=0).exists():
            raise serializers.ValidationError("父部门不存在")
        return value
    
    def create(self, validated_data):
        """创建部门"""
        # 获取父部门ID
        parent_id = validated_data.get('parent_id')
        
        # 构建tree_path
        if parent_id == 0:
            # 顶级部门
            tree_path = '0'
        else:
            # 获取父部门
            parent_dept = Department.objects.get(id=parent_id)
            tree_path = f"{parent_dept.tree_path},{parent_id}" if parent_dept.tree_path else str(parent_id)
        
        # 设置tree_path
        validated_data['tree_path'] = tree_path
        
        # 设置创建时间
        validated_data['create_time'] = timezone.now()
        
        # 设置创建人
        user_id = self.context.get('user_id')
        if user_id:
            validated_data['create_by'] = user_id
        
        # 创建部门
        return Department.objects.create(**validated_data)


class DeptUpdateSerializer(StandardModelSerializer):
    """部门更新序列化器"""
    parentId = BigIntAsStringField(source='parent_id', required=False)
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'parentId', 'status', 'sort']
    
    def validate_code(self, value):
        """验证部门编码唯一性（排除自身）"""
        instance = getattr(self, 'instance', None)
        if instance and instance.code != value:
            if Department.objects.filter(code=value, is_deleted=0).exists():
                raise serializers.ValidationError("部门编码已存在")
        return value
    
    def validate_parentId(self, value):
        """验证父部门是否存在，并防止循环引用"""
        instance = getattr(self, 'instance', None)
        
        # 检查父部门是否存在
        if value != 0 and not Department.objects.filter(id=value, is_deleted=0).exists():
            raise serializers.ValidationError("父部门不存在")
        
        # 防止将自己设为父部门
        if instance and instance.id == value:
            raise serializers.ValidationError("不能将自己设为父部门")
        
        # 防止将自己的子部门设为父部门（循环引用）
        if instance and value != 0:
            # 获取所有子部门ID
            child_ids = []
            self._get_all_children_ids(instance.id, child_ids)
            
            if value in child_ids:
                raise serializers.ValidationError("不能将自己的子部门设为父部门")
        
        return value
    
    def _get_all_children_ids(self, dept_id, result_list):
        """递归获取所有子部门ID"""
        children = Department.objects.filter(parent_id=dept_id, is_deleted=0)
        for child in children:
            result_list.append(child.id)
            self._get_all_children_ids(child.id, result_list)
    
    def update(self, instance, validated_data):
        """更新部门"""
        # 检查父部门是否变更
        old_parent_id = instance.parent_id
        new_parent_id = validated_data.get('parent_id', old_parent_id)
        
        # 如果父部门变更，需要更新tree_path
        if new_parent_id != old_parent_id:
            # 构建新的tree_path
            if new_parent_id == 0:
                # 顶级部门
                new_tree_path = '0'
            else:
                # 获取父部门
                parent_dept = Department.objects.get(id=new_parent_id)
                new_tree_path = f"{parent_dept.tree_path},{new_parent_id}" if parent_dept.tree_path else str(new_parent_id)
            
            # 保存原来的tree_path
            old_tree_path = instance.tree_path
            
            # 更新当前部门的tree_path
            validated_data['tree_path'] = new_tree_path
            
            # 设置更新时间和更新人
            validated_data['update_time'] = timezone.now()
            user_id = self.context.get('user_id')
            if user_id:
                validated_data['update_by'] = user_id
            
            # 更新部门
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            # 更新所有子部门的tree_path
            self._update_children_tree_path(instance.id, old_tree_path, new_tree_path)
            
            return instance
        else:
            # 父部门未变更，正常更新
            # 设置更新时间和更新人
            validated_data['update_time'] = timezone.now()
            user_id = self.context.get('user_id')
            if user_id:
                validated_data['update_by'] = user_id
            
            # 更新部门
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            return instance
    
    def _update_children_tree_path(self, dept_id, old_path, new_path):
        """递归更新子部门的tree_path"""
        children = Department.objects.filter(parent_id=dept_id, is_deleted=0)
        for child in children:
            # 构建新的tree_path
            child_tree_path = child.tree_path
            if child_tree_path.startswith(old_path):
                child_tree_path = child_tree_path.replace(old_path, new_path, 1)
                
                # 更新子部门的tree_path
                child.tree_path = child_tree_path
                child.update_time = timezone.now()
                child.save(update_fields=['tree_path', 'update_time'])
                
                # 递归更新子部门的子部门
                self._update_children_tree_path(child.id, child.tree_path.replace(new_path, old_path, 1), child.tree_path)


class DeptFormSerializer(StandardModelSerializer):
    """部门表单数据序列化器"""
    parentId = BigIntAsStringField(source='parent_id')
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'parentId', 'status', 'sort']
