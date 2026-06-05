"""平台-代码生成模型。

"""

from django.db import models


class GenTable(models.Model):
    """
    表名：gen_table
    表说明：代码生成配置表，用于存储自动生成业务代码的相关配置信息。
    """

    table_name = models.CharField(max_length=100, unique=True, verbose_name="表名", help_text="数据库表名")
    module_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="模块名", help_text="模块名称")
    package_name = models.CharField(max_length=255, verbose_name="包名", help_text="包名")
    business_name = models.CharField(max_length=100, verbose_name="业务名", help_text="业务名称")
    entity_name = models.CharField(max_length=100, verbose_name="实体类名", help_text="实体类名称")
    author = models.CharField(max_length=50, verbose_name="作者", help_text="代码作者")
    parent_menu_id = models.BigIntegerField(null=True, blank=True, verbose_name="上级菜单ID", help_text="上级菜单ID，对应 sys_menu 的 id")
    remove_table_prefix = models.CharField(max_length=20, blank=True, null=True, verbose_name="移除表前缀", help_text="要移除的表前缀，如: sys_")
    page_type = models.CharField(max_length=20, blank=True, null=True, verbose_name="页面类型", help_text="页面类型(classic|curd)")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    is_deleted = models.SmallIntegerField(default=0, verbose_name="是否删除", help_text="是否删除")

    class Meta:
        db_table = "gen_table"
        verbose_name = "代码生成配置表"
        verbose_name_plural = "代码生成配置表"
        app_label = "codegen"

    def __str__(self):
        return self.table_name


class GenTableColumn(models.Model):
    """
    表名：gen_table_column
    表说明：代码生成字段配置表，用于记录各字段的生成配置，辅助自动生成业务代码中的字段定义。
    """

    table = models.ForeignKey("GenTable", on_delete=models.CASCADE, verbose_name="表配置ID", help_text="关联的表配置ID")
    column_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="数据库列名", help_text="数据库中的列名")
    column_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="数据库列类型", help_text="数据库列类型")
    column_length = models.IntegerField(blank=True, null=True, verbose_name="列长度", help_text="数据库列长度")
    field_name = models.CharField(max_length=100, verbose_name="字段名称", help_text="字段名称")
    field_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="字段类型", help_text="字段数据类型")
    field_sort = models.IntegerField(blank=True, null=True, verbose_name="字段排序", help_text="字段排序")
    field_comment = models.CharField(max_length=255, blank=True, null=True, verbose_name="字段描述", help_text="字段描述")
    max_length = models.IntegerField(blank=True, null=True, verbose_name="最大长度", help_text="字段最大长度")
    is_required = models.BooleanField(default=False, verbose_name="是否必填", help_text="是否必填")
    is_show_in_list = models.BooleanField(default=False, verbose_name="列表显示", help_text="是否在列表中显示")
    is_show_in_form = models.BooleanField(default=False, verbose_name="表单显示", help_text="是否在表单中显示")
    is_show_in_query = models.BooleanField(default=False, verbose_name="查询条件显示", help_text="是否在查询条件中显示")
    query_type = models.SmallIntegerField(blank=True, null=True, verbose_name="查询方式", help_text="查询方式")
    form_type = models.SmallIntegerField(blank=True, null=True, verbose_name="表单类型", help_text="表单类型")
    dict_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="字典类型", help_text="字典类型")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")

    class Meta:
        db_table = "gen_table_column"
        verbose_name = "代码生成字段配置表"
        verbose_name_plural = "代码生成字段配置表"
        app_label = "codegen"

    def __str__(self):
        return self.field_name
