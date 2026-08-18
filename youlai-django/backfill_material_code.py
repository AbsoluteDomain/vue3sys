"""
回填 assembly_recipes 表的 material_code 字段

逻辑：
1. 优先使用 component_id / raw_material_id 查找未删除(is_del=0)的产品，取其 material_code
2. 若该 ID 对应产品已删除(is_del=1)，则尝试在未删除的同名产品中找一条作为回退
3. 仍找不到则保持 material_code 为空

用法：python manage.py shell -c "exec(open('backfill_material_code.py').read())"
或：python manage.py runscript backfill_material_code  (若安装了 django-extensions)
"""
import os
import sys

import django


def main():
    # 兼容直接 python backfill_material_code.py 运行
    if not os.environ.get("DJANGO_SECRET_KEY"):
        # 尝试加载 .env
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    django.setup()

    from apps.product.boms.models import AssemblyRecipe
    from apps.product.products.models import Product

    recipes = AssemblyRecipe.objects.all()
    total = recipes.count()
    updated = 0
    skipped = 0
    missing = 0

    for r in recipes:
        pid = r.component_id or r.raw_material_id
        name = r.component_name or r.raw_material_name or ""

        if not pid and not name:
            skipped += 1
            continue

        # 已有 material_code 则跳过
        if r.material_code:
            skipped += 1
            continue

        # 1. 优先按 ID 查未删除产品
        product = None
        if pid:
            product = Product.objects.filter(id=pid, is_del=0).first()

        # 2. ID 对应产品已删除 -> 按名称在未删除产品中回退
        if not product and name:
            product = Product.objects.filter(name=name, is_del=0).first()

        if not product or not product.material_code:
            missing += 1
            print(f"  [SKIP] recipe#{r.id} 未找到可用 material_code (pid={pid}, name={name})")
            continue

        r.material_code = product.material_code
        r.save(update_fields=["material_code"])
        updated += 1
        print(f"  [OK]   recipe#{r.id} -> material_code={r.material_code}")

    print(f"\n总计 {total} 条，更新 {updated} 条，跳过 {skipped} 条，未匹配 {missing} 条")


if __name__ == "__main__":
    main()
