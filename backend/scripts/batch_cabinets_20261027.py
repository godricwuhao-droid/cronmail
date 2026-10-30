# -*- coding: utf-8 -*-
"""批量数据录入（2026-10-27，用户直接指令，已授权改生产数据）：
  1. 全部设备归属雅安机房：
     UPDATE rental_record SET machine_room_id = {雅安机房id} WHERE machine_room_id IS NULL
     （雅安机房按 name LIKE '%雅安%' 查 machine_room 表，以实际查询为准）
  2. 批量录入机柜 + 机架（全部 45U，cabinet.power_on=1 默认通电），
     层级：机房 → 排(rack_row) → 机柜(cabinet) → 机架(rack)，
     命名沿用 ADR-026 迁移脚本惯例（backend/scripts/migrate_rack_hierarchy.py）：
       - 排：按机柜名前缀字母建「X排」（已存在则复用）
       - 机柜：E08~E11 / F01~F09 / C01~C08（共 21 个，power_on=1）
       - 机架：每柜 1 个，名「{柜名}-45U」，capacity_u=45，
         rack.machine_room_id 同步填机房 id（查询层归属约定，ADR-026）
       - A排 A01~A10 已存在（21 台设备迁移时已建），仅检查确认，不重复建

幂等：按 (排: machine_room_id+name) / (机柜: rack_row_id+name) /
      (机架: cabinet_id+name) 查重，已存在跳过；脚本可重跑。

用法：
    python backend/scripts/batch_cabinets_20261027.py --dry-run   # 演练
    python backend/scripts/batch_cabinets_20261027.py             # 执行
"""
import argparse
import sys
from datetime import datetime

import pymysql

DSN = dict(host='192.168.180.171', port=30308, user='root',
           password='Qwert7891', database='asset_ops', charset='utf8mb4')

# 新机柜清单（排 → 机柜名列表）
NEW_CABINETS = {
    'E排': ['E08', 'E09', 'E10', 'E11'],
    'F排': [f'F{i:02d}' for i in range(1, 10)],   # F01~F09
    'C排': [f'C{i:02d}' for i in range(1, 9)],    # C01~C08
}
# 已存在仅检查（不建）
CHECK_ONLY = {'A排': [f'A{i:02d}' for i in range(1, 11)]}  # A01~A10
RACK_U = 45


def find_yaan_room(cur) -> dict:
    cur.execute("SELECT id, name, code FROM machine_room WHERE name LIKE %s", ('%雅安%',))
    rows = cur.fetchall()
    if len(rows) != 1:
        print(f"错误：name 含「雅安」的机房数量为 {len(rows)}（期望 1）：{rows}")
        sys.exit(1)
    return rows[0]


