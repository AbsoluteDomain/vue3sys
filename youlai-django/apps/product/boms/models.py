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

    finished_product_id = models.IntegerField(

        null=True,

        blank=True,

        verbose_name="成品产品ID",

        help_text="关联 products.id，作为 BOM 对应成品的唯一关联键",

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

    product_name = models.TextField(
        blank=True,
        default="",
        verbose_name="成品名称（遗留字段，不再使用）",
    )

    raw_material_id = models.IntegerField(null=True, blank=True, verbose_name="原材料ID")

    raw_material_name = models.TextField(null=True, blank=True, verbose_name="原材料名称")

    raw_material_quantity = models.IntegerField(null=True, blank=True, verbose_name="原材料数量")

    component_id = models.IntegerField(null=True, blank=True, verbose_name="组件ID")

    component_name = models.TextField(null=True, blank=True, verbose_name="组件名称")

    component_quantity = models.IntegerField(null=True, blank=True, verbose_name="组件数量")

    material_code = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="物料编码",
        help_text="冗余存储，用于产品删除重建后通过物料编码回溯",
    )

    created_at = models.DateTimeField(null=True, blank=True, verbose_name="创建时间")

    updated_at = models.DateTimeField(null=True, blank=True, verbose_name="更新时间")



    class Meta:

        db_table = "assembly_recipes"

        verbose_name = "装配配方"

        verbose_name_plural = "装配配方"



    def __str__(self):

        part = self.component_name or self.raw_material_name or ""
        if part:
            return f"{part}#{self.id}"
        return f"recipe#{self.id}"


class BomAttachment(models.Model):

    """BOM 附件表 bom_attachment，文件本体存放在 MinIO"""

    TYPE_EXCEL = "excel"
    TYPE_PDF = "pdf"
    TYPE_URDF = "urdf"

    TYPE_CHOICES = (
        (TYPE_EXCEL, "Excel"),
        (TYPE_PDF, "PDF"),
        (TYPE_URDF, "URDF"),
    )

    id = models.AutoField(primary_key=True, verbose_name="主键")

    bom_id = models.IntegerField(db_index=True, verbose_name="BOM ID")

    file_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
        verbose_name="文件类型",
    )

    file_name = models.CharField(max_length=255, verbose_name="原始文件名")

    file_url = models.CharField(max_length=500, verbose_name="访问地址")

    storage_path = models.CharField(
        max_length=500,
        verbose_name="对象存储路径",
        help_text="URDF 压缩包解压后存入口 urdf 文件路径，删除时按所在目录整体清理",
    )

    file_size = models.BigIntegerField(default=0, verbose_name="文件大小(字节)")

    mime_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="MIME类型",
    )

    uploader_id = models.IntegerField(null=True, blank=True, verbose_name="上传人ID")

    uploader_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="上传人姓名",
    )

    is_del = models.IntegerField(default=0, verbose_name="删除标记")

    created_at = models.DateTimeField(null=True, blank=True, verbose_name="创建时间")

    updated_at = models.DateTimeField(null=True, blank=True, verbose_name="更新时间")

    class Meta:

        db_table = "bom_attachment"

        verbose_name = "BOM附件"

        verbose_name_plural = "BOM附件"

    def __str__(self):

        return f"{self.file_type}:{self.file_name}"


