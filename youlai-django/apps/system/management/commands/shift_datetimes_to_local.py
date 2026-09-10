"""一次性命令：把全库 datetime 历史数据从 UTC 字面值整体平移为北京时间字面值。

背景：
    项目由 USE_TZ=True（数据库存 UTC）切换为 USE_TZ=False（数据库直接存北京时间）。
    切换前的历史数据全部是 UTC 字面值，需要整体 +8h，否则页面时间会少 8 小时。

用法：
    # 1) 干跑（默认，只读）：逐列检查 + 检测"疑似已是本地时间"的风险数据
    python manage.py shift_datetimes_to_local

    # 2) 正式执行（平移 8 小时；风险列默认跳过）
    python manage.py shift_datetimes_to_local --execute

    # 3) 干跑确认风险列属于"合理的未来日期"（如日期选择器预录数据）后，
    #    连同风险列一起平移：
    python manage.py shift_datetimes_to_local --execute --force

三重防重复保护：
    1. marker 表 _system_datetime_shift_log：执行成功后留痕，再次执行直接拒绝；
    2. 风险列检测：平移后会产生未来时间的列默认跳过；
    3. 风险列占比 >20% 时判定整库已是本地时间，即使 --force 也中止。

执行时机（重要）：
    必须在【新代码（USE_TZ=False）部署之后、服务对外恢复之前】执行一次。
    执行前请先全库备份。全新部署的库（数据本来就是北京时间）不要执行本命令。
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

MARKER_TABLE = "_system_datetime_shift_log"


class Command(BaseCommand):
    help = "把全库 datetime 历史数据从 UTC 整体平移为北京时间（默认 +8 小时），仅应执行一次"

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true", help="正式执行更新；缺省为只读干跑")
        parser.add_argument("--hours", type=int, default=8, help="平移小时数，默认 8")
        parser.add_argument("--force", action="store_true", help="连风险列（疑似已是本地时间）也强制平移")

    def _discover_columns(self, cursor):
        """返回 [(table, column), ...]，覆盖全库所有 datetime/datetime(6) 列。

        排除 django_migrations：其 applied 仅记录迁移应用时间，不参与业务逻辑，
        保持原始值便于与 Git 历史迁移时间对照。
        排除 marker 表自身。
        """
        cursor.execute(
            """
            SELECT TABLE_NAME, COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND DATA_TYPE IN ('datetime', 'timestamp')
              AND TABLE_NAME NOT IN ('django_migrations', %s)
            ORDER BY TABLE_NAME, ORDINAL_POSITION
            """,
            [MARKER_TABLE],
        )
        return cursor.fetchall()

    def _ensure_marker_table(self, cursor):
        """创建幂等保护表（DDL，MySQL 会隐式提交，须在业务事务外执行）。"""
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{MARKER_TABLE}` (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
                shifted_at DATETIME(6) NOT NULL COMMENT '本次平移执行时间（北京时间）',
                hours INT NOT NULL COMMENT '平移小时数',
                updated_cells INT NOT NULL DEFAULT 0 COMMENT '更新的单元格总数',
                note VARCHAR(255) NOT NULL DEFAULT '' COMMENT '备注'
            ) COMMENT='UTC转北京时间一次性迁移留痕（有记录即禁止重复执行）'
            """
        )

    def _marker_exists(self, cursor):
        cursor.execute(f"SELECT shifted_at, hours FROM `{MARKER_TABLE}` ORDER BY id LIMIT 1")
        return cursor.fetchone()

    def handle(self, *args, **options):
        do_execute = options["execute"]
        hours = options["hours"]
        force = options["force"]

        cursor = connection.cursor()
        self._ensure_marker_table(cursor)
        existing = self._marker_exists(cursor)

        if existing and do_execute:
            raise CommandError(
                f"检测到本库已于 {existing[0]} 执行过 {existing[1]} 小时平移"
                f"（{MARKER_TABLE} 有记录），禁止重复执行。"
                "如已从备份恢复并确认需要重跑，请先手工删除该表后再执行。"
            )

        columns = self._discover_columns(cursor)

        self.stdout.write(self.style.NOTICE(
            f"模式：{'正式执行' if do_execute else '干跑（只读，不修改数据）'}，平移 +{hours} 小时"
        ))
        if existing:
            self.stdout.write(self.style.WARNING(
                f"注意：{MARKER_TABLE} 显示本库已于 {existing[0]} 执行过平移（干跑仅供检查）。"
            ))
        self.stdout.write(f"发现 datetime/timestamp 列：{len(columns)} 个\n")

        risk_cols = []   # 疑似已是本地时间的列（平移后会出现未来时间）
        zero_cols = []   # 全为 NULL / 0 行的列
        ok_cols = []

        # 全量体检
        for table, column in columns:
            col_sql = f"`{table}`.`{column}`"
            cursor.execute(f"SELECT COUNT(*) FROM `{table}` WHERE {col_sql} IS NOT NULL")
            non_null = cursor.fetchone()[0]
            if non_null == 0:
                zero_cols.append((table, column))
                continue

            # 风险检测：UTC 值 +8h 不会超过当前北京时间；
            # 若平移后出现晚于 NOW()+1小时（容差）的值，说明该列本来就是本地时间。
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM `{table}`
                WHERE {col_sql} IS NOT NULL
                  AND DATE_ADD({col_sql}, INTERVAL %s HOUR) > DATE_ADD(NOW(), INTERVAL 1 HOUR)
                """,
                [hours],
            )
            risk_count = cursor.fetchone()[0]

            cursor.execute(f"SELECT MIN({col_sql}), MAX({col_sql}) FROM `{table}`")
            min_v, max_v = cursor.fetchone()

            if risk_count > 0:
                risk_cols.append((table, column, non_null, risk_count, min_v, max_v))
            else:
                ok_cols.append((table, column, non_null, min_v, max_v))

        self.stdout.write(self.style.SUCCESS(f"安全列 {len(ok_cols)} 个："))
        for table, column, non_null, min_v, max_v in ok_cols:
            self.stdout.write(f"  - {table}.{column:<18} 非空 {non_null:>6} 行, 范围 {min_v} ~ {max_v}")

        if zero_cols:
            self.stdout.write(f"\n空列 {len(zero_cols)} 个（无数据，跳过）：")
            for table, column in zero_cols:
                self.stdout.write(f"  - {table}.{column}")

        if risk_cols:
            self.stdout.write(self.style.WARNING(
                f"\n风险列 {len(risk_cols)} 个（平移后会出现未来时间，疑似已经是北京时间）："
            ))
            for table, column, non_null, risk_count, min_v, max_v in risk_cols:
                self.stdout.write(self.style.WARNING(
                    f"  ! {table}.{column:<18} 非空 {non_null} 行，其中 {risk_count} 行平移后超过当前时间，"
                    f"范围 {min_v} ~ {max_v}"
                ))

        if not do_execute:
            self.stdout.write(self.style.NOTICE(
                "\n干跑结束，未修改任何数据。确认无误后追加 --execute 执行；执行前请务必备份数据库。"
            ))
            if risk_cols and not force:
                self.stdout.write(self.style.WARNING(
                    "存在风险列，正式执行时这些列会自动跳过；若已逐列核实是合理的未来日期，加 --force 一并平移。"
                ))
            return

        # 防误跑：若绝大多数列都判风险，说明整库已是本地时间（典型：全新部署库误执行），
        # 即使 --force 也中止。
        non_empty_cols = len(ok_cols) + len(risk_cols)
        risk_ratio = len(risk_cols) / non_empty_cols if non_empty_cols else 0
        if non_empty_cols and risk_ratio > 0.2:
            raise CommandError(
                f"{len(risk_cols)}/{non_empty_cols} 个非空列平移后会出现未来时间（{risk_ratio:.0%}），"
                "整库数据疑似已经是北京时间，已中止。全新部署的库不需要执行本命令。"
            )

        targets = ok_cols if not force else ok_cols + [
            (t, c, nn, mn, mx) for t, c, nn, rc, mn, mx in risk_cols
        ]
        skipped = [f"{t}.{c}" for t, c, *_ in risk_cols] if not force else []

        total_updated = 0
        try:
            with transaction.atomic():
                for table, column, *_ in targets:
                    col_sql = f"`{table}`.`{column}`"
                    cursor.execute(
                        f"UPDATE `{table}` SET {col_sql} = DATE_ADD({col_sql}, INTERVAL %s HOUR) "
                        f"WHERE {col_sql} IS NOT NULL",
                        [hours],
                    )
                    total_updated += cursor.rowcount
                    self.stdout.write(f"  更新 {table}.{column}: {cursor.rowcount} 行")
                # 与数据更新同一事务留痕：更新失败回滚则不留痕，可安全重跑
                cursor.execute(
                    f"INSERT INTO `{MARKER_TABLE}` (shifted_at, hours, updated_cells, note) "
                    f"VALUES (NOW(), %s, %s, %s)",
                    [hours, total_updated, "shift_datetimes_to_local"],
                )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"执行失败，已回滚：{exc}"))
            raise

        self.stdout.write(self.style.SUCCESS(
            f"\n完成：共更新 {total_updated} 个单元格，涉及 {len(targets)} 列。"
        ))
        if skipped:
            self.stdout.write(self.style.WARNING("以下风险列已跳过：" + ", ".join(skipped)))
        self.stdout.write(self.style.WARNING(
            "此命令不可重复执行。请立即恢复服务，并核对页面与数据库工具中的时间是否一致。"
        ))