def main():
    parser = argparse.ArgumentParser(description='批量录入机柜/机架 + 设备归属雅安机房')
    parser.add_argument('--dry-run', action='store_true', help='演练模式：不执行任何写操作')
    args = parser.parse_args()

    conn = pymysql.connect(**DSN)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    mode = 'dry-run（不写入）' if args.dry_run else '执行'
    print('=' * 90)
    print(f'目标库: {DSN["host"]}:{DSN["port"]}/{DSN["database"]}   模式: {mode}')

    # ---------- 0. 定位雅安机房 ----------
    room = find_yaan_room(cur)
    print(f'雅安机房: id={room["id"]}  name={room["name"]}  code={room["code"]}')

    # ---------- 1. 设备归属 ----------
    cur.execute('SELECT COUNT(*) AS n FROM rental_record WHERE machine_room_id IS NULL')
    null_count = cur.fetchone()['n']
    print()
    print('=' * 90)
    print(f'【1. 设备归属】改前 rental_record.machine_room_id IS NULL 台数: {null_count}')
    if null_count and not args.dry_run:
        cur.execute('UPDATE rental_record SET machine_room_id=%s WHERE machine_room_id IS NULL',
                    (room['id'],))
        print(f'  UPDATE rental_record SET machine_room_id={room["id"]} '
              f'WHERE machine_room_id IS NULL  (rows={cur.rowcount})')
    elif null_count:
        print(f'  [dry-run] 将执行 UPDATE rental_record SET machine_room_id={room["id"]} '
              f'WHERE machine_room_id IS NULL（{null_count} 台）')

    # ---------- 2. 排/机柜/机架 查重与计划 ----------
    cur.execute('SELECT id, machine_room_id, name FROM rack_row ORDER BY id')
    rows = cur.fetchall()
    row_index = {(r['machine_room_id'], r['name']): r for r in rows}

    cur.execute('SELECT id, rack_row_id, name FROM cabinet ORDER BY id')
    cabs = cur.fetchall()
    cab_index = {(c['rack_row_id'], c['name']): c for c in cabs}

    cur.execute('SELECT id, cabinet_id, name, capacity_u FROM rack ORDER BY id')
    racks = cur.fetchall()
    rack_index = {(r['cabinet_id'], r['name']): r for r in racks}

    plan = []   # (kind, name, action, detail)
    for row_name, cab_names in NEW_CABINETS.items():
        row = row_index.get((room['id'], row_name))
        row_action = '复用' if row else '新建'
        if not row:
            plan.append(('排', row_name, '新建', f'rack_row(machine_room_id={room["id"]}, name={row_name})'))
        for cab_name in cab_names:
            cab = cab_index.get((row['id'], cab_name)) if row else None
            cab_action = '复用' if cab else '新建'
            if not cab:
                plan.append(('机柜', cab_name, '新建',
                             f'cabinet(rack_row_id={row["id"] if row else "新建"}, '
                             f'name={cab_name}, power_on=1)'))
            rack_name = f'{cab_name}-{RACK_U}U'
            rack = rack_index.get((cab['id'], rack_name)) if cab else None
            if not rack:
                plan.append(('机架', rack_name, '新建',
                             f'rack(cabinet_id={cab["id"] if cab else "新建"}, name={rack_name}, '
                             f'capacity_u={RACK_U}, machine_room_id={room["id"]})'))

    # A排检查（不建）
    a_row = row_index.get((room['id'], 'A排'))
    a_missing = []
    if not a_row:
        a_missing = list(CHECK_ONLY['A排'])
    else:
        for cab_name in CHECK_ONLY['A排']:
            if (a_row['id'], cab_name) not in cab_index:
                a_missing.append(cab_name)

    print()
    print('=' * 90)
    print(f'【2. 机柜录入】will-change 清单（新建 {len(plan)} 条）')
    for kind, name, action, detail in plan:
        print(f'  [{kind}] {name}  {action}: {detail}')
    if a_row is None:
        print(f'  [检查] A排 不存在，缺失机柜: {a_missing}')
    else:
        print(f'  [检查] A排(id={a_row["id"]}) 机柜 A01~A10: '
              f'{"全部存在 ✔" if not a_missing else f"缺失 {a_missing} ✘"}')

    # ---------- 3. 执行 ----------
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    created = {'排': [], '机柜': [], '机架': []}
    if not args.dry_run:
        print()
        print('=' * 90)
        print('【执行写入】')
        for row_name, cab_names in NEW_CABINETS.items():
            row = row_index.get((room['id'], row_name))
            if row is None:
                cur.execute('INSERT INTO rack_row (machine_room_id, name, created_at) VALUES (%s,%s,%s)',
                            (room['id'], row_name, now))
                row = {'id': cur.lastrowid, 'machine_room_id': room['id'], 'name': row_name}
                row_index[(room['id'], row_name)] = row
                created['排'].append(row_name)
                print(f"  INSERT rack_row '{row_name}' -> id={row['id']}")
            for cab_name in cab_names:
                cab = cab_index.get((row['id'], cab_name))
                if cab is None:
                    cur.execute(
                        'INSERT INTO cabinet (rack_row_id, name, power_on, created_at) VALUES (%s,%s,1,%s)',
                        (row['id'], cab_name, now))
                    cab = {'id': cur.lastrowid, 'rack_row_id': row['id'], 'name': cab_name}
                    cab_index[(row['id'], cab_name)] = cab
                    created['机柜'].append(cab_name)
                    print(f"  INSERT cabinet '{cab_name}' -> id={cab['id']} (power_on=1)")
                rack_name = f'{cab_name}-{RACK_U}U'
                rack = rack_index.get((cab['id'], rack_name))
                if rack is None:
                    cur.execute(
                        'INSERT INTO rack (machine_room_id, cabinet_id, name, capacity_u, created_at) '
                        'VALUES (%s,%s,%s,%s,%s)',
                        (room['id'], cab['id'], rack_name, RACK_U, now))
                    created['机架'].append(rack_name)
                    print(f"  INSERT rack '{rack_name}' -> id={cur.lastrowid} (capacity_u={RACK_U})")
        conn.commit()
        print(f'  已提交: 排 {len(created["排"])} / 机柜 {len(created["机柜"])} / 机架 {len(created["机架"])}')
    else:
        print()
        print('[dry-run] 未执行任何写操作')

    # ---------- 4. 改后复查 ----------
    print()
    print('=' * 90)
    print('【改后复查】')
    cur.execute('SELECT COUNT(*) AS n FROM rental_record WHERE machine_room_id IS NULL')
    null_after = cur.fetchone()['n']
    cur.execute('SELECT machine_room_id, COUNT(*) AS n FROM rental_record GROUP BY machine_room_id')
    dist = cur.fetchall()
    print(f'  rental_record.machine_room_id IS NULL: {null_after} 台（目标 0）')
    for d in dist:
        cur.execute('SELECT name FROM machine_room WHERE id=%s', (d['machine_room_id'],))
        r = cur.fetchone()
        print(f'    machine_room_id={d["machine_room_id"]} ({r["name"] if r else "?"}): {d["n"]} 台')

    cur.execute('''
        SELECT rr.name AS row_name, c.name AS cab_name, r.name AS rack_name, r.capacity_u
        FROM rack_row rr
        JOIN cabinet c ON c.rack_row_id = rr.id
        LEFT JOIN rack r ON r.cabinet_id = c.id
        WHERE rr.machine_room_id = %s
        ORDER BY rr.name, c.name
    ''', (room['id'],))
    hierarchy = cur.fetchall()
    by_row = {}
    for h in hierarchy:
        by_row.setdefault(h['row_name'], []).append(h)
    print(f'  {room["name"]} 层级复查（排→柜→架）:')
    for rn in sorted(by_row):
        items = by_row[rn]
        bad = [i for i in items
               if i['rack_name'] is None or i['rack_name'] != f'{i["cab_name"]}-{RACK_U}U'
               or i['capacity_u'] != RACK_U]
        status = '✔' if not bad else '✘'
        print(f'    {rn}: {len(items)} 柜  {status}')
        for i in items:
            flag = '' if (i['rack_name'] == f'{i["cab_name"]}-{RACK_U}U' and i['capacity_u'] == RACK_U) else '  ← 异常'
            print(f'      {i["cab_name"]:>5} -> {i["rack_name"]} (capacity_u={i["capacity_u"]}){flag}')

    conn.close()
    print()
    print('完成。')


if __name__ == '__main__':
    main()
