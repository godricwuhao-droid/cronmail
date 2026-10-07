#!/usr/bin/env python3
"""
资产运营管理平台数据迁移脚本（ADR-019 平台拆分）

从源库 cronmail 复制资产侧表数据到独立库 asset_ops。

- 幂等可重跑：按表 DELETE（按过滤范围）+ INSERT（按主键），重复执行结果一致
- 只读源库：对源库仅执行 SELECT
- --dry-run：不执行任何写操作，仅打印迁移计划与行数核对
- 排除一切 project_* 表、satellite_data_contract、compute_service_contract、
  contract_service_line 表
- 过滤规则：
    attachment / attachment_status / attachment_category 仅复制
    contract_type='compute_leasing'（算力租赁合同）相关行
    attachment_item 仅复制 compute_leasing 分类下的子项
    system_config 仅复制非 llm_* / 非 project 相关键

连接串来源（优先级从高到低）：
    --source-url / --target-url 命令行参数
    环境变量 MIGRATE_SOURCE_URL / MIGRATE_TARGET_URL
    环境变量 DATABASE_URL（作为兜底默认值）

用法示例：
    # 演练（不写入任何库，推荐先执行）
    python scripts/migrate_to_asset_ops.py \
        --source-url "mysql+pymysql://root:pass@host:3306/cronmail" \
        --target-url "mysql+pymysql://root:pass@host:3306/asset_ops" \
        --dry-run

    # 真实迁移（需用户确认后执行；目标库须已存在且已 create_all 建表）
    python scripts/migrate_to_asset_ops.py \
        --source-url "..." --target-url "..."
"""
import argparse
import os
import sys

from sqlalchemy import MetaData, create_engine, func, select, text

# 确保 backend 目录在 sys.path 中（直接运行本脚本时）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# 迁移表清单（按外键依赖顺序排列）
# filter_desc: 人类可读的过滤条件说明
# 无过滤 = 全表复制
# ============================================================
MIGRATE_TABLES = [
    # (表名, 过滤说明)
    ("customer", None),
    ("contact", None),
    ("rental_record", None),
    ("rental_contact", None),
    ("contract", None),
    ("contract_rental", None),
    ("contract_contact", None),
    ("change_log", None),
    ("email_template", None),
    ("email_log", None),
    ("smtp_config", None),
    ("dingtalk_config", None),
    ("system_config", "key 非 llm_* 且非 project 相关"),
    ("attachment_category", "contract_type='compute_leasing'"),
    ("attachment_item", "category 属 compute_leasing 分类"),
    ("attachment", "contract_type='compute_leasing'"),
    ("attachment_status", "contract_type='compute_leasing'"),
]

# 明确排除的表（项目/卫星/算力服务侧），用于报告展示
EXCLUDED_TABLES = [
    "project_type",
    "project_contract",
    "project_service_line",
    "project_contract_payment",
    "satellite_data_contract",
    "compute_service_contract",
    "contract_service_line",
    "alembic_version",
]

# 注意：必须为 1（逐行插入）。
# 原因：contract.renewed_from_id 为自引用外键，pymysql executemany 会把
# 多行合并为单条 INSERT ... VALUES (...),(...)，MySQL 不保证行级提交顺序，
# 会触发 1452 外键错误。逐行插入保证按源库读取顺序（父行先于子行）落库。
BATCH_SIZE = 1


def count_rows(conn, table, where=None) -> int:
    stmt = select(func.count()).select_from(table)
    if where is not None:
        stmt = stmt.where(where)
    return int(conn.execute(stmt).scalar_one())


def fetch_rows(conn, table_name: str, cols: list[str], where=None):
    """原生 SELECT 读取行（只读），返回 dict 列表。
    使用原生 SQL 而非 ORM 表对象，目的是完整保留 JSON 列的原始存储形式
    （JSON 字面量 null 与 SQL NULL 均原样保留），配合 insert_rows 的原生
    INSERT 实现字节级保真迁移。列集合按目标库表结构选取。"""
    col_sql = ", ".join(f"`{c}`" for c in cols)
    if where is not None:
        compiled = where.compile(compile_kwargs={"literal_binds": False})
        stmt = text(f"SELECT {col_sql} FROM `{table_name}` WHERE {compiled}")
        params = dict(compiled.params)
    else:
        stmt = text(f"SELECT {col_sql} FROM `{table_name}`")
        params = {}
    return [dict(r) for r in conn.execute(stmt, params).mappings().all()]


