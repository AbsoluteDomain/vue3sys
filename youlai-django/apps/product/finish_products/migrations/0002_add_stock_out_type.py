from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finish_products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='finishproduct',
            name='stock_out_type',
            field=models.IntegerField(choices=[(1, '外销'), (2, '研发')], default=1, help_text='1:外销, 2:研发', verbose_name='出库类型'),
        ),
    ]
