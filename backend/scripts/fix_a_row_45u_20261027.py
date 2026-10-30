# -*- coding: utf-8 -*-
"""雅安机房 A 排存量机架统一 45U（2026-10-27，用户指令「机柜数据都是45U」补齐）：
  - A04-42U：capacity_u 已是 45（ADR-026 迁移遗留名称/容量不一致）→ 仅改名 A04-45U
  - A05-42U ~ A10-42U（6 个）：capacity_u 42→45 + 改名 A0X-45U
  - A01~A03 已是 45U，幂等跳过

安全前提（先查后改）：扩容 42→45 只会让已定位设备区间 [u_position, u_position+u_size-1]
更宽松（ADR-028），不会破坏合法性；脚本仍输出改前已定位设备清单，改后对 A 排全部
已定位设备做区间合法性复查（越界 + 同机架重叠）。

幂等：机架名已是 {柜名}-45U 且 capacity_u=45 的跳过；脚本可重跑。

用法：
    python backend/scripts/fix_a_row_45u_20261027.py --dry-run   # 演练
    python backend/scripts/fix_a_row_45u_20261027.py             # 执行
"""
import argparse
import sys

import pymysql

DSN = dict(host='192.168.180.171', port=30308, user='root',
           password='Qwert7891', database='asset_ops', charset='utf8mb4')
TARGET_U = 45
A_CABINETS = [f'A{i:02d}' for i in range(1, 11)]   # A01~A10


def find_yaan_room(cur) -> int:
    cur.execute("SELECT id FROM machine_room WHERE name LIKE %s", ('%雅安%',))
    rows = cur.fetchall()
    if len(rows) != 1:
        print(f'错误：name 含「雅安」的机房数量为 {len(rows)}（期望 1）：{rows}')
        sys.exit(1)
    return rows[0]['id']


def fetch_a_racks(cur, room_id: int) -> list:
    """雅安机房 A 排 A01~A10 机柜下的机架（含已定位设备数）"""
    in_clause = ', '.join(['%s'] * len(A_CABINETS))
    sql = ('SELECT r.id, r.name, r.capacity_u, r.cabinet_id, c.name AS cab_name, '
           '(SELECT COUNT(*) FROM rental_record d '
           ' WHERE d.rack_id = r.id AND d.u_position IS NOT NULL) AS placed_n '
           'FROM rack_row rr '
           'JOIN cabinet c ON c.rack_row_id = rr.id '
           'JOIN rack r ON r.cabinet_id = c.id '
           'WHERE rr.machine_room_id = %s AND rr.name = %s '
           '  AND c.name IN (' + in_clause + ') '
           'ORDER BY c.name')
    cur.execute(sql, [room_id, 'A排'] + A_CABINETS)
    return cur.fetchall()


def fetch_placed(cur, rack_ids: list) -> list:
    cur.execute('''
        SELECT d.id, d.machine_model, d.rack_id, r.name AS rack_name, r.capacity_u,
               d.u_position, d.u_size
        FROM rental_record d JOIN rack r ON d.rack_id = r.id
        WHERE d.rack_id IN (%s) AND d.u_position IS NOT NULL
        ORDER BY r.name, d.u_position
    ''' % ', '.join(['%s'] * len(rack_ids)), rack_ids)
    return cur.fetchall()