def delete_target_rows(conn, table, where=None) -> int:
    stmt = table.delete()
    if where is not None:
        stmt = stmt.where(where)
    result = conn.execute(stmt)
    return result.rowcount


def insert_rows(conn, table_name: str, rows: list[dict]) -> int:
    """原生参数化 INSERT。与 fetch_rows 的原生 SELECT 配对：
    JSON 列保持原始文本、SQL NULL 保持 NULL，实现字节级保真，
    避免 ORM JSON 绑定层把 None 序列化成 JSON 字面量 'null'。"""
    if not rows:
        return 0
    cols = list(rows[0].keys())
    col_sql = ", ".join(f"`{c}`" for c in cols)
    ph_sql = ", ".join(f":{c}" for c in cols)
    sql = text(f"INSERT INTO `{table_name}` ({col_sql}) VALUES ({ph_sql})")
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        total += conn.execute(sql, batch).rowcount
    return total


def main() -> int:
    parser = argparse.ArgumentParser(
        description="cronmail → asset_ops 数据迁移（幂等，支持 --dry-run）"
    )
    parser.add_argument(
        "--source-url",
        default=os.environ.get("MIGRATE_SOURCE_URL") or os.environ.get("DATABASE_URL"),
        help="源库连接串（默认: 环境变量 MIGRATE_SOURCE_URL 或 DATABASE_URL）",
    )
    parser.add_argument(
        "--target-url",
        default=os.environ.get("MIGRATE_TARGET_URL") or os.environ.get("DATABASE_URL"),
        help="目标库连接串（默认: 环境变量 MIGRATE_TARGET_URL 或 DATABASE_URL）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="演练模式：不执行任何写操作，仅打印迁移计划与行数核对",
    )
    args = parser.parse_args()

    if not args.source_url or not args.target_url:
        print("错误: 未提供源库/目标库连接串（--source-url/--target-url 或环境变量）")
        return 2

    mode = "DRY-RUN（不写入）" if args.dry_run else "真实迁移"
    print("=" * 72)
    print(f"资产运营管理平台数据迁移  [{mode}]")
    print(f"源库:   {args.source_url.split('@')[-1]}")
    print(f"目标库: {args.target_url.split('@')[-1]}")
    print("=" * 72)

    # ---- 源库引擎（只读使用）----
    src_engine = create_engine(args.source_url, pool_pre_ping=True)
    meta = MetaData()
    with src_engine.connect() as conn:
        meta.reflect(bind=conn, only=[t for t, _ in MIGRATE_TABLES])

    missing = [t for t, _ in MIGRATE_TABLES if t not in meta.tables]
    if missing:
        print(f"错误: 源库缺少表: {missing}")
        return 2

    def get_where(table_name: str, md: MetaData):
        """按指定库的元数据构造过滤条件（源/目标库列结构可能不同）"""
        if table_name == "system_config":
            t = md.tables[table_name]
            return ~t.c.key.like("llm%") & ~t.c.key.like("%project%")
        if table_name in ("attachment", "attachment_status", "attachment_category"):
            return md.tables[table_name].c.contract_type == "compute_leasing"
        if table_name == "attachment_item":
            cat = md.tables["attachment_category"]
            return md.tables["attachment_item"].c.category_id.in_(
                select(cat.c.id).where(cat.c.contract_type == "compute_leasing")
            )
        return None

    # ---- 目标库引擎（dry-run 下仅尝试只读计数，失败不致命）----
    tgt_engine = create_engine(args.target_url, pool_pre_ping=True)
    tgt_available = True
    try:
        with tgt_engine.connect() as conn:
            conn.execute(select(func.count()).select_from(meta.tables["customer"]))
    except Exception as e:
        tgt_available = False
        if args.dry_run:
            print(f"注意: 目标库不可达或尚未建库（{type(e).__name__}），dry-run 下目标行数记为 N/A")
        else:
            print(f"错误: 目标库不可用（{type(e).__name__}: {e.orig if hasattr(e, 'orig') else e}）")
            print("提示: 真实迁移前须先创建 asset_ops 库并启动一次应用完成 create_all 建表")
            return 2

    # ---- 目标库元数据：写入（DELETE/INSERT）必须用目标库表结构，
    #      因为源库可能残留目标库已裁剪掉的列（如 attachment_category.project_type）----
    tgt_meta = MetaData()
    if tgt_available:
        with tgt_engine.connect() as conn:
            tgt_meta.reflect(bind=conn, only=[t for t, _ in MIGRATE_TABLES])
        tgt_missing = [t for t, _ in MIGRATE_TABLES if t not in tgt_meta.tables]
        if tgt_missing:
            print(f"错误: 目标库缺少表: {tgt_missing}")
            return 2

    report = []  # (table, filter_desc, src_count, tgt_count, action)

    tgt_conn = tgt_engine.connect() if tgt_available else None
    try:
        if tgt_conn is not None and not args.dry_run:
            # 迁移期间临时关闭目标库外键检查：contract.renewed_from_id 为自引用外键，
            # 且 SELECT 无排序保证父行先于子行读取，逐行插入仍可能违反 1452。
            # 仅影响目标库（asset_ops），提交后恢复。
            from sqlalchemy import text
            tgt_conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        with src_engine.connect() as src_conn:
            for table_name, filter_desc in MIGRATE_TABLES:
                # 真实模式统一使用目标库表对象（列集合/列类型与写入端一致）；
                # dry-run 且目标库不可用时退回源库表对象
                if tgt_conn is not None:
                    table = tgt_meta.tables[table_name]
                    where = get_where(table_name, tgt_meta)
                else:
                    table = meta.tables[table_name]
                    where = get_where(table_name, meta)

                src_count = count_rows(src_conn, table, where)

                tgt_count = None
                if tgt_conn is not None:
                    try:
                        tgt_count = count_rows(tgt_conn, table, where)
                    except Exception:
                        tgt_count = None

                if args.dry_run:
                    action = f"计划: DELETE（过滤范围内）后 INSERT {src_count} 行"
                else:
                    deleted = delete_target_rows(tgt_conn, table, where)
                    tgt_cols = [c.name for c in table.columns]
                    rows = fetch_rows(src_conn, table.name, tgt_cols, where)
                    inserted = insert_rows(tgt_conn, table.name, rows)
                    tgt_count = count_rows(tgt_conn, table, where)
                    action = f"DELETE {deleted} 行, INSERT {inserted} 行"

                report.append((table_name, filter_desc, src_count, tgt_count, action))

            # 真实模式：全部表处理完后统一提交
            if not args.dry_run:
                tgt_conn.commit()
                from sqlalchemy import text
                tgt_conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                tgt_conn.commit()
                print("\n[OK] 所有表迁移完成，已提交事务（外键检查已恢复）")
    finally:
        if tgt_conn is not None:
            tgt_conn.close()

    # ---- 逐表行数核对报告 ----
    print()
    print("=" * 72)
    print("逐表行数核对报告（源 / 目标 / 差异）")
    print("=" * 72)
    header = f"{'表名':<22}{'过滤条件':<34}{'源行数':>8}{'目标行数':>10}  操作"
    print(header)
    print("-" * 72)
    all_ok = True
    for table_name, filter_desc, src_count, tgt_count, action in report:
        fd = filter_desc or "-"
        if tgt_count is None:
            tgt_str = "N/A"
            diff_str = ""
        else:
            tgt_str = str(tgt_count)
            diff = src_count - tgt_count
            if diff != 0:
                all_ok = False
            diff_str = f"  (差异 {diff:+d})"
        print(f"{table_name:<22}{fd:<34}{src_count:>8}{tgt_str:>10}  {action}{diff_str}")
    print("-" * 72)
    print(f"排除表（不迁移）: {', '.join(EXCLUDED_TABLES)}")

    if args.dry_run:
        print("\n[DRY-RUN] 未对任何库执行写操作。")
        print("真实迁移命令（需用户确认后执行）:")
        print(f"  python scripts/migrate_to_asset_ops.py --source-url '<src>' --target-url '<tgt>'")
    elif all_ok:
        print("\n[OK] 源/目标行数全部一致")
    else:
        print("\n[WARN] 存在行数差异，请人工核对")
        return 1

    src_engine.dispose()
    tgt_engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
