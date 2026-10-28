from django.db.models import Max

from apps.product.boms.models import BomList

from .models import TestRecord


def create_test_record_from_product(product, test_status, unqualified_values="", test_desc=""):
    """成品测试状态变更为测试合格/测试不良时，写入一条测试记录快照"""
    bom = BomList.objects.filter(id=product.bom_id, is_del=0).first()
    max_test_cnt = (
        TestRecord.objects.filter(
            product_id=product.id,
            sn_code=product.sn_code or "",
        ).aggregate(max_cnt=Max("test_cnt"))["max_cnt"]
        or 0
    )
    return TestRecord.objects.create(
        product_id=product.id,
        sn_code=product.sn_code or "",
        product_model=(bom.bom_model or "") if bom else "",
        unqualified_values=unqualified_values or "",
        test_desc=test_desc or "",
        test_status=test_status,
        test_cnt=max_test_cnt + 1,
    )
