"""
ADR-022 冒烟测试（临时 SQLite + TestClient，不部署、不动现有库）
验证：U 位结构化占位/冲突/解绑校验、机房不一致 400、U 越界 400、
列表/详情 rack_id/u_position/rack_name、point-map 的 u_cells 网格（含空格）

ADR-026 适配：
- 机架创建走 排→机柜→机架 三层（旧 /machine-rooms/{id}/racks 已删除）
- points 改为 point-map（rows→cabinets→racks→u_cells 嵌套）

ADR-028 适配：
- rack_name 字段名不变，值改为纯机架名（去掉「机柜名/」前缀）
- U 越界 400 文案改为「{n}U 设备无法放置于 … 超出机架容量（占用 Ux~Uy）」
- 重复占位 409 文案改为「与 {机架} 的 {型号}（Ux）位置冲突，所选 Ux~Uy 重叠」
- 新增 u_size 默认 1 透出 + 多 U 设备 u_cells 区间标记断言

运行方式（backend 目录下）：
    venv/bin/python scripts/smoke_adr022.py
"""
import json
import os
import sys
import tempfile

# 脚本位于 backend/scripts/，将 backend 根加入 sys.path 以 import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp(prefix="cronmail_adr022_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"

from fastapi.testclient import TestClient
import main
from src.core.database import Base, engine

Base.metadata.create_all(bind=engine)
client = TestClient(main.app)

ok = []


def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    ok.append(cond)


# ---------- 前置：机房 + 排 + 机柜 + 机架（ADR-026 三层） ----------
r = client.post("/api/machine-rooms", json={"name": "上海一号机房", "code": "SH-01"})
check("POST /machine-rooms 201", r.status_code == 201, r.text)
room1 = r.json()

r = client.post("/api/machine-rooms", json={"name": "北京机房", "code": "BJ-01"})
check("POST /machine-rooms 2 (北京)", r.status_code == 201, r.text)
room2 = r.json()

r = client.post(f"/api/machine-rooms/{room1['id']}/rows", json={"name": "A排"})
check("POST rows A排 201", r.status_code == 201, r.text)
row1 = r.json()

r = client.post(f"/api/machine-rooms/{room1['id']}/rows/{row1['id']}/cabinets", json={"name": "A-01"})
check("POST cabinets A-01 201", r.status_code == 201, r.text)
cab1 = r.json()

r = client.post(f"/api/machine-rooms/{room1['id']}/rows/{row1['id']}/cabinets", json={"name": "A-02"})
check("POST cabinets A-02 201", r.status_code == 201, r.text)
cab2 = r.json()

r = client.post(f"/api/cabinets/{cab1['id']}/racks", json={"name": "A-01-4U", "capacity_u": 4})
check("POST racks A-01-4U (4U) 201", r.status_code == 201, r.text)
rack1 = r.json()

r = client.post(f"/api/cabinets/{cab2['id']}/racks", json={"name": "A-02-42U", "capacity_u": 42})
check("POST racks A-02-42U (42U) 201", r.status_code == 201, r.text)
rack2 = r.json()

r = client.post(f"/api/machine-rooms/{room2['id']}/rows", json={"name": "B排"})
check("POST rows B排 201", r.status_code == 201, r.text)
row_b = r.json()

r = client.post(f"/api/machine-rooms/{room2['id']}/rows/{row_b['id']}/cabinets", json={"name": "B-01"})
check("POST cabinets B-01 (北京) 201", r.status_code == 201, r.text)
cab_b = r.json()

r = client.post(f"/api/cabinets/{cab_b['id']}/racks", json={"name": "B-01-8U", "capacity_u": 8})
check("POST racks B-01-8U (北京) 201", r.status_code == 201, r.text)
rack_b = r.json()

# ---------- 正常占位 ----------
r = client.post("/api/rentals", json={
    "machine_model": "Dell R740",
    "machine_room_id": room1["id"],
    "rack_id": rack1["id"],
    "u_position": 1,
    "private_ip": "192.168.180.170",
    "remark": "捷易（带宽）",
})
check("POST /rentals 占位 U1 201", r.status_code == 201, r.text)
rental1 = r.json()
check("详情含 rack_id/u_position/rack_name(纯机架名)/u_size=1",
      rental1.get("rack_id") == rack1["id"] and rental1.get("u_position") == 1
      and rental1.get("rack_name") == "A-01-4U" and rental1.get("u_size") == 1,
      json.dumps({k: rental1.get(k) for k in ("rack_id", "u_position", "rack_name", "u_size")}, ensure_ascii=False))

# 只给 rack_id 不给 u_position（在架未定位）合法
r = client.post("/api/rentals", json={
    "machine_model": "Dell R750",
    "machine_room_id": room1["id"],
    "rack_id": rack1["id"],
})
check("POST /rentals 只给 rack_id 201", r.status_code == 201, r.text)
rental2 = r.json()
check("未定位 U 时 u_position=null", rental2.get("u_position") is None and rental2.get("rack_id") == rack1["id"])

