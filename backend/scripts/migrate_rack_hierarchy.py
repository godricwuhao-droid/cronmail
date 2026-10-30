#!/usr/bin/env python3
"""
机房层级模型存量迁移脚本（ADR-026：机房→排→机柜→机架）

将存量两级数据（机房→rack）迁移为四级（机房→RackRow→Cabinet→Rack）：
  1. 按机架名首字母归组 → 建排「X排」（如 A01 → A排；已存在则复用）
  2. 每个存量 rack（如 A01, 42U, power_on）→ 建机柜「A01」（power_on 迁移）
     → rack 改挂 cabinet_id，机架名改为「A01-42U」（对齐用户机架命名惯例「编号-容量U」）
  3. 回填 rack.machine_room_id = 排所属机房（保证与 cabinet→row→room 一致）
  4. 设备 rental_record.rack_id 不变（指向同一 rack 行）

特性：
  - 幂等可重复执行（已迁移的 rack 跳过；排/机柜已存在则复用）
  - --dry-run：不执行任何写操作，仅打印迁移计划
  - --drop-power-on：迁移完成后执行 `ALTER TABLE rack DROP COLUMN power_on;`
    （默认不删；该列删除后不可回滚，建议确认迁移结果后再单独执行）
  - 迁移窗口内需停写（避免迁移期间新增/修改 rack）

前置条件（部署顺序，详见 docs/backend/database.md）：
  1. 先执行 DDL 建表（rack_row / cabinet）+ `ALTER TABLE rack ADD COLUMN cabinet_id`
  2. 再执行本脚本
  3. 最后（可选）执行 `ALTER TABLE rack DROP COLUMN power_on;`

连接串来源（优先级从高到低）：
    --url 命令行参数
    环境变量 MIGRATE_RACK_HIERARCHY_URL
    环境变量 DATABASE_URL（兜底）

用法示例：
    # 演练（不写入任何库，推荐先执行）
    python scripts/migrate_rack_hierarchy.py --dry-run

    # 真实迁移
    python scripts/migrate_rack_hierarchy.py

    # 迁移 + 删除 rack.power_on 列（确认迁移结果后）
    python scripts/migrate_rack_hierarchy.py --drop-power-on
"""
import argparse
import os
import sys

from sqlalchemy import MetaData, create_engine, inspect, text

# 确保 backend 目录在 sys.path 中（直接运行本脚本时）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.timezone import local_now  # noqa: E402


def resolve_url(args) -> str:
    url = (
        args.url
        or os.environ.get("MIGRATE_RACK_HIERARCHY_URL")
        or os.environ.get("DATABASE_URL")
    )
    if not url:
        print("错误：未提供数据库连接串（--url / MIGRATE_RACK_HIERARCHY_URL / DATABASE_URL）")
        sys.exit(1)
    return url


def quote_ident(engine, ident: str) -> str:
    """标识符引用（MySQL 用反引号，SQLite 用双引号）"""
    if engine.dialect.name == "mysql":
        return f"`{ident}`"
    return f'"{ident}"'


def table_exists(engine, table: str) -> bool:
    return inspect(engine).has_table(table)


def column_exists(engine, table: str, column: str) -> bool:
    return column in [c["name"] for c in inspect(engine).get_columns(table)]


