from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finish_products', '0006_unqualifieditem'),
    ]

    operations = [
        migrations.CreateModel(
            name='FinishedProductLog',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='主键ID')),
                ('finish_product_id', models.BigIntegerField(blank=True, null=True, verbose_name='成品ID')),
                ('sn_code', models.CharField(blank=True, default='', max_length=255, verbose_name='SN码')),
                ('operation_type', models.CharField(choices=[('create', '新增'), ('update', '修改'), ('rollback', '回退'), ('bind_joint', '绑定关节'), ('stock_change', '库存变更')], max_length=20, verbose_name='操作类型')),
                ('operator_id', models.BigIntegerField(blank=True, null=True, verbose_name='操作人ID')),
                ('operator_name', models.CharField(blank=True, default='', max_length=100, verbose_name='操作人姓名')),
                ('before_data', models.JSONField(blank=True, null=True, verbose_name='变更前数据快照')),
                ('after_data', models.JSONField(blank=True, null=True, verbose_name='变更后数据快照')),
                ('changed_fields', models.JSONField(blank=True, default=list, verbose_name='变更字段列表')),
                ('description', models.CharField(blank=True, default='', max_length=500, verbose_name='操作描述')),
                ('ip', models.CharField(blank=True, max_length=45, null=True, verbose_name='IP地址')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='记录时间')),
            ],
            options={
                'verbose_name': '成品操作记录',
                'verbose_name_plural': '成品操作记录',
                'db_table': 'finished_product_log',
                'ordering': ['-create_time', '-id'],
            },
        ),
    ]