# ---------- 校验错误 ----------
r = client.post("/api/rentals", json={
    "machine_model": "X1", "machine_room_id": room1["id"], "rack_id": 9999, "u_position": 1,
})
check("机架不存在 404", r.status_code == 404, r.text)

r = client.post("/api/rentals", json={
    "machine_model": "X2", "machine_room_id": room1["id"], "rack_id": rack1["id"], "u_position": 5,
})
check("U 越界 400", r.status_code == 400 and "超出机架容量" in r.json()["detail"], r.text)

r = client.post("/api/rentals", json={
    "machine_model": "X3", "machine_room_id": room1["id"], "rack_id": rack1["id"], "u_position": 0,
})
check("U=0 校验 422", r.status_code == 422, r.text)

r = client.post("/api/rentals", json={
    "machine_model": "X4", "machine_room_id": room1["id"], "u_position": 3,
})
check("只给 u_position 不给 rack_id 400", r.status_code == 400, r.text)

# 机房不一致：北京机架 B-01-8U + 上海机房
r = client.post("/api/rentals", json={
    "machine_model": "X5", "machine_room_id": room1["id"], "rack_id": rack_b["id"], "u_position": 2,
})
check("机架与机房不一致 400", r.status_code == 400 and "不属于" in r.json()["detail"], r.text)

# 重复占位 409
r = client.post("/api/rentals", json={
    "machine_model": "X6", "machine_room_id": room1["id"], "rack_id": rack1["id"], "u_position": 1,
})
check("重复占位 409", r.status_code == 409, r.text)
check("409 detail 含占用设备型号+区间", "Dell R740" in r.json()["detail"] and "位置冲突" in r.json()["detail"], r.text)

# 同 U 不同机架合法
r = client.post("/api/rentals", json={
    "machine_model": "X7", "machine_room_id": room1["id"], "rack_id": rack2["id"], "u_position": 1,
})
check("同 U 不同机架 201", r.status_code == 201, r.text)
rental3 = r.json()

# ---------- 更新路径 ----------
# 更新到已占 U 位 → 409
r = client.put(f"/api/rentals/{rental3['id']}", json={"rack_id": rack1["id"], "u_position": 1})
check("PUT 移到已占 U 位 409", r.status_code == 409, r.text)

# 更新自身 U 位（不变）→ 200
r = client.put(f"/api/rentals/{rental1['id']}", json={"rack_id": rack1["id"], "u_position": 1})
check("PUT 自身占位不变 200", r.status_code == 200, r.text)

# 更新 U 越界 → 400
r = client.put(f"/api/rentals/{rental1['id']}", json={"u_position": 99})
check("PUT U 越界 400", r.status_code == 400, r.text)

# 解绑机架：rack_id=null → u_position 同步置 null
r = client.put(f"/api/rentals/{rental1['id']}", json={"rack_id": None})
check("解绑机架 200", r.status_code == 200, r.text)
check("解绑后 rack/u 均 null", r.json().get("rack_id") is None and r.json().get("u_position") is None,
      json.dumps({k: r.json().get(k) for k in ("rack_id", "u_position")}, ensure_ascii=False))

# 解绑机架同时指定 U 位 → 400
r = client.put(f"/api/rentals/{rental2['id']}", json={"rack_id": None, "u_position": 2})
check("解绑机架同时指定 U 位 400", r.status_code == 400, r.text)

# 重新占位 U2
r = client.put(f"/api/rentals/{rental1['id']}", json={"rack_id": rack1["id"], "u_position": 2})
check("重新占位 U2 200", r.status_code == 200 and r.json()["u_position"] == 2, r.text)

# ---------- 列表：rack_id 筛选 + 字段 ----------
r = client.get("/api/rentals", params={"rack_id": rack1["id"]})
check("列表按 rack_id 筛选", r.status_code == 200 and r.json()["total"] == 2, r.text)
item = r.json()["items"][0]
check("列表项含 rack_id/u_position/rack_name(纯机架名)",
      item.get("rack_id") == rack1["id"] and item.get("rack_name") == "A-01-4U",
      json.dumps({k: item.get(k) for k in ("rack_id", "u_position", "rack_name")}, ensure_ascii=False))

r = client.get("/api/rentals", params={"rack_id": rack2["id"]})
check("列表按 rack_id 筛选(A-02)", r.json()["total"] == 1 and r.json()["items"][0]["rack_name"] == "A-02-42U")

