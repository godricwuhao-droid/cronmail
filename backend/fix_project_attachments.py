"""
一次性数据迁移脚本：将合同 d00fbd55-c679-49c9-a2a8-14864c62a0c1 的附件记录
从 compute_service 迁移到 project 类型。

幂等设计：只处理 contract_type='compute_service' 的记录，
重复执行不会出错（已改过的记录 contract_type 已变成 'project'，不会被再次匹配）。

执行方式：
  cd /data/CronMail/backend
  python fix_project_attachments.py

如果是 K8s Pod 环境，需要先 exec 到 Pod 内执行：
  kubectl exec -n cronmail deploy/cronmail-backend-api -- python /app/fix_project_attachments.py
"""
import os
import sys
import shutil

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.core.database import SessionLocal

# ---- 配置 ----
CONTRACT_ID = "d00fbd55-c679-49c9-a2a8-14864c62a0c1"
OLD_CONTRACT_TYPE = "compute_service"
NEW_CONTRACT_TYPE = "project"
UPLOAD_BASE_DIR = "/app/uploads"

# compute_service「合同扫描件」item_id（前端之前硬编码的）
OLD_ITEM_ID = "1ec0d655-ada9-4114-9082-502fc373d1a4"
# project「合同扫描件」item_id（需要在数据库中动态查找）


def find_project_scan_item_id(db):
    """查找 project 类型下「合同扫描件」子项的 item_id"""
    result = db.execute(text("""
        SELECT ai.id
        FROM attachment_item ai
        JOIN attachment_category ac ON ac.id = ai.category_id
        WHERE ac.contract_type = 'project'
          AND ai.name = '合同扫描件'
          AND ai.is_active = 1
        LIMIT 1
    """))
    row = result.fetchone()
    if row is None:
        print("[ERROR] 未找到 project 类型下「合同扫描件」子项，请确认默认分类已初始化")
        sys.exit(1)
    return row[0]


def migrate_database(db, new_item_id):
    """迁移 attachment 和 attachment_status 表"""
    print("=" * 60)
    print("[DB] 开始数据库迁移...")

    # 1. 迁移 attachment 表
    result = db.execute(text("""
        SELECT id, file_path, item_id
        FROM attachment
        WHERE contract_id = :cid
          AND contract_type = :old_type
    """), {"cid": CONTRACT_ID, "old_type": OLD_CONTRACT_TYPE})
    attachments = result.fetchall()

    print(f"[DB] 找到 {len(attachments)} 条 attachment 记录需要迁移")

    for att_id, file_path, item_id in attachments:
        # 只处理 item_id 是 compute_service「合同扫描件」的记录
        if item_id != OLD_ITEM_ID:
            print(f"  [SKIP] attachment {att_id}: item_id={item_id} 不是旧 item_id，跳过")
            continue

        new_file_path = file_path.replace(
            f"{OLD_CONTRACT_TYPE}/{CONTRACT_ID}/",
            f"{NEW_CONTRACT_TYPE}/{CONTRACT_ID}/",
            1
        )

        db.execute(text("""
            UPDATE attachment
            SET contract_type = :new_type,
                item_id = :new_item_id,
                file_path = :new_path
            WHERE id = :id
        """), {
            "new_type": NEW_CONTRACT_TYPE,
            "new_item_id": new_item_id,
            "new_path": new_file_path,
            "id": att_id,
        })
        print(f"  [OK] attachment {att_id}: contract_type -> project, "
              f"item_id -> {new_item_id}, file_path updated")

    # 2. 迁移 attachment_status 表
    result2 = db.execute(text("""
        SELECT id, item_id
        FROM attachment_status
        WHERE contract_id = :cid
          AND contract_type = :old_type
    """), {"cid": CONTRACT_ID, "old_type": OLD_CONTRACT_TYPE})
    statuses = result2.fetchall()

    print(f"[DB] 找到 {len(statuses)} 条 attachment_status 记录需要迁移")

    for status_id, item_id in statuses:
        if item_id != OLD_ITEM_ID:
            print(f"  [SKIP] attachment_status {status_id}: item_id={item_id} 不是旧 item_id，跳过")
            continue

        db.execute(text("""
            UPDATE attachment_status
            SET contract_type = :new_type,
                item_id = :new_item_id
            WHERE id = :id
        """), {
            "new_type": NEW_CONTRACT_TYPE,
            "new_item_id": new_item_id,
            "id": status_id,
        })
        print(f"  [OK] attachment_status {status_id}: contract_type -> project, "
              f"item_id -> {new_item_id}")

    db.commit()
    print("[DB] 数据库迁移完成，已 commit")


def migrate_nfs():
    """迁移 NFS 文件目录"""
    print("=" * 60)
    print("[NFS] 开始文件目录迁移...")

    old_dir = os.path.join(UPLOAD_BASE_DIR, OLD_CONTRACT_TYPE, CONTRACT_ID)
    new_dir = os.path.join(UPLOAD_BASE_DIR, NEW_CONTRACT_TYPE, CONTRACT_ID)

    if not os.path.exists(old_dir):
        print(f"[NFS] 旧目录不存在: {old_dir}，跳过文件迁移")
        return

    if os.path.exists(new_dir):
        print(f"[NFS] 新目录已存在: {new_dir}")
        # 幂等：把旧目录中不在新目录的文件移过去
        for fname in os.listdir(old_dir):
            old_path = os.path.join(old_dir, fname)
            new_path = os.path.join(new_dir, fname)
            if os.path.exists(new_path):
                print(f"  [SKIP] 文件已存在: {new_path}，删除旧文件 {old_path}")
                if os.path.isfile(old_path):
                    os.remove(old_path)
                elif os.path.isdir(old_path):
                    shutil.rmtree(old_path)
            else:
                shutil.move(old_path, new_path)
                print(f"  [MOVE] {old_path} -> {new_path}")
        # 清理空的旧目录
        try:
            if not os.listdir(old_dir):
                os.rmdir(old_dir)
                print(f"  [RMDIR] 空目录已删除: {old_dir}")
        except OSError:
            pass
    else:
        # 新目录不存在，确保父目录存在后直接移动
        os.makedirs(os.path.dirname(new_dir), exist_ok=True)
        shutil.move(old_dir, new_dir)
        print(f"  [MOVE] {old_dir} -> {new_dir}")

    # 清理 compute_service 下可能为空的 CONTRACT_ID 目录
    cs_contract_dir = os.path.join(UPLOAD_BASE_DIR, OLD_CONTRACT_TYPE, CONTRACT_ID)
    if os.path.exists(cs_contract_dir):
        try:
            if not os.listdir(cs_contract_dir):
                os.rmdir(cs_contract_dir)
                print(f"  [RMDIR] 空目录已删除: {cs_contract_dir}")
        except OSError:
            pass

    print("[NFS] 文件目录迁移完成")


def main():
    print("=" * 60)
    print("项目：fix_project_attachments")
    print(f"合同 ID: {CONTRACT_ID}")
    print(f"迁移方向: {OLD_CONTRACT_TYPE} -> {NEW_CONTRACT_TYPE}")
    print("=" * 60)

    db = SessionLocal()
    try:
        new_item_id = find_project_scan_item_id(db)
        print(f"[INFO] project「合同扫描件」item_id = {new_item_id}")

        migrate_database(db, new_item_id)
        migrate_nfs()

        print("=" * 60)
        print("[DONE] 迁移全部完成！")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()
