"""数据迁移：将附件记录的 item_id 从兜底分类迁移到对应 project_type 的专属子项

执行方式：kubectl exec -n cronmail deploy/cronmail-backend-api -- python /app/migrate_attachment_items.py
"""

import sys
sys.path.insert(0, '/app')
from src.core.database import SessionLocal
from src.attachment.models import Attachment, AttachmentItem, AttachmentCategory, AttachmentStatus
from src.project.models import ProjectContract

db = SessionLocal()

try:
    # 1. 获取所有 project 类型的附件
    attachments = db.query(Attachment).filter(
        Attachment.contract_type == 'project'
    ).all()
    print(f"project 类型附件总数: {len(attachments)}")

    # 2. 建立 (old_item_id, project_type) → new_item_id 的映射
    # 先查每个附件对应的合同 project_type
    moved = 0
    skipped = 0

    for att in attachments:
        # 获取当前 item
        old_item = db.query(AttachmentItem).filter(
            AttachmentItem.id == att.item_id
        ).first()
        if not old_item:
            skipped += 1
            continue

        # 获取当前分类
        old_cat = db.query(AttachmentCategory).filter(
            AttachmentCategory.id == old_item.category_id
        ).first()
        if not old_cat or old_cat.project_type is not None:
            # 已经是专属分类，不需要迁移
            skipped += 1
            continue

        # 获取合同 project_type
        contract = db.query(ProjectContract).filter(
            ProjectContract.id == att.contract_id
        ).first()
        if not contract or not contract.project_type:
            skipped += 1
            continue

        pt = contract.project_type

        # 查找同 code/name 的专属分类
        new_cat = db.query(AttachmentCategory).filter(
            AttachmentCategory.contract_type == 'project',
            AttachmentCategory.project_type == pt,
            AttachmentCategory.code == old_cat.code,
            AttachmentCategory.is_active == True,
        ).first()
        if not new_cat:
            print(f"  WARN: 未找到专属分类 code={old_cat.code} project_type={pt}")
            skipped += 1
            continue

        # 查找同 name 的专属子项
        new_item = db.query(AttachmentItem).filter(
            AttachmentItem.category_id == new_cat.id,
            AttachmentItem.name == old_item.name,
            AttachmentItem.is_active == True,
        ).first()
        if not new_item:
            print(f"  WARN: 未找到专属子项 name={old_item.name} cat={new_cat.name}")
            skipped += 1
            continue

        # 迁移 item_id
        old_item_id = att.item_id
        att.item_id = new_item.id
        moved += 1
        print(f"  [{att.filename[:30]}] item {old_item_id[:8]} → {new_item.id[:8]} ({pt})")

        # 同时迁移 attachment_status
        status_records = db.query(AttachmentStatus).filter(
            AttachmentStatus.contract_type == 'project',
            AttachmentStatus.contract_id == att.contract_id,
            AttachmentStatus.item_id == old_item_id,
        ).all()
        for sr in status_records:
            sr.item_id = new_item.id
            print(f"    status item_id 同步迁移")

    db.commit()
    print(f"\n=== 迁移完成 ===")
    print(f"迁移: {moved}, 跳过: {skipped}")

finally:
    db.close()