# ---------- 多 U 设备（ADR-028） ----------
# 2U 设备放 U2（占用 U2~U3）
r = client.post("/api/rentals", json={
    "machine_model": "Supermicro 2U", "machine_room_id": room1["id"],
    "rack_id": rack2["id"], "u_position": 2, "u_size": 2,
})
check("POST /rentals 2U 设备 201", r.status_code == 201 and r.json().get("u_size") == 2, r.text)
rental4 = r.json()

# 1U 设备放 U3 → 与 U2~U3 区间相交 → 409
r = client.post("/api/rentals", json={
    "machine_model": "X8", "machine_room_id": room1["id"], "rack_id": rack2["id"], "u_position": 3,
})
check("1U 与 2U 区间重叠 409", r.status_code == 409 and "位置冲突" in r.json()["detail"], r.text)

# ---------- point-map：u_cells 网格（ADR-026 rows→cabinets→racks 嵌套） ----------
r = client.get(f"/api/machine-rooms/{room1['id']}/point-map")
check("GET point-map 200", r.status_code == 200, r.text)
pts = r.json()
check("point-map rows 层级", len(pts["rows"]) == 1 and pts["rows"][0]["name"] == "A排"
      and len(pts["rows"][0]["cabinets"]) == 2, json.dumps([x["name"] for x in pts["rows"]], ensure_ascii=False))
cab_items = {c["name"]: c for c in pts["rows"][0]["cabinets"]}
a1 = next(x for x in cab_items["A-01"]["racks"] if x["name"] == "A-01-4U")
a2 = next(x for x in cab_items["A-02"]["racks"] if x["name"] == "A-02-42U")
check("机柜透出 power_on", cab_items["A-01"]["power_on"] is True and cab_items["A-02"]["power_on"] is True)

check("u_cells 长度=capacity_u", len(a1["u_cells"]) == 4 and len(a2["u_cells"]) == 42,
      f"A-01-4U={len(a1['u_cells'])} A-02-42U={len(a2['u_cells'])}")
check("u_cells u 从 1 开始连续", [c["u"] for c in a1["u_cells"]] == list(range(1, 5)))

# rental1 现在在 U2，U1 应为空
check("U1 空格设备字段 null",
      a1["u_cells"][0]["rental_id"] is None and a1["u_cells"][0]["machine_model"] is None
      and a1["u_cells"][0]["private_ip"] is None and a1["u_cells"][0]["status"] is None,
      json.dumps(a1["u_cells"][0], ensure_ascii=False))
cell2 = a1["u_cells"][1]
check("U2 格子=rental1",
      cell2["rental_id"] == rental1["id"] and cell2["machine_model"] == "Dell R740"
      and cell2["private_ip"] == "192.168.180.170" and cell2["remark"] == "捷易（带宽）",
      json.dumps(cell2, ensure_ascii=False))
check("U3/U4 空格", a1["u_cells"][2]["rental_id"] is None and a1["u_cells"][3]["rental_id"] is None)
check("A-02-42U U1=rental3", a2["u_cells"][0]["rental_id"] == rental3["id"])
check("A-02-42U U2/U3=2U 设备 rental4（区间标记，ADR-028）",
      a2["u_cells"][1]["rental_id"] == rental4["id"] and a2["u_cells"][2]["rental_id"] == rental4["id"]
      and a2["u_cells"][1]["machine_model"] == "Supermicro 2U",
      json.dumps([a2["u_cells"][1], a2["u_cells"][2]], ensure_ascii=False))
check("A-02-42U U4 起其余 39 格全空", all(c["rental_id"] is None for c in a2["u_cells"][3:]))

# rental2 只给 rack_id 未定位 U → 进 unlocated
check("unlocated 含未定位设备", any(d["rental_id"] == rental2["id"] for d in pts["unlocated"]),
      json.dumps(pts["unlocated"], ensure_ascii=False))

# ---------- locations 级联选择源（ADR-026） ----------
r = client.get(f"/api/machine-rooms/{room1['id']}/locations")
check("GET locations 200", r.status_code == 200, r.text)
locs = r.json()
check("locations 三级嵌套",
      len(locs["rows"]) == 1 and locs["rows"][0]["name"] == "A排"
      and [c["name"] for c in locs["rows"][0]["cabinets"]] == ["A-01", "A-02"]
      and [x["name"] for x in locs["rows"][0]["cabinets"][0]["racks"]] == ["A-01-4U"]
      and locs["rows"][0]["cabinets"][0]["racks"][0]["capacity_u"] == 4,
      json.dumps(locs, ensure_ascii=False))
check("locations 轻量（无 note/power_on）",
      "note" not in locs["rows"][0] and "power_on" not in locs["rows"][0]["cabinets"][0])

print()
print("RESULT:", "ALL PASS" if all(ok) else f"{ok.count(False)} FAILED / {len(ok)}")
os.system(f"rm -rf {_tmp}")
raise SystemExit(0 if all(ok) else 1)