def migrate(engine, dry_run: bool, drop_power_on: bool) -> int:
    """执行迁移，返回退出码（0 成功，1 失败）"""
    # ---------- 前置检查 ----------
    missing = [t for t in ("rack_row", "cabinet") if not table_exists(engine, t)]
    if missing:
        print(f"错误：缺少表 {missing}，请先执行 ADR-026 DDL 建表（见 docs/backend/database.md）")
        return 1
    if not column_exists(engine, "rack", "cabinet_id"):
        print("错误：rack 表缺少 cabinet_id 列，请先执行 ALTER TABLE rack ADD COLUMN cabinet_id")
        return 1

    has_power_on = column_exists(engine, "rack", "power_on")
    if drop_power_on and not has_power_on:
        print("提示：rack.power_on 列不存在，跳过 DROP（幂等）")

    with engine.begin() as conn:
        meta = MetaData()
        meta.reflect(bind=conn, only=["machine_room", "rack", "rack_row", "cabinet"])
        mr_t, rack_t = meta.tables["machine_room"], meta.tables["rack"]
        row_t, cab_t = meta.tables["rack_row"], meta.tables["cabinet"]

        # ---------- 读取存量数据 ----------
        racks = [
            dict(r) for r in conn.execute(
                text(f"SELECT * FROM {quote_ident(engine, 'rack')} ORDER BY id")
            ).mappings().all()
        ]
        rows = [
            dict(r) for r in conn.execute(
                text(f"SELECT * FROM {quote_ident(engine, 'rack_row')} ORDER BY id")
            ).mappings().all()
        ]
        cabinets = [
            dict(r) for r in conn.execute(
                text(f"SELECT * FROM {quote_ident(engine, 'cabinet')} ORDER BY id")
            ).mappings().all()
        ]
        rooms = {r["id"]: r["name"] for r in conn.execute(
            text(f"SELECT id, name FROM {quote_ident(engine, 'machine_room')}")
        ).mappings().all()}

        # 内存索引：(room_id, name) → row；(row_id, name) → cabinet
        row_index = {(r["machine_room_id"], r["name"]): r for r in rows}
        cab_index = {(c["rack_row_id"], c["name"]): c for c in cabinets}

        pending = [r for r in racks if r["cabinet_id"] is None]
        skipped = [r for r in racks if r["cabinet_id"] is not None]

        print(f"存量机架 {len(racks)} 个：待迁移 {len(pending)}，已迁移（跳过）{len(skipped)}")
        if not pending:
            print("无可迁移数据，迁移完成（幂等）")

        # ---------- 迁移 ----------
        errors = 0
        for rack in pending:
            name = rack["name"] or ""
            room_id = rack["machine_room_id"]
            room_name = rooms.get(room_id, f"#{room_id}")

            # 1. 首字母归排「X排」（机柜名取机架基础名：若已带「-容量U」后缀则剥离，
            #    保证部分失败重跑时幂等）
            suffix = f"-{rack['capacity_u']}U"
            base_name = name[:-len(suffix)] if name.endswith(suffix) else name
            if not base_name:
                print(f"  [错误] rack#{rack['id']} 名称为空，无法归排，跳过")
                errors += 1
                continue
            row_name = f"{base_name[0]}排"
            row = row_index.get((room_id, row_name))
            row_action = "复用" if row else "新建"

            # 2. 机柜 = 机架基础名（同排同名复用）
            cab = cab_index.get((row["id"], base_name)) if row else None
            cab_action = "复用" if cab else "新建"
            power_on = rack.get("power_on") if has_power_on else True
            new_rack_name = f"{base_name}-{rack['capacity_u']}U"

            print(
                f"  rack#{rack['id']} '{name}' ({room_name}) → "
                f"排 '{row_name}' [{row_action}] / 机柜 '{name}' [{cab_action}] / "
                f"机架名 → '{new_rack_name}' / power_on={power_on}"
            )
            if dry_run:
                continue

            # 真实执行
            if row is None:
                row = {"id": None, "machine_room_id": room_id, "name": row_name}
                result = conn.execute(
                    row_t.insert().values(
                        machine_room_id=room_id, name=row_name, created_at=local_now()
                    )
                )
                row["id"] = result.inserted_primary_key[0]
                row_index[(room_id, row_name)] = row

            if cab is None:
                cab = {"id": None, "rack_row_id": row["id"], "name": base_name}
                result = conn.execute(
                    cab_t.insert().values(
                        rack_row_id=row["id"], name=base_name,
                        power_on=bool(power_on) if power_on is not None else True,
                        created_at=local_now(),
                    )
                )
                cab["id"] = result.inserted_primary_key[0]
                cab_index[(row["id"], name)] = cab

            # 3. rack 改挂 cabinet_id + 改名 + 回填 machine_room_id
            conn.execute(
                rack_t.update()
                .where(rack_t.c.id == rack["id"])
                .values(
                    cabinet_id=cab["id"],
                    name=new_rack_name,
                    machine_room_id=room_id,
                )
            )

        if dry_run:
            print("\n[dry-run] 未执行任何写操作")

        # ---------- 4. DROP power_on（可选，最后一步） ----------
        if drop_power_on and not dry_run and has_power_on:
            conn.execute(text(
                f"ALTER TABLE {quote_ident(engine, 'rack')} "
                f"DROP COLUMN {quote_ident(engine, 'power_on')}"
            ))
            print("已执行: ALTER TABLE rack DROP COLUMN power_on")

    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description="机房层级模型存量迁移（ADR-026）")
    parser.add_argument("--url", help="数据库连接串（默认取 MIGRATE_RACK_HIERARCHY_URL / DATABASE_URL）")
    parser.add_argument("--dry-run", action="store_true", help="演练模式：不执行任何写操作")
    parser.add_argument("--drop-power-on", action="store_true",
                        help="迁移完成后执行 ALTER TABLE rack DROP COLUMN power_on（默认不删）")
    args = parser.parse_args()

    url = resolve_url(args)
    engine = create_engine(url)
    print(f"目标库: {url.split('@')[-1]}  模式: {'dry-run' if args.dry_run else '执行'}")
    sys.exit(migrate(engine, dry_run=args.dry_run, drop_power_on=args.drop_power_on))


if __name__ == "__main__":
    main()
