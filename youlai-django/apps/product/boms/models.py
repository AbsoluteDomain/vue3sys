from django.db import models





class BomList(models.Model):

    """BOM 主表 bom_list"""



    TYPE_JOINT = 0

    TYPE_ROBOT_ARM = 1

    TYPE_OTHER = 2

    TYPE_CHOICES = (

        (TYPE_JOINT, "关节"),

        (TYPE_ROBOT_ARM, "机械臂"),

        (TYPE_OTHER, "其他"),

    )



    id = models.AutoField(primary_key=True, verbose_name="BOM ID")

    bom_model = models.CharField(max_length=255, verbose_name="BOM型号")

    bom_name = models.CharField(

        max_length=255,

        blank=True,

        null=True,

        verbose_name="BOM名称",

    )

    material_code = models.CharField(

        max_length=255,

        blank=True,

        null=True,

        verbose_name="物料编码",

    )

    is_del = models.IntegerField(default=0, verbose_name="删除标记")

    type = models.IntegerField(

        default=TYPE_JOINT,

        choices=TYPE_CHOICES,

        verbose_name="类型",

    )



    class Meta:

        db_table = "bom_list"

        verbose_name = "BOM清单"

        verbose_name_plural = "BOM清单"



    def __str__(self):

        return self.bom_name or self.bom_model





class AssemblyRecipe(models.Model):

    """BOM 明细 assembly_recipes，通过 bom_id 关联 bom_list"""



    id = models.AutoField(primary_key=True, verbose_name="ID")

    bom_id = models.IntegerField(null=True, blank=True, verbose_name="BOM ID")

    product_name = models.TextField(verbose_name="成品名称")

    raw_material_id = models.IntegerField(null=True, blank=True, verbose_name="原材料ID")

    raw_material_name = models.TextField(null=True, blank=True, verbose_name="原材料名称")

    raw_material_quantity = models.IntegerField(null=True, blank=True, verbose_name="原材料数量")

    component_id = models.IntegerField(null=True, blank=True, verbose_name="组件ID")

    component_name = models.TextField(null=True, blank=True, verbose_name="组件名称")

    component_quantity = models.IntegerField(null=True, blank=True, verbose_name="组件数量")

    created_at = models.DateTimeField(null=True, blank=True, verbose_name="创建时间")

    updated_at = models.DateTimeField(null=True, blank=True, verbose_name="更新时间")



    class Meta:

        db_table = "assembly_recipes"

        verbose_name = "装配配方"

        verbose_name_plural = "装配配方"



    def __str__(self):

        return f"{self.product_name}#{self.id}"


