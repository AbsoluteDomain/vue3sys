# Generated for material_code -> product_id 关联重构

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boms', '0002_assemblyrecipe_material_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='bomlist',
            name='finished_product_id',
            field=models.IntegerField(blank=True, help_text='关联 products.id，作为 BOM 对应成品的唯一关联键', null=True, verbose_name='成品产品ID'),
        ),
    ]
