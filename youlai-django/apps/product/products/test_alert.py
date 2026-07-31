import json
from apps.product.products.views import stock_alert_list
from django.test import RequestFactory

factory = RequestFactory()
request = factory.get('/api/v1/product/stock-alert/list/')
response = stock_alert_list(request)
data = json.loads(response.content)
print('预警总数:', data['data']['total'])
print('预警数量:', data['data']['alert_count'])
if data['data']['list']:
    print()
    print('前5条预警记录:')
    for item in data['data']['list'][:5]:
        print(f'  {item["product_name"]}, 库存: {item["current_stock"]}, 预警: {item["is_alert"]}, 类型: {item["alert_type"]}')
