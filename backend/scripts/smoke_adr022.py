"""
ADR-022 冒烟测试（临时 SQLite + TestClient，不部署、不动现有库）
验证：U 位结构化占位/冲突/解绑校验、机房不一致 400、U 越界 400、
列表/详情 rack_id/u_position/rack_name、points 的 u_cells 网格（含空格）

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


# ---------- 前置：机房 + 机架 ----------
r = client.post("/api/machine-rooms", json={"name": "上海一号机房", "code": "SH-01"})
check("POST /machine-rooms 201", r.status_code == 201, r.text)
room1 = r.json()

r = client.post("/api/machine-rooms", json={"name": "北京机房", "code": "BJ-01"})
check("POST /machine-rooms 2 (北京)", r.status_code == 201, r.text)
room2 = r.json()

r = client.post(f"/api/machine-rooms/{room1['id']}/racks", json={"name": "A-01", "capacity_u": 4})
check("POST racks A-01 (4U) 201", r.status_code == 201, r.text)
rack1 = r.json()

r = client.post(f"/api/machine-rooms/{room1['id']}/racks", json={"name": "A-02", "capacity_u": 42})
check("POST racks A-02 (42U) 201", r.status_code == 201, r.text)
rack2 = r.json()

r = client.post(f"/api/machine-rooms/{room2['id']}/racks", json={"name": "B-01", "capacity_u": 8})
check("POST racks B-01 (北京) 201", r.status_code == 201, r.text)
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
check("详情含 rack_id/u_position/rack_name",
      rental1.get("rack_id") == rack1["id"] and rental1.get("u_position") == 1 and rental1.get("rack_name") == "A-01",
      json.dumps({k: rental1.get(k) for k in ("rack_id", "u_position", "rack_name")}, ensure_ascii=False))

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
check("U 越界 400", r.status_code == 400 and "U 位超出范围" in r.json()["detail"], r.text)

r = client.post("/api/rentals", json={
    "machine_model": "X3", "machine_room_id": room1["id"], "rack_id": rack1["id"], "u_position": 0,
})
check("U=0 校验 422", r.status_code == 422, r.text)

r = client.post("/api/rentals", json={
    "machine_model": "X4", "machine_room_id": room1["id"], "u_position": 3,
})
check("只给 u_position 不给 rack_id 400", r.status_code == 400, r.text)

# 机房不一致：北京机架 B-01 + 上海机房
r = client.post("/api/rentals", json={
    "machine_model": "X5", "machine_room_id": room1["id"], "rack_id": rack_b["id"], "u_position": 2,
})
check("机架与机房不一致 400", r.status_code == 400 and "不属于" in r.json()["detail"], r.text)

# 重复占位 409
r = client.post("/api/rentals", json={
    "machine_model": "X6", "machine_room_id": room1["id"], "rack_id": rack1["id"], "u_position": 1,
})
check("重复占位 409", r.status_code == 409, r.text)
check("409 detail 含占用设备型号", "Dell R740" in r.json()["detail"], r.text)

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
check("列表项含 rack_id/u_position/rack_name",
      item.get("rack_id") == rack1["id"] and item.get("rack_name") == "A-01",
      json.dumps({k: item.get(k) for k in ("rack_id", "u_position", "rack_name")}, ensure_ascii=False))

r = client.get("/api/rentals", params={"rack_id": rack2["id"]})
check("列表按 rack_id 筛选(A-02)", r.json()["total"] == 1 and r.json()["items"][0]["rack_name"] == "A-02")

# ---------- points：u_cells 网格 ----------
r = client.get(f"/api/machine-rooms/{room1['id']}/points")
check("GET points 200", r.status_code == 200, r.text)
pts = r.json()
a1 = next(x for x in pts["racks"] if x["name"] == "A-01")
a2 = next(x for x in pts["racks"] if x["name"] == "A-02")

check("u_cells 长度=capacity_u", len(a1["u_cells"]) == 4 and len(a2["u_cells"]) == 42,
      f"A-01={len(a1['u_cells'])} A-02={len(a2['u_cells'])}")
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
check("A-02 U1=rental3", a2["u_cells"][0]["rental_id"] == rental3["id"])
check("A-02 其余 41 格全空", all(c["rental_id"] is None for c in a2["u_cells"][1:]))

# devices 前缀匹配逻辑保留（未定位 U 的在架设备仍按存量规则展示；此处无前缀匹配数据则为空）
check("devices 数组保留", "devices" in a1 and isinstance(a1["devices"], list))

# ---------- 汇总 ----------
print()
print("RESULT:", "ALL PASS" if all(ok) else f"{ok.count(False)} FAILED / {len(ok)}")
os.system(f"rm -rf {_tmp}")
raise SystemExit(0 if all(ok) else 1)
