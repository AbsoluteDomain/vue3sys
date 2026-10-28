from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.product.repair.models import Repair
from apps.system.dicts.models import DictionaryItem


class Command(BaseCommand):
    help = "回填返修记录的不良项值(unqualified_values)与返修描述(repair_desc)"

    def handle(self, *args, **options):
        label_value_map = {
            item.label: item.value
            for item in DictionaryItem.objects.filter(
                dict_code="unqualified_status", status=1
            )
        }
        qs = Repair.objects.filter(
            Q(unqualified_values="") & Q(repair_desc="")
        ).exclude(repair_info="")
        total = qs.count()
        updated = 0
        for repair in qs:
            first_line, _, rest = (repair.repair_info or "").strip().partition("\n")
            if first_line.startswith("不良项："):
                labels = [
                    label.strip()
                    for label in first_line[len("不良项："):].split("、")
                    if label.strip()
                ]
                values = [
                    label_value_map[label] for label in labels if label in label_value_map
                ]
                repair.unqualified_values = ",".join(values)
                repair.repair_desc = rest.strip()
            else:
                repair.unqualified_values = ""
                repair.repair_desc = (repair.repair_info or "").strip()
            # 排除 update_time，避免回填操作改变「最后返修时间」的展示
            repair.save(update_fields=["unqualified_values", "repair_desc"])
            updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"共 {total} 条待回填，已回填 {updated} 条")
        )
