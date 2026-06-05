"""系统管理-字典模型。

"""

from django.db import models


class Dictionary(models.Model):
    """
    表名：sys_dict
    表说明：字典类型表，用于存储各种业务枚举、状态、类型等的编码和名称。
    """

    dict_code = models.CharField(max_length=50, verbose_name="类型编码", help_text="类型编码")
    name = models.CharField(max_length=50, verbose_name="类型名称", help_text="类型名称")
    status = models.SmallIntegerField(default=0, verbose_name="状态", help_text="状态（0: 正常; 1: 禁用）")
    remark = models.CharField(max_length=255, blank=True, null=True, verbose_name="备注", help_text="备注")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    create_by = models.BigIntegerField(null=True, blank=True, verbose_name="创建人ID", help_text="创建人ID")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    update_by = models.BigIntegerField(null=True, blank=True, verbose_name="修改人ID", help_text="修改人ID")
    is_deleted = models.SmallIntegerField(default=0, verbose_name="是否删除", help_text="是否删除（1-删除，0-未删除）")

    class Meta:
        db_table = "sys_dict"
        verbose_name = "字典类型表"
        verbose_name_plural = "字典类型表"

    def __str__(self):
        return self.name


class DictionaryItem(models.Model):
    """
    表名：sys_dict_item
    表说明：字典项表，用于记录字典中每个具体项的值和标签。
    """

    dict_code = models.CharField(
        max_length=50,
        verbose_name="关联字典编码",
        help_text="关联字典编码，与 sys_dict 表中的 dict_code 对应",
    )
    value = models.CharField(max_length=50, verbose_name="字典项值", help_text="字典项值")
    label = models.CharField(max_length=100, verbose_name="字典项标签", help_text="字典项标签")
    tag_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="标签类型",
        help_text="标签类型（前端展示用）",
    )
    status = models.SmallIntegerField(default=0, verbose_name="状态", help_text="状态（1-正常，0-禁用）")
    sort = models.IntegerField(default=0, verbose_name="排序", help_text="排序")
    remark = models.CharField(max_length=255, blank=True, null=True, verbose_name="备注", help_text="备注")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    create_by = models.BigIntegerField(null=True, blank=True, verbose_name="创建人ID", help_text="创建人ID")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    update_by = models.BigIntegerField(null=True, blank=True, verbose_name="修改人ID", help_text="修改人ID")

    class Meta:
        db_table = "sys_dict_item"
        verbose_name = "字典项表"
        verbose_name_plural = "字典项表"

    def __str__(self):
        return self.label
