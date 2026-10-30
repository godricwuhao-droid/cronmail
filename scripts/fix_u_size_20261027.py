# -*- coding: utf-8 -*-
"""批量修改设备 u_size：4090/8468→4，6133→2，并保证已定位设备区间合法性。
ADR-028：区间 [u_position, u_position + u_size - 1]，须 ≤ capacity_u 且同机架不重叠。
"""
import pymysql

DSN = dict(host='192.168.180.171', port=30308, user='root',
           password='Qwert7891', database='asset_ops', charset='utf8mb4')

RULES = [('%4090%', 4), ('%8468%', 4), ('%6133%', 2)]


def main():
    conn = pymysql.connect(**DSN)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # ---------- 1. 改前清单 ----------
    like = ' OR '.join(['d.machine_model LIKE %s'] * len(RULES))
    cur.execute(f'''
        SELECT d.id, d.machine_model, d.rack_id, r.name AS rack_name,
               r.capacity_u, d.u_position, d.u_size
        FROM rental_record d LEFT JOIN rack r ON d.rack_id = r.id
        WHERE {like}
        ORDER BY d.rack_id, d.u_position, d.id
    ''', [p for p, _ in RULES])
    targets = cur.fetchall()

    print('=' * 90)
    print('【改前清单】')
    print(f"{'id':<38}{'model':<12}{'rack':<12}{'cap':>4}{'pos':>5}{'size':>5}  -> new_size")
    for t in targets:
        new_size = next(s for p, s in RULES if t['machine_model'] and p.strip('%') in t['machine_model'])
        t['new_size'] = new_size
        print(f"{t['id']:<38}{t['machine_model']:<12}{str(t['rack_name']):<12}"
              f"{str(t['capacity_u']):>4}{str(t['u_position']):>5}{t['u_size']:>5}  -> {new_size}")

    # ---------- 2. 计算 will-change（含已定位设备的 u_position 调整） ----------
    # 每个机架的已定位设备占用（改后视角：目标设备用新 size/新 pos，其他设备不变）
    changes = []  # (id, field, old, new, reason)
    for t in targets:
        if t['u_size'] == t['new_size'] and t['u_position'] is None:
            continue
        if t['u_position'] is None:
            if t['u_size'] != t['new_size']:
                changes.append((t['id'], 'u_size', t['u_size'], t['new_size'], '未定位，直接改 u_size'))
            continue
        # 已定位：计算新 u_position
        cap = t['capacity_u']
        old_top = min(t['u_position'] + t['u_size'] - 1, cap)
        new_pos = old_top - t['new_size'] + 1
        # 收集同机架其他已定位设备区间（排除自身）
        cur.execute('''
            SELECT d.id, d.u_position, d.u_size, r.name
            FROM rental_record d JOIN rack r ON d.rack_id = r.id
            WHERE d.rack_id = %s AND d.u_position IS NOT NULL AND d.id <> %s
        ''', (t['rack_id'], t['id']))
        others = [(o['u_position'], o['u_position'] + o['u_size'] - 1) for o in cur.fetchall()]

        def overlaps(pos):
            lo, hi = pos, pos + t['new_size'] - 1
            return hi > cap or any(lo <= ohi and olo <= hi for olo, ohi in others)

        reason = []
        if t['u_position'] + t['new_size'] - 1 > cap:
            reason.append(f"越界(原区间上端{t['u_position']+t['u_size']-1}，新size={t['new_size']}需下移)")
        while new_pos >= 1 and overlaps(new_pos):
            new_pos -= 1
        if new_pos < 1:
            # 找不到合法位置：保留现状（u_position 不动），仅改 u_size
            print(f"!! {t['id']} ({t['machine_model']}, {t['rack_name']}) 无合法位置，u_position 保持 {t['u_position']} 不变")
            if t['u_size'] != t['new_size']:
                changes.append((t['id'], 'u_size', t['u_size'], t['new_size'], '无合法位置，仅改 u_size'))
        else:
            if new_pos != t['u_position']:
                reason.append(f"新底部={new_pos}（原上端{old_top}-新size+1）")
            if t['u_size'] != t['new_size']:
                changes.append((t['id'], 'u_size', t['u_size'], t['new_size'],
                                f"型号规则；{';'.join(reason) or '位置不变'}"))
            if new_pos != t['u_position']:
                changes.append((t['id'], 'u_position', t['u_position'], new_pos,
                                f"{'；'.join(reason)}"))

    print()
    print('=' * 90)
    print('【will-change 清单】')
    for cid, field, old, new, why in changes:
        print(f"  {cid}  {field}: {old} -> {new}   ({why})")
    if not changes:
        print('  （无变化）')

    # ---------- 3. 执行 UPDATE ----------
    print()
    print('=' * 90)
    print('【执行 UPDATE】')
    for cid, field, old, new, why in changes:
        cur.execute(f'UPDATE rental_record SET {field}=%s WHERE id=%s', (new, cid))
        print(f"  UPDATE rental_record SET {field}={new} WHERE id={cid}  (rows={cur.rowcount})")
    conn.commit()

    # ---------- 4. 改后复查：全部设备区间合法性 ----------
    print()
    print('=' * 90)
    print('【改后复查】全部已定位设备区间校验')
    cur.execute('''
        SELECT d.id, d.machine_model, r.name AS rack_name, r.capacity_u, d.u_position, d.u_size
        FROM rental_record d JOIN rack r ON d.rack_id = r.id
        WHERE d.u_position IS NOT NULL
        ORDER BY r.name, d.u_position
    ''')
    placed = cur.fetchall()
    ok = True
    by_rack = {}
    for p in placed:
        by_rack.setdefault(p['rack_name'], []).append(p)
    for rack, devs in by_rack.items():
        cap = devs[0]['capacity_u']
        for p in devs:
            lo, hi = p['u_position'], p['u_position'] + p['u_size'] - 1
            bounds_ok = lo >= 1 and hi <= cap
            inter = [o['id'] for o in devs if o['id'] != p['id']
                     and lo <= o['u_position'] + o['u_size'] - 1
                     and o['u_position'] <= hi]
            status = 'OK' if (bounds_ok and not inter) else 'FAIL'
            if status == 'FAIL':
                ok = False
            print(f"  [{status}] {p['rack_name']}({cap}U) {p['id']} {p['machine_model']:<10}"
                  f"区间[{lo},{hi}] 邻居冲突={inter or '无'}")
    print()
    print('校验结果：', '全部通过 ✔' if ok else '存在不合法区间 ✘')

    # 三类设备改后汇总
    cur.execute(f'''
        SELECT d.machine_model, d.u_size, COUNT(*) AS n
        FROM rental_record d WHERE {like}
        GROUP BY d.machine_model, d.u_size ORDER BY d.machine_model, d.u_size
    ''', [p for p, _ in RULES])
    print('【三类设备改后 u_size 分布】')
    for row in cur.fetchall():
        print(f"  {row['machine_model']:<12} u_size={row['u_size']}  数量={row['n']}")
    conn.close()


if __name__ == '__main__':
    main()
