from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FinishProduct',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('sn_code', models.CharField(blank=True, help_text='产品唯一标识', max_length=255, null=True, verbose_name='SN码')),
                ('bom_id', models.IntegerField(verbose_name='BOM ID')),
                ('name', models.CharField(max_length=255, verbose_name='成品名称')),
                ('status', models.IntegerField(choices=[(0, '未测试'), (1, '测试中'), (2, '测试合格'), (3, '测试不良')], default=0, verbose_name='测试状态')),
                ('description', models.CharField(blank=True, max_length=255, null=True, verbose_name='描述')),
                ('create_time', models.DateTimeField(blank=True, null=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(blank=True, null=True, verbose_name='更新时间')),
                ('test_time', models.DateTimeField(blank=True, null=True, verbose_name='测试状态修改时间')),
                ('stock_in_time', models.DateTimeField(blank=True, null=True, verbose_name='入库时间')),
                ('stock_out_time', models.DateTimeField(blank=True, null=True, verbose_name='出库时间')),
                ('inventory_stock', models.IntegerField(choices=[(0, '未入库'), (1, '入库'), (2, '出库')], default=0, verbose_name='库存状态')),
                ('repair', models.IntegerField(choices=[(0, '新品'), (1, '返修品')], default=0, verbose_name='是否返修')),
                ('parent_sn_code', models.CharField(blank=True, help_text='记录该成品所属的父级产品SN码', max_length=255, null=True, verbose_name='父级SN码')),
            ],
            options={
                'verbose_name': '成品',
                'verbose_name_plural': '成品',
                'db_table': 'finish_product',
                'ordering': ['-create_time', '-id'],
            },
        ),
    ]
