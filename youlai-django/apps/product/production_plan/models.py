from django.db import models


class ProductionPlan(models.Model):
    """生产计划表"""

    id = models.AutoField(primary_key=True, verbose_name="ID")
    plan_date = models.DateField(verbose_name="计划日期")
    bom_id = models.IntegerField(verbose_name="BOM ID")
    quantity = models.IntegerField(default=1, verbose_name="计划数量")
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name="更新时间")

    class Meta:
        db_table = "production_plan"
        verbose_name = "生产计划"
        verbose_name_plural = "生产计划"
        unique_together = ("plan_date", "bom_id")

    def __str__(self):
        return f"{self.plan_date} - BOM:{self.bom_id}"