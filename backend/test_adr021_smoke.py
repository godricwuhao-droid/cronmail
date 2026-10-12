"""
ADR-021 冒烟测试（临时 SQLite，不部署、不动现有库）
验证：机房/机架 CRUD、409 删除保护、点位图、未上架列表、
rental 机房筛选、machine_room_name 填充、change_log 自动记录
"""
import json
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="cronmail_adr021_")
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


# ---------- 机房 CRUD ----------
r = client.post("/api/machine-rooms", json={"name": "上海一号机房", "code": "SH-01", "address": "上海市", "note": "n1"})
check("POST /machine-rooms 201", r.status_code == 201, r.text)
room1 = r.json()

r = client.post("/api/machine-rooms", json={"name": "上海一号机房", "code": "SH-02"})
check("机房重名 400", r.status_code == 400, r.text)

r = client.post("/api/machine-rooms", json={"name": "北京机房", "code": "SH-01"})
check("机房重码 400", r.status_code == 400, r.text)

r = client.get("/api/machine-rooms", params={"search": "上海"})
check("GET /machine-rooms 搜索", r.status_code == 200 and r.json()["total"] == 1, r.text)

r = client.put(f"/api/machine-rooms/{room1['id']}", json={"note": "updated"})
check("PUT /machine-rooms/{id}", r.status_code == 200 and r.json()["note"] == "updated", r.text)

# ---------- 机架 CRUD ----------
r = client.post(f"/api/machine-rooms/{room1['id']}/racks", json={"name": "A-01", "capacity_u": 42})
check("POST racks 201", r.status_code == 201, r.text)
rack1 = r.json()

r = client.post(f"/api/machine-rooms/{room1['id']}/racks", json={"name": "A-01"})
check("机架重名 400", r.status_code == 400, r.text)

r = client.post("/api/machine-rooms/9999/racks", json={"name": "B-01"})
check("机房不存在建机架 404", r.status_code == 404, r.text)

r = client.put(f"/api/machine-rooms/{room1['id']}/racks/{rack1['id']}", json={"capacity_u": 24})
check("PUT racks/{id}", r.status_code == 200 and r.json()["capacity_u"] == 24, r.text)

# ---------- 设备 + 机房关联 ----------
r = client.post("/api/rentals", json={"machine_model": "Dell R740", "machine_room_id": room1["id"], "rack_location": "A-01-05-U12", "memory_gb": 64})
check("POST /rentals 带机房 201", r.status_code == 201, r.text)
rental1 = r.json()
check("详情含 machine_room_name", rental1.get("machine_room_name") == "上海一号机房", json.dumps({k: rental1.get(k) for k in ("machine_room_id", "machine_room_name")}, ensure_ascii=False))

r = client.post("/api/rentals", json={"machine_model": "Dell R750", "machine_room_id": 9999})
check("机房不存在建设备 404", r.status_code == 404, r.text)

r = client.post("/api/rentals", json={"machine_model": "In-Stock R730", "rack_location": "仓库货架3"})
check("POST /rentals 未上架 201", r.status_code == 201, r.text)
rental2 = r.json()
check("未上架 machine_room_name=null", rental2.get("machine_room_name") is None)

# ---------- 列表筛选 ----------
r = client.get("/api/rentals", params={"machine_room_id": room1["id"]})
check("列表按机房筛选", r.status_code == 200 and r.json()["total"] == 1 and r.json()["items"][0]["machine_room_name"] == "上海一号机房", r.text)

r = client.get("/api/rentals", params={"warehoused": True})
check("列表未上架筛选", r.status_code == 200 and r.json()["total"] == 1 and r.json()["items"][0]["id"] == rental2["id"], r.text)

# ---------- 点位图 ----------
r = client.get(f"/api/machine-rooms/{room1['id']}/points")
check("GET points 200", r.status_code == 200, r.text)
pts = r.json()
check("points.room", pts["room"]["name"] == "上海一号机房")
check("points.racks 设备归属", len(pts["racks"]) == 1 and len(pts["racks"][0]["devices"]) == 1 and pts["racks"][0]["devices"][0]["rental_id"] == rental1["id"], json.dumps(pts["racks"], ensure_ascii=False))
check("points.warehoused", len(pts["warehoused"]) == 1 and pts["warehoused"][0]["rental_id"] == rental2["id"])