def main():
    parser = argparse.ArgumentParser(description='A 排存量机架统一 45U（扩容+改名）')
    parser.add_argument('--dry-run', action='store_true', help='演练模式：不执行任何写操作')
    args = parser.parse_args()

    conn = pymysql.connect(**DSN)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    mode = 'dry-run（不写入）' if args.dry_run else '执行'
    print('=' * 90)
    print(f'目标库: {DSN["host"]}:{DSN["port"]}/{DSN["database"]}   模式: {mode}')

    # ---------- 0. 定位雅安机房 ----------
    room_id = find_yaan_room(cur)
    print(f'雅安机房: id={room_id}')

    # ---------- 1. 改前清单 ----------
    racks = fetch_a_racks(cur, room_id)
    if len(racks) != 10:
        print(f'错误：A 排 A01~A10 机架数量为 {len(racks)}（期望 10）')
        for r in racks:
            print(f'  {r["cab_name"]} -> {r["name"]} (capacity_u={r["capacity_u"]})')
        sys.exit(1)

    print()
    print('=' * 90)
    print('【改前清单】A 排 A01~A10 机架')
    print(f"{'cab':<6}{'rack_id':>8}  {'name':<12}{'cap':>4}  {'已定位':>6}  计划")
    plan = []   # (rack_id, old_name, old_cap, new_name, new_cap)
    for r in racks:
        new_name = f'{r["cab_name"]}-{TARGET_U}U'
        need = (r['name'] != new_name) or (r['capacity_u'] != TARGET_U)
        if need:
            plan.append((r['id'], r['name'], r['capacity_u'], new_name, TARGET_U))
            action = f'改名 {new_name}' + ('' if r['capacity_u'] == TARGET_U else f' + capacity {r["capacity_u"]}→{TARGET_U}')
        else:
            action = '跳过（已是 45U）'
        print(f"{r['cab_name']:<6}{r['id']:>8}  {r['name']:<12}{r['capacity_u']:>4}  "
              f"{r['placed_n']:>6}  {action}")

    # 改前已定位设备（安全前提：扩容只会更宽松；列出 43~45 区间设备确认）
    rack_ids = [r['id'] for r in racks]
    placed = fetch_placed(cur, rack_ids)
    print()
    print('=' * 90)
    print(f'【改前已定位设备】A 排共 {len(placed)} 台')
    for p in placed:
        top = p['u_position'] + p['u_size'] - 1
        flag = ''
        if p['capacity_u'] == 42 and top > 42:
            flag = '  ← 原 42U 架 43~45 区间（扩容后变合法）'
        elif top > p['capacity_u']:
            flag = '  ← 越界（异常）'
        print(f"  {p['rack_name']:<12}(cap={p['capacity_u']}) {p['id']} {str(p['machine_model']):<12}"
              f"区间[{p['u_position']},{top}] u_size={p['u_size']}{flag}")

    # ---------- 2. 执行 UPDATE ----------
    print()
    print('=' * 90)
    print(f'【执行 UPDATE】{len(plan)} 条')
    if not plan:
        print('  （无变化，幂等跳过）')
    if not args.dry_run:
        for rid, old_name, old_cap, new_name, new_cap in plan:
            if old_name == new_name and old_cap == new_cap:
                continue
            if old_cap != new_cap:
                cur.execute('UPDATE rack SET name=%s, capacity_u=%s WHERE id=%s',
                            (new_name, new_cap, rid))
                print(f"  UPDATE rack SET name='{new_name}', capacity_u={new_cap} WHERE id={rid}  (rows={cur.rowcount})")
            else:
                cur.execute('UPDATE rack SET name=%s WHERE id=%s', (new_name, rid))
                print(f"  UPDATE rack SET name='{new_name}' WHERE id={rid}  (rows={cur.rowcount})")
        conn.commit()
        print('  已提交。')
    else:
        for rid, old_name, old_cap, new_name, new_cap in plan:
            print(f"  [dry-run] rack id={rid}: '{old_name}'(cap={old_cap}) -> '{new_name}'(cap={new_cap})")
        print('  [dry-run] 未执行任何写操作')

    # ---------- 3. 改后全量复查 ----------
    print()
    print('=' * 90)
    print('【改后复查】A 排机架命名/容量 + 已定位设备区间合法性')
    racks_after = fetch_a_racks(cur, room_id)
    ok = True
    for r in racks_after:
        expect = f'{r["cab_name"]}-{TARGET_U}U'
        good = r['name'] == expect and r['capacity_u'] == TARGET_U
        ok = ok and good
        print(f"  [{'✔' if good else '✘'}] {r['cab_name']} -> {r['name']} (capacity_u={r['capacity_u']})")

    placed_after = fetch_placed(cur, [r['id'] for r in racks_after])
    by_rack = {}
    for p in placed_after:
        by_rack.setdefault(p['rack_name'], []).append(p)
    for rack_name, devs in sorted(by_rack.items()):
        cap = devs[0]['capacity_u']
        for p in devs:
            lo, hi = p['u_position'], p['u_position'] + p['u_size'] - 1
            bounds_ok = lo >= 1 and hi <= cap
            inter = [o['id'] for o in devs if o['id'] != p['id']
                     and lo <= o['u_position'] + o['u_size'] - 1
                     and o['u_position'] <= hi]
            status = '✔' if (bounds_ok and not inter) else '✘'
            ok = ok and bounds_ok and not inter
            print(f"  [{status}] {rack_name}({cap}U) {p['id']} {str(p['machine_model']):<12}"
                  f"区间[{lo},{hi}] 冲突={inter or '无'}")
    print()
    print('复查结果：', '全部通过 ✔' if ok else '存在异常 ✘')
    conn.close()
    print('完成。')


if __name__ == '__main__':
    main()