r = client.get("/api/machine-rooms/9999/points")
check("points 机房不存在 404", r.status_code == 404)

r = client.get("/api/machine-rooms/warehoused")
check("GET /warehoused", r.status_code == 200 and r.json()["total"] == 1, r.text)

# ---------- change_log 自动记录 ----------
from src.core.database import SessionLocal
from src.contract.models import ChangeLog

db = SessionLocal()
before = db.query(ChangeLog).filter(ChangeLog.target_type == "rental", ChangeLog.target_id == rental1["id"]).count()
db.close()

# 无变化更新 → 不写日志
r = client.put(f"/api/rentals/{rental1['id']}", json={"memory_gb": 64})
check("无变化更新 200", r.status_code == 200, r.text)
db = SessionLocal()
after_noop = db.query(ChangeLog).filter(ChangeLog.target_type == "rental", ChangeLog.target_id == rental1["id"]).count()
db.close()
check("无变化不写日志", after_noop == before, f"before={before} after={after_noop}")

# 多字段变化 + root_password → 写结构化 JSON
r = client.put(f"/api/rentals/{rental1['id']}", json={"memory_gb": 128, "root_password": "NewPass123!", "remark": "升级内存"})
check("有变化更新 200", r.status_code == 200, r.text)
db = SessionLocal()
logs = db.query(ChangeLog).filter(ChangeLog.target_type == "rental", ChangeLog.target_id == rental1["id"]).order_by(ChangeLog.created_at.desc()).all()
db.close()
check("有变化写日志", len(logs) == before + 1, f"count={len(logs)}")
content = json.loads(logs[0].content)
fields = {d["field"]: d for d in content}
check("diff 字段正确", set(fields) == {"内存(GB)", "Root密码", "备注"}, json.dumps(content, ensure_ascii=False))
check("内存 diff 值", fields["内存(GB)"]["old"] == 64 and fields["内存(GB)"]["new"] == 128)
check("密码脱敏", fields["Root密码"]["old"] == "***" and fields["Root密码"]["new"] == "***")

# 解绑机房（machine_room_id=null）→ 记录所属机房变化 + 进入未上架
r = client.put(f"/api/rentals/{rental1['id']}", json={"machine_room_id": None})
check("解绑机房 200", r.status_code == 200 and r.json()["machine_room_name"] is None, r.text)
db = SessionLocal()
log2 = db.query(ChangeLog).filter(ChangeLog.target_type == "rental", ChangeLog.target_id == rental1["id"]).order_by(ChangeLog.created_at.desc()).first()
db.close()
c2 = json.loads(log2.content)
check("解绑记录所属机房", c2 == [{"field": "所属机房", "old": room1["id"], "new": None}], json.dumps(c2, ensure_ascii=False))
r = client.get("/api/rentals", params={"warehoused": True})
check("解绑后进入未上架", r.json()["total"] == 2)

# ---------- 删除保护 409 ----------
# 重新绑定设备到机房
client.put(f"/api/rentals/{rental1['id']}", json={"machine_room_id": room1["id"]})
r = client.delete(f"/api/machine-rooms/{room1['id']}")
check("有机房设备删机房 409", r.status_code == 409, r.text)

r = client.delete(f"/api/machine-rooms/{room1['id']}/racks/{rack1['id']}")
check("有机架设备删机架 409", r.status_code == 409, r.text)

# 解绑后可删
client.put(f"/api/rentals/{rental1['id']}", json={"machine_room_id": None})
r = client.delete(f"/api/machine-rooms/{room1['id']}/racks/{rack1['id']}")
check("空机架可删", r.status_code == 200, r.text)
r = client.delete(f"/api/machine-rooms/{room1['id']}")
check("无设备机房可删", r.status_code == 200, r.text)
r = client.delete("/api/machine-rooms/9999")
check("删不存在机房 404", r.status_code == 404)

print()
print("RESULT:", "ALL PASS" if all(ok) else f"{ok.count(False)} FAILED / {len(ok)}")
os.system(f"rm -rf {_tmp}")
raise SystemExit(0 if all(ok) else 1)
